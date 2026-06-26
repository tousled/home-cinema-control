import json
import unittest
from unittest.mock import MagicMock, call, patch

from home_cinema_control.media_servers.common.constants import DEVICE_ID
from home_cinema_control.media_servers.jellyfin.websocket_event_mapper import (
    JellyfinWebsocketEventMapper,
    command_from_jellyfin_general_command_message,
    command_from_jellyfin_playstate_message,
)
from home_cinema_control.media_servers.jellyfin.provider import JellyfinProvider
from home_cinema_control.media_servers.jellyfin.websocket_listener import (
    JellyfinWebsocket,
)
from home_cinema_control.playback.state import BridgePlaybackState


class JellyfinWebsocketListenerTest(unittest.TestCase):
    def test_provider_creates_configured_jellyfin_listener(self):
        listener = JellyfinProvider().create_playback_listener(
            config=_config(),
            config_file="/tmp/config.json",
            language={"msg": "ok"},
        )

        self.assertIsInstance(listener, JellyfinWebsocket)
        expected = _config()["media_servers"]["providers"]["jellyfin"]["server_url"]
        actual = listener.config["media_servers"]["providers"]["jellyfin"]["server_url"]
        self.assertEqual(expected, actual)

    def test_on_open_subscribes_to_session_updates(self):
        listener = _listener_with_mocks()
        ws = MagicMock()

        listener.on_open(ws)

        listener._session_monitor.reset.assert_called_once()
        ws.send.assert_called_once_with('{"MessageType":"SessionsStart", "Data": "0,1500"}')

    def test_on_open_subscribes_then_starts_capability_registration(self):
        listener = _listener_with_mocks()
        listener._start_capability_registration = MagicMock()
        ws = MagicMock()

        listener.on_open(ws)

        listener._session_monitor.reset.assert_called_once()
        ws.send.assert_called_once_with('{"MessageType":"SessionsStart", "Data": "0,1500"}')
        listener._start_capability_registration.assert_called_once_with()

    def test_capability_registration_succeeds_on_first_attempt(self):
        listener = _listener_with_mocks()
        listener._sleep = MagicMock()

        listener._register_capabilities_with_retry()

        listener.media_server_session.set_capabilities.assert_called_once_with()
        listener._sleep.assert_not_called()

    def test_capability_registration_retries_until_server_ready(self):
        listener = _listener_with_mocks()
        listener._capability_retry_delays = (2, 5, 10)
        listener._sleep = MagicMock()
        listener.media_server_session.set_capabilities.side_effect = [
            RuntimeError("loading"),
            RuntimeError("loading"),
            None,
        ]

        listener._register_capabilities_with_retry()

        self.assertEqual(3, listener.media_server_session.set_capabilities.call_count)
        self.assertEqual([call(2), call(5)], listener._sleep.call_args_list)

    def test_capability_registration_gives_up_after_all_attempts(self):
        listener = _listener_with_mocks()
        listener._capability_retry_delays = (2, 5)
        listener._sleep = MagicMock()
        listener.media_server_session.set_capabilities.side_effect = RuntimeError(
            "still loading"
        )

        with self.assertLogs(level="WARNING") as logs:
            listener._register_capabilities_with_retry()

        self.assertEqual(3, listener.media_server_session.set_capabilities.call_count)
        self.assertTrue(
            any("capabilities" in r.getMessage() for r in logs.records)
        )

    def test_setup_services_does_not_register_capabilities(self):
        listener = _listener_with_mocks()
        listener._playback_services = MagicMock()
        session = MagicMock()
        session.user_info = {"AccessToken": "token"}
        listener._session_factory = MagicMock(return_value=session)
        listener._command_handler_factory = MagicMock()
        listener._session_monitor_factory = MagicMock()
        listener._websocket_event_mapper_factory = MagicMock()

        listener._setup_services()

        session.set_capabilities.assert_not_called()
        self.assertIs(session, listener.media_server_session)

    def test_on_message_dispatches_session_updates(self):
        listener = _listener_with_mocks()
        sessions = [{"DeviceId": "tv-1"}]

        listener.on_message(None, json.dumps({"MessageType": "Sessions", "Data": sessions}))

        listener._session_monitor.on_sessions_update.assert_called_once_with(sessions)

    def test_on_message_dispatches_commands(self):
        listener = _listener_with_mocks()

        listener.on_message(
            None,
            json.dumps({"MessageType": "Playstate", "Data": {"Command": "Pause"}}),
        )
        listener.on_message(
            None,
            json.dumps(
                {
                    "MessageType": "GeneralCommand",
                    "Data": {"Name": "SetAudioStreamIndex", "Arguments": {"Index": 2}},
                }
            ),
        )
        listener.on_message(
            None,
            json.dumps(
                {
                    "MessageType": "Play",
                    "Data": {"PlayCommand": "PlayNow", "ItemIds": ["item-1"]},
                }
            ),
        )

        self.assertEqual(
            [
                call(command_from_jellyfin_playstate_message({"Command": "Pause"})),
                call(
                    command_from_jellyfin_general_command_message(
                        {"Name": "SetAudioStreamIndex", "Arguments": {"Index": 2}}
                    )
                ),
            ],
            listener.playback_command_handler.handle_command.call_args_list,
        )
        listener.playback_command_handler.handle_playback_intent.assert_called_once()
        intent = listener.playback_command_handler.handle_playback_intent.call_args.args[0]
        self.assertEqual("item-1", intent.media_item_id)

    def test_on_error_logs_expected_close_without_traceback(self):
        from websocket import WebSocketConnectionClosedException

        listener = _listener_with_mocks()

        with self.assertLogs(level="INFO") as logs:
            listener.on_error(
                None,
                WebSocketConnectionClosedException("Connection to remote host was lost."),
            )

        self.assertEqual(1, len(logs.records))
        record = logs.records[0]
        self.assertEqual("INFO", record.levelname)
        self.assertIsNone(record.exc_info)

    def test_on_error_logs_unexpected_error_with_traceback(self):
        listener = _listener_with_mocks()

        with self.assertLogs(level="WARNING") as logs:
            listener.on_error(None, ValueError("boom"))

        self.assertEqual(1, len(logs.records))
        record = logs.records[0]
        self.assertEqual("WARNING", record.levelname)
        self.assertIsNotNone(record.exc_info)

    def test_connect_uses_jellyfin_socket_endpoint(self):
        listener = _listener_with_mocks()
        listener.jellyfin_session.user_info = {"AccessToken": "token"}

        with patch(
            "home_cinema_control.media_servers.jellyfin.websocket_listener.WebSocketApp"
        ) as ws_app:
            listener._connect()

        ws_app.assert_called_once()
        uri = ws_app.call_args.args[0]
        self.assertEqual(
            f"ws://jellyfin.local:8096/socket?ApiKey=token&api_key=token&deviceId={DEVICE_ID}",
            uri,
        )
        headers = ws_app.call_args.kwargs["header"]
        self.assertIn('Token="token"', headers["Authorization"])
        self.assertEqual("token", headers["X-Emby-Token"])
        self.assertEqual("token", headers["X-MediaBrowser-Token"])
        ws_app.return_value.run_forever.assert_called_once_with(
            ping_interval=10,
            reconnect=10,
        )

    def test_connect_uses_active_provider_when_multiple_are_configured(self):
        listener = _listener_with_mocks()
        listener.config = {
            "media_servers": {
                "active": "jellyfin",
                "providers": {
                    "emby": {"server_url": "http://emby.local:8096", "access_token": "emby-tok"},
                    "jellyfin": {"server_url": "http://jellyfin.local:8096"},
                },
            }
        }
        listener.jellyfin_session.user_info = {"AccessToken": "token"}

        with patch(
                "home_cinema_control.media_servers.jellyfin.websocket_listener.WebSocketApp"
        ) as ws_app:
            listener._connect()

        uri = ws_app.call_args.args[0]
        self.assertEqual(
            f"ws://jellyfin.local:8096/socket?ApiKey=token&api_key=token&deviceId={DEVICE_ID}",
            uri,
        )
        headers = ws_app.call_args.kwargs["header"]
        self.assertIn('Token="token"', headers["Authorization"])
        self.assertEqual("token", headers["X-Emby-Token"])


def _listener_with_mocks():
    listener = JellyfinWebsocket(config=_config(), config_file="/tmp/config.json")
    listener.playback_state = BridgePlaybackState()
    listener.jellyfin_session = MagicMock()
    listener.media_server_session = listener.jellyfin_session
    listener.jellyfin_session.user_info = {"AccessToken": "token"}
    listener.jellyfin_session.get_item_info.return_value = {
        "UserData": {"PlaybackPositionTicks": 0}
    }
    listener.jellyfin_session.find_controlling_session_id.return_value = (
        "controller-session"
    )
    listener.playback_command_handler = MagicMock()
    listener._session_monitor = MagicMock()
    listener._websocket_event_mapper = JellyfinWebsocketEventMapper(
        jellyfin_session=listener.jellyfin_session,
    )
    return listener


def _config():
    return {
        "media_servers": {
            "active": "jellyfin",
            "providers": {
                "jellyfin": {
                    "server_url": "http://jellyfin.local:8096",
                    "access_token": "token",
                    "user_id": "user-1",
                }
            },
        },
        "playback": {
            "hcc_controlled_device": "tv-1",
            "use_all_libraries": True,
            "libraries": [],
            "path_mappings": [],
        },
    }


if __name__ == "__main__":
    unittest.main()
