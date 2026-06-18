import unittest

from home_cinema_control.media_servers.emby.constants import EMBY_TICKS_PER_SECOND
from home_cinema_control.playback.observed_event_reporter import (
    ObservedPlaybackEventReporter,
)
from home_cinema_control.playback.observed_events import (
    ObservedPlaybackEvent,
    ObservedPlaybackEventType,
    ObservedPlaybackState,
)


class ObservedPlaybackEventReporterTest(unittest.TestCase):
    def test_reports_observed_pause(self):
        sink = RecordingSink()
        reporter = _reporter(sink=sink)

        result = reporter.report(
            ObservedPlaybackEvent(
                event_type=ObservedPlaybackEventType.PLAYBACK_STATE_CHANGED,
                playback_state=ObservedPlaybackState.PAUSED,
            )
        )

        self.assertTrue(result.reported)
        self.assertEqual(
            ("event", "Pause", 123 * EMBY_TICKS_PER_SECOND, True, None, None),
            sink.calls[0],
        )

    def test_reports_observed_unpause(self):
        sink = RecordingSink()
        reporter = _reporter(sink=sink)

        result = reporter.report(
            ObservedPlaybackEvent(
                event_type=ObservedPlaybackEventType.PLAYBACK_STATE_CHANGED,
                playback_state=ObservedPlaybackState.PLAYING,
            )
        )

        self.assertTrue(result.reported)
        self.assertEqual(
            ("event", "Unpause", 123 * EMBY_TICKS_PER_SECOND, False, None, None),
            sink.calls[0],
        )

    def test_reports_observed_stop(self):
        sink = RecordingSink()
        reporter = _reporter(sink=sink)

        result = reporter.report(
            ObservedPlaybackEvent(
                event_type=ObservedPlaybackEventType.PLAYBACK_STATE_CHANGED,
                playback_state=ObservedPlaybackState.STOPPED,
            )
        )

        self.assertTrue(result.reported)
        self.assertEqual(("stopped", 123, False), sink.calls[0])

    def test_reports_observed_audio_track(self):
        sink = RecordingSink()
        reporter = _reporter(sink=sink)

        result = reporter.report(
            ObservedPlaybackEvent(
                event_type=ObservedPlaybackEventType.AUDIO_TRACK_CHANGED,
                player_audio_track_index=2,
            )
        )

        self.assertTrue(result.reported)
        self.assertEqual(
            (
                "event",
                "AudioTrackChange",
                123 * EMBY_TICKS_PER_SECOND,
                False,
                22,
                None,
            ),
            sink.calls[0],
        )

    def test_reports_observed_subtitle_track(self):
        sink = RecordingSink()
        reporter = _reporter(sink=sink)

        result = reporter.report(
            ObservedPlaybackEvent(
                event_type=ObservedPlaybackEventType.SUBTITLE_TRACK_CHANGED,
                player_subtitle_track_index=3,
            )
        )

        self.assertTrue(result.reported)
        self.assertEqual(
            (
                "event",
                "SubtitleTrackChange",
                123 * EMBY_TICKS_PER_SECOND,
                False,
                None,
                55,
            ),
            sink.calls[0],
        )

    def test_skips_unmapped_audio_track(self):
        sink = RecordingSink()
        reporter = _reporter(sink=sink, mapper=FakeTrackMapper(audio_tracks={}))

        result = reporter.report(
            ObservedPlaybackEvent(
                event_type=ObservedPlaybackEventType.AUDIO_TRACK_CHANGED,
                player_audio_track_index=2,
            )
        )

        self.assertFalse(result.reported)
        self.assertEqual([], sink.calls)

    def test_position_update_caches_seconds_and_reports_progress(self):
        sink = RecordingSink()
        reporter = _reporter(sink=sink)

        result = reporter.report(
            ObservedPlaybackEvent(
                event_type=ObservedPlaybackEventType.POSITION_UPDATED,
                position_seconds=4527,
            )
        )

        self.assertTrue(result.reported)
        self.assertEqual([("progress", 4527)], sink.calls)

    def test_state_event_uses_cached_position_over_provider(self):
        sink = RecordingSink()
        reporter = _reporter(sink=sink)
        reporter.report(
            ObservedPlaybackEvent(
                event_type=ObservedPlaybackEventType.POSITION_UPDATED,
                position_seconds=4527,
            )
        )
        sink.calls.clear()

        reporter.report(
            ObservedPlaybackEvent(
                event_type=ObservedPlaybackEventType.PLAYBACK_STATE_CHANGED,
                playback_state=ObservedPlaybackState.PAUSED,
            )
        )

        self.assertEqual(
            ("event", "Pause", 4527 * EMBY_TICKS_PER_SECOND, True, None, None),
            sink.calls[0],
        )

    def test_state_event_uses_sink_position_before_provider(self):
        sink = RecordingSink(last_position_ticks=456 * EMBY_TICKS_PER_SECOND)
        reporter = _reporter(sink=sink)

        reporter.report(
            ObservedPlaybackEvent(
                event_type=ObservedPlaybackEventType.PLAYBACK_STATE_CHANGED,
                playback_state=ObservedPlaybackState.PAUSED,
            )
        )

        self.assertEqual(
            ("event", "Pause", 456 * EMBY_TICKS_PER_SECOND, True, None, None),
            sink.calls[0],
        )


def _reporter(*, sink, mapper=None):
    return ObservedPlaybackEventReporter(
        sink=sink,
        position_provider=FakePositionProvider(),
        track_mapper=mapper or FakeTrackMapper(),
    )


class RecordingSink:
    def __init__(self, *, last_position_ticks=None):
        self.calls = []
        self._last_position_ticks = last_position_ticks

    @property
    def last_position_ticks(self):
        if self._last_position_ticks is None:
            raise AttributeError
        return self._last_position_ticks

    def report_event(
        self,
        event_name,
        *,
        position_ticks,
        is_paused=False,
        audio_track_id=None,
        subtitle_track_id=None,
    ):
        self.calls.append(
            (
                "event",
                event_name,
                position_ticks,
                is_paused,
                audio_track_id,
                subtitle_track_id,
            )
        )

    def stopped(
        self,
        *,
        position_seconds,
        duration_seconds=0,
        is_paused=False,
        is_muted=False,
        played=True,
    ):
        self.calls.append(("stopped", position_seconds, played))

    def progress(self, *, position_seconds, duration_seconds=0):
        self.calls.append(("progress", position_seconds))


class FakePositionProvider:
    def current_position_ticks(self):
        return 123 * EMBY_TICKS_PER_SECOND


class FakeTrackMapper:
    def __init__(self, *, audio_tracks=None, subtitle_tracks=None):
        self.audio_tracks = {2: 22} if audio_tracks is None else audio_tracks
        self.subtitle_tracks = (
            {0: -1, 3: 55} if subtitle_tracks is None else subtitle_tracks
        )

    def player_audio_to_source_track_id(self, player_track_index):
        return self.audio_tracks.get(player_track_index)

    def player_subtitle_to_source_track_id(self, player_track_index):
        return self.subtitle_tracks.get(player_track_index)


if __name__ == "__main__":
    unittest.main()
