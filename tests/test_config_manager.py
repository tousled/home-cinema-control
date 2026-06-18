import json
import os
import tempfile
import unittest
from pathlib import Path

from home_cinema_control.config.manager import (
    load_effective_config,
    save_effective_config,
    sanitize_config_for_web,
    is_configured,
    is_smb_active,
)


class ConfigManagerTest(unittest.TestCase):
    def test_sanitize_config_for_web_removes_media_server_token_values(self):
        sanitized = sanitize_config_for_web(
            {
                "media_server": {
                    "type": "emby",
                    "server_url": "http://emby",
                    "display_name": "Pedro",
                    "access_token": "token",
                    "user_id": "user1",
                },
                "app": {"release_repository": "tousled/home-cinema-control"},
            }
        )

        self.assertEqual("http://emby", sanitized["media_server"]["server_url"])
        self.assertEqual("Pedro", sanitized["media_server"]["display_name"])
        self.assertNotIn("access_token", sanitized["media_server"])
        self.assertNotIn("user_id", sanitized["media_server"])
        self.assertTrue(sanitized["media_server"]["access_token_configured"])
        self.assertEqual(
            "tousled/home-cinema-control", sanitized["app"]["release_repository"]
        )

    def test_sanitize_config_for_web_removes_legacy_flat_emby_keys(self):
        sanitized = sanitize_config_for_web(
            {
                "media_server": {
                    "type": "emby",
                    "server_url": "http://emby",
                    "access_token": "token",
                    "user_id": "user1",
                },
                "emby_server": "http://legacy",
                "user_name": "legacy-user",
                "user_password": "legacy-password",
                "user_password_configured": True,
            }
        )

        self.assertNotIn("emby_server", sanitized)
        self.assertNotIn("user_name", sanitized)
        self.assertNotIn("user_password", sanitized)
        self.assertNotIn("user_password_configured", sanitized)

    def test_load_effective_config_merges_config_and_nested_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            secrets_file = Path(directory) / "secrets.json"
            config_file.write_text(
                json.dumps(
                    {
                        "media_server": {
                            "type": "emby",
                            "server_url": "http://emby",
                            "display_name": "Pedro",
                            "access_token_configured": True,
                        }
                    }
                ),
                encoding="utf-8",
            )
            secrets_file.write_text(
                json.dumps(
                    {
                        "media_server": {
                            "access_token": "token",
                            "user_id": "user1",
                        }
                    }
                ),
                encoding="utf-8",
            )

            previous_secrets_path = os.environ.get("HCC_SECRETS_FILE_PATH")
            os.environ["HCC_SECRETS_FILE_PATH"] = str(secrets_file)

            try:
                effective_config = load_effective_config(config_file)
            finally:
                if previous_secrets_path is None:
                    os.environ.pop("HCC_SECRETS_FILE_PATH", None)
                else:
                    os.environ["HCC_SECRETS_FILE_PATH"] = previous_secrets_path

        self.assertEqual("http://emby", effective_config["media_server"]["server_url"])
        self.assertEqual("Pedro", effective_config["media_server"]["display_name"])
        self.assertEqual("token", effective_config["media_server"]["access_token"])
        self.assertEqual("user1", effective_config["media_server"]["user_id"])

    def test_save_effective_config_preserves_existing_nested_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            secrets_file = Path(directory) / "secrets.json"
            config_file.write_text(
                json.dumps(
                    {
                        "media_server": {
                            "type": "emby",
                            "server_url": "http://old",
                            "display_name": "Pedro",
                            "access_token_configured": True,
                        }
                    }
                ),
                encoding="utf-8",
            )
            secrets_file.write_text(
                json.dumps(
                    {
                        "media_server": {
                            "access_token": "token",
                            "user_id": "user1",
                        }
                    }
                ),
                encoding="utf-8",
            )

            previous_secrets_path = os.environ.get("HCC_SECRETS_FILE_PATH")
            os.environ["HCC_SECRETS_FILE_PATH"] = str(secrets_file)

            try:
                save_effective_config(
                    config_file,
                    {
                        "media_server": {
                            "type": "emby",
                            "server_url": "http://new",
                            "display_name": "Pedro",
                            "access_token_configured": True,
                        }
                    },
                )
            finally:
                if previous_secrets_path is None:
                    os.environ.pop("HCC_SECRETS_FILE_PATH", None)
                else:
                    os.environ["HCC_SECRETS_FILE_PATH"] = previous_secrets_path

            public_config = json.loads(config_file.read_text(encoding="utf-8"))
            secrets = json.loads(secrets_file.read_text(encoding="utf-8"))

        self.assertEqual("http://new", public_config["media_server"]["server_url"])
        self.assertNotIn("access_token", public_config["media_server"])
        self.assertNotIn("user_id", public_config["media_server"])
        self.assertTrue(public_config["media_server"]["access_token_configured"])
        self.assertEqual("token", secrets["media_server"]["access_token"])
        self.assertEqual("user1", secrets["media_server"]["user_id"])

    def test_is_configured_accepts_token_based_media_server_config(self):
        self.assertTrue(
            is_configured(
                {
                    "media_server": {
                        "server_url": "http://emby",
                        "access_token": "token",
                        "user_id": "user1",
                    }
                }
            )
        )

    def test_is_configured_rejects_missing_token(self):
        self.assertFalse(
            is_configured(
                {
                    "media_server": {
                        "server_url": "http://emby",
                        "user_id": "user1",
                    }
                }
            )
        )

    def test_is_smb_active_true_when_enabled_without_credentials(self):
        # Anonymous/guest SMB shares are valid; the toggle alone must decide.
        self.assertTrue(
            is_smb_active({"oppo": {"use_smb": True}, "smb": {"username": "", "password": ""}})
        )

    def test_is_smb_active_true_when_enabled_with_credentials(self):
        self.assertTrue(
            is_smb_active(
                {"oppo": {"use_smb": True}, "smb": {"username": "nas_user", "password": "nas_pass"}}
            )
        )

    def test_is_smb_active_false_when_disabled_even_with_credentials(self):
        self.assertFalse(
            is_smb_active(
                {"oppo": {"use_smb": False}, "smb": {"username": "nas_user", "password": "nas_pass"}}
            )
        )

    def test_is_smb_active_false_when_oppo_section_missing(self):
        self.assertFalse(is_smb_active({}))


if __name__ == "__main__":
    unittest.main()