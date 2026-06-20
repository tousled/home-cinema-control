import json
import unittest
from unittest.mock import MagicMock, call, patch

from home_cinema_control.media_servers.common.constants import DEVICE_ID
from home_cinema_control.media_servers.common.playback_command_handler import (
    command_from_general_command_message,
    command_from_playstate_message,
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
        self.assertEqual(_config()["media_server"]["server_url"], listener.config["media_server"]["server_url"])

    def test_on_open_subscribes_to_session_updates(self):
        listener = _listener_with_mocks()
        ws = MagicMock()

        listener.on_open(ws)

        listener._session_monitor.reset.assert_called_once()
        ws.send.assert_called_once_with('{"MessageType":"SessionsStart", "Data": "0,1500"}')

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
            json.dumps({"MessageType": "Play", "Data": {"PlayCommand": "PlayNow"}}),
        )

        self.assertEqual(
            [
                call(command_from_playstate_message({"Command": "Pause"})),
                call(
                    command_from_general_command_message(
                        {"Name": "SetAudioStreamIndex", "Arguments": {"Index": 2}}
                    )
                ),
            ],
            listener.playback_command_handler.handle_command.call_args_list,
        )
        listener.playback_command_handler.handle_play.assert_called_once_with(
            {"PlayCommand": "PlayNow"}
        )

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
            f"ws://jellyfin.local:8096/socket?api_key=token&deviceId={DEVICE_ID}",
            uri,
        )
        ws_app.return_value.run_forever.assert_called_once_with(
            ping_interval=10,
            reconnect=10,
        )


def _listener_with_mocks():
    listener = JellyfinWebsocket(config=_config(), config_file="/tmp/config.json")
    listener.playback_state = BridgePlaybackState()
    listener.jellyfin_session = MagicMock()
    listener.jellyfin_session.user_info = {"AccessToken": "token"}
    listener.playback_command_handler = MagicMock()
    listener._session_monitor = MagicMock()
    return listener


def _config():
    return {
        "media_server": {
            "type": "jellyfin",
            "server_url": "http://jellyfin.local:8096",
            "access_token": "token",
            "user_id": "user-1",
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
