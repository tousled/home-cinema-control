import json
import logging

from websocket import WebSocketApp

from home_cinema_control.media_servers.emby.session import EmbySession
from home_cinema_control.config.manager import load_effective_config
from home_cinema_control.media_servers.emby.constants import DEVICE_ID
from home_cinema_control.media_servers.emby.playback_command_handler import (
    EmbyPlaybackCommandHandler,
)
from home_cinema_control.media_servers.emby.session_monitor import EmbySessionMonitor
from home_cinema_control.playback.dispatch import PlaybackIntentDispatcher
from home_cinema_control.playback.application import PlaybackApplicationService
from home_cinema_control.playback.state import BridgePlaybackState
from home_cinema_control.devices.oppo.playback_command_control import (
    create_oppo_playback_command_control,
)


class EmbyWebsocket:
    def __init__(self):
        self.config = None
        self.emby_session = None
        self.playback_state: BridgePlaybackState | None = None
        self.config_file = ""
        self.language = None
        self._ws_app = None
        self.playback_application_service = None
        self.playback_command_handler = None
        self._session_monitor = None
        logging.info("ws::Init")

    def stop(self):
        logging.info("ws::stop")
        if self._ws_app:
            self._ws_app.close()

    def reload_config(self):
        logging.info("Reloading config")
        config = load_effective_config(self.config_file)
        self.update_config(config)
        return config

    def update_config(self, config: dict) -> None:
        self.config = config
        if self.emby_session:
            self.emby_session.config = config

    def _play(self, data):
        self.playback_command_handler.handle_play(data)

    def on_message(self, _ws, msg):
        msg_json = json.loads(msg)
        msg_type = msg_json.get("MessageType")
        data = msg_json.get("Data")

        if msg_type == "Sessions" and isinstance(data, list):
            logging.info(
                "ws::Message Arrived: Sessions | playstate=%s | sessions=%s",
                self.playback_state.playstate,
                len(data),
            )
        else:
            logging.info(
                "ws::Message Arrived: %s | playstate=%s",
                msg_type,
                self.playback_state.playstate,
            )

        if msg_type == "Play":
            self._play(data)
        elif msg_type == "Playstate":
            self.playback_command_handler.handle_playback_state(data)
        elif msg_type == "GeneralCommand":
            self.playback_command_handler.handle_general_command(data)
        elif msg_type == "Sessions":
            self._session_monitor.on_sessions_update(data)
        else:
            logging.debug("WebSocket Message Type: %s", msg_type)

    def on_error(self, _ws, error):
        logging.warning("WebSocket error", exc_info=error)

    def on_close(self, _ws, close_status_code=None, close_msg=None):
        logging.info(
            "WebSocket connection closed | status=%s | msg=%s",
            close_status_code,
            close_msg,
        )
        if self._session_monitor:
            self._session_monitor.reset()

    def on_open(self, ws):
        logging.info("WebSocket connection opened")
        self._session_monitor.reset()
        ws.send('{"MessageType":"SessionsStart", "Data": "0,1500"}')

    def run(self):
        self._setup_services()
        self._connect()

    def _setup_services(self):
        self.playback_state = BridgePlaybackState()
        self.emby_session = EmbySession(self.config, self.playback_state)
        self.emby_session.lang = self.language
        self.emby_session.set_capabilities()

        self.playback_application_service = PlaybackApplicationService(
            playback_session=self.emby_session,
            playback_state=self.playback_state,
            reload_config=self.reload_config,
        )
        dispatcher = PlaybackIntentDispatcher(
            playback_application_service=self.playback_application_service,
        )
        self.playback_command_handler = EmbyPlaybackCommandHandler(
            emby_session=self.emby_session,
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
        self._session_monitor = EmbySessionMonitor(
            emby_session=self.emby_session,
            playback_state=self.playback_state,
            config_provider=lambda: self.config,
            dispatcher=dispatcher,
        )

    def _connect(self):
        media_server = self.config.get("media_server") or {}
        server_url = str(media_server.get("server_url", "")).rstrip("/")
        access_token = (self.emby_session.user_info or {}).get(
            "AccessToken"
        ) or media_server.get("access_token", "")

        if not server_url:
            raise RuntimeError(
                "Emby WebSocket is not configured: missing media_server.server_url"
            )

        if not access_token:
            raise RuntimeError(
                "Emby WebSocket is not configured: missing media_server.access_token"
            )

        uri = server_url.replace("http://", "ws://").replace("https://", "wss://")
        uri = f"{uri}/?api_key={access_token}&deviceId={DEVICE_ID}"

        logging.debug("WebSocket URI: %s", uri.replace(access_token, "***"))

        self._ws_app = WebSocketApp(
            uri,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )

        logging.info("WebSocket client initialized")
        self._ws_app.run_forever(ping_interval=10, reconnect=10)
        logging.info("WebSocket client stopped")
