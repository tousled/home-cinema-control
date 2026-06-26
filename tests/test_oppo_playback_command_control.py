import unittest

from home_cinema_control.devices.oppo.playback_command_control import (
    create_oppo_playback_command_control,
)
from home_cinema_control.devices.oppo.tolerant_http import OppoTolerantHttpClient


class OppoPlaybackCommandControlTest(unittest.TestCase):
    def test_uses_tolerant_http_session_by_default(self):
        control = create_oppo_playback_command_control(_config("auto"))

        self.assertIsInstance(control.client.http_session, OppoTolerantHttpClient)

    def test_without_callback_has_no_preamble_callback(self):
        control = create_oppo_playback_command_control(_config("auto"))

        self.assertIsNone(control.client.http_session._on_verbose_preamble)

    def test_with_callback_wires_preamble_callback(self):
        received = []
        callback = received.append
        control = create_oppo_playback_command_control(
            _config("auto"),
            on_verbose_preamble=callback,
        )

        self.assertIs(control.client.http_session._on_verbose_preamble, callback)

    def test_legacy_stable_config_still_uses_tolerant_http_session(self):
        control = create_oppo_playback_command_control(_config("stable"))

        self.assertIsInstance(control.client.http_session, OppoTolerantHttpClient)

    def test_domain_commands_send_oppo_remote_keys(self):
        client = RecordingOppoControlApiClient()
        control = create_oppo_playback_command_control(_config("auto"))
        control = type(control)(control.config, client=client)

        cases = [
            (control.pause, "PAU"),
            (control.resume, "PLA"),
            (control.toggle_play_pause, "PAU"),
            (control.stop, "STP"),
            (control.next_track, "NXT"),
            (control.previous_track, "PRE"),
        ]

        for command, expected_key in cases:
            with self.subTest(expected_key=expected_key):
                result = command()

                self.assertTrue(result.successful)
                self.assertEqual(expected_key, client.calls[-1])


class RecordingOppoControlApiClient:
    def __init__(self):
        self.calls = []

    def send_remote_key(self, key):
        self.calls.append(key)
        return f"sent {key}"


def _config(observation_mode):
    return {
        "oppo": {
            "ip": "192.168.1.50",
            "observation_mode": observation_mode,
        },
        "media_server": {
            "server_url": "http://192.168.1.100:8096",
        },
    }


if __name__ == "__main__":
    unittest.main()
