import unittest

from home_cinema_control.devices.oppo.playback_state import (
    OppoPlaybackCategory,
    OppoPlaybackStatus,
)
from home_cinema_control.devices.oppo.playback_status_client import (
    OppoPlaybackStatusClient,
    _tcp_status_response_is_complete,
)


class RecordingTcpClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class OppoPlaybackStatusClientTest(unittest.TestCase):
    def test_parses_verbose_qpl_response_as_playing(self):
        client = OppoPlaybackStatusClient(host="192.168.1.50")
        client._tcp = RecordingTcpClient("@QPL OK PLAY\r@UAT TS 02/02 UNK 5.1")

        result = client.query_playback_state()

        self.assertTrue(result.ok)
        self.assertEqual(OppoPlaybackStatus.PLAY, result.status)
        self.assertEqual(OppoPlaybackCategory.ACTIVE, result.category)

    def test_verbose_qpl_response_is_complete(self):
        self.assertTrue(_tcp_status_response_is_complete("@QPL OK PLAY\r@UPL PLAY"))
        self.assertTrue(_tcp_status_response_is_complete("@OK MEDIA CENTER"))
        self.assertFalse(_tcp_status_response_is_complete("@UPL PLAY"))


if __name__ == "__main__":
    unittest.main()
