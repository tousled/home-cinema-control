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
