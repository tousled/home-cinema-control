import unittest

from home_cinema_control.media_servers.common.playback_command_handler import (
    command_from_general_command_message,
    command_from_playstate_message,
)
from home_cinema_control.media_servers.jellyfin.playback_command_handler import (
    JellyfinPlaybackCommandHandler,
)
from home_cinema_control.playback.intent import PlaybackIntent, PlaybackOrigin
from home_cinema_control.playback.startup.models import DeviceCommandResult
from home_cinema_control.playback.state import BridgePlaybackState


def _playstate(handler, data):
    handler.handle_command(command_from_playstate_message(data))


def _general(handler, data):
    handler.handle_command(command_from_general_command_message(data))


class JellyfinPlaybackCommandHandlerTest(unittest.TestCase):
    def test_play_now_goes_to_parent_playback_flow(self):
        dispatcher = RecordingDispatcher()
        handler = JellyfinPlaybackCommandHandler(
            jellyfin_session=RecordingJellyfinSession(),
            playback_state=BridgePlaybackState(),
            config_provider=lambda: {},
            playback_intent_dispatcher_factory=lambda: dispatcher,
            active_publisher_provider=lambda: None,
            oppo_control_factory=lambda config: RecordingOppoControl(config, []),
        )

        handler.handle_play({"PlayCommand": "PlayNow", "ItemIds": ["1234"]})

        self.assertEqual(1, len(dispatcher.dispatched_intents))
        dispatched_intent, dispatched_origin = dispatcher.dispatched_intents[0]
        self.assertEqual("1234", dispatched_intent.media_item_id)
        self.assertEqual(PlaybackOrigin.REMOTE_CONTROL_COMMAND, dispatched_origin)

    def test_resolves_controlling_session_when_jellyfin_omits_session_id(self):
        # Jellyfin's "Play" message never carries the controller's own session
        # id either (see playback_request.py) — the handler is responsible
        # for resolving it via the user's other active sessions. Regression
        # test for the real bug: every startup notification for Jellyfin
        # silently skipped sending because this resolution never happened.
        dispatcher = RecordingDispatcher()
        handler = JellyfinPlaybackCommandHandler(
            jellyfin_session=RecordingJellyfinSession(
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

    def test_does_not_resolve_controlling_session_when_jellyfin_provides_one(self):
        jellyfin_session = RecordingJellyfinSession(controlling_session_id="should-not-be-used")
        dispatcher = RecordingDispatcher()
        handler = JellyfinPlaybackCommandHandler(
            jellyfin_session=jellyfin_session,
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
        self.assertEqual([], jellyfin_session.resolve_calls)

    def test_playstate_command_uses_latest_config(self):
        controls = []
        config = {"name": "old"}
        handler = JellyfinPlaybackCommandHandler(
            jellyfin_session=RecordingJellyfinSession(),
            playback_state=BridgePlaybackState(),
            config_provider=lambda: config,
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            active_publisher_provider=lambda: None,
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config,
                controls,
            ),
        )

        config = {"name": "new"}
        _playstate(handler, {"Command": "Stop"})

        self.assertEqual([("remote_key", "new", "STP")], controls)

    def test_audio_track_change_applies_to_oppo_and_notifies_jellyfin(self):
        controls = []
        publisher = RecordingPublisher()
        state = _default_playback_state()
        handler = JellyfinPlaybackCommandHandler(
            jellyfin_session=RecordingJellyfinSession(),
            playback_state=state,
            config_provider=lambda: {"name": "config"},
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            active_publisher_provider=lambda: publisher,
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config,
                controls,
            ),
        )

        _general(handler,
            {"Name": "SetAudioStreamIndex", "Arguments": {"Index": "2"}}
        )

        self.assertEqual([("audio", "config", 20)], controls)
        self.assertEqual(2, state.active_session.selected_audio_track_id)
        self.assertEqual("AudioTrackChange", publisher.events[-1]["event_name"])
        self.assertEqual(2, publisher.events[-1]["audio_track_id"])

    def test_seek_relative_uses_current_oppo_position(self):
        controls = []
        handler = JellyfinPlaybackCommandHandler(
            jellyfin_session=RecordingJellyfinSession(),
            playback_state=_default_playback_state(),
            config_provider=lambda: {"name": "config"},
            playback_intent_dispatcher_factory=lambda: RecordingDispatcher(),
            active_publisher_provider=lambda: None,
            oppo_control_factory=lambda current_config: RecordingOppoControl(
                current_config,
                controls,
                current_position_ticks=100,
            ),
        )

        _playstate(handler, {"Command": "SeekRelative", "SeekPositionTicks": 50})

        self.assertEqual([("seek", "config", 150)], controls)


class RecordingJellyfinSession:
    def __init__(self, controlling_session_id=None):
        self._controlling_session_id = controlling_session_id
        self.resolve_calls = []

    def find_controlling_session_id(self, controlling_user_id):
        self.resolve_calls.append(controlling_user_id)
        return self._controlling_session_id

    def get_item_info(self, user_id, item_id):
        return {"UserData": {"PlaybackPositionTicks": 0}}

    def resolve_audio_track_index(self, user_id, item_id, index):
        return index * 10

    def resolve_subtitle_track_index(self, user_id, item_id, index):
        return index * 10


class RecordingDispatcher:
    def __init__(self):
        self.dispatched_intents = []

    def dispatch(self, intent, *, origin):
        self.dispatched_intents.append((intent, origin))


class RecordingOppoControl:
    def __init__(self, config, controls, current_position_ticks=0):
        self.config = config
        self.controls = controls
        self._current_position_ticks = current_position_ticks

    def send_remote_key(self, key):
        self.controls.append(("remote_key", self.config["name"], key))
        return DeviceCommandResult.success()

    def seek_to_position_ticks(self, position_ticks):
        self.controls.append(("seek", self.config["name"], position_ticks))
        return DeviceCommandResult.success()

    def current_position_ticks(self):
        return self._current_position_ticks

    def select_audio_track(self, audio_index):
        self.controls.append(("audio", self.config["name"], audio_index))
        return DeviceCommandResult.success()

    def select_subtitle_track(self, subtitle_index):
        self.controls.append(("subtitle", self.config["name"], subtitle_index))
        return DeviceCommandResult.success()


class RecordingPublisher:
    def __init__(self):
        self.events = []
        self.last_position_ticks = 0

    def report_event(self, event_name, **kwargs):
        self.events.append({"event_name": event_name, **kwargs})


def _default_playback_state():
    state = BridgePlaybackState()
    state.start_loading(
        PlaybackIntent(
            media_item_id="item-1",
            media_source_id="source-1",
            source_user_id="user-1",
            source_client_session_id="session-1",
            source_device_id="device-1",
            source_device_name="TV",
            start_position_seconds=0,
            selected_audio_track_id=1,
            selected_subtitle_track_id=-1,
        )
    )
    state.playstate = "Playing"
    return state


if __name__ == "__main__":
    unittest.main()
