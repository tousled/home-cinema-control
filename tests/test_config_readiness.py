import unittest

from home_cinema_control.web.config_readiness import compute_config_readiness
from home_cinema_control.web.setup_verification import mark_section_verified


def _base_config(**overrides):
    config = {
        "media_servers": {"active": "emby", "providers": {"emby": {"server_url": ""}}},
        "oppo": {"ip": ""},
        "tv": {"enabled": False},
        "av": {"enabled": False},
    }
    config.update(overrides)
    return config


def _emby_provider(*, playback=None, **fields):
    """media_servers override for the common case of a single emby provider."""
    if playback is not None:
        fields = {**fields, "playback": playback}
    return {"active": "emby", "providers": {"emby": fields}}


class MediaServerReadinessTest(unittest.TestCase):
    def test_incomplete_when_no_url(self):
        r = compute_config_readiness(_base_config())
        self.assertEqual("incomplete", r["media_server"]["status"])

    def test_incomplete_when_url_but_no_token(self):
        r = compute_config_readiness(_base_config(
            media_servers=_emby_provider(server_url="http://emby:8096")
        ))
        self.assertEqual("incomplete", r["media_server"]["status"])
        self.assertIn("Token not configured", r["media_server"]["detail"])

    def test_configured_when_token_present(self):
        r = compute_config_readiness(_base_config(
            media_servers=_emby_provider(
                server_url="http://emby:8096",
                access_token_configured=True,
                display_name="Admin",
            )
        ))
        self.assertEqual("configured", r["media_server"]["status"])
        self.assertEqual("Admin", r["media_server"]["detail"])

    def test_configured_reads_active_provider_from_migrated_shape(self):
        config = _base_config(
            media_servers={
                "active": "jellyfin",
                "providers": {
                    "emby": {"server_url": "http://emby:8096"},
                    "jellyfin": {
                        "server_url": "http://jf:8096",
                        "access_token_configured": True,
                        "display_name": "Pedro",
                    },
                },
            }
        )
        r = compute_config_readiness(config)
        self.assertEqual("configured", r["media_server"]["status"])
        self.assertEqual("Pedro", r["media_server"]["detail"])

    def test_verified_when_matching_media_server_verification_exists(self):
        config = _base_config(
            media_servers=_emby_provider(
                server_url="http://emby:8096",
                access_token_configured=True,
                display_name="Admin",
                playback={"hcc_controlled_device": "lg-client"},
            ),
        )
        r = compute_config_readiness(mark_section_verified(config, "media_server"))
        self.assertEqual("verified", r["media_server"]["status"])

    def test_stale_when_verified_media_server_fields_change(self):
        config = _base_config(
            media_servers=_emby_provider(
                server_url="http://emby:8096",
                access_token_configured=True,
                playback={"hcc_controlled_device": "lg-client"},
            ),
        )
        verified = mark_section_verified(config, "media_server")
        verified["media_servers"]["providers"]["emby"]["playback"]["hcc_controlled_device"] = (
            "mobile-client"
        )
        r = compute_config_readiness(verified)
        self.assertEqual("stale", r["media_server"]["status"])


class MediaPlayerReadinessTest(unittest.TestCase):
    def test_incomplete_when_no_ip(self):
        r = compute_config_readiness(_base_config())
        self.assertEqual("incomplete", r["media_player"]["status"])

    def test_configured_when_ip_set(self):
        r = compute_config_readiness(_base_config(oppo={"ip": "192.168.1.10"}))
        self.assertEqual("configured", r["media_player"]["status"])
        self.assertEqual("192.168.1.10", r["media_player"]["detail"])

    def test_verified_when_matching_media_player_verification_exists(self):
        config = _base_config(oppo={"ip": "192.168.1.10"})
        r = compute_config_readiness(mark_section_verified(config, "media_player"))
        self.assertEqual("verified", r["media_player"]["status"])


