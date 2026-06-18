import unittest

from home_cinema_control.devices.oppo.tolerant_http import OppoTolerantHttpClient


class OppoTolerantHttpClientTest(unittest.TestCase):
    def test_reads_normal_http_response(self):
        client = OppoTolerantHttpClient(
            socket_factory=FakeSocketFactory(
                b'HTTP/1.1 200 OK\r\nContent-Length: 16\r\n\r\n{"success":true}'
            )
        )

        response = client.get("http://192.168.1.50:436/getplayingtime", timeout=1)

        self.assertEqual(200, response.status_code)
        self.assertEqual('{"success":true}', response.text)

    def test_discards_verbose_lines_before_http_status(self):
        preambles = []
        client = OppoTolerantHttpClient(
            socket_factory=FakeSocketFactory(
                b"@UPL PAUS\r@UST 03/03 ENG\rHTTP/1.1 200 OK\r\n"
                b"Content-Length: 16\r\n\r\n"
                b'{"success":true}'
            ),
            on_verbose_preamble=preambles.append,
        )

        response = client.get("http://192.168.1.50:436/getplayingtime", timeout=1)

        self.assertEqual(200, response.status_code)
        self.assertEqual('{"success":true}', response.text)
        self.assertEqual(["@UPL PAUS\r@UST 03/03 ENG\r"], preambles)

    def test_sends_get_request_with_path_query_and_connection_close(self):
        socket_factory = FakeSocketFactory(
            b'HTTP/1.1 200 OK\r\nContent-Length: 16\r\n\r\n{"success":true}'
        )
        client = OppoTolerantHttpClient(socket_factory=socket_factory)

        client.get("http://192.168.1.50:436/setplaytime?%7B%7D", timeout=1)

        self.assertEqual(("192.168.1.50", 436), socket_factory.address)
        self.assertIn(b"GET /setplaytime?%7B%7D HTTP/1.1", socket_factory.socket.sent)
        self.assertIn(b"Connection: close", socket_factory.socket.sent)


class FakeSocketFactory:
    def __init__(self, response):
        self.socket = FakeSocket(response)
        self.address = None
        self.timeout = None

    def __call__(self, address, timeout):
        self.address = address
        self.timeout = timeout
        return self.socket


class FakeSocket:
    def __init__(self, response):
        self._response = response
        self._read = False
        self.sent = b""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def settimeout(self, timeout):
        self.timeout = timeout

    def sendall(self, payload):
        self.sent += payload

    def recv(self, _size):
        if self._read:
            return b""
        self._read = True
        return self._response


if __name__ == "__main__":
    unittest.main()
