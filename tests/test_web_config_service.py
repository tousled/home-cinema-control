import json
import os
import tempfile
import unittest
from pathlib import Path

from home_cinema_control.config.models import (
    AppConfig,
    MediaServerProviderConfig,
    OppoConfig,
)
from home_cinema_control.web.config_service import WebConfigService


class FakeRuntime:
    def __init__(self):
        self.config = {
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {
                        "server_url": "http://emby",
                        "display_name": "Pedro",
                        "access_token": "secret-token",
                        "user_id": "emby-user-id",
                    }
                },
            }
        }
        self.saved_config = None

    def load_config(self):
        return dict(self.config)

    def save_config(self, config):
        self.saved_config = dict(config)


class WebConfigServiceTest(unittest.TestCase):
    def test_load_model_validates_runtime_config_and_applies_defaults(self):
        service = WebConfigService(runtime=FakeRuntime(), config_file="/tmp/config.json")

        model = service.load_model()

        self.assertEqual("emby", model.media_servers.active)
        self.assertIsInstance(model.app, AppConfig)
        self.assertIsInstance(model.oppo, OppoConfig)

    def test_section_accessors_return_typed_config_models(self):
        service = WebConfigService(runtime=FakeRuntime(), config_file="/tmp/config.json")
        config = {
            "app": {"include_prerelease": True},
            "oppo": {"ip": "192.168.1.10"},
            "media_servers": {
                "active": "jellyfin",
                "providers": {
                    "jellyfin": {
                        "server_url": "http://jellyfin",
                        "display_name": "Jellyfin",
                    }
                },
            },
        }

        self.assertTrue(service.app(config).include_prerelease)
        self.assertEqual("192.168.1.10", service.oppo(config).ip)
        self.assertEqual("jellyfin", service.active_media_server_type(config))
        self.assertIsInstance(
            service.active_media_server(config),
            MediaServerProviderConfig,
        )
        self.assertEqual(
            "http://jellyfin",
            service.active_media_server(config).server_url,
        )

    def test_with_app_updates_applies_typed_defaults_and_preserves_other_sections(self):
        service = WebConfigService(runtime=FakeRuntime(), config_file="/tmp/config.json")
        config = {
            "app": {"include_prerelease": False},
            "oppo": {"ip": "192.168.1.10"},
        }

        updated = service.with_app_updates(config, include_prerelease=True)

        self.assertIsNot(config, updated)
        self.assertTrue(updated["app"]["include_prerelease"])
        self.assertEqual("tousled/home-cinema-control", updated["app"]["release_repository"])
        self.assertEqual({"ip": "192.168.1.10"}, updated["oppo"])

    def test_sanitized_config_loads_and_sanitizes_once(self):
        service = WebConfigService(runtime=FakeRuntime(), config_file="/tmp/config.json")

        sanitized = service.sanitized_config()

        provider = sanitized["media_servers"]["providers"]["emby"]
        self.assertTrue(provider["access_token_configured"])
        self.assertNotIn("access_token", provider)

    def test_sanitizes_loaded_config_for_web(self):
        service = WebConfigService(runtime=FakeRuntime(), config_file="/tmp/config.json")

        sanitized = service.sanitize(service.load_config())

        provider = sanitized["media_servers"]["providers"]["emby"]
        self.assertEqual("http://emby", provider["server_url"])
        self.assertEqual("Pedro", provider["display_name"])
        self.assertTrue(provider["access_token_configured"])
        self.assertNotIn("access_token", provider)
        self.assertNotIn("user_id", provider)

    def test_prepare_submitted_config_preserves_existing_media_server_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            secrets_file = Path(directory) / "secrets.json"

            config_file.write_text(
                json.dumps(
                    {
                        "media_servers": {
                            "active": "emby",
                            "providers": {
                                "emby": {"server_url": "http://old", "display_name": "Pedro"}
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            secrets_file.write_text(
                json.dumps(
                    {
                        "media_servers": {
                            "providers": {
                                "emby": {
                                    "access_token": "secret-token",
                                    "user_id": "emby-user-id",
                                }
                            }
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
                        "media_servers": {
                            "active": "emby",
                            "providers": {
                                "emby": {"server_url": "http://new", "display_name": "Pedro"}
                            },
                        }
                    }
                )
            finally:
                if previous_secrets_path is None:
                    os.environ.pop("HCC_SECRETS_FILE_PATH", None)
                else:
                    os.environ["HCC_SECRETS_FILE_PATH"] = previous_secrets_path

        provider = prepared["media_servers"]["providers"]["emby"]
        self.assertEqual("http://new", provider["server_url"])
        self.assertEqual("Pedro", provider["display_name"])
        self.assertEqual("secret-token", provider["access_token"])
        self.assertEqual("emby-user-id", provider["user_id"])
        self.assertIsNone(runtime.saved_config)

    def test_prepare_submitted_config_does_not_reintroduce_legacy_password_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            secrets_file = Path(directory) / "secrets.json"

            config_file.write_text(
                json.dumps(
                    {
                        "media_servers": {
                            "active": "emby",
                            "providers": {
                                "emby": {"server_url": "http://old", "display_name": "Pedro"}
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            secrets_file.write_text(
                json.dumps(
                    {
                        "media_servers": {
                            "providers": {
                                "emby": {
                                    "access_token": "secret-token",
                                    "user_id": "emby-user-id",
                                }
                            }
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
                        "media_servers": {
                            "active": "emby",
                            "providers": {
                                "emby": {"server_url": "http://new", "display_name": "Pedro"}
                            },
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
        provider = prepared["media_servers"]["providers"]["emby"]
        self.assertEqual("http://new", provider["server_url"])
        self.assertEqual("secret-token", provider["access_token"])
        self.assertEqual("emby-user-id", provider["user_id"])

    def test_save_config_delegates_to_runtime_without_preparing_full_config(self):
        runtime = FakeRuntime()
        service = WebConfigService(runtime=runtime, config_file="/tmp/config.json")
        config = {"app": {"language": "es-ES"}}

        service.save_config(config)

        self.assertEqual(config, runtime.saved_config)


if __name__ == "__main__":
    unittest.main()
