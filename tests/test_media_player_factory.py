import unittest

from unittest.mock import patch

from home_cinema_control.playback.media_player_factory import (
    MediaPlayerType,
    configured_media_player_type,
)


class MediaPlayerFactoryTest(unittest.TestCase):
    def test_legacy_configuration_defaults_to_oppo(self):
        self.assertEqual(MediaPlayerType.OPPO, configured_media_player_type({}))

    def test_explicit_player_type_is_normalized(self):
        self.assertEqual(
            MediaPlayerType.KODI,
            configured_media_player_type({"media_player": {"type": "KODI"}}),
        )

    def test_unknown_player_type_is_rejected_before_factory_selection(self):
        with self.assertRaisesRegex(ValueError, "Unsupported media player type"):
            configured_media_player_type({"media_player": {"type": "zidoo"}})

    @patch(
        "home_cinema_control.playback.media_player_factory.create_oppo_playback_adapter"
    )
    def test_oppo_factory_selection_is_kept_behind_generic_factory(self, create_oppo):
        create_oppo.return_value = object()

        from home_cinema_control.playback.media_player_factory import (
            create_media_player_adapter,
        )

        result = create_media_player_adapter({"media_player": {"type": "oppo"}})

        self.assertIs(create_oppo.return_value, result)
        create_oppo.assert_called_once()

    def test_kodi_selection_is_explicitly_not_implemented_yet(self):
        from home_cinema_control.playback.media_player_factory import (
            create_media_player_adapter,
        )

        with self.assertRaisesRegex(NotImplementedError, "Kodi media-player"):
            create_media_player_adapter({"media_player": {"type": "kodi"}})


if __name__ == "__main__":
    unittest.main()
