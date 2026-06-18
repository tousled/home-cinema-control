import unittest

from home_cinema_control.devices.oppo.svm_mode import (
    OppoSVMModeClient,
    svm_response_is_complete,
    svm_response_is_successful,
)


class OppoSVMModeClientTest(unittest.TestCase):
    def test_sets_svm_mode_with_expected_payload(self):
        tcp = RecordingTcpClient(response="@SVM OK 0")
        client = OppoSVMModeClient(_config(), tcp_client=tcp)

        result = client.set_mode(0)

        self.assertTrue(result.successful)
        self.assertEqual([b"#SVM 0\r"], tcp.payloads)

    def test_rejects_unexpected_response(self):
        tcp = RecordingTcpClient(response="@SVM ER 0")
        client = OppoSVMModeClient(_config(), tcp_client=tcp)

        result = client.set_mode(0)

        self.assertFalse(result.successful)
        self.assertIn("unexpected response", result.detail)

    def test_accepts_observed_svm_ok_formats(self):
        self.assertTrue(svm_response_is_successful("@SVM OK 3", mode=3))
        self.assertTrue(svm_response_is_successful("@OK 3", mode=3))
        self.assertTrue(svm_response_is_successful("OK 3", mode=3))

    def test_complete_accepts_error_response(self):
        self.assertTrue(svm_response_is_complete("@SVM ER 0", mode=0))


class RecordingTcpClient:
    def __init__(self, *, response):
        self.response = response
        self.payloads = []

    def request(self, **kwargs):
        self.payloads.append(kwargs["payload"])
        return self.response


def _config():
    return {
        "OPPO_Port": 23,
        "oppo": {
            "ip": "192.168.1.50",
            "connection_timeout_seconds": 3,
        },
    }


if __name__ == "__main__":
    unittest.main()
