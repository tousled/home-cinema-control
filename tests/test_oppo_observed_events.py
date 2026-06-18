import unittest

from home_cinema_control.devices.oppo.observed_events import (
    translate_oppo_verbose_event,
)
from home_cinema_control.devices.oppo.verbose_events import parse_verbose_event
from home_cinema_control.playback.observed_events import (
    ObservedPlaybackEventType,
    ObservedPlaybackState,
)


class OppoObservedEventsTest(unittest.TestCase):
    def test_translates_play_event(self):
        event = translate_oppo_verbose_event(parse_verbose_event("@UPL PLAY"))

        self.assertEqual(
            ObservedPlaybackEventType.PLAYBACK_STATE_CHANGED,
            event.event_type,
        )
        self.assertEqual(ObservedPlaybackState.PLAYING, event.playback_state)

    def test_translates_pause_event(self):
        event = translate_oppo_verbose_event(parse_verbose_event("@UPL PAUS"))

        self.assertEqual(
            ObservedPlaybackEventType.PLAYBACK_STATE_CHANGED,
            event.event_type,
        )
        self.assertEqual(ObservedPlaybackState.PAUSED, event.playback_state)

    def test_translates_stop_event(self):
        event = translate_oppo_verbose_event(parse_verbose_event("@UPL STOP"))

        self.assertEqual(
            ObservedPlaybackEventType.PLAYBACK_STATE_CHANGED,
            event.event_type,
        )
        self.assertEqual(ObservedPlaybackState.STOPPED, event.playback_state)

    def test_ignores_non_semantic_playback_state(self):
        event = translate_oppo_verbose_event(parse_verbose_event("@UPL MCTR"))

        self.assertIsNone(event)

    def test_translates_audio_track_event(self):
        event = translate_oppo_verbose_event(
            parse_verbose_event("@UAT TM 01/03 ENG 7.1")
        )

        self.assertEqual(
            ObservedPlaybackEventType.AUDIO_TRACK_CHANGED,
            event.event_type,
        )
        self.assertEqual(1, event.player_audio_track_index)

    def test_ignores_audio_track_departure_event(self):
        event = translate_oppo_verbose_event(
            parse_verbose_event("@UAT TH 02/03 SPA 7.1")
        )

        self.assertIsNone(event)

    def test_ignores_audio_track_transition_event(self):
        event = translate_oppo_verbose_event(
            parse_verbose_event("@UAT UN 01/03 ENG 7.1")
        )

        self.assertIsNone(event)

    def test_translates_subtitle_track_event(self):
        event = translate_oppo_verbose_event(parse_verbose_event("@UST 03/03 ENG"))

        self.assertEqual(
            ObservedPlaybackEventType.SUBTITLE_TRACK_CHANGED,
            event.event_type,
        )
        self.assertEqual(3, event.player_subtitle_track_index)

    def test_translates_subtitle_off_event(self):
        event = translate_oppo_verbose_event(parse_verbose_event("@UST 00/03 OFF"))

        self.assertEqual(
            ObservedPlaybackEventType.SUBTITLE_TRACK_CHANGED,
            event.event_type,
        )
        self.assertEqual(0, event.player_subtitle_track_index)

    def test_translates_utc_position_event(self):
        event = translate_oppo_verbose_event(
            parse_verbose_event("@UTC 000 015 C 01:15:27")
        )

        self.assertEqual(ObservedPlaybackEventType.POSITION_UPDATED, event.event_type)
        self.assertEqual(1 * 3600 + 15 * 60 + 27, event.position_seconds)

    def test_ignores_malformed_utc_event(self):
        event = translate_oppo_verbose_event(parse_verbose_event("@UTC bad"))

        self.assertIsNone(event)

    def test_ignores_unrecognized_events(self):
        event = translate_oppo_verbose_event(parse_verbose_event("@U3D 2D"))

        self.assertIsNone(event)


if __name__ == "__main__":
    unittest.main()
