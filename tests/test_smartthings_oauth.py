import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from home_cinema_control.devices.tv.adapters.smartthings_oauth import (
    SMARTTHINGS_AUTH_URL,
    SMARTTHINGS_TOKEN_URL,
    SmartThingsOAuthClient,
    SmartThingsSecrets,
    SmartThingsTokenStore,
)

CLIENT_ID = "test-client-id"
CLIENT_SECRET = "test-client-secret"
ACCESS_TOKEN = "access-abc"
REFRESH_TOKEN = "refresh-xyz"
DEVICE_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"


def _oauth() -> SmartThingsOAuthClient:
    return SmartThingsOAuthClient(CLIENT_ID, CLIENT_SECRET)


def _ok_token_response(access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN, expires_in=86400):
    resp = Mock(status_code=200)
    resp.raise_for_status = Mock()
    resp.json.return_value = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in,
    }
    return resp


class SmartThingsSecretsTest(unittest.TestCase):
    def test_all_fields_default_to_empty(self):
        s = SmartThingsSecrets()
        self.assertEqual("", s.client_id)
        self.assertEqual("", s.client_secret)
        self.assertEqual("", s.access_token)
        self.assertEqual("", s.refresh_token)
        self.assertIsNone(s.token_expires_at)


class SmartThingsTokenStoreTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self._secrets_path = Path(self._tmp.name) / "secrets.json"

    def tearDown(self):
        self._tmp.cleanup()

    def _store(self):
        return SmartThingsTokenStore(self._secrets_path)

    def test_load_returns_none_when_file_missing(self):
        self.assertIsNone(self._store().load())

    def test_load_returns_none_when_section_absent(self):
        self._secrets_path.write_text(json.dumps({"smb": {"password": ""}}))
        self.assertIsNone(self._store().load())

    def test_load_returns_secrets_when_section_present(self):
        self._secrets_path.write_text(json.dumps({
            "samsung_smartthings": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "access_token": ACCESS_TOKEN,
                "refresh_token": REFRESH_TOKEN,
                "token_expires_at": None,
            }
        }))
        secrets = self._store().load()
        self.assertIsNotNone(secrets)
        self.assertEqual(CLIENT_ID, secrets.client_id)
        self.assertEqual(ACCESS_TOKEN, secrets.access_token)
        self.assertEqual(REFRESH_TOKEN, secrets.refresh_token)

    def test_save_writes_section_to_new_file(self):
        s = SmartThingsSecrets(client_id=CLIENT_ID, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
        self._store().save(s)
        data = json.loads(self._secrets_path.read_text())
        self.assertIn("samsung_smartthings", data)
        self.assertEqual(CLIENT_ID, data["samsung_smartthings"]["client_id"])

    def test_save_does_not_overwrite_other_keys(self):
        self._secrets_path.write_text(json.dumps({"smb": {"password": "secret"}}))
        self._store().save(SmartThingsSecrets(client_id=CLIENT_ID))
        data = json.loads(self._secrets_path.read_text())
        self.assertEqual("secret", data["smb"]["password"])
        self.assertIn("samsung_smartthings", data)

    def test_save_then_load_roundtrip(self):
        original = SmartThingsSecrets(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            access_token=ACCESS_TOKEN,
            refresh_token=REFRESH_TOKEN,
        )
        store = self._store()
        store.save(original)
        loaded = store.load()
        self.assertEqual(original.client_id, loaded.client_id)
        self.assertEqual(original.access_token, loaded.access_token)
        self.assertEqual(original.refresh_token, loaded.refresh_token)


class SmartThingsOAuthClientAuthUrlTest(unittest.TestCase):
    def test_authorization_url_contains_base_url(self):
        url = _oauth().authorization_url("http://hcc/callback", "state123")
        self.assertIn(SMARTTHINGS_AUTH_URL, url)

    def test_authorization_url_contains_client_id(self):
        url = _oauth().authorization_url("http://hcc/callback", "state123")
        self.assertIn(CLIENT_ID, url)

    def test_authorization_url_contains_state(self):
        url = _oauth().authorization_url("http://hcc/callback", "mystate")
        self.assertIn("mystate", url)

    def test_authorization_url_contains_redirect_uri(self):
        url = _oauth().authorization_url("http://hcc:8090/callback", "s")
        self.assertIn("hcc", url)
        self.assertIn("callback", url)

    def test_authorization_url_contains_required_scopes(self):
        url = _oauth().authorization_url("http://hcc/callback", "s")
        self.assertIn("r%3Adevices", url)


class SmartThingsOAuthClientExchangeCodeTest(unittest.TestCase):
    _PATCH = "home_cinema_control.devices.tv.adapters.smartthings_oauth.requests.post"

    def test_posts_to_token_url(self):
        with patch(self._PATCH, return_value=_ok_token_response()) as mock_post:
            _oauth().exchange_code("code123", "http://hcc/callback")
        self.assertEqual(SMARTTHINGS_TOKEN_URL, mock_post.call_args.args[0])

    def test_uses_authorization_code_grant(self):
        with patch(self._PATCH, return_value=_ok_token_response()) as mock_post:
            _oauth().exchange_code("code123", "http://hcc/callback")
        data = mock_post.call_args.kwargs["data"]
        self.assertEqual("authorization_code", data["grant_type"])
        self.assertEqual("code123", data["code"])

    def test_returns_secrets_with_access_and_refresh_tokens(self):
        with patch(self._PATCH, return_value=_ok_token_response()):
            result = _oauth().exchange_code("code123", "http://hcc/callback")
        self.assertEqual(ACCESS_TOKEN, result.access_token)
        self.assertEqual(REFRESH_TOKEN, result.refresh_token)

    def test_preserves_client_credentials_in_result(self):
        with patch(self._PATCH, return_value=_ok_token_response()):
            result = _oauth().exchange_code("code123", "http://hcc/callback")
        self.assertEqual(CLIENT_ID, result.client_id)
        self.assertEqual(CLIENT_SECRET, result.client_secret)

    def test_sets_token_expires_at_from_expires_in(self):
        before = datetime.now(timezone.utc)
        with patch(self._PATCH, return_value=_ok_token_response(expires_in=3600)):
            result = _oauth().exchange_code("code123", "http://hcc/callback")
        after = datetime.now(timezone.utc)
        self.assertIsNotNone(result.token_expires_at)
        self.assertGreater(result.token_expires_at, before + timedelta(seconds=3500))
        self.assertLess(result.token_expires_at, after + timedelta(seconds=3700))


class SmartThingsOAuthClientRefreshTest(unittest.TestCase):
    _PATCH = "home_cinema_control.devices.tv.adapters.smartthings_oauth.requests.post"

    def _existing_secrets(self):
        return SmartThingsSecrets(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            access_token="old-access",
            refresh_token=REFRESH_TOKEN,
        )

    def test_posts_to_token_url(self):
        with patch(self._PATCH, return_value=_ok_token_response()) as mock_post:
            _oauth().refresh(self._existing_secrets())
        self.assertEqual(SMARTTHINGS_TOKEN_URL, mock_post.call_args.args[0])

    def test_uses_refresh_token_grant(self):
        with patch(self._PATCH, return_value=_ok_token_response()) as mock_post:
            _oauth().refresh(self._existing_secrets())
        data = mock_post.call_args.kwargs["data"]
        self.assertEqual("refresh_token", data["grant_type"])
        self.assertEqual(REFRESH_TOKEN, data["refresh_token"])

    def test_returns_new_access_token(self):
        with patch(self._PATCH, return_value=_ok_token_response(access_token="new-access")):
            result = _oauth().refresh(self._existing_secrets())
        self.assertEqual("new-access", result.access_token)

    def test_preserves_existing_refresh_token_when_server_does_not_rotate(self):
        response_without_refresh = Mock(status_code=200)
        response_without_refresh.raise_for_status = Mock()
        response_without_refresh.json.return_value = {
            "access_token": "new-access",
            "expires_in": 86400,
        }
        with patch(self._PATCH, return_value=response_without_refresh):
            result = _oauth().refresh(self._existing_secrets())
        self.assertEqual(REFRESH_TOKEN, result.refresh_token)

    def test_uses_server_refresh_token_when_rotated(self):
        with patch(self._PATCH, return_value=_ok_token_response(refresh_token="new-refresh")):
            result = _oauth().refresh(self._existing_secrets())
        self.assertEqual("new-refresh", result.refresh_token)

    def test_preserves_client_credentials(self):
        with patch(self._PATCH, return_value=_ok_token_response()):
            result = _oauth().refresh(self._existing_secrets())
        self.assertEqual(CLIENT_ID, result.client_id)
        self.assertEqual(CLIENT_SECRET, result.client_secret)


if __name__ == "__main__":
    unittest.main()
