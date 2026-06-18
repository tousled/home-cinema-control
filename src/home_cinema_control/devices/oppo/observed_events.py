from __future__ import annotations

from home_cinema_control.devices.oppo.verbose_events import OppoVerboseEvent
from home_cinema_control.playback.observed_events import (
    ObservedPlaybackEvent,
    ObservedPlaybackEventType,
    ObservedPlaybackState,
)


_UPL_STATE_MAP = {
    "PLAY": ObservedPlaybackState.PLAYING,
    "PAUS": ObservedPlaybackState.PAUSED,
    "STOP": ObservedPlaybackState.STOPPED,
}


def translate_oppo_verbose_event(
    event: OppoVerboseEvent,
) -> ObservedPlaybackEvent | None:
    if event.code == "UPL":
        return _translate_playback_state_event(event)

    if event.code == "UAT":
        parts = event.payload.strip().split()
        prefix = parts[0].upper() if parts else ""
        if prefix in ("TH", "UN"):
            return None
        track_index = _parse_menu_position(event.payload)
        if track_index is None:
            return None
        return ObservedPlaybackEvent(
            event_type=ObservedPlaybackEventType.AUDIO_TRACK_CHANGED,
            player_audio_track_index=track_index,
            raw=event.raw,
        )

    if event.code == "UST":
        track_index = _parse_menu_position(event.payload)
        if track_index is None:
            return None
        return ObservedPlaybackEvent(
            event_type=ObservedPlaybackEventType.SUBTITLE_TRACK_CHANGED,
            player_subtitle_track_index=track_index,
            raw=event.raw,
        )

    if event.code == "UTC":
        position_seconds = _parse_utc_position(event.payload)
        if position_seconds is None:
            return None
        return ObservedPlaybackEvent(
            event_type=ObservedPlaybackEventType.POSITION_UPDATED,
            position_seconds=position_seconds,
            raw=event.raw,
        )

    return None


def _translate_playback_state_event(
    event: OppoVerboseEvent,
) -> ObservedPlaybackEvent | None:
    state = _UPL_STATE_MAP.get(event.payload.strip().upper())
    if state is None:
        return None

    return ObservedPlaybackEvent(
        event_type=ObservedPlaybackEventType.PLAYBACK_STATE_CHANGED,
        playback_state=state,
        raw=event.raw,
    )


def _parse_utc_position(payload: str) -> int | None:
    # format: "000 015 C HH:MM:SS"
    parts = payload.strip().split()
    if len(parts) < 4:
        return None
    try:
        h, m, s = parts[3].split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)
    except (ValueError, AttributeError):
        return None


def _parse_menu_position(payload: str) -> int | None:
    menu_token = next(
        (token for token in payload.strip().split() if "/" in token),
        "",
    )
    if not menu_token:
        return None

    selected, _total = menu_token.split("/", maxsplit=1)
    try:
        return int(selected)
    except ValueError:
        return None
