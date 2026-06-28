import logging
import threading
import time
from collections.abc import Callable

from websocket import WebSocketConnectionClosedException

from home_cinema_control import __version__
from home_cinema_control.config.manager import (
    active_media_server_config,
    load_effective_config,
    save_effective_config,
)
from home_cinema_control.devices.oppo.playback_command_control import (
    create_oppo_playback_command_control,
)
from home_cinema_control.media_servers.common.constants import DEVICE_ID
from home_cinema_control.media_servers.common.websocket_events import (
    MediaServerWebsocketEventKind,
)
from home_cinema_control.playback.application import PlaybackApplicationService
from home_cinema_control.playback.dispatch import PlaybackIntentDispatcher
from home_cinema_control.playback.state import BridgePlaybackState
from home_cinema_control.telemetry.service import TelemetryService


class MediaServerWebsocketListener:
    def __init__(
        self,
        *,
        provider_name: str,
        session_attribute_name: str,
        session_factory: Callable,
        command_handler_factory: Callable,
        session_monitor_factory: Callable,
        websocket_event_mapper_factory: Callable,
        session_subscription_message: str,
        websocket_app_factory: Callable,
        websocket_uri_factory: Callable[[str, str], str],
        websocket_headers_factory: Callable[[str], dict] | None = None,
        config=None,
        config_file: str = "",
        language=None,
        playback_services=None,
    ):
        self._provider_name = provider_name
        self._session_attribute_name = session_attribute_name
        self._session_factory = session_factory
        self._command_handler_factory = command_handler_factory
        self._session_monitor_factory = session_monitor_factory
        self._websocket_event_mapper_factory = websocket_event_mapper_factory
        self._session_subscription_message = session_subscription_message
        self._websocket_app_factory = websocket_app_factory
        self._websocket_uri_factory = websocket_uri_factory
        self._websocket_headers_factory = websocket_headers_factory

        self.config = config
        self.media_server_session = None
        setattr(self, self._session_attribute_name, None)
        self.playback_state: BridgePlaybackState | None = None
        self.config_file = config_file
        self.language = language
        self._playback_services = playback_services
        self._ws_app = None
        self.playback_application_service = None
        self.playback_command_handler = None
        self._session_monitor = None
        self._websocket_event_mapper = None
        # After a full media-server restart the websocket reconnects before the
        # REST API finishes loading (503 "server is loading"), so capability
        # registration must retry off the websocket read thread until it sticks.
        self._capability_retry_delays = (2, 5, 10, 20, 30)
        self._sleep = time.sleep
        logging.info("%s websocket init", self._provider_name)

    def stop(self):
        logging.info("%s websocket stop", self._provider_name)
        if self._ws_app:
            self._ws_app.close()

    def reload_config(self):
        logging.info("Reloading config")
        config = load_effective_config(self.config_file)
        self.update_config(config)
        return config

    def update_config(self, config: dict) -> None:
        self.config = config
        if self.media_server_session:
            self.media_server_session.config = config

    def play_from_command(self, data):
        event = self._websocket_event_mapper.map_play_payload(data)
        if event.kind != MediaServerWebsocketEventKind.PLAYBACK_INTENT:
            logging.debug(
                "%s direct play command ignored | type=%s",
                self._provider_name,
                event.raw_type,
            )
            return
        self.playback_command_handler.handle_playback_intent(event.playback_intent)

    def on_message(self, _ws, msg):
        event = self._websocket_event_mapper.map(msg)

        if event.kind == MediaServerWebsocketEventKind.SESSIONS_UPDATE:
            logging.info(
                "%s websocket message: Sessions | playstate=%s | sessions=%s",
                self._provider_name,
                self.playback_state.playstate,
                len(event.sessions or []),
            )
        else:
            logging.info(
                "%s websocket message: %s | playstate=%s",
                self._provider_name,
                event.raw_type,
                self.playback_state.playstate,
            )

        if event.kind == MediaServerWebsocketEventKind.PLAYBACK_INTENT:
            if event.playback_intent is None:
                return
            self.playback_command_handler.handle_playback_intent(
                event.playback_intent
            )
        elif event.kind == MediaServerWebsocketEventKind.PLAYBACK_COMMAND:
            if event.command is None:
                return
            self.playback_command_handler.handle_command(event.command)
        elif event.kind == MediaServerWebsocketEventKind.SESSIONS_UPDATE:
            self._session_monitor.on_sessions_update(event.sessions or [])
        else:
            logging.debug(
                "%s websocket message type: %s",
                self._provider_name,
                event.raw_type,
            )

    def on_error(self, _ws, error):
        if isinstance(error, WebSocketConnectionClosedException):
            logging.info(
                "%s WebSocket connection lost; will reconnect",
                self._provider_name,
            )
            return
        logging.warning("%s WebSocket error", self._provider_name, exc_info=error)

    def on_close(self, _ws, close_status_code=None, close_msg=None):
        logging.info(
            "%s WebSocket connection closed | status=%s | msg=%s",
            self._provider_name,
            close_status_code,
            close_msg,
        )
        if self._session_monitor:
            self._session_monitor.reset()

    def on_open(self, ws):
        logging.info("%s WebSocket connection opened", self._provider_name)
        self._session_monitor.reset()
        ws.send(self._session_subscription_message)
        self._start_capability_registration()

    def _start_capability_registration(self) -> None:
        thread = threading.Thread(
            target=self._register_capabilities_with_retry,
            name=f"{self._provider_name}-capability-registration",
            daemon=True,
        )
        thread.start()

    def _register_capabilities_with_retry(self) -> None:
        """Re-register media-control capabilities, retrying while the server loads.

        Runs off the websocket read thread because the connection reopens before
        the media server's REST API is ready after a full restart; retrying here
        is the only chance to register, since the now-open websocket will not
        fire on_open again to trigger another attempt.
        """
        session = self.media_server_session
        if session is None:
            return
        total_attempts = 1 + len(self._capability_retry_delays)
        for attempt in range(1, total_attempts + 1):
            try:
                session.set_capabilities()
                if attempt > 1:
                    logging.info(
                        "%s media-control capabilities registered on attempt %s",
                        self._provider_name,
                        attempt,
                    )
                return
            except Exception:
                if attempt < total_attempts:
                    delay = self._capability_retry_delays[attempt - 1]
                    logging.info(
                        "%s capability registration not ready (attempt %s/%s); "
                        "retrying in %ss",
                        self._provider_name,
                        attempt,
                        total_attempts,
                        delay,
                    )
                    self._sleep(delay)
                else:
                    logging.warning(
                        "%s failed to register media-control capabilities after "
                        "%s attempts; remote-control UI may not appear until the "
                        "next reconnect",
                        self._provider_name,
                        total_attempts,
                        exc_info=True,
                    )

    def run(self):
        self._setup_services()
        self._connect()

    def _setup_services(self):
        if self._playback_services is None:
            raise RuntimeError(f"{self._provider_name} playback services are not configured.")

        self.playback_state = BridgePlaybackState()
        session = self._session_factory(self.config, self.playback_state)
        session.lang = self.language
        # Capability registration is owned by on_open so it re-runs on every
        # reconnect, not just cold start (see spec
        # 2026-06-26-websocket-reconnect-capability-reregistration).
        self.media_server_session = session
        setattr(self, self._session_attribute_name, session)

        self.playback_application_service = PlaybackApplicationService(
            playback_session=session,
            playback_state=self.playback_state,
            reload_config=self.reload_config,
            media_server_playback_services=self._playback_services,
            telemetry_service=TelemetryService(
                config_file=self.config_file,
                load_config=lambda: load_effective_config(self.config_file),
                save_config=lambda config: save_effective_config(
                    self.config_file, config
                ),
            ),
        )
        dispatcher = PlaybackIntentDispatcher(
            playback_application_service=self.playback_application_service,
        )
        self.playback_command_handler = self._command_handler_factory(
            session,
            playback_state=self.playback_state,
            config_provider=lambda: self.config,
            playback_intent_dispatcher_factory=lambda: dispatcher,
            oppo_control_factory=lambda config: create_oppo_playback_command_control(
                config,
                on_verbose_preamble=getattr(
                    self.playback_application_service.active_oppo_playback,
                    "preamble_callback",
                    None,
                ),
            ),
            active_publisher_provider=lambda: (
                self.playback_application_service.active_publisher
            ),
        )
        self._session_monitor = self._session_monitor_factory(
            session,
            playback_state=self.playback_state,
            config_provider=lambda: self.config,
            dispatcher=dispatcher,
        )
        self._websocket_event_mapper = self._websocket_event_mapper_factory(session)

    def _connect(self):
        media_server = active_media_server_config(self.config)
        server_url = media_server.server_url.rstrip("/")
        session = self.media_server_session or getattr(
            self,
            self._session_attribute_name,
            None,
        )
        access_token = (session.user_info or {}).get(
            "AccessToken"
        ) if session else ""
        access_token = access_token or media_server.access_token

        if not server_url:
            raise RuntimeError(
                f"{self._provider_name} WebSocket is not configured: "
                "missing media_server.server_url"
            )

        if not access_token:
            raise RuntimeError(
                f"{self._provider_name} WebSocket is not configured: "
                "missing media_server.access_token"
            )

        uri = self._websocket_uri_factory(server_url, access_token)
        headers = (
            self._websocket_headers_factory(access_token)
            if self._websocket_headers_factory
            else None
        )
        logging.debug(
            "%s WebSocket URI: %s",
            self._provider_name,
            uri.replace(access_token, "***"),
        )

        self._ws_app = self._websocket_app_factory(
            uri,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            header=headers,
        )

        logging.info("%s WebSocket client initialized", self._provider_name)
        self._ws_app.run_forever(ping_interval=10, reconnect=10)
        logging.info("%s WebSocket client stopped", self._provider_name)


def emby_websocket_uri(server_url: str, access_token: str) -> str:
    uri = server_url.replace("http://", "ws://").replace("https://", "wss://")
    return f"{uri}/?api_key={access_token}&deviceId={DEVICE_ID}"


def jellyfin_websocket_uri(server_url: str, access_token: str) -> str:
    uri = server_url.replace("http://", "ws://").replace("https://", "wss://")
    return (
        f"{uri}/socket?ApiKey={access_token}"
        f"&api_key={access_token}&deviceId={DEVICE_ID}"
    )


def jellyfin_websocket_headers(access_token: str) -> dict:
    auth_string = (
        'MediaBrowser Client="Home Cinema Control",'
        'Device="Home Cinema Control",'
        f'DeviceId="{DEVICE_ID}",'
        f'Version="{__version__}",'
        f'Token="{access_token}"'
    )
    return {
        "Authorization": auth_string,
        "X-Emby-Authorization": auth_string,
        "X-Emby-Token": access_token,
        "X-MediaBrowser-Token": access_token,
    }
