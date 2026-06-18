import json
import unittest
import urllib.parse
from types import SimpleNamespace

from home_cinema_control.network.http import LoggingHttpSession, _redact_url


class RedactUrlTest(unittest.TestCase):
    def test_redacts_password_inside_oppo_style_json_query_blob(self):
        payload = {"server": "NAS-SERVER", "userName": "nasuser", "password": "secret"}
        url = "http://192.168.1.50:436/mountSharedFolder?" + urllib.parse.quote(
            json.dumps(payload)
        )

        redacted = _redact_url(url)

        self.assertNotIn("secret", redacted)
        decoded = json.loads(urllib.parse.unquote(redacted.split("?", 1)[1]))
        self.assertEqual("***", decoded["password"])
        self.assertEqual("nasuser", decoded["userName"])

    def test_redacts_password_in_plain_key_value_query(self):
        url = "http://example.com/login?username=nasuser&password=secret"

        redacted = _redact_url(url)

        self.assertNotIn("secret", redacted)
        self.assertIn("username=nasuser", redacted)

    def test_returns_url_unchanged_when_no_query_string(self):
        url = "http://example.com/getdevicelist"

        self.assertEqual(url, _redact_url(url))

    def test_returns_url_unchanged_when_query_is_not_json_or_pairs(self):
        url = "http://example.com/endpoint?notarealquery"

        self.assertEqual(url, _redact_url(url))


class LoggingHttpSessionTest(unittest.TestCase):
    def test_logs_redacted_url_not_raw_password(self):
        payload = {"server": "nas", "password": "secret"}
        url = "http://oppo:436/mountSharedFolder?" + urllib.parse.quote(json.dumps(payload))

        fake_response = SimpleNamespace(status_code=200, text="ok")
        fake_session = SimpleNamespace(request=lambda method, url, **kwargs: fake_response)
        http_session = LoggingHttpSession(name="oppo", session=fake_session)

        with self.assertLogs("home_cinema_control.network.http", level="DEBUG") as captured:
            http_session.get(url)

        joined = "\n".join(captured.output)
        self.assertNotIn("secret", joined)


if __name__ == "__main__":
    unittest.main()
