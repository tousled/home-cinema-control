import json
import os
import tempfile
import unittest
from pathlib import Path

from home_cinema_control.config.manager import (
    clear_media_server_auth,
    clear_smb_credentials,
    load_effective_config,
    merge_existing_secrets,
    sanitize_config_for_web,
    save_effective_config,
)

_SECRETS_ENV = "HCC_SECRETS_FILE_PATH"


class SmbSecretsTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._dir = Path(self._tmpdir.name)
        self._config_path = self._dir / "config.json"
        self._secrets_path = self._dir / "secrets.json"
        self._config_path.write_text("{}", encoding="utf-8")
        self._secrets_path.write_text(
            json.dumps({
                "media_server": {"access_token": "", "user_id": ""},
                "smb": {"username": "", "password": ""},
            }),
            encoding="utf-8",
        )
        self._prev = os.environ.get(_SECRETS_ENV)
        os.environ[_SECRETS_ENV] = str(self._secrets_path)

    def tearDown(self):
        if self._prev is None:
            os.environ.pop(_SECRETS_ENV, None)
        else:
            os.environ[_SECRETS_ENV] = self._prev
        self._tmpdir.cleanup()

    def test_smb_username_written_to_config_password_to_secrets(self):
        save_effective_config(
            self._config_path,
            {"smb": {"username": "nas_user", "password": "nas_pass"}},
        )

        config_data = json.loads(self._config_path.read_text())
        secrets_data = json.loads(self._secrets_path.read_text())

        self.assertEqual("nas_user", config_data["smb"]["username"])
        self.assertNotIn("password", config_data.get("smb", {}))
        self.assertNotIn("username", secrets_data.get("smb", {}))
        self.assertEqual("nas_pass", secrets_data["smb"]["password"])

    def test_sanitize_exposes_username_and_password_configured_for_both_credentials(self):
        result = sanitize_config_for_web({"smb": {"username": "nas_user", "password": "nas_pass"}})

        self.assertEqual("nas_user", result["smb"]["username"])
        self.assertTrue(result["smb"]["password_configured"])
        self.assertNotIn("password", result["smb"])

    def test_sanitize_exposes_username_only_state(self):
        result = sanitize_config_for_web({"smb": {"username": "nas_user", "password": ""}})

        self.assertEqual("nas_user", result["smb"]["username"])
        self.assertFalse(result["smb"]["password_configured"])

    def test_sanitize_exposes_no_credentials_state(self):
        result = sanitize_config_for_web({"smb": {"username": "", "password": ""}})

        self.assertEqual("", result["smb"]["username"])
        self.assertFalse(result["smb"]["password_configured"])

    def test_sanitize_exposes_no_credentials_when_smb_absent(self):
        result = sanitize_config_for_web({})

        self.assertEqual("", result["smb"]["username"])
        self.assertFalse(result["smb"]["password_configured"])

    def test_saving_blank_password_preserves_existing_password(self):
        save_effective_config(
            self._config_path,
            {"smb": {"username": "nas_user", "password": "nas_pass"}},
        )

        save_effective_config(
            self._config_path,
            {"smb": {"username": "nas_user", "password": ""}},
        )

        secrets_data = json.loads(self._secrets_path.read_text())
        self.assertEqual("nas_pass", secrets_data["smb"]["password"])

    def test_saving_blank_username_clears_it(self):
        # Unlike the password, the username is not a secret: the UI always
        # sees its real value, so a blank submission means the user cleared it.
        save_effective_config(
            self._config_path,
            {"smb": {"username": "nas_user", "password": "nas_pass"}},
        )

        save_effective_config(
            self._config_path,
            {"smb": {"username": "", "password": ""}},
        )

        config_data = json.loads(self._config_path.read_text())
        self.assertEqual("", config_data["smb"]["username"])

    def test_clear_smb_credentials_wipes_config_username_and_secrets_password(self):
        save_effective_config(
            self._config_path,
            {"smb": {"username": "nas_user", "password": "nas_pass"}},
        )

        clear_smb_credentials(self._config_path)

        config_data = json.loads(self._config_path.read_text())
        secrets_data = json.loads(self._secrets_path.read_text())
        self.assertEqual("", config_data["smb"]["username"])
        self.assertEqual("", secrets_data["smb"]["password"])
        self.assertNotIn("username", secrets_data.get("smb", {}))

    def test_clear_media_server_auth_wipes_secrets_and_monitored_device(self):
        save_effective_config(
            self._config_path,
            {
                "media_server": {
                    "type": "emby",
                    "server_url": "http://emby.local",
                    "display_name": "Pedro",
                    "access_token": "emby-token",
                    "user_id": "emby-user",
                },
                "playback": {
                    "hcc_controlled_device": "emby-device",
                    "path_mappings": [{"source_path": "/movies", "verified": True}],
                },
            },
        )

        clear_media_server_auth(self._config_path)

        config_data = json.loads(self._config_path.read_text())
        secrets_data = json.loads(self._secrets_path.read_text())

        self.assertEqual("", config_data["media_server"]["display_name"])
        self.assertFalse(config_data["media_server"]["access_token_configured"])
        self.assertEqual("", config_data["playback"]["hcc_controlled_device"])
        self.assertEqual("", secrets_data["media_server"]["access_token"])
        self.assertEqual("", secrets_data["media_server"]["user_id"])
        # Verified path mappings survive a provider switch: Emby and Jellyfin
        # may point at the same NAS paths.
        self.assertEqual(
            [{"source_path": "/movies", "verified": True}],
            config_data["playback"]["path_mappings"],
        )
        # server_url and type are untouched by the auth clear.
        self.assertEqual("http://emby.local", config_data["media_server"]["server_url"])
        self.assertEqual("emby", config_data["media_server"]["type"])

    def test_load_effective_config_reads_username_from_config_and_password_from_secrets(self):
        self._config_path.write_text(
            json.dumps({"smb": {"username": "nas_user"}}), encoding="utf-8"
        )
        self._secrets_path.write_text(
            json.dumps({"smb": {"password": "nas_pass"}}), encoding="utf-8"
        )

        effective = load_effective_config(self._config_path)

        self.assertEqual("nas_user", effective["smb"]["username"])
        self.assertEqual("nas_pass", effective["smb"]["password"])

    def test_load_effective_config_still_merges_legacy_secrets_username(self):
        # Backward compatibility: installs from before the username/password
        # split stored both in secrets.json. They still merge in correctly.
        self._secrets_path.write_text(
            json.dumps({"smb": {"username": "nas_user", "password": "nas_pass"}}),
            encoding="utf-8",
        )

        effective = load_effective_config(self._config_path)

        self.assertEqual("nas_user", effective["smb"]["username"])
        self.assertEqual("nas_pass", effective["smb"]["password"])

    def test_merge_existing_secrets_new_password_wins_over_empty_secrets(self):
        # Bug: first-time credential save was silently lost because empty secrets.json
        # values overwrote newly submitted credentials via _deep_merge(config, secrets).
        submitted = {"smb": {"username": "nas_user", "password": "nas_pass"}}

        merged = merge_existing_secrets(self._config_path, submitted)

        self.assertEqual("nas_user", merged["smb"]["username"])
        self.assertEqual("nas_pass", merged["smb"]["password"])

    def test_merge_existing_secrets_fills_in_blank_password_from_secrets(self):
        self._secrets_path.write_text(
            json.dumps({"smb": {"password": "nas_pass"}}),
            encoding="utf-8",
        )
        submitted = {"smb": {"username": "", "password": ""}}

        merged = merge_existing_secrets(self._config_path, submitted)

        # Username is not a secret: a blank submission is taken literally.
        self.assertEqual("", merged["smb"]["username"])
        self.assertEqual("nas_pass", merged["smb"]["password"])


if __name__ == "__main__":
    unittest.main()
