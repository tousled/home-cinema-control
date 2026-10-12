import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from home_cinema_control.playback.active_context import ActivePlaybackRuntimeContext
from home_cinema_control.playback.events import (
    PlaybackEvent,
    PlaybackEventContext,
    PlaybackHandoffFinalizedEvent,
)
from home_cinema_control.playback.handoff import PlaybackHandoffService
from home_cinema_control.playback.content_kind import MediaContentKind
from home_cinema_control.playback.intent import PlaybackIntent, PlaybackOrigin
from home_cinema_control.playback.state import BridgePlaybackState
from home_cinema_control.playback.state_detector import PlaybackStateDetector
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    PlaybackOutputSwitchResult,
)
from home_cinema_control.playback.timing import PlaybackStartupTimer


class RecordingPublisher:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


class PlaybackHandoffServiceTest(unittest.TestCase):
    def test_startup_completion_sends_content_kind_message(self):
        handoff = self._startup_handoff()
        actions = []
        messaging = SimpleNamespace(action=lambda content_kind: actions.append(content_kind))

        handoff._on_startup_completed(
            None,
            intent=_intent(),
            movie="/movies/aquaman.mkv",
            messaging=messaging,
            content_kind=MediaContentKind.CONCERT,
            playback_wiring=SimpleNamespace(
                playback_event_publisher=None,
                during_playback_orchestrator=SimpleNamespace(),
            ),
            startup_timer=PlaybackStartupTimer(),
        )

        self.assertEqual([MediaContentKind.CONCERT], actions)
        self.assertEqual("Playing", handoff._state.playstate)

    def test_startup_metric_serialization_failure_does_not_interrupt_playback(self):
        handoff = self._startup_handoff()
        messaging = SimpleNamespace(action=lambda content_kind: None)

        with patch(
            "home_cinema_control.playback.handoff.build_startup_metrics",
            side_effect=RuntimeError("serialization failed"),
        ):
            handoff._on_startup_completed(
                SimpleNamespace(),
                intent=_intent(),
                movie="/movies/aquaman.mkv",
                messaging=messaging,
                content_kind=MediaContentKind.MOVIE,
                playback_wiring=SimpleNamespace(
                    playback_event_publisher=None,
                    during_playback_orchestrator=SimpleNamespace(),
                ),
                startup_timer=PlaybackStartupTimer(),
            )

        self.assertEqual("Playing", handoff._state.playstate)

    def test_remembers_non_hdmi_tv_return_app(self):
        handoff = self._handoff()

        handoff._remember_playback_return_tv_app_id(
            _playback_result_with_previous_tv_app("com.emby.app")
        )

        self.assertEqual("com.emby.app", handoff._playback_return_tv_app_id)

    def test_does_not_overwrite_return_app_with_hdmi_input(self):
        handoff = self._handoff()
        handoff._playback_return_tv_app_id = "com.emby.app"

        handoff._remember_playback_return_tv_app_id(
            _playback_result_with_previous_tv_app("com.webos.app.hdmi3")
        )

        self.assertEqual("com.emby.app", handoff._playback_return_tv_app_id)

    def test_keeps_return_app_while_replacement_finish_is_joining(self):
        handoff = self._handoff(replacement_requested=True)
        handoff._playback_return_tv_app_id = "com.emby.app"

        handoff._clear_playback_return_tv_app_id_after_final_finish(
            _playback_result_with_previous_tv_app("com.emby.app", finished=True)
        )

        self.assertEqual("com.emby.app", handoff._playback_return_tv_app_id)

    def test_clears_return_app_after_final_finish(self):
        handoff = self._handoff()
        handoff._playback_return_tv_app_id = "com.emby.app"

        handoff._clear_playback_return_tv_app_id_after_final_finish(
            _playback_result_with_previous_tv_app("com.emby.app", finished=True)
        )

        self.assertIsNone(handoff._playback_return_tv_app_id)

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

    def _handoff(self, *, replacement_requested=False):
        return PlaybackHandoffService(
            playback_session=SimpleNamespace(config={}),
            playback_state=BridgePlaybackState(),
            media_server_playback_services=None,
            oppo_lifecycle=SimpleNamespace(finish_playback=Mock()),
            replacement_requested=lambda: replacement_requested,
        )

    def _startup_handoff(self):
        return PlaybackHandoffService(
            playback_session=SimpleNamespace(config={}),
            playback_state=BridgePlaybackState(),
            media_server_playback_services=SimpleNamespace(
                create_observed_playback_consumer=lambda **kwargs: object(),
                create_observed_track_mapper=lambda playback_session, *, playback_state: object(),
            ),
            oppo_lifecycle=SimpleNamespace(
                finish_playback=Mock(),
                record_playback_started=Mock(),
                configure_observed_event_reporting=Mock(),
            ),
            replacement_requested=lambda: False,
        )


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


def _playback_result_with_previous_tv_app(previous_tv_app_id, *, finished=False):
    return SimpleNamespace(
        startup_result=SimpleNamespace(
            output_switch_result=PlaybackOutputSwitchResult(
                previous_tv_app_id=previous_tv_app_id,
                tv_input_result=DeviceCommandResult.success(),
                av_power_result=DeviceCommandResult.success(),
                av_input_result=DeviceCommandResult.success(),
            )
        ),
        finish_result=object() if finished else None,
    )
