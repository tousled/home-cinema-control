import unittest

from home_cinema_control.web.setup_verification import section_fingerprint


class MediaServerSectionPayloadTest(unittest.TestCase):
    """_section_payload's "media_server" branch reads through
    active_media_server_config/active_media_server_type, i.e. always the
    active entry in media_servers.providers, never a flat media_server dict.
    """

    def test_fingerprint_reflects_active_providers_real_data(self):
        config = {
            "media_servers": {
                "active": "jellyfin",
                "providers": {
                    "emby": {"server_url": "http://emby-stale"},
                    "jellyfin": {
                        "server_url": "http://jf",
                        "display_name": "Pedro",
                        "access_token_configured": True,
                    },
                },
            },
            "playback": {"hcc_controlled_device": "tv-1"},
        }

        other_emby_shape = {**config, "media_servers": {**config["media_servers"], "active": "emby"}}

        self.assertNotEqual(
            section_fingerprint("media_server", config),
            section_fingerprint("media_server", other_emby_shape),
        )

    def test_fingerprint_changes_when_active_provider_differs(self):
        config = {
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {"server_url": "http://emby"},
                    "jellyfin": {"server_url": "http://jf"},
                },
            }
        }
        switched = {**config, "media_servers": {**config["media_servers"], "active": "jellyfin"}}

        self.assertNotEqual(
            section_fingerprint("media_server", config),
            section_fingerprint("media_server", switched),
        )


if __name__ == "__main__":
    unittest.main()
