from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from home_cinema_control.media_servers.emby.constants import EMBY_TICKS_PER_SECOND
from home_cinema_control.playback.intent import PlaybackIntent

if TYPE_CHECKING:
    from home_cinema_control.playback.diagnostics import PlaybackDiagnostic


@dataclass
class ActivePlaybackSession:
    """Typed description of the playback currently owned by the bridge.

    This is the source of truth for the active item, selected tracks, source
    client and resolved player media path. `to_media_server_payload()` exists
    only for Emby-facing code that still expects the old dictionary payload.
    """

    media_item_id: str
    media_source_id: str
    source_user_id: str
    source_client_session_id: str | None
    start_position_seconds: int
    selected_audio_track_id: int
    selected_subtitle_track_id: int
    source_device_id: str = ""
    source_device_name: str = ""
    content_server: str = ""
    content_directory: str = ""
    playback_file_name: str = ""
    playback_file_format: str = ""
    network_protocol: str = ""
    production_year: int | None = None
    title: str = ""

    @classmethod
    def from_intent(cls, intent: PlaybackIntent) -> "ActivePlaybackSession":
        return cls(
            media_item_id=intent.media_item_id,
            media_source_id=intent.media_source_id,
            source_user_id=intent.source_user_id,
            source_client_session_id=intent.source_client_session_id,
            source_device_id=intent.source_device_id,
            source_device_name=intent.source_device_name,
            start_position_seconds=intent.start_position_seconds,
            selected_audio_track_id=intent.selected_audio_track_id,
            selected_subtitle_track_id=intent.selected_subtitle_track_id,
        )

    def apply_media_location(self, *, media_location: Any, item_info: dict[str, Any]) -> None:
        self.content_server = media_location.content_server
        self.content_directory = media_location.content_directory
        self.playback_file_name = media_location.playback_file_name
        self.playback_file_format = media_location.playback_file_format
        self.network_protocol = media_location.network_protocol or ""
        self.production_year = item_info.get("ProductionYear")
        self.title = item_info["Name"]

    def update_tracks(
        self,
        *,
        audio_track_id: int | None = None,
        subtitle_track_id: int | None = None,
    ) -> None:
        if audio_track_id is not None:
            self.selected_audio_track_id = audio_track_id

        if subtitle_track_id is not None:
            self.selected_subtitle_track_id = subtitle_track_id

    def to_media_server_payload(self) -> dict[str, Any]:
        return {
            "ItemIds": [self.media_item_id],
            "MediaSourceId": self.media_source_id,
            "AudioStreamIndex": self.selected_audio_track_id,
            "SubtitleStreamIndex": self.selected_subtitle_track_id,
            "ControllingUserId": self.source_user_id,
            "SessionID": self.source_client_session_id,
            "StartPositionTicks": (
                self.start_position_seconds * EMBY_TICKS_PER_SECOND
            ),
            "Device_Id": self.source_device_id,
            "DeviceName": self.source_device_name,
        }

    def to_runtime_status(self) -> dict[str, Any]:
        """Serialize the active session for status/UI consumers."""
        return {
            "media_item_id": self.media_item_id,
            "media_source_id": self.media_source_id,
            "source_user_id": self.source_user_id,
            "source_client_session_id": self.source_client_session_id,
            "source_device_id": self.source_device_id,
            "source_device_name": self.source_device_name,
            "start_position_seconds": self.start_position_seconds,
            "selected_audio_track_id": self.selected_audio_track_id,
            "selected_subtitle_track_id": self.selected_subtitle_track_id,
            "content_server": self.content_server,
            "content_directory": self.content_directory,
            "playback_file_name": self.playback_file_name,
            "playback_file_format": self.playback_file_format,
            "network_protocol": self.network_protocol,
            "production_year": self.production_year,
            "title": self.title,
        }


class BridgePlaybackState:
    """Mutable playback state shared across bridge components.

    `active_session` is the typed source of truth for the playback currently
    owned by the bridge.
    """

    def __init__(self) -> None:
        self.playstate: str = "Free"
        self.active_session: ActivePlaybackSession | None = None
        self.last_diagnostic: PlaybackDiagnostic | None = None
        self.diagnostic_history: list[PlaybackDiagnostic] = []

    def start_loading(self, intent: PlaybackIntent) -> None:
        self.playstate = "Loading"
        self.active_session = ActivePlaybackSession.from_intent(intent)

    def set_active_media_location(
        self,
        *,
        media_location: Any,
        item_info: dict[str, Any],
    ) -> None:
        if self.active_session is not None:
            self.active_session.apply_media_location(
                media_location=media_location,
                item_info=item_info,
            )

    def update_active_tracks(
        self,
        *,
        audio_track_id: int | None = None,
        subtitle_track_id: int | None = None,
    ) -> None:
        if self.active_session is not None:
            self.active_session.update_tracks(
                audio_track_id=audio_track_id,
                subtitle_track_id=subtitle_track_id,
            )

    def record_diagnostic(self, diagnostic: PlaybackDiagnostic) -> None:
        self.last_diagnostic = diagnostic
        self.diagnostic_history.append(diagnostic)
        if len(self.diagnostic_history) > 20:
            self.diagnostic_history = self.diagnostic_history[-20:]

    def clear_last_diagnostic(self) -> None:
        self.last_diagnostic = None

    def diagnostic_history_status(self, *, limit: int = 5) -> list[dict[str, Any]]:
        return [
            diagnostic.to_dict()
            for diagnostic in self.diagnostic_history[-max(0, limit):]
        ]

    def finish(self) -> None:
        self.playstate = "Free"
        self.active_session = None
