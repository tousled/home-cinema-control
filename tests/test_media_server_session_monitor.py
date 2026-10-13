import unittest
from unittest.mock import MagicMock

from home_cinema_control.media_servers.common.models import (
    MediaServerItemPlaybackInfo,
    MediaServerNowPlaying,
    MediaServerSession,
)
from home_cinema_control.media_servers.common.session_monitor import (
    MediaServerSessionMonitor,
)
from home_cinema_control.playback.events import PlaybackRejectedEvent
from home_cinema_control.playback.intent import PlaybackOrigin
from home_cinema_control.playback.state import BridgePlaybackState


class MediaServerSessionMonitorTest(unittest.TestCase):
    def setUp(self):
        self.dispatcher = MagicMock()
        self.playback_event_publisher = MagicMock()
        self.monitor = MediaServerSessionMonitor(
            provider_name="test-provider",
            playback_state=BridgePlaybackState(),
            config_provider=lambda: self._config(),
            dispatcher=self.dispatcher,
            is_item_path_in_library=lambda library_id, path: library_id == "library-1",
            playback_event_publisher=self.playback_event_publisher,
        )

    def test_admits_provider_mapped_domain_session(self):
        self.monitor.on_monitored_session(
            self._session(),
            MediaServerItemPlaybackInfo(played=False, play_count=0),
            config=self._config(),
        )

        self.dispatcher.dispatch.assert_called_once()
        intent = self.dispatcher.dispatch.call_args.args[0]
        self.assertEqual("item-1", intent.media_item_id)
        self.assertEqual(
            PlaybackOrigin.OBSERVED_TV_CLIENT,
            self.dispatcher.dispatch.call_args.kwargs["origin"],
        )

    def test_rejects_domain_session_without_verified_path_mapping(self):
        config = self._config()
        config["media_servers"]["providers"]["emby"]["playback"]["path_mappings"][0][
            "verified"
        ] = False

        self.monitor.on_monitored_session(
            self._session(),
            MediaServerItemPlaybackInfo(played=False, play_count=0),
            config=config,
        )

        self.dispatcher.dispatch.assert_not_called()
        rejected = self.playback_event_publisher.publish.call_args.args[0]
        self.assertIsInstance(rejected, PlaybackRejectedEvent)
        self.assertEqual("PATH_MAPPING_NOT_VERIFIED", rejected.diagnostic_code)

    def test_uses_the_most_specific_mapping_without_falling_back(self):
        config = self._config()
        config["media_servers"]["providers"]["emby"]["playback"]["path_mappings"] = [
            {
                "source_path": "/movies",
                "player_path": "/NAS/Movies",
                "verified": True,
            },
            {
                "source_path": "/movies/4k",
                "player_path": "/NAS/Movies4K",
                "verified": False,
            },
        ]
        session = self._session()
        session.now_playing.path = "/movies/4k/alien.mkv"

        self.monitor.on_monitored_session(
            session,
            MediaServerItemPlaybackInfo(played=False, play_count=0),
            config=config,
        )

        self.dispatcher.dispatch.assert_not_called()
        self.assertEqual("PATH_MAPPING_NOT_VERIFIED", self.monitor._state.last_diagnostic.code)

    @staticmethod
    def _session():
        return MediaServerSession(
            device_id="device-1",
            device_name="Living room TV",
            user_id="user-1",
            client_session_id="client-1",
            now_playing=MediaServerNowPlaying(
                item_id="item-1",
                name="Movie",
                path="/movies/movie.mkv",
                item_type="Movie",
                container="mkv",
            ),
            position_ticks=20_000_000,
            media_source_id="source-1",
            audio_stream_index=2,
            subtitle_stream_index=3,
        )

    @staticmethod
    def _config():
        return {
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {
                        "playback": {
                            "use_all_libraries": False,
                            "libraries": [
                                {"id": "library-1", "name": "Movies", "active": True}
                            ],
                            "path_mappings": [
                                {
                                    "source_path": "/movies",
                                    "player_path": "/NAS/Movies",
                                    "protocol": "nfs",
                                    "verified": True,
                                }
                            ],
                        }
                    }
                },
            }
        }


if __name__ == "__main__":
    unittest.main()
