import unittest

from home_cinema_control.devices.oppo.playback_state import (
    OppoPlaybackCategory,
    OppoPlaybackStatus,
)
from home_cinema_control.media_servers.emby.playback_command_handler import (
    EmbyPlaybackCommandHandler,
)
from home_cinema_control.playback.intent import PlaybackOrigin
from home_cinema_control.playback.state import BridgePlaybackState
from home_cinema_control.playback.startup.models import OppoPlaybackState


class EmbyPlaybackCommandHandlerTest(unittest.TestCase):
    def test_play_now_goes_to_parent_playback_flow(self):
        dispatcher = RecordingDispatcher()
        handler = EmbyPlaybackCommandHandler(
            emby_session=RecordingEmbySession(),
            playback_state=BridgePlaybackState(),
            config_provider=lambda: {},
            playback_intent_dispatcher_factory=lambda: dispatcher,
            active_publisher_provider=lambda: None,
            oppo_control_factory=lambda config: RecordingOppoControl(config, []),
        )
        payload = {"PlayCommand": "PlayNow", "ItemIds": ["1234"]}

        handler.handle_play(payload)

        self.assertEqual(1, len(dispatcher.dispatched_intents))
        dispatched_intent, dispatched_origin = dispatcher.dispatched_intents[0]
        self.assertEqual("1234", dispatched_intent.media_item_id)
        self.assertEqual(PlaybackOrigin.REMOTE_CONTROL_COMMAND, dispatched_origin)

    def test_resolves_controlling_session_when_emby_omits_session_id(self):
        # Emby's "Play" message never carries the controller's own session id
        # (see playback_request.py) — the handler is responsible for resolving
        # it via the user's other active sessions.
        dispatcher = RecordingDispatcher()
        handler = EmbyPlaybackCommandHandler(
            emby_session=RecordingEmbySession(
                controlling_session_id="resolved-session"
            ),
            playback_state=BridgePlaybackState(),
            config_provider=lambda: {},
            playback_intent_dispatcher_factory=lambda: dispatcher,
            active_publisher_provider=lambda: None,
            oppo_control_factory=lambda config: RecordingOppoControl(config, []),
        )
        payload = {
            "PlayCommand": "PlayNow",
            "ItemIds": ["1234"],
            "ControllingUserId": "user-1",
        }

        handler.handle_play(payload)

        dispatched_intent, _ = dispatcher.dispatched_intents[0]
        self.assertEqual("resolved-session", dispatched_intent.source_client_session_id)

    def test_does_not_resolve_controlling_session_when_emby_provides_one(self):
        emby_session = RecordingEmbySession(controlling_session_id="should-not-be-used")
        dispatcher = RecordingDispatcher()
        handler = EmbyPlaybackCommandHandler(
            emby_session=emby_session,
            playback_state=BridgePlaybackState(),
            config_provider=lambda: {},
            playback_intent_dispatcher_factory=lambda: dispatcher,
            active_publisher_provider=lambda: None,
            oppo_control_factory=lambda config: RecordingOppoControl(config, []),
        )
        payload = {
            "PlayCommand": "PlayNow",
            "ItemIds": ["1234"],
            "SessionID": "real-session",
        }

        handler.handle_play(payload)

        dispatched_intent, _ = dispatcher.dispatched_intents[0]
        self.assertEqual("real-session", dispatched_intent.source_client_session_id)
        self.assertEqual([], emby_session.resolve_calls)

    def test_playstate_command_uses_latest_config(self):
        controls = []
        config = {"name": "old"}
        handler = EmbyPlaybackCommandHandler(
            emby_session=RecordingEmbySession(),
            playback_state=BridgePlaybackState(),
            config_provider=lambda: config,
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            active_publisher_provider=lambda: None,
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config, controls
            ),
        )

        config = {"name": "new"}
        handler.handle_playback_state({"Command": "Stop"})

        self.assertEqual([("remote_key", "new", "STP")], controls)

    def test_pause_does_not_toggle_oppo_when_already_paused(self):
        controls = []
        publisher = RecordingPublisher()
        state = _default_playback_state()
        state.playstate = "Paused"
        handler = EmbyPlaybackCommandHandler(
            emby_session=RecordingEmbySession(),
            playback_state=state,
            config_provider=lambda: {"name": "config"},
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config,
                controls,
                playback_states=[
                    _state(OppoPlaybackStatus.PAUSE),
                ],
            ),
            active_publisher_provider=lambda: publisher,
        )

        handler.handle_playback_state({"Command": "Pause"})

        self.assertNotIn(("remote_key", "config", "PAU"), controls)
        self.assertEqual("Paused", state.playstate)
        self.assertEqual("Pause", publisher.events[-1]["event_name"])
        self.assertTrue(publisher.events[-1]["is_paused"])

    def test_unpause_does_not_send_play_when_oppo_is_already_playing(self):
        controls = []
        publisher = RecordingPublisher()
        state = _default_playback_state()
        state.playstate = "Playing"
        handler = EmbyPlaybackCommandHandler(
            emby_session=RecordingEmbySession(),
            playback_state=state,
            config_provider=lambda: {"name": "config"},
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config,
                controls,
                playback_states=[
                    _state(OppoPlaybackStatus.PLAY),
                ],
            ),
            active_publisher_provider=lambda: publisher,
        )

        handler.handle_playback_state({"Command": "Unpause"})

        self.assertNotIn(("remote_key", "config", "PLA"), controls)
        self.assertEqual("Playing", state.playstate)
        self.assertEqual("Unpause", publisher.events[-1]["event_name"])
        self.assertFalse(publisher.events[-1]["is_paused"])

    def test_playpause_reports_resulting_oppo_state_after_toggle(self):
        controls = []
        publisher = RecordingPublisher()
        state = _default_playback_state()
        state.playstate = "Playing"
        handler = EmbyPlaybackCommandHandler(
            emby_session=RecordingEmbySession(),
            playback_state=state,
            config_provider=lambda: {"name": "config"},
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config,
                controls,
                playback_states=[
                    _state(OppoPlaybackStatus.PAUSE),
                ],
            ),
            active_publisher_provider=lambda: publisher,
        )

        handler.handle_playback_state({"Command": "PlayPause"})

        self.assertIn(("remote_key", "config", "PAU"), controls)
        self.assertEqual("Paused", state.playstate)
        self.assertEqual("Pause", publisher.events[-1]["event_name"])
        self.assertTrue(publisher.events[-1]["is_paused"])

    def test_playpause_does_not_read_oppo_state_when_active_publisher_exists(self):
        controls = []
        state_reads = []
        publisher = RecordingPublisher()
        state = _default_playback_state()
        state.playstate = "Playing"
        handler = EmbyPlaybackCommandHandler(
            emby_session=RecordingEmbySession(),
            playback_state=state,
            config_provider=lambda: {"name": "config"},
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config,
                controls,
                on_get_state=lambda: state_reads.append("qpl"),
            ),
            active_publisher_provider=lambda: publisher,
        )

        handler.handle_playback_state({"Command": "PlayPause"})

        self.assertEqual([], state_reads)
        self.assertIn(("remote_key", "config", "PAU"), controls)
        self.assertEqual("Paused", state.playstate)
        self.assertEqual("Pause", publisher.events[-1]["event_name"])
        self.assertTrue(publisher.events[-1]["is_paused"])

    def test_audio_track_change_applies_to_oppo_and_notifies_emby(self):
        controls = []
        publisher = RecordingPublisher()
        state = _default_playback_state()
        handler = EmbyPlaybackCommandHandler(
            emby_session=RecordingEmbySession(),
            playback_state=state,
            config_provider=lambda: {"name": "config"},
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config, controls
            ),
            active_publisher_provider=lambda: publisher,
        )

        handler.handle_general_command(
            {"Name": "SetAudioStreamIndex", "Arguments": {"Index": "2"}}
        )

        self.assertIn(("audio", "config", 2), controls)
        self.assertEqual(2, state.active_session.selected_audio_track_id)
        self.assertEqual("AudioTrackChange", publisher.events[-1]["event_name"])
        self.assertEqual(2, publisher.events[-1]["audio_track_id"])

    def test_audio_track_change_does_not_read_oppo_state_when_active_publisher_exists(self):
        controls = []
        state_reads = []
        publisher = RecordingPublisher()
        state = _default_playback_state()
        state.playstate = "Paused"
        handler = EmbyPlaybackCommandHandler(
            emby_session=RecordingEmbySession(),
            playback_state=state,
            config_provider=lambda: {"name": "config"},
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config,
                controls,
                on_get_state=lambda: state_reads.append("qpl"),
            ),
            active_publisher_provider=lambda: publisher,
        )

        handler.handle_general_command(
            {"Name": "SetAudioStreamIndex", "Arguments": {"Index": "2"}}
        )

        self.assertEqual([], state_reads)
        self.assertIn(("audio", "config", 2), controls)
        self.assertEqual("AudioTrackChange", publisher.events[-1]["event_name"])
        self.assertTrue(publisher.events[-1]["is_paused"])

    def test_audio_track_change_without_active_publisher_skips_emby_event(self):
        controls = []
        state = _default_playback_state()
        handler = EmbyPlaybackCommandHandler(
            emby_session=RecordingEmbySession(),
            playback_state=state,
            config_provider=lambda: {"name": "config"},
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config, controls
            ),
            active_publisher_provider=lambda: None,
        )

        handler.handle_general_command(
            {"Name": "SetAudioStreamIndex", "Arguments": {"Index": "2"}}
        )

        self.assertIn(("audio", "config", 2), controls)
        self.assertEqual(2, state.active_session.selected_audio_track_id)

    def test_subtitle_track_change_applies_to_oppo_and_notifies_emby(self):
        controls = []
        publisher = RecordingPublisher()
        state = _default_playback_state()
        handler = EmbyPlaybackCommandHandler(
            emby_session=RecordingEmbySession(),
            playback_state=state,
            config_provider=lambda: {"name": "config"},
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config, controls
            ),
            active_publisher_provider=lambda: publisher,
        )

        handler.handle_general_command(
            {"Name": "SetSubtitleStreamIndex", "Arguments": {"Index": "3"}}
        )

        self.assertIn(("subtitle", "config", 1), controls)
        self.assertEqual(3, state.active_session.selected_subtitle_track_id)
        self.assertEqual("SubtitleTrackChange", publisher.events[-1]["event_name"])
        self.assertEqual(3, publisher.events[-1]["subtitle_track_id"])

    def test_subtitle_track_change_does_not_read_oppo_state_when_active_publisher_exists(self):
        controls = []
        state_reads = []
        publisher = RecordingPublisher()
        state = _default_playback_state()
        handler = EmbyPlaybackCommandHandler(
            emby_session=RecordingEmbySession(),
            playback_state=state,
            config_provider=lambda: {"name": "config"},
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config,
                controls,
                on_get_state=lambda: state_reads.append("qpl"),
            ),
            active_publisher_provider=lambda: publisher,
        )

        handler.handle_general_command(
            {"Name": "SetSubtitleStreamIndex", "Arguments": {"Index": "3"}}
        )

        self.assertEqual([], state_reads)
        self.assertIn(("subtitle", "config", 1), controls)
        self.assertEqual("SubtitleTrackChange", publisher.events[-1]["event_name"])

    def test_seek_uses_absolute_position_from_emby(self):
        controls = []
        handler = EmbyPlaybackCommandHandler(
            emby_session=RecordingEmbySession(),
            playback_state=BridgePlaybackState(),
            config_provider=lambda: {"name": "config"},
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            active_publisher_provider=lambda: None,
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config, controls
            ),
        )

        handler.handle_playback_state(
            {
                "Command": "Seek",
                "SeekPositionTicks": 120_000_000,
            }
        )

        self.assertEqual([("seek", "config", 120_000_000)], controls)

    def test_seek_relative_adds_delta_to_current_oppo_position(self):
        controls = []
        handler = EmbyPlaybackCommandHandler(
            emby_session=RecordingEmbySession(),
            playback_state=BridgePlaybackState(),
            config_provider=lambda: {"name": "config"},
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            active_publisher_provider=lambda: None,
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config, controls, current_position_ticks=1_000_000_000
            ),
        )

        handler.handle_playback_state(
            {
                "Command": "SeekRelative",
                "SeekPositionTicks": 30_000_000,
            }
        )

        self.assertEqual([("seek", "config", 1_030_000_000)], controls)

    def test_seek_relative_never_seeks_before_start(self):
        controls = []
        handler = EmbyPlaybackCommandHandler(
            emby_session=RecordingEmbySession(),
            playback_state=BridgePlaybackState(),
            config_provider=lambda: {"name": "config"},
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            active_publisher_provider=lambda: None,
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config, controls, current_position_ticks=100_000_000
            ),
        )

        handler.handle_playback_state(
            {
                "Command": "SeekRelative",
                "SeekPositionTicks": -30_000_0000,
            }
        )

        self.assertEqual([("seek", "config", 0)], controls)

    def test_fast_forward_defaults_to_ten_second_relative_seek(self):
        controls = []
        handler = EmbyPlaybackCommandHandler(
            emby_session=RecordingEmbySession(),
            playback_state=BridgePlaybackState(),
            config_provider=lambda: {"name": "config"},
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            active_publisher_provider=lambda: None,
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config, controls, current_position_ticks=1_000_000_000
            ),
        )

        handler.handle_playback_state({"Command": "FastForward"})

        self.assertEqual([("seek", "config", 1_100_000_000)], controls)

    def test_rewind_defaults_to_ten_second_relative_seek(self):
        controls = []
        handler = EmbyPlaybackCommandHandler(
            emby_session=RecordingEmbySession(),
            playback_state=BridgePlaybackState(),
            config_provider=lambda: {"name": "config"},
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            active_publisher_provider=lambda: None,
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config, controls, current_position_ticks=1_000_000_000
            ),
        )

        handler.handle_playback_state({"Command": "Rewind"})

        self.assertEqual([("seek", "config", 900_000_000)], controls)


