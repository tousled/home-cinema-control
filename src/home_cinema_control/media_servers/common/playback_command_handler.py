from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from home_cinema_control.media_servers.common.models import (
    MediaServerCommand,
    MediaServerCommandKind,
)
from home_cinema_control.playback.intent import PlaybackIntent, PlaybackOrigin
from home_cinema_control.playback.ports import MediaPlayerPort
from home_cinema_control.playback.state import BridgePlaybackState
from home_cinema_control.playback.time_units import TICKS_PER_SECOND

DEFAULT_REMOTE_SKIP_SECONDS = 10

_Kind = MediaServerCommandKind


class MediaServerPlaybackCommandHandler:
    """Translate media-server playback commands into bridge playback actions.

    The handler operates on :class:`MediaServerCommand` domain objects. Wire
    messages are mapped to commands at the websocket edge
    (:func:`command_from_playstate_message`,
    :func:`command_from_general_command_message`); the handler never reads
    provider wire shape.
    """

    def __init__(
        self,
        *,
        provider_name: str,
        media_server_session,
        playback_state: BridgePlaybackState,
        config_provider: Callable[[], dict[str, Any]],
        playback_intent_dispatcher_factory: Callable,
        active_publisher_provider: Callable[[], Any],
        oppo_control_factory: Callable[[dict[str, Any]], MediaPlayerPort],
        play_command_parser: Callable[[dict[str, Any]], PlaybackIntent],
    ) -> None:
        self._provider_name = provider_name
        self._session = media_server_session
        self._state = playback_state
        self._config_provider = config_provider
        self._playback_intent_dispatcher_factory = playback_intent_dispatcher_factory
        self._oppo_control_factory = oppo_control_factory
        self._active_publisher_provider = active_publisher_provider
        self._play_command_parser = play_command_parser

    def handle_play(self, data: dict) -> None:
        # ``data`` is opaque here: the provider's play-command parser is the
        # inbound mapper (wire -> domain). It returns None for anything that is
        # not an actionable PlayNow, so the handler never reads wire shape.
        intent = self._play_command_parser(data)
        if intent is None:
            return

        logging.info(
            "%s play command -> handoff | item_id=%s | media_source_id=%s | "
            "device=%s | start_seconds=%s | audio=%s | subtitle=%s",
            self._provider_name,
            intent.media_item_id,
            intent.media_source_id,
            intent.source_device_name,
            intent.start_position_seconds,
            intent.selected_audio_track_id,
            intent.selected_subtitle_track_id,
        )
        self._playback_intent_dispatcher_factory().dispatch(
            intent,
            origin=PlaybackOrigin.REMOTE_CONTROL_COMMAND,
        )

    def handle_command(self, command: MediaServerCommand) -> None:
        kind = command.kind

        if kind == _Kind.SEEK:
            self._seek_to_absolute_position(command.position_ticks or 0)
            return

        if kind == _Kind.SEEK_RELATIVE:
            self._seek_to_relative_position(command.offset_ticks or 0)
            return

        if kind in (_Kind.PAUSE, _Kind.UNPAUSE, _Kind.PLAY_PAUSE):
            self._handle_play_pause_command(kind)
            return

        if kind == _Kind.SET_AUDIO_TRACK:
            self._handle_audio_track_change(command.track_index or 0)
            return

        if kind == _Kind.SET_SUBTITLE_TRACK:
            self._handle_subtitle_track_change(command.track_index or 0)
            return

        remote_key = _remote_key_for_kind(kind)
        if remote_key is None:
            logging.debug(
                "Ignoring unsupported %s command | name=%s",
                self._provider_name,
                command.raw_name,
            )
            return

        result = self._oppo_control.send_remote_key(remote_key)
        if not result.successful:
            logging.warning(
                "OPPO playstate command failed | name=%s | result=%s",
                command.raw_name,
                result,
            )

    def _handle_audio_track_change(self, source_audio_index: int) -> None:
        params = self._current_playback_request_params()
        audio_index = self._session.resolve_audio_track_index(
            params["ControllingUserId"],
            params["item_id"],
            source_audio_index,
        )
        logging.info(
            "Mapped %s audio index to OPPO audio index | source_index=%s | oppo_index=%s",
            self._provider_name,
            source_audio_index,
            audio_index,
        )
        result = self._oppo_control.select_audio_track(audio_index)
        if not result.successful:
            logging.warning("OPPO audio track change failed | result=%s", result)
            return

        self._state.update_active_tracks(audio_track_id=source_audio_index)
        self._report_interaction_event(
            "AudioTrackChange",
            audio_stream_index=source_audio_index,
        )

    def _handle_subtitle_track_change(self, source_subtitle_index: int) -> None:
        params = self._current_playback_request_params()
        subtitle_index = self._session.resolve_subtitle_track_index(
            params["ControllingUserId"],
            params["item_id"],
            source_subtitle_index,
        )
        logging.info(
            "Mapped %s subtitle index to OPPO subtitle index | source_index=%s | oppo_index=%s",
            self._provider_name,
            source_subtitle_index,
            subtitle_index,
        )
        result = self._oppo_control.select_subtitle_track(subtitle_index)
        if not result.successful:
            logging.warning("OPPO subtitle track change failed | result=%s", result)
            return

        self._state.update_active_tracks(subtitle_track_id=source_subtitle_index)
        self._report_interaction_event(
            "SubtitleTrackChange",
            subtitle_stream_index=source_subtitle_index,
        )

    def _handle_play_pause_command(self, kind: MediaServerCommandKind) -> None:
        oppo_state = None
        if self._active_publisher() is None:
            oppo_state = self._current_oppo_state_or_none()

        if self._play_pause_command_is_already_satisfied(kind, oppo_state):
            logging.info(
                "Skipping OPPO play/pause command because requested state is already active | "
                "command=%s | oppo_state=%s | bridge_playstate=%s",
                kind.value,
                oppo_state.status.value if oppo_state is not None else None,
                self._state.playstate,
            )
            self._report_playstate_interaction_from_current_state(kind)
            return

        remote_key = _remote_key_for_kind(kind)
        if remote_key is None:
            return

        previous_playstate = self._state.playstate
        if kind == _Kind.PAUSE:
            self._state.playstate = "Paused"
        elif kind == _Kind.UNPAUSE:
            self._state.playstate = "Playing"
        elif kind == _Kind.PLAY_PAUSE:
            self._state.playstate = (
                "Playing" if self._state.playstate == "Paused" else "Paused"
            )

        result = self._oppo_control.send_remote_key(remote_key)
        if not result.successful:
            logging.warning(
                "OPPO play/pause command failed | command=%s | result=%s",
                kind.value,
                result,
            )
            self._state.playstate = previous_playstate
            return

        self._report_playstate_interaction_from_current_state(kind)

    def _play_pause_command_is_already_satisfied(
        self,
        kind: MediaServerCommandKind,
        oppo_state,
    ) -> bool:
        if kind == _Kind.PAUSE:
            return (
                oppo_state is not None and oppo_state.is_paused
            ) or self._state.playstate == "Paused"

        if kind == _Kind.UNPAUSE:
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

    def _seek_to_absolute_position(self, position_ticks: int) -> None:
        logging.info(
            "Seeking OPPO playback to absolute media-server position | "
            "position_ticks=%s",
            position_ticks,
        )
        self._oppo_control.seek_to_position_ticks(position_ticks)

    def _seek_to_relative_position(self, offset_ticks: int) -> None:
        current_ticks = self._current_oppo_position_ticks()
        target_ticks = max(0, current_ticks + offset_ticks)

        logging.info(
            "Seeking OPPO playback to relative media-server position | "
            "current_ticks=%s | offset_ticks=%s | target_ticks=%s",
            current_ticks,
            offset_ticks,
            target_ticks,
        )
        self._oppo_control.seek_to_position_ticks(target_ticks)

    def _report_playstate_interaction_from_current_state(
        self, kind: MediaServerCommandKind
    ) -> None:
        if kind == _Kind.PLAY_PAUSE:
            pause_event = self._pause_event_from_current_oppo_state()
        else:
            pause_event = _pause_event_for_kind(kind)

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
            "Skipping %s PlayPause interaction report because player state is not "
            "play/pause | raw=%s",
            self._provider_name,
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
                "Skipping %s interaction event because active playback session "
                "is not available | event=%s",
                self._provider_name,
                event_name,
            )
            return

        publisher = self._active_publisher()

        if publisher is not None:
            position_ticks = publisher.last_position_ticks
        else:
            logging.debug(
                "Skipping %s interaction event because active publisher is not "
                "available | event=%s",
                self._provider_name,
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
    def _oppo_control(self) -> MediaPlayerPort:
        return self._oppo_control_factory(self._config)


def command_from_playstate_message(data: dict[str, Any]) -> MediaServerCommand:
    """Inbound mapper: a ``Playstate`` websocket message -> domain command.

    Fast-forward/rewind defaults and relative-seek offsets are resolved here, at
    the edge, so the handler only applies an explicit ``offset_ticks``.
    """
    command = data.get("Command")

    if command == "Seek":
        return MediaServerCommand(
            kind=_Kind.SEEK,
            position_ticks=int(data["SeekPositionTicks"]),
            raw_name=command,
        )

    if command == "SeekRelative":
        return MediaServerCommand(
            kind=_Kind.SEEK_RELATIVE,
            offset_ticks=int(data.get("SeekPositionTicks", 0)),
            raw_name=command,
        )

    if command == "FastForward":
        return MediaServerCommand(
            kind=_Kind.SEEK_RELATIVE,
            offset_ticks=int(
                data.get(
                    "SeekPositionTicks",
                    DEFAULT_REMOTE_SKIP_SECONDS * TICKS_PER_SECOND,
                )
            ),
            raw_name=command,
        )

    if command == "Rewind":
        return MediaServerCommand(
            kind=_Kind.SEEK_RELATIVE,
            offset_ticks=int(
                data.get(
                    "SeekPositionTicks",
                    -DEFAULT_REMOTE_SKIP_SECONDS * TICKS_PER_SECOND,
                )
            ),
            raw_name=command,
        )

    kind = {
        "Pause": _Kind.PAUSE,
        "Unpause": _Kind.UNPAUSE,
        "PlayPause": _Kind.PLAY_PAUSE,
        "Stop": _Kind.STOP,
        "NextTrack": _Kind.NEXT_TRACK,
        "PreviousTrack": _Kind.PREVIOUS_TRACK,
    }.get(command)

    if kind is None:
        return MediaServerCommand(kind=_Kind.UNSUPPORTED, raw_name=str(command or ""))

    return MediaServerCommand(kind=kind, raw_name=command)


def command_from_general_command_message(data: dict[str, Any]) -> MediaServerCommand:
    """Inbound mapper: a ``GeneralCommand`` websocket message -> domain command."""
    name = data.get("Name")
    args = data.get("Arguments") or {}

    if name == "SetAudioStreamIndex":
        return MediaServerCommand(
            kind=_Kind.SET_AUDIO_TRACK,
            track_index=int(args["Index"]),
            raw_name=name,
        )

    if name == "SetSubtitleStreamIndex":
        return MediaServerCommand(
            kind=_Kind.SET_SUBTITLE_TRACK,
            track_index=int(args["Index"]),
            raw_name=name,
        )

    return MediaServerCommand(kind=_Kind.UNSUPPORTED, raw_name=str(name or ""))


def _remote_key_for_kind(kind: MediaServerCommandKind) -> str | None:
    return {
        _Kind.STOP: "STP",
        _Kind.PAUSE: "PAU",
        _Kind.UNPAUSE: "PLA",
        _Kind.NEXT_TRACK: "NXT",
        _Kind.PREVIOUS_TRACK: "PRE",
        _Kind.PLAY_PAUSE: "PAU",
    }.get(kind)


def _pause_event_for_kind(kind: MediaServerCommandKind) -> tuple[str, bool] | None:
    return {
        _Kind.PAUSE: ("Pause", True),
        _Kind.UNPAUSE: ("Unpause", False),
    }.get(kind)
