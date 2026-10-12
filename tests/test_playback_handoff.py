import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from home_cinema_control.playback.active_context import ActivePlaybackRuntimeContext
from home_cinema_control.playback.events import (
    PlaybackEvent,
    PlaybackEventContext,
    PlaybackHandoffFinalizedEvent,
)
from home_cinema_control.playback.handoff import PlaybackHandoffService
from home_cinema_control.playback.intent import PlaybackIntent, PlaybackOrigin
from home_cinema_control.playback.state import BridgePlaybackState
from home_cinema_control.playback.state_detector import PlaybackStateDetector


class RecordingPublisher:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


class PlaybackHandoffServiceTest(unittest.TestCase):
    def test_finalized_event_is_published_after_cleanup(self):
        state = BridgePlaybackState()
        state.start_loading(_intent())
        state.playstate = "Playing"
        context = ActivePlaybackRuntimeContext()
        context.activate(
            SimpleNamespace(
                playback_event_publisher=object(),
                startup_wiring=SimpleNamespace(media_player=object()),
            )
        )
        publisher = RecordingPublisher()
        detector = PlaybackStateDetector()
        detector.start_session(
            PlaybackEventContext(
                session_id="playback-1",
                title="Movie",
                source="emby",
                player="oppo",
            )
        )
        oppo_lifecycle = SimpleNamespace(finish_playback=Mock())
        handoff = PlaybackHandoffService(
            playback_session=SimpleNamespace(config={}),
            playback_state=state,
            media_server_playback_services=None,
            oppo_lifecycle=oppo_lifecycle,
            playback_event_publisher=publisher,
            playback_state_detector=detector,
            active_context=context,
            replacement_requested=lambda: False,
        )

        handoff._finalize_handoff(
            handoff_id="handoff-1",
            intent=_intent(),
            origin=PlaybackOrigin.OBSERVED_TV_CLIENT,
            movie="/movies/movie.mkv",
            result=SimpleNamespace(successful=True, finish_result=object()),
            orchestration_started=True,
        )

        self.assertEqual("Free", state.playstate)
        self.assertIsNone(context.publisher)
        self.assertIsNone(context.media_player)
        self.assertIsInstance(publisher.events[0], PlaybackEvent)
        finalized = publisher.events[-1]
        self.assertIsInstance(finalized, PlaybackHandoffFinalizedEvent)
        self.assertEqual("playback-1", finalized.playback_session_id)
        self.assertTrue(finalized.successful)
        oppo_lifecycle.finish_playback.assert_called_once_with({})

    def test_cleanup_and_finalized_event_run_when_handoff_raises(self):
        state = BridgePlaybackState()
        context = ActivePlaybackRuntimeContext()
        context.activate(
            SimpleNamespace(
                playback_event_publisher=object(),
                startup_wiring=SimpleNamespace(media_player=object()),
            )
        )
        publisher = RecordingPublisher()
        handoff = PlaybackHandoffService(
            playback_session=SimpleNamespace(config={}),
            playback_state=state,
            media_server_playback_services=None,
            oppo_lifecycle=SimpleNamespace(finish_playback=Mock()),
            playback_event_publisher=publisher,
            active_context=context,
            replacement_requested=lambda: False,
        )
        handoff._run_handoff = Mock(side_effect=RuntimeError("boom"))

        with self.assertRaisesRegex(RuntimeError, "boom"):
            handoff.run(_intent(), origin=PlaybackOrigin.REMOTE_CONTROL_COMMAND)

        self.assertEqual("Free", state.playstate)
        self.assertIsNone(context.publisher)
        self.assertIsNone(context.media_player)
        finalized = publisher.events[-1]
        self.assertIsInstance(finalized, PlaybackHandoffFinalizedEvent)
        self.assertFalse(finalized.successful)


def _intent() -> PlaybackIntent:
    return PlaybackIntent(
        media_item_id="item-1",
        media_source_id="source-1",
        source_user_id="user-1",
        source_client_session_id="client-1",
        source_device_id="device-1",
        source_device_name="Living room",
        start_position_seconds=0,
        selected_audio_track_id=1,
        selected_subtitle_track_id=-1,
    )
