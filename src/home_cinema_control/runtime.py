import json
import logging
import logging.handlers
import os
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

import psutil

from home_cinema_control.web.runtime_config import _LANG_PATH, load_runtime_config
from home_cinema_control.web.static_assets import load_json_asset
from home_cinema_control.config.manager import is_configured, save_effective_config
from home_cinema_control.media_servers.common.provider import MediaServerProviderFactory
from home_cinema_control.playback.diagnostics import PlaybackDiagnostic
from home_cinema_control.playback.dispatch import bridge_playback_is_active


@dataclass(frozen=True)
class RuntimePaths:
    base_dir: Path
    config_file: Path
    log_file: Path


def build_runtime_paths(base_dir: str | Path, config_file: str | Path) -> RuntimePaths:
    base_dir = Path(base_dir)
    return RuntimePaths(
        base_dir=base_dir,
        config_file=Path(config_file),
        log_file=base_dir / "emby_xnoppo_client_logging.log",
    )


_LOG_LEVELS = {0: logging.CRITICAL, 1: logging.INFO, 2: logging.DEBUG}


def _resolve_log_level(value: object) -> int:
    return _LOG_LEVELS.get(value, logging.CRITICAL)


def configure_logging(config: dict, log_file: str | Path) -> None:
    # One log level drives both sinks: the rotating file (which feeds the web
    # logs screen) and the container console. 0=off, 1=info, 2=debug.
    level_setting = config["app"].get("log_level", 0)
    level = _resolve_log_level(level_setting)
    # Debug is verbose, so its file rotates sooner.
    max_bytes = 5 * 1024 * 1024 if level == logging.DEBUG else 50 * 1024 * 1024

    _configure_rotating_logging(log_file, level=level, max_bytes=max_bytes)

    if level_setting == 0:
        print(
            "Logging configured with app.log_level=0; normal application logs are disabled. "
            "Set app.log_level to 1 for info logs or 2 for debug logs.",
            flush=True,
        )

    logging.getLogger("websocket").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


class JsonLinesFormatter(logging.Formatter):
    """One JSON object per log record, so the web UI can render colored,
    severity-filterable log lines instead of a plain text dump.

    Exception tracebacks are folded into `message` (rather than left as a
    separate trailing block) so each record still maps to exactly one line.
    """

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"
        return json.dumps(
            {
                "timestamp": self.formatTime(record, "%d/%m/%Y %I:%M:%S %p"),
                "level": record.levelname,
                "logger": record.name,
                "message": message,
            },
            ensure_ascii=False,
        )


def _configure_rotating_logging(
        log_file: str | Path,
        *,
        level: int,
        max_bytes: int,
) -> None:
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        mode="a",
        maxBytes=max_bytes,
        backupCount=2,
        encoding="utf-8",
        delay=False,
    )
    file_handler.setFormatter(JsonLinesFormatter())

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s: %(message)s",
            datefmt="%d/%m/%Y %I:%M:%S %p",
        )
    )

    logging.basicConfig(level=level, handlers=[file_handler, console_handler], force=True)


