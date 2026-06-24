import unittest

from home_cinema_control.media_servers.common.provider import (
    MediaServerProviderFactory,
    create_media_server_provider,
)
from home_cinema_control.media_servers.emby.provider import EmbyProvider
from home_cinema_control.media_servers.jellyfin.provider import JellyfinProvider


class CreateMediaServerProviderTest(unittest.TestCase):
    """create_media_server_provider dispatches via active_media_server_type,
    which reads media_servers.active.
    """

    def test_dispatches_emby_by_default(self):
        provider = create_media_server_provider({})
        self.assertIsInstance(provider, EmbyProvider)

    def test_dispatches_jellyfin_when_active(self):
        provider = create_media_server_provider(
            {"media_servers": {"active": "jellyfin"}}
        )
        self.assertIsInstance(provider, JellyfinProvider)

    def test_dispatches_from_active_pointer_with_multiple_providers_configured(self):
        provider = create_media_server_provider(
            {
                "media_servers": {
                    "active": "jellyfin",
                    "providers": {
                        "emby": {"server_url": "http://emby"},
                        "jellyfin": {"server_url": "http://jf"},
                    },
                }
            }
        )
        self.assertIsInstance(provider, JellyfinProvider)

    def test_unsupported_provider_type_raises(self):
        with self.assertRaises(ValueError):
            create_media_server_provider({"media_servers": {"active": "plex"}})

    def test_factory_create_delegates_to_function(self):
        provider = MediaServerProviderFactory().create(
            {"media_servers": {"active": "emby"}}
        )
        self.assertIsInstance(provider, EmbyProvider)


if __name__ == "__main__":
    unittest.main()