class MediaPathsReadinessTest(unittest.TestCase):
    def test_incomplete_when_no_paths(self):
        r = compute_config_readiness(_base_config())
        self.assertEqual("incomplete", r["media_paths"]["status"])

    def test_incomplete_when_unverified_paths(self):
        r = compute_config_readiness(_base_config(
            media_servers=_emby_provider(
                playback={"path_mappings": [{"name": "Movies", "verified": False}]}
            )
        ))
        self.assertEqual("incomplete", r["media_paths"]["status"])
        self.assertIn("0/1", r["media_paths"]["detail"])

    def test_configured_when_all_verified(self):
        r = compute_config_readiness(_base_config(
            media_servers=_emby_provider(
                playback={"path_mappings": [{"name": "Movies", "verified": True}]}
            )
        ))
        self.assertEqual("configured", r["media_paths"]["status"])
        self.assertIn("1/1", r["media_paths"]["detail"])

    def test_ignores_inactive_providers_path_mappings(self):
        config = _base_config(
            media_servers={
                "active": "emby",
                "providers": {
                    "emby": {"playback": {"path_mappings": []}},
                    "jellyfin": {
                        "playback": {
                            "path_mappings": [{"name": "Movies", "verified": True}]
                        }
                    },
                },
            }
        )
        r = compute_config_readiness(config)
        self.assertEqual("incomplete", r["media_paths"]["status"])
        self.assertEqual("No paths configured", r["media_paths"]["detail"])


class TvReadinessTest(unittest.TestCase):
    def test_disabled_when_not_enabled(self):
        r = compute_config_readiness(_base_config())
        self.assertEqual("disabled", r["tv"]["status"])

    def test_incomplete_when_enabled_without_ip(self):
        r = compute_config_readiness(_base_config(
            tv={"enabled": True, "model": "LG", "ip": ""}
        ))
        self.assertEqual("incomplete", r["tv"]["status"])

    def test_configured_when_enabled_with_ip(self):
        r = compute_config_readiness(_base_config(
            tv={"enabled": True, "model": "LG", "ip": "192.168.1.5"}
        ))
        self.assertEqual("configured", r["tv"]["status"])

    def test_verified_when_matching_tv_verification_exists(self):
        config = _base_config(tv={"enabled": True, "model": "LG", "ip": "192.168.1.5"})
        r = compute_config_readiness(mark_section_verified(config, "tv"))
        self.assertEqual("verified", r["tv"]["status"])

    def test_stale_when_verified_tv_ip_changes(self):
        config = _base_config(tv={"enabled": True, "model": "LG", "ip": "192.168.1.5"})
        verified = mark_section_verified(config, "tv")
        verified["tv"]["ip"] = "192.168.1.55"
        r = compute_config_readiness(verified)
        self.assertEqual("stale", r["tv"]["status"])

    def test_configured_scripts_model_with_script(self):
        r = compute_config_readiness(_base_config(
            tv={"enabled": True, "model": "SCRIPTS", "startup_script": "/usr/local/bin/tv_on.sh"}
        ))
        self.assertEqual("configured", r["tv"]["status"])


class AvReadinessTest(unittest.TestCase):
    def test_disabled_when_not_enabled(self):
        r = compute_config_readiness(_base_config())
        self.assertEqual("disabled", r["av"]["status"])

    def test_incomplete_when_enabled_without_ip(self):
        r = compute_config_readiness(_base_config(
            av={"enabled": True, "model": "Denon", "ip": ""}
        ))
        self.assertEqual("incomplete", r["av"]["status"])

    def test_configured_when_enabled_with_ip(self):
        r = compute_config_readiness(_base_config(
            av={"enabled": True, "model": "Denon", "ip": "192.168.1.6"}
        ))
        self.assertEqual("configured", r["av"]["status"])

    def test_verified_when_matching_av_verification_exists(self):
        config = _base_config(av={"enabled": True, "model": "Denon", "ip": "192.168.1.6"})
        r = compute_config_readiness(mark_section_verified(config, "av"))
        self.assertEqual("verified", r["av"]["status"])


if __name__ == "__main__":
    unittest.main()