class HomeCinemaControlRuntime:
    def __init__(
        self,
        *,
        paths: RuntimePaths,
        version: str,
            media_server_provider_factory=None,
        exit_process=os._exit,
    ):
        self.paths = paths
        self.version = version
        self._media_server_provider_factory = (
                media_server_provider_factory or MediaServerProviderFactory()
        )
        self._exit_process = exit_process
        self.playback_listener = None
        self.playback_listener_thread = None

    def load_config(self) -> dict:
        return load_runtime_config(str(self.paths.config_file), version=self.version)

    def load_language(self, config: dict | None = None) -> dict:
        if config is None:
            config = self.load_config()

        language = config["app"]["language"]
        return load_json_asset(str(_LANG_PATH / language / "lang.json"))

    def save_config(self, config: dict) -> None:
        save_effective_config(self.paths.config_file, config)
        self.update_active_config(config)

    def update_active_config(self, config: dict) -> None:
        if self.playback_listener is None:
            return

        self.playback_listener.update_config(config)

    def start_playback_listener_if_configured(self) -> bool:
        config = self.load_config()
        if not is_configured(config):
            logging.info(
                "Config is not complete yet. Web UI is available; "
                "media-server playback listener will not start."
            )
            return False

        language = self.load_language(config)
        self.start_playback_listener(config=config, language=language)
        return True

    def start_playback_listener(self, *, config: dict, language: dict) -> None:
        provider = self._media_server_provider_factory.create(config)
        self.playback_listener = provider.create_playback_listener(
            config=config,
            config_file=str(self.paths.config_file),
            language=language,
        )

        self.playback_listener_thread = threading.Thread(
            target=_run_playback_listener,
            args=(self.playback_listener,),
            daemon=True,
        )
        self.playback_listener_thread.start()

    def has_active_playback(self) -> bool:
        if self.playback_listener is None:
            return False

        playstate = getattr(self.playback_listener.playback_state, "playstate", None)
        return bridge_playback_is_active(playstate)

    def stop_playback_listener(self) -> None:
        """Cleanly stop the current listener, if any.

        If playback is active, waits for its normal finish/cleanup flow (TV/AV
        restore, media-server reporting) to actually complete first — never
        tears down the websocket while something is still in progress.
        """
        if self.playback_listener is None:
            return

        app_service = getattr(
            self.playback_listener, "playback_application_service", None
        )
        if app_service is not None:
            app_service.stop_active_playback_and_wait()

        self.playback_listener.stop()
        if self.playback_listener_thread is not None:
            self.playback_listener_thread.join(timeout=10)

        self.playback_listener = None
        self.playback_listener_thread = None

    def restart_playback_listener(self) -> bool:
        """The only safe way to make the running listener match the current
        config after a provider switch or re-login: stop_playback_listener(),
        then start fresh from the (now-updated) config on disk. Replaces a
        bare start_playback_listener_if_configured() call at any call site
        that might already have a listener running — that combination used to
        leave the old listener's thread/connection orphaned.
        """
        self.stop_playback_listener()
        return self.start_playback_listener_if_configured()

    def get_state(self) -> dict:
        status = {"Version": self.version}

        try:
            state = self.playback_listener.playback_state
            status["Playstate"] = state.playstate
            active_session = getattr(state, "active_session", None)
            status["ActiveSession"] = (
                active_session.to_runtime_status()
                if active_session is not None
                else None
            )
            last_diagnostic = getattr(state, "last_diagnostic", None)
            status["LastDiagnostic"] = (
                last_diagnostic.to_dict() if last_diagnostic is not None else None
            )
            history = getattr(state, "diagnostic_history_status", None)
            status["DiagnosticHistory"] = history(limit=5) if callable(history) else []
        except AttributeError:
            status["Playstate"] = "Not_Connected"
            status["ActiveSession"] = None
            status["LastDiagnostic"] = None
            status["DiagnosticHistory"] = []

        status["cpu_perc"] = psutil.cpu_percent()
        status["mem_perc"] = psutil.virtual_memory().percent
        logging.debug(psutil.virtual_memory().percent)
        logging.debug(status)
        return status

    def set_last_diagnostic(self, diagnostic: PlaybackDiagnostic) -> None:
        try:
            state = self.playback_listener.playback_state
            record = getattr(state, "record_diagnostic", None)
            if callable(record):
                record(diagnostic)
            else:
                state.last_diagnostic = diagnostic
        except AttributeError:
            pass

    def clear_last_diagnostic(self) -> None:
        try:
            state = self.playback_listener.playback_state
            clear = getattr(state, "clear_last_diagnostic", None)
            if callable(clear):
                clear()
            else:
                state.last_diagnostic = None
        except AttributeError:
            pass

    def get_support_summary(self) -> dict:
        state = self.get_state()
        return {
            "version": state.get("Version"),
            "playstate": state.get("Playstate"),
            "active_session": state.get("ActiveSession"),
            "last_diagnostic": state.get("LastDiagnostic"),
            "diagnostic_history": state.get("DiagnosticHistory", []),
            "resources": {
                "cpu_perc": state.get("cpu_perc"),
                "mem_perc": state.get("mem_perc"),
            },
        }

    def start_movie(self, data: dict) -> None:
        if self.playback_listener is None:
            raise RuntimeError("Playback listener is not running")

        self.playback_listener.play_from_command(data)

    def restart_process(self) -> None:
        # The process is about to exit (Docker's restart policy brings it back
        # up, reading config fresh) — there is nothing to "reconnect" here,
        # only to stop cleanly first. The previous version called
        # playback_listener.run() right after stop(), which reconnects and
        # blocks on run_forever(): the process likely never reached
        # _exit_process at all when a listener was running.
        logging.info("Restarting process")
        try:
            self.stop_playback_listener()
        except Exception:
            logging.exception(
                "Failed to stop the playback listener during process restart"
            )
        self._exit_process(0)


def _run_playback_listener(listener) -> None:
    logging.info("Playback listener thread: starting")
    listener.run()
    logging.info("Playback listener thread: finished")
