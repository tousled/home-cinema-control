import json
import unittest

from home_cinema_control.telemetry.snapshot import build_telemetry_payload


def _config(**overrides):
    config = {
        "Version": "1.2.3",
        "app": {
            "language": "es-ES",
            "update_webhook_url": "https://deploy.example/hook-secret",
        },
        "telemetry": {
            "enabled": True,
            "installation_id": "11111111-1111-4111-8111-111111111111",
        },
        "media_servers": {
            "active": "emby",
            "providers": {
                "emby": {
                    "server_url": "http://emby.local:8096",
                    "display_name": "Pedro Emby Server",
                    "access_token": "emby-token-secret",
                    "user_id": "emby-user-id",
                    "playback": {
                        "hcc_controlled_device": "Living Room TV",
                        "use_all_libraries": False,
                        "libraries": [
                            {
                                "id": "lib-1",
                                "name": "Private Movies",
                                "path": "/volume1/video/private",
                            }
                        ],
                        "path_mappings": [
                            {
                                "name": "Movies",
                                "source_path": "/volume1/video/private",
                                "player_path": "/mnt/private",
                                "protocol": "nfs",
                                "verified": True,
                            }
                        ],
                    },
                }
            },
        },
        "oppo": {
            "ip": "192.168.1.50",
            "use_smb": False,
        },
        "tv": {
            "enabled": True,
            "ip": "192.168.1.51",
            "mac": "aa:bb:cc:dd:ee:ff",
            "model": "LG OLED Living Room",
            "startup_script": "/config/scripts/private-tv-start.sh",
        },
        "av": {
            "enabled": True,
            "ip": "192.168.1.52",
            "model": "Denon AVC-X3800H",
            "power_on_command": "secret-power-command",
        },
        "smb": {
            "username": "nas-user",
            "password": "nas-password-secret",
        },
    }
    config.update(overrides)
    return config


class TestTelemetryPayload(unittest.TestCase):
    def test_builds_allowlisted_product_snapshot(self):
        payload = build_telemetry_payload(
            _config(),
            "heartbeat",
            event_id="22222222-2222-4222-8222-222222222222",
            occurred_at="2026-06-28T12:00:00+00:00",
        )

        self.assertEqual(1, payload.schema_version)
        self.assertEqual("heartbeat", payload.event_name)
        self.assertEqual("1.2.3", payload.hcc_version)
        self.assertEqual("es-ES", payload.language)
        self.assertEqual("emby", payload.product.media_server_provider)
        self.assertTrue(payload.product.media_server_configured)
        self.assertTrue(payload.product.media_player_configured)
        self.assertEqual("lg", payload.product.tv_model)
        self.assertEqual("denon", payload.product.av_model)
        self.assertTrue(payload.product.nfs_enabled)
        self.assertFalse(payload.product.smb_enabled)
        self.assertEqual({}, payload.event)

    def test_serialized_payload_does_not_leak_sensitive_config_values(self):
        payload = build_telemetry_payload(
            _config(),
            "playback_failed",
            event={
                "component": "path",
                "path": "/volume1/video/private/Movie.mkv",
                "token": "event-token-secret",
            },
        )

        serialized = payload.model_dump_json()

        forbidden_fragments = [
            "192.168.1.50",
            "192.168.1.51",
            "192.168.1.52",
            "aa:bb:cc:dd:ee:ff",
            "http://emby.local:8096",
            "Pedro Emby Server",
            "emby-token-secret",
            "emby-user-id",
            "Living Room TV",
            "Private Movies",
            "/volume1/video/private",
            "/mnt/private",
            "/config/scripts/private-tv-start.sh",
            "secret-power-command",
            "nas-user",
            "nas-password-secret",
            "Movie.mkv",
            "event-token-secret",
            "https://deploy.example/hook-secret",
        ]
        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, serialized)

        self.assertEqual({"result": "failed", "component": "path"}, payload.event)

    def test_unknown_models_are_not_sent_as_free_form_values(self):
        config = _config()
        config["tv"]["model"] = "Pedro Custom Cinema TV"
        config["av"]["model"] = "My Private AVR"

        payload = build_telemetry_payload(config, "heartbeat")

        self.assertEqual("unknown", payload.product.tv_model)
        self.assertEqual("unknown", payload.product.av_model)

    def test_disabled_devices_report_none_model(self):
        config = _config()
        config["tv"]["enabled"] = False
        config["av"]["enabled"] = False

        payload = build_telemetry_payload(config, "heartbeat")

        self.assertEqual("none", payload.product.tv_model)
        self.assertEqual("none", payload.product.av_model)

    def test_roadmap_interest_is_allowlisted_and_deduplicated(self):
        payload = build_telemetry_payload(
            _config(),
            "roadmap_interest_submitted",
            event={
                "interests": [
                    "plex",
                    "home_assistant",
                    "plex",
                    "/private/path",
                    "zidoo_dune",
                ],
            },
        )

        self.assertEqual(
            {"interests": ["plex", "home_assistant", "zidoo_dune"]},
            payload.event,
        )
        self.assertNotIn("/private/path", json.dumps(payload.event))

    def test_requires_installation_id(self):
        config = _config()
        config["telemetry"]["installation_id"] = ""

        with self.assertRaises(ValueError):
            build_telemetry_payload(config, "heartbeat")


if __name__ == "__main__":
    unittest.main()
