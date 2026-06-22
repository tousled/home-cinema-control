import unittest
from types import SimpleNamespace

from home_cinema_control.media_servers.emby.playback import (
    MediaContentKind,
    MediaServerPlaybackSource,
)
from home_cinema_control.playback.intent import PlaybackIntent
from home_cinema_control.playback.state import ActivePlaybackSession, BridgePlaybackState


class BridgePlaybackStateTest(unittest.TestCase):
    def test_tracks_active_session_from_playback_intent(self):
        state = BridgePlaybackState()
        intent = _intent()

        state.start_loading(intent)

        self.assertEqual("Loading", state.playstate)
        self.assertIsInstance(state.active_session, ActivePlaybackSession)
        self.assertEqual("media-1", state.active_session.media_item_id)
        self.assertEqual(123, state.active_session.start_position_seconds)

    def test_applies_media_location_to_active_session(self):
        state = BridgePlaybackState()
        state.start_loading(_intent())
        media_location = SimpleNamespace(
            content_server="nas",
            content_directory="Movies/Film",
            playback_file_name="movie.mkv",
            playback_file_format="mkv",
            network_protocol="nfs",
        )

        state.set_active_media_location(
            media_location=media_location,
            item_info=MediaServerPlaybackSource(
                path="/nas/Movies/Film/movie.mkv",
                container="mkv",
                duration_seconds=0,
                production_year=2021,
                title="Movie Name",
                content_kind=MediaContentKind.MOVIE,
            ),
        )

        self.assertEqual("nas", state.active_session.content_server)
        self.assertEqual("Movies/Film", state.active_session.content_directory)
        self.assertEqual("movie.mkv", state.active_session.playback_file_name)
        self.assertEqual("mkv", state.active_session.playback_file_format)
        self.assertEqual("nfs", state.active_session.network_protocol)
        self.assertEqual(2021, state.active_session.production_year)
        self.assertEqual("Movie Name", state.active_session.title)

    def test_updates_selected_tracks_on_active_session(self):
        state = BridgePlaybackState()
        state.start_loading(_intent())

        state.update_active_tracks(audio_track_id=3, subtitle_track_id=4)

        self.assertEqual(3, state.active_session.selected_audio_track_id)
        self.assertEqual(4, state.active_session.selected_subtitle_track_id)

    def test_finishes_active_session(self):
        state = BridgePlaybackState()
        state.start_loading(_intent())
        state.playstate = "Playing"

        state.finish()

        self.assertEqual("Free", state.playstate)
        self.assertIsNone(state.active_session)


def _intent() -> PlaybackIntent:
    return PlaybackIntent(
        media_item_id="media-1",
        media_source_id="source-1",
        source_user_id="user-1",
        source_client_session_id="session-1",
        source_device_id="device-1",
        source_device_name="Living Room TV",
        start_position_seconds=123,
        selected_audio_track_id=2,
        selected_subtitle_track_id=-1,
    )


if __name__ == "__main__":
    unittest.main()