class RecordingDispatcher:
    def __init__(self):
        self.dispatched_intents = []

    def dispatch(self, intent, *, origin):
        self.dispatched_intents.append((intent, origin))


class RecordingPublisher:
    def __init__(self):
        self.events = []
        self.last_position_ticks = 0

    def report_event(
        self,
        event_name,
        *,
        position_ticks,
        is_paused=False,
        audio_track_id=None,
        subtitle_track_id=None,
        **kwargs,
    ):
        self.events.append(
            {
                "event_name": event_name,
                "position_ticks": position_ticks,
                "is_paused": is_paused,
                "audio_track_id": audio_track_id,
                "subtitle_track_id": subtitle_track_id,
            }
        )


def _default_playback_state() -> BridgePlaybackState:
    state = BridgePlaybackState()
    state.start_loading(_intent())
    return state


def _intent():
    from home_cinema_control.playback.intent import PlaybackIntent

    return PlaybackIntent(
        media_item_id="item-1",
        media_source_id="media-source-1",
        source_user_id="user-1",
        source_client_session_id=None,
        source_device_id="",
        source_device_name="",
        start_position_seconds=0,
        selected_audio_track_id=1,
        selected_subtitle_track_id=-1,
    )


class RecordingEmbySession:
    def __init__(self, controlling_session_id=None):
        self._controlling_session_id = controlling_session_id
        self.resolve_calls = []

    def find_controlling_session_id(self, controlling_user_id):
        self.resolve_calls.append(controlling_user_id)
        return self._controlling_session_id

    def get_item_info(self, user_id, item_id):
        return {
            "MediaStreams": [
                {"Type": "Video", "Index": 0},
                {"Type": "Audio", "Index": 1},
                {"Type": "Audio", "Index": 2},
                {"Type": "Subtitle", "Index": 3},
                {"Type": "Subtitle", "Index": 4},
            ]
        }

    def resolve_audio_track_index(self, user_id, item_id, index):
        info = self.get_item_info(user_id, item_id)
        oppo_index = 0
        for stream in info["MediaStreams"]:
            if stream["Type"] == "Audio":
                oppo_index += 1
                if stream["Index"] == index:
                    return oppo_index
        return 1

    def resolve_subtitle_track_index(self, user_id, item_id, index):
        if index < 0:
            return 0
        info = self.get_item_info(user_id, item_id)
        oppo_index = 0
        for stream in info["MediaStreams"]:
            if stream["Type"] == "Subtitle":
                oppo_index += 1
                if stream["Index"] == index:
                    return oppo_index
        return 0


