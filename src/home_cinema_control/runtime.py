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


def configure_logging(config: dict, log_file: str | Path) -> None:
    debug_level = config["app"]["log_level"]

    if debug_level == 0:
        logging.basicConfig(
            format="%(asctime)s %(levelname)s: %(message)s",
            datefmt="%d/%m/%Y %I:%M:%S %p",
            level=logging.CRITICAL,
            handlers=[logging.StreamHandler(sys.stdout)],
            force=True,
        )
        print(
            "Logging configured with app.log_level=0; normal application logs are disabled. "
            "Set app.log_level to 1 for info logs or 2 for debug logs.",
            flush=True,
        )
    elif debug_level == 1:
        _configure_rotating_logging(log_file, level=logging.INFO, max_bytes=50 * 1024 * 1024)
    elif debug_level == 2:
        _configure_rotating_logging(log_file, level=logging.DEBUG, max_bytes=5 * 1024 * 1024)

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


def _configure_rotating_logging(log_file: str | Path, *, level: int, max_bytes: int) -> None:
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
        logging.info("Restarting process")
        try:
            if self.playback_listener is not None:
                self.playback_listener.stop()
                self.playback_listener.run()
        except Exception:
            pass
        self._exit_process(0)


def _run_playback_listener(listener) -> None:
    logging.info("Playback listener thread: starting")
    listener.run()
    logging.info("Playback listener thread: finished")
