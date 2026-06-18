import unittest

from home_cinema_control.web.setup_actions import (
    persist_verification_if_submitted_matches_saved,
    sanitized_submitted_section,
)


class FakeConfigService:
    def __init__(self, saved_config):
        self.saved_config = saved_config
        self.saved = None

    def load_config(self):
        return self.saved_config

    def save_config(self, config):
        self.saved = config

    def prepare_submitted_config(self, config):
        return {
            **config,
            "media_server": {
                **(config.get("media_server") or {}),
                "access_token": "secret-token",
            },
        }

    def sanitize(self, config):
        media_server = dict(config.get("media_server") or {})
        media_server.pop("access_token", None)
        return {**config, "media_server": media_server}


class SetupActionsTest(unittest.TestCase):
    def test_persists_verification_when_submitted_section_matches_saved(self):
        config = {
            "oppo": {
                "ip": "192.168.1.10",
                "connection_timeout_seconds": 3,
                "playback_start_timeout_seconds": 30,
                "nfs_mount_timeout_seconds": 60,
            }
        }
        service = FakeConfigService(config)

        _, persisted = persist_verification_if_submitted_matches_saved(
            config_service=service,
            submitted_config=config,
            section="media_player",
        )

        self.assertTrue(persisted)
        self.assertIn("setup_verification", service.saved)
        self.assertIn("media_player", service.saved["setup_verification"])

    def test_does_not_persist_verification_when_submitted_section_differs(self):
        service = FakeConfigService({"tv": {"enabled": True, "model": "LG", "ip": "1.1.1.1"}})

        _, persisted = persist_verification_if_submitted_matches_saved(
            config_service=service,
            submitted_config={"tv": {"enabled": True, "model": "LG", "ip": "1.1.1.2"}},
            section="tv",
        )

        self.assertFalse(persisted)
        self.assertIsNone(service.saved)

    def test_sanitized_submitted_section_merges_secrets_then_removes_them(self):
        service = FakeConfigService({})

        section = sanitized_submitted_section(
            config_service=service,
            submitted_config={"media_server": {"server_url": "http://emby"}},
            section_key="media_server",
        )

        self.assertEqual("http://emby", section["server_url"])
        self.assertNotIn("access_token", section)


if __name__ == "__main__":
    unittest.main()
