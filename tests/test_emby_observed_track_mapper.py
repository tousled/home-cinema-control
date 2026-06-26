import unittest

from home_cinema_control.media_servers.emby.observed_track_mapper import (
    EmbyObservedTrackMapper,
)
from home_cinema_control.media_servers.common.media_tracks import (
    MediaTrack,
    MediaTrackKind,
)
from home_cinema_control.playback.intent import PlaybackIntent
from home_cinema_control.playback.state import BridgePlaybackState


class EmbyObservedTrackMapperTest(unittest.TestCase):
    def test_maps_observed_oppo_audio_index_to_emby_stream_index(self):
        mapper = EmbyObservedTrackMapper(
            FakeEmbySession(),
            playback_state=_playback_state(),
        )

        self.assertEqual(2, mapper.player_audio_to_source_track_id(2))

    def test_maps_observed_oppo_subtitle_index_to_emby_stream_index(self):
        mapper = EmbyObservedTrackMapper(
            FakeEmbySession(),
            playback_state=_playback_state(),
        )

        self.assertEqual(5, mapper.player_subtitle_to_source_track_id(3))

    def test_maps_observed_oppo_subtitle_off_to_emby_disabled_subtitle(self):
        mapper = EmbyObservedTrackMapper(
            FakeEmbySession(),
            playback_state=_playback_state(),
        )

        self.assertEqual(-1, mapper.player_subtitle_to_source_track_id(0))

    def test_returns_none_when_no_active_payload_exists(self):
        mapper = EmbyObservedTrackMapper(
            FakeEmbySession(),
            playback_state=BridgePlaybackState(),
        )

        self.assertIsNone(mapper.player_audio_to_source_track_id(1))

    def test_uses_active_bridge_playback_session(self):
        mapper = EmbyObservedTrackMapper(
            FakeEmbySession(),
            playback_state=_playback_state(),
        )

        self.assertEqual(2, mapper.player_audio_to_source_track_id(2))


class FakeEmbySession:
    def get_item_tracks(self, user_id, item_id):
        if user_id != "user-1" or item_id != "3092":
            raise AssertionError((user_id, item_id))

        return [
            MediaTrack(kind=MediaTrackKind.VIDEO, source_index=0),
            MediaTrack(kind=MediaTrackKind.AUDIO, source_index=1),
            MediaTrack(kind=MediaTrackKind.AUDIO, source_index=2),
            MediaTrack(kind=MediaTrackKind.SUBTITLE, source_index=3),
            MediaTrack(kind=MediaTrackKind.SUBTITLE, source_index=4),
            MediaTrack(kind=MediaTrackKind.SUBTITLE, source_index=5),
        ]


def _playback_state() -> BridgePlaybackState:
    state = BridgePlaybackState()
    state.start_loading(
        PlaybackIntent(
            media_item_id="3092",
            media_source_id="media-source-1",
            source_user_id="user-1",
            source_client_session_id="session-1",
            source_device_id="device-1",
            source_device_name="Living Room TV",
            start_position_seconds=0,
            selected_audio_track_id=2,
            selected_subtitle_track_id=5,
        )
    )
    return state


if __name__ == "__main__":
    unittest.main()
