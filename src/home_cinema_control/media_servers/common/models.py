from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


MediaServerProviderType = Literal["emby", "jellyfin"]


class MediaServerCommandKind(str, Enum):
    """The in-playback control instructions HCC understands, provider-neutral."""

    SEEK = "seek"
    SEEK_RELATIVE = "seek_relative"
    PAUSE = "pause"
    UNPAUSE = "unpause"
    PLAY_PAUSE = "play_pause"
    STOP = "stop"
    NEXT_TRACK = "next_track"
    PREVIOUS_TRACK = "previous_track"
    SET_AUDIO_TRACK = "set_audio_track"
    SET_SUBTITLE_TRACK = "set_subtitle_track"
    UNSUPPORTED = "unsupported"


class MediaServerCommand(BaseModel):
    """An in-playback control instruction issued by the media server, mapped to
    HCC domain.

    Distinct from ``PlaybackIntent`` (which *starts* playback): a command
    *mutates* playback already in progress. The command handler dispatches on
    ``kind`` and never reads provider wire shape; each provider's edge maps its
    websocket message into this value object. Relative-seek offsets and
    fast-forward/rewind defaults are resolved during mapping, so the handler
    only ever applies an explicit ``offset_ticks``.
    """

    model_config = ConfigDict(extra="allow")

    kind: MediaServerCommandKind
    position_ticks: int | None = None
    offset_ticks: int | None = None
    track_index: int | None = None
    raw_name: str = ""


class MediaServerLoginCredentials(BaseModel):
    model_config = ConfigDict(extra="allow")

    user_name: str = ""
    password: str = ""


class MediaServerLibrary(BaseModel):
    """A media-server library as HCC needs it, independent of provider API shape.

    Providers map their own API response into this value object; the shared
    reconciliation logic that preserves the user's choices lives here so it is
    not duplicated per provider.
    """

    model_config = ConfigDict(extra="allow")

    id: str = ""
    name: str = ""
    active: bool = False

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy_capitalized_keys(cls, data):
        """Every install predating this model wrote the raw Emby/Jellyfin API
        field names (Id/Name/Active) straight into playback.libraries — this
        is the real, current shape of every existing 1.0.5 config.json, not a
        hypothetical. Without this, id/name/active silently read as
        ""/""/False (the field defaults) instead of raising, so a library
        list looked valid but every library was inactive — full playback
        detection regression for any install not using use_all_libraries.
        Only fills in a field when the canonical lowercase one is absent;
        never overrides real lowercase data. Pops the capitalized originals
        once consumed so they don't linger as inert extras forever.
        """
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        if not normalized.get("id") and "Id" in normalized:
            normalized["id"] = str(normalized.pop("Id"))
        if not normalized.get("name") and "Name" in normalized:
            normalized["name"] = str(normalized.pop("Name"))
        if not normalized.get("active") and "Active" in normalized:
            normalized["active"] = bool(normalized.pop("Active"))
        return normalized

    def reconciled_with(
        self, existing: "MediaServerLibrary | None"
    ) -> "MediaServerLibrary":
        """Return a copy that keeps the user's previously chosen ``active`` flag."""
        if existing is None:
            return self
        return self.model_copy(update={"active": existing.active})


class MediaServerDevice(BaseModel):
    """A controllable playback device discovered from the media server."""

    model_config = ConfigDict(extra="allow")

    id: str = ""
    name: str = ""
    app_name: str = ""


class MediaServerNowPlaying(BaseModel):
    """The item a monitored session is currently playing, as HCC needs it."""

    model_config = ConfigDict(extra="allow")

    item_id: str = ""
    name: str = ""
    path: str = ""
    item_type: str | None = None
    container: str | None = None
    video_type: str | None = None


class MediaServerSession(BaseModel):
    """An observed session the media server reports, mapped to HCC domain.

    The session monitor reasons over this value object instead of a raw provider
    payload, so the shared handoff policy never touches provider wire shape. Each
    provider maps its own Sessions payload into this at its edge.
    """

    model_config = ConfigDict(extra="allow")

    device_id: str = ""
    device_name: str = ""
    user_id: str = ""
    client_session_id: str | None = None
    last_activity_at: str = ""
    now_playing: MediaServerNowPlaying | None = None
    position_ticks: int | None = None
    media_source_id: str = ""
    audio_stream_index: int = 1
    subtitle_stream_index: int = -1


def find_controlling_session_id(
        sessions: list[MediaServerSession],
        *,
        controlling_user_id: str,
        own_device_id: str,
) -> str | None:
    """Among this user's other active sessions (excluding our own device),
    return the id of the one that was active most recently.

    Shared policy, not wire-format handling: both Emby's and Jellyfin's "Play"
    websocket message have the same gap (never identify the controller's own
    session, only the bridge's target session), and once each provider maps
    its own Sessions payload into MediaServerSession at the edge, resolving
    the real controller is the same domain-level operation either way. See
    ADR-0001.
    """
    if not controlling_user_id:
        return None

    candidates = [
        session for session in sessions
        if session.device_id != own_device_id and session.user_id == controlling_user_id
    ]
    if not candidates:
        return None

    candidates.sort(key=lambda session: session.last_activity_at)
    return candidates[-1].client_session_id


class MediaServerItemPlaybackInfo(BaseModel):
    """Saved userdata and selected media-source detail for an item, mapped to HCC
    domain.

    Providers fetch the raw item response (``get_item_info``) and map it here,
    at the edge, before it reaches shared session-monitor policy. Emby and
    Jellyfin share this Item-API response shape (Jellyfin forked it from Emby),
    the same precedent already accepted for ``track_mapping`` and
    ``command_from_playstate_message``.
    """

    model_config = ConfigDict(extra="allow")

    saved_position_ticks: int | None = None
    played: bool | None = None
    play_count: int | None = None
    playback_percentage: float | None = None
    media_source_container: str | None = None
    media_source_video_type: str | None = None

    @classmethod
    def from_item_response(
        cls,
        item_info: dict | None,
        *,
        media_source_id: str | None,
    ) -> "MediaServerItemPlaybackInfo":
        item_info = item_info or {}
        user_data = item_info.get("UserData") or {}
        media_source = _selected_media_source(
            item_info.get("MediaSources") or [],
            media_source_id,
        )
        saved_position_ticks = user_data.get("PlaybackPositionTicks")

        return cls(
            saved_position_ticks=(
                int(saved_position_ticks) if saved_position_ticks is not None else None
            ),
            played=user_data.get("Played"),
            play_count=user_data.get("PlayCount"),
            playback_percentage=user_data.get("PlayedPercentage"),
            media_source_container=(media_source or {}).get("Container"),
            media_source_video_type=(media_source or {}).get("VideoType"),
        )


def _selected_media_source(
    media_sources: list[dict],
    media_source_id: str | None,
) -> dict | None:
    if media_source_id:
        for media_source in media_sources:
            if media_source.get("Id") == media_source_id:
                return media_source

    if media_sources:
        return media_sources[0]

    return None


class LibraryPath(BaseModel):
    """A source path exposed by a media-server library, used for path mapping."""

    library_name: str = ""
    source_path: str = ""


def is_library_active(
    libraries: list[MediaServerLibrary], library_name: str
) -> bool:
    """True when a library with the given name is marked active."""
    return any(
        library.name == library_name and library.active for library in libraries
    )