class RecordingOppoControl:
    def __init__(
        self,
        config,
        calls,
        *,
        current_position_ticks=0,
        playback_states=None,
        on_get_state=None,
    ):
        self._config = config
        self._calls = calls
        self._current_position_ticks = current_position_ticks
        self._playback_states = list(playback_states or [_state(OppoPlaybackStatus.PLAY)])
        self._on_get_state = on_get_state

    def send_remote_key(self, key):
        self._calls.append(("remote_key", self._config["name"], key))
        return RecordingCommandResult(successful=True)

    def select_audio_track(self, audio_index):
        self._calls.append(("audio", self._config["name"], audio_index))
        return RecordingCommandResult(successful=True)

    def select_subtitle_track(self, subtitle_index):
        self._calls.append(("subtitle", self._config["name"], subtitle_index))
        return RecordingCommandResult(successful=True)

    def seek_to_position_ticks(self, position_ticks):
        self._calls.append(("seek", self._config["name"], position_ticks))
        return RecordingCommandResult(successful=True)

    def current_position_ticks(self):
        return self._current_position_ticks

    def get_playback_state(self):
        if self._on_get_state is not None:
            self._on_get_state()

        if len(self._playback_states) > 1:
            return self._playback_states.pop(0)

        return self._playback_states[0]


class RecordingCommandResult:
    def __init__(self, *, successful):
        self.successful = successful



def _state(status):
    return OppoPlaybackState(
        status=status,
        category=OppoPlaybackCategory.ACTIVE,
        raw_response=f"@OK {status.value}",
        ok=True,
    )


if __name__ == "__main__":
    unittest.main()
