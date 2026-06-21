from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from home_cinema_control.media_servers.emby.playback_request import (
    build_playback_intent_from_play_command,
)
from home_cinema_control.media_servers.emby.constants import EMBY_TICKS_PER_SECOND
from home_cinema_control.playback.intent import PlaybackOrigin
from home_cinema_control.playback.ports import MediaPlayerControl
from home_cinema_control.playback.state import BridgePlaybackState
DEFAULT_REMOTE_SKIP_SECONDS = 10


class EmbyPlaybackCommandHandler:
    """Translate Emby playback commands into bridge playback actions."""

    def __init__(
        self,
        *,
        emby_session,
        playback_state: BridgePlaybackState,
        config_provider: Callable[[], dict[str, Any]],
        playback_intent_dispatcher_factory: Callable,
        active_publisher_provider: Callable[[], Any],
        oppo_control_factory: Callable[[dict[str, Any]], MediaPlayerControl],
    ) -> None:
        self._emby_session = emby_session
        self._state = playback_state
        self._config_provider = config_provider
        self._playback_intent_dispatcher_factory = playback_intent_dispatcher_factory
        self._oppo_control_factory = oppo_control_factory
        self._active_publisher_provider = active_publisher_provider

    def handle_play(self, data: dict) -> None:
        command = data["PlayCommand"]
        if command != "PlayNow":
            return

        logging.info(
            "Emby websocket play command | command=%s | item_ids=%s | "
            "start_position_present=%s | start_position_ticks=%s | "
            "saved_position_ticks=%s | media_source_id=%s | "
            "audio_stream_index=%s | subtitle_stream_index=%s | "
            "device=%s",
            command,
            data.get("ItemIds"),
            "StartPositionTicks" in data,
            data.get("StartPositionTicks"),
            data.get("SavedPlaybackPositionTicks"),
            data.get("MediaSourceId"),
            data.get("AudioStreamIndex"),
            data.get("SubtitleStreamIndex"),
            data.get("DeviceName"),
        )
        intent = build_playback_intent_from_play_command(
            data,
            load_item_info=self._emby_session.get_item_info,
        )
        self._playback_intent_dispatcher_factory().dispatch(
            intent,
            origin=PlaybackOrigin.REMOTE_CONTROL_COMMAND,
        )

    def handle_general_command(self, data: dict) -> None:
        command = data["Name"]
        args = data["Arguments"]

        if command == "SetAudioStreamIndex":
            self._handle_audio_track_change(args)

        if command == "SetSubtitleStreamIndex":
            self._handle_subtitle_track_change(args)


    def handle_playback_state(self, data: dict) -> None:
        command = data["Command"]
        if command == "Seek":
            self._seek_to_absolute_position(data)
            return

        if command == "SeekRelative":
            self._seek_to_relative_position(data)
            return

        if command == "FastForward":
            self._seek_to_relative_position(
                data,
                default_relative_ticks=(
                    DEFAULT_REMOTE_SKIP_SECONDS * EMBY_TICKS_PER_SECOND
                ),
            )
            return

        if command == "Rewind":
            self._seek_to_relative_position(
                data,
                default_relative_ticks=(
                    -DEFAULT_REMOTE_SKIP_SECONDS * EMBY_TICKS_PER_SECOND
                ),
            )
            return

        if command in {"Pause", "Unpause", "PlayPause"}:
            self._handle_play_pause_command(command)
            return

        remote_key = _remote_key_for_playstate_command(command)
        if remote_key is None:
            logging.debug(
                "Ignoring unsupported Emby playstate command | command=%s | data=%s",
                command,
                data,
            )
            return

        result = self._oppo_control.send_remote_key(remote_key)
        if not result.successful:
            logging.error(
                "OPPO playstate command failed | command=%s | result=%s",
                command,
                result,
            )

    def _handle_audio_track_change(self, args: dict[str, Any]) -> None:
        emby_audio_index = int(args["Index"])
        params = self._current_playback_request_params()
        audio_index = self._emby_session.resolve_audio_track_index(
            params["ControllingUserId"],
            params["item_id"],
            emby_audio_index,
        )
        logging.info(
            "Mapped Emby audio index to OPPO audio index | emby_index=%s | oppo_index=%s",
            emby_audio_index,
            audio_index,
        )
        result = self._oppo_control.select_audio_track(audio_index)
        if not result.successful:
            logging.error("OPPO audio track change failed | result=%s", result)
            return

        self._state.update_active_tracks(audio_track_id=emby_audio_index)
        self._report_interaction_event(
            "AudioTrackChange",
            audio_stream_index=emby_audio_index,
        )

    def _handle_subtitle_track_change(self, args: dict[str, Any]) -> None:
        emby_subtitle_index = int(args["Index"])
        params = self._current_playback_request_params()
        subtitle_index = self._emby_session.resolve_subtitle_track_index(
            params["ControllingUserId"],
            params["item_id"],
            emby_subtitle_index,
        )
        logging.info(
            "Mapped Emby subtitle index to OPPO subtitle index | emby_index=%s | oppo_index=%s",
            emby_subtitle_index,
            subtitle_index,
        )
        result = self._oppo_control.select_subtitle_track(subtitle_index)
        if not result.successful:
            logging.error("OPPO subtitle track change failed | result=%s", result)
            return

        self._state.update_active_tracks(subtitle_track_id=emby_subtitle_index)
        self._report_interaction_event(
            "SubtitleTrackChange",
            subtitle_stream_index=emby_subtitle_index,
        )

    def _handle_play_pause_command(self, command: str) -> None:
        oppo_state = None
        if self._active_publisher() is None:
            oppo_state = self._current_oppo_state_or_none()

        if self._play_pause_command_is_already_satisfied(command, oppo_state):
            logging.info(
                "Skipping OPPO play/pause command because requested state is already active | "
                "command=%s | oppo_state=%s | bridge_playstate=%s",
                command,
                oppo_state.status.value if oppo_state is not None else None,
                self._state.playstate,
            )
            self._report_playstate_interaction_from_current_state(command)
            return

        remote_key = _remote_key_for_playstate_command(command)
        if remote_key is None:
            return

        # Update bridge state before the hardware command so that a concurrent
        # duplicate Playstate message from Emby is rejected by _play_pause_command_is_already_satisfied.
        previous_playstate = self._state.playstate
        if command == "Pause":
            self._state.playstate = "Paused"
        elif command == "Unpause":
            self._state.playstate = "Playing"
        elif command == "PlayPause":
            self._state.playstate = (
                "Playing" if self._state.playstate == "Paused" else "Paused"
            )

        result = self._oppo_control.send_remote_key(remote_key)
        if not result.successful:
            logging.error(
                "OPPO play/pause command failed | command=%s | result=%s",
                command,
                result,
            )
            self._state.playstate = previous_playstate
            return

        self._report_playstate_interaction_from_current_state(command)

    def _play_pause_command_is_already_satisfied(
        self,
        command: str,
        oppo_state,
    ) -> bool:
        # Both the bridge state and the live OPPO state are valid indicators.
        # OR logic: either source alone is enough to declare the command satisfied.
        # This handles two cases:
        #   - Common: bridge state is authoritative for commands the bridge sent.
        #   - Edge case: OPPO physical remote changed state that the bridge hasn't seen yet.
        if command == "Pause":
            return (
                oppo_state is not None and oppo_state.is_paused
            ) or self._state.playstate == "Paused"

        if command == "Unpause":
            return (
                oppo_state is not None and oppo_state.is_playing
            ) or self._state.playstate != "Paused"

        return False

    def _current_oppo_state_or_none(self):
        try:
            return self._oppo_control.get_playback_state()
        except Exception:
            logging.exception("Could not read OPPO state before play/pause command.")
            return None

    def _seek_to_absolute_position(self, data: dict) -> None:
        position_ticks = int(data["SeekPositionTicks"])
        logging.info(
            "Seeking OPPO playback to absolute media-server position | "
            "position_ticks=%s",
            position_ticks,
        )
        self._oppo_control.seek_to_position_ticks(position_ticks)

    def _seek_to_relative_position(
        self,
        data: dict,
        *,
        default_relative_ticks: int = 0,
    ) -> None:
        relative_ticks = int(data.get("SeekPositionTicks", default_relative_ticks))
        current_ticks = self._current_oppo_position_ticks()
        target_ticks = max(0, current_ticks + relative_ticks)

        logging.info(
            "Seeking OPPO playback to relative media-server position | "
            "current_ticks=%s | relative_ticks=%s | target_ticks=%s",
            current_ticks,
            relative_ticks,
            target_ticks,
        )
        self._oppo_control.seek_to_position_ticks(target_ticks)

    def _report_playstate_interaction_from_current_state(self, command: str) -> None:
        if command == "PlayPause":
            pause_event = self._pause_event_from_current_oppo_state()
        else:
            pause_event = _pause_event_for_playstate_command(command)

        if pause_event is None:
            return

        event_name, is_paused = pause_event
        self._report_interaction_event(event_name, is_paused=is_paused)
        self._state.playstate = "Paused" if is_paused else "Playing"

    def _pause_event_from_current_oppo_state(self) -> tuple[str, bool] | None:
        if self._active_publisher() is not None:
            if self._state.playstate == "Paused":
                return "Pause", True
            return "Unpause", False

        try:
            state = self._oppo_control.get_playback_state()
        except Exception:
            logging.exception("Could not read OPPO state after PlayPause command.")
            return None

        if state.is_paused:
            return "Pause", True

        if state.is_playing:
            return "Unpause", False

        logging.warning(
            "Skipping Emby PlayPause interaction report because player state is not "
            "play/pause | raw=%s",
            state.raw_response,
        )
        return None

    def _report_interaction_event(
        self,
        event_name: str,
        *,
        is_paused: bool | None = None,
        audio_stream_index: int | None = None,
        subtitle_stream_index: int | None = None,
    ) -> None:
        active_session = self._state.active_session
        if active_session is None:
            logging.debug(
                "Skipping Emby interaction event because active playback session "
                "is not available | event=%s",
                event_name,
            )
            return

        publisher = self._active_publisher()

        if publisher is not None:
            # The monitoring loop keeps the publisher position up to date via periodic
            # progress() calls. Use that cached value — no OPPO network call needed.
            position_ticks = publisher.last_position_ticks
        else:
            logging.debug(
                "Skipping Emby interaction event because active publisher is not "
                "available | event=%s",
                event_name,
            )
            return

        effective_is_paused = (
            self._is_currently_paused() if is_paused is None else is_paused
        )

        publisher.report_event(
            event_name,
            position_ticks=position_ticks,
            is_paused=effective_is_paused,
            audio_track_id=audio_stream_index,
            subtitle_track_id=subtitle_stream_index,
        )

    def _is_currently_paused(self) -> bool:
        return self._state.playstate == "Paused"

    def _current_oppo_position_ticks(self) -> int:
        return self._oppo_control.current_position_ticks()

    def _current_playback_request_params(self) -> dict[str, Any]:
        active_session = self._state.active_session
        if active_session is None:
            raise RuntimeError("No active playback session is available.")

        return {
            "item_id": active_session.media_item_id,
            "media_source_id": active_session.media_source_id,
            "audio_stream_index": active_session.selected_audio_track_id,
            "subtitle_stream_index": active_session.selected_subtitle_track_id,
            "ControllingUserId": active_session.source_user_id,
            "Session_id": active_session.source_client_session_id,
            "DeviceName": active_session.source_device_name,
            "Device_Id": active_session.source_device_id,
        }

    @property
    def _config(self) -> dict[str, Any]:
        return self._config_provider()

    def _active_publisher(self):
        return self._active_publisher_provider()

    @property
    def _oppo_control(self) -> MediaPlayerControl:
        return self._oppo_control_factory(self._config)


def _remote_key_for_playstate_command(command: str) -> str | None:
    return {
        "Stop": "STP",
        "Pause": "PAU",
        "Unpause": "PLA",
        "NextTrack": "NXT",
        "PreviousTrack": "PRE",
        "PlayPause": "PAU",
    }.get(command)


def _pause_event_for_playstate_command(command: str) -> tuple[str, bool] | None:
    return {
        "Pause": ("Pause", True),
        "Unpause": ("Unpause", False),
    }.get(command)
