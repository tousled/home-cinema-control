import json
import os
import tempfile
import unittest
from pathlib import Path

from home_cinema_control.web.config_service import WebConfigService


class FakeRuntime:
    def __init__(self):
        self.config = {
            "media_server": {
                "type": "emby",
                "server_url": "http://emby",
                "display_name": "Pedro",
                "access_token": "secret-token",
                "user_id": "emby-user-id",
            }
        }
        self.saved_config = None

    def load_config(self):
        return dict(self.config)

    def save_config(self, config):
        self.saved_config = dict(config)


class WebConfigServiceTest(unittest.TestCase):
    def test_sanitizes_loaded_config_for_web(self):
        service = WebConfigService(runtime=FakeRuntime(), config_file="/tmp/config.json")

        sanitized = service.sanitize(service.load_config())

        self.assertEqual("http://emby", sanitized["media_server"]["server_url"])
        self.assertEqual("Pedro", sanitized["media_server"]["display_name"])
        self.assertTrue(sanitized["media_server"]["access_token_configured"])
        self.assertNotIn("access_token", sanitized["media_server"])
        self.assertNotIn("user_id", sanitized["media_server"])

    def test_prepare_submitted_config_preserves_existing_media_server_secrets(self):
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
                            "access_token": "secret-token",
                            "user_id": "emby-user-id",
                        }
                    }
                ),
                encoding="utf-8",
            )

            previous_secrets_path = os.environ.get("HCC_SECRETS_FILE_PATH")
            os.environ["HCC_SECRETS_FILE_PATH"] = str(secrets_file)

            try:
                runtime = FakeRuntime()
                service = WebConfigService(runtime=runtime, config_file=config_file)

                prepared = service.prepare_submitted_config(
                    {
                        "media_server": {
                            "type": "emby",
                            "server_url": "http://new",
                            "display_name": "Pedro",
                            "access_token_configured": True,
                        }
                    }
                )
            finally:
                if previous_secrets_path is None:
                    os.environ.pop("HCC_SECRETS_FILE_PATH", None)
                else:
                    os.environ["HCC_SECRETS_FILE_PATH"] = previous_secrets_path

        self.assertEqual("http://new", prepared["media_server"]["server_url"])
        self.assertEqual("Pedro", prepared["media_server"]["display_name"])
        self.assertEqual("secret-token", prepared["media_server"]["access_token"])
        self.assertEqual("emby-user-id", prepared["media_server"]["user_id"])
        self.assertIsNone(runtime.saved_config)

    def test_prepare_submitted_config_does_not_reintroduce_legacy_password_keys(self):
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
                            "access_token": "secret-token",
                            "user_id": "emby-user-id",
                        }
                    }
                ),
                encoding="utf-8",
            )

            previous_secrets_path = os.environ.get("HCC_SECRETS_FILE_PATH")
            os.environ["HCC_SECRETS_FILE_PATH"] = str(secrets_file)

            try:
                runtime = FakeRuntime()
                service = WebConfigService(runtime=runtime, config_file=config_file)

                prepared = service.prepare_submitted_config(
                    {
                        "media_server": {
                            "type": "emby",
                            "server_url": "http://new",
                            "display_name": "Pedro",
                        },
                        "user_password": "",
                        "user_password_configured": True,
                        "emby_server": "http://legacy",
                        "user_name": "legacy-user",
                    }
                )
            finally:
                if previous_secrets_path is None:
                    os.environ.pop("HCC_SECRETS_FILE_PATH", None)
                else:
                    os.environ["HCC_SECRETS_FILE_PATH"] = previous_secrets_path

        self.assertNotIn("user_password", prepared)
        self.assertNotIn("user_password_configured", prepared)
        self.assertNotIn("emby_server", prepared)
        self.assertNotIn("user_name", prepared)
        self.assertEqual("http://new", prepared["media_server"]["server_url"])
        self.assertEqual("secret-token", prepared["media_server"]["access_token"])
        self.assertEqual("emby-user-id", prepared["media_server"]["user_id"])

    def test_save_config_delegates_to_runtime_without_preparing_full_config(self):
        runtime = FakeRuntime()
        service = WebConfigService(runtime=runtime, config_file="/tmp/config.json")
        config = {"app": {"language": "es-ES"}}

        service.save_config(config)

        self.assertEqual(config, runtime.saved_config)


if __name__ == "__main__":
    unittest.main()
