from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from home_cinema_control.media_servers.emby.constants import EMBY_TICKS_PER_SECOND
from home_cinema_control.playback.content_kind import MediaContentKind
from home_cinema_control.playback.notification_sender import (
    send_stop_with_delivery_reliability,
)

PLAYBACK_PROGRESS_INTERVAL_SECONDS = 10


_EMBY_TYPE_TO_CONTENT_KIND = {
    "Movie": MediaContentKind.MOVIE,
    "Episode": MediaContentKind.EPISODE,
    "MusicVideo": MediaContentKind.CONCERT,
    "LiveTvProgram": MediaContentKind.LIVE_TV,
    "Recording": MediaContentKind.LIVE_TV,
    "TvChannel": MediaContentKind.LIVE_TV,
    "LiveTvChannel": MediaContentKind.LIVE_TV,
}


def _content_kind_from_emby_type(emby_type: str | None) -> MediaContentKind:
    return _EMBY_TYPE_TO_CONTENT_KIND.get(emby_type, MediaContentKind.OTHER)


@dataclass(frozen=True)
class MediaServerPlaybackSource:
    """The resolved file + metadata for what's actually being played.

    The counterpart to `MediaServerPlaybackContext`: context is the request,
    source is what got resolved. Mapped once at this adapter edge from the raw
    Emby `Item`/`MediaSource` wire dicts — policy code reads these typed
    fields and never Emby's own field names.
    """

    path: str
    container: str
    duration_seconds: int
    production_year: int | None
    title: str
    content_kind: MediaContentKind

    @classmethod
    def from_emby_item(
            cls,
            item_data: dict[str, Any],
            media_source_id: str,
    ) -> MediaServerPlaybackSource:
        media_source = _find_media_source(item_data, media_source_id)

        return cls(
            path=media_source.get("Path", ""),
            container=media_source.get("Container", ""),
            duration_seconds=_duration_seconds(media_source),
            production_year=item_data.get("ProductionYear"),
            title=item_data.get("Name", ""),
            content_kind=_content_kind_from_emby_type(item_data.get("Type")),
        )


def _find_media_source(
        item_data: dict[str, Any],
        media_source_id: str,
) -> dict[str, Any]:
    for media_source in item_data.get("MediaSources", []):
        if media_source.get("Id") == media_source_id:
            return media_source

    return item_data


def _duration_seconds(media_source: dict[str, Any]) -> int:
    try:
        return max(0, int(media_source.get("RunTimeTicks", 0)) // EMBY_TICKS_PER_SECOND)
    except (TypeError, ValueError):
        return 0


@dataclass(frozen=True)
class MediaServerPlaybackContext:
    """Playback metadata translated from the media server event.

    Naming is intentionally project-domain oriented:

    - media_library_item_id: movie/episode/library entry being played.
    - media_source_file_id: concrete file/source/version selected for that item.
    - source_client_session_id: original TV/app client session that requested playback.
    - media_server_playback_id: server playback lifecycle id used for check-ins.
    - *_ticks: media-server time units. In Emby these are .NET ticks, 100ns each.
    """

    media_library_item_id: str
    media_source_file_id: str
    selected_audio_track_id: int
    selected_subtitle_track_id: int
    media_server_user_id: str
    source_client_session_id: str | None
    media_server_playback_id: str
    start_position_ticks: int

    @classmethod
    def from_intent(cls, intent) -> MediaServerPlaybackContext:
        return cls(
            media_library_item_id=intent.media_item_id,
            media_source_file_id=intent.media_source_id,
            selected_audio_track_id=intent.selected_audio_track_id,
            selected_subtitle_track_id=intent.selected_subtitle_track_id,
            media_server_user_id=intent.source_user_id,
            source_client_session_id=intent.source_client_session_id,
            media_server_playback_id=str(uuid.uuid4()),
            start_position_ticks=intent.start_position_seconds * EMBY_TICKS_PER_SECOND,
        )

    @classmethod
    def from_event(cls, data, *, load_user_item):
        media_library_item_id = _selected_media_library_item_id(data)
        start_position_ticks = _start_position_ticks(data)
        media_server_user_id = data.get("ControllingUserId", "")

        if start_position_ticks < 0:
            item_info = load_user_item(media_server_user_id, media_library_item_id)
            start_position_ticks = int(
                item_info.get("UserData", {}).get("PlaybackPositionTicks", 0)
            )

        return cls(
            media_library_item_id=str(media_library_item_id),
            media_source_file_id=data.get("MediaSourceId", ""),
            selected_audio_track_id=int(data.get("AudioStreamIndex", 1)),
            selected_subtitle_track_id=int(data.get("SubtitleStreamIndex", -1)),
            media_server_user_id=media_server_user_id,
            source_client_session_id=data.get("SessionID"),
            media_server_playback_id=data.get("PlaySessionId") or str(uuid.uuid4()),
            start_position_ticks=start_position_ticks,
        )


class MediaServerPlaybackEventPublisher:
    """Publishes media-server playback lifecycle events for the external player."""

    def __init__(
        self,
        client,
        *,
        bridge_session_id: str,
        context: MediaServerPlaybackContext,
        progress_interval_seconds: int = PLAYBACK_PROGRESS_INTERVAL_SECONDS,
    ):
        self._client = client
        self._bridge_session_id = bridge_session_id
        self.context = context
        self.progress_interval_seconds = progress_interval_seconds
        self._last_reported_second: int | None = None
        self._current_audio_track_id = context.selected_audio_track_id
        self._current_subtitle_track_id = context.selected_subtitle_track_id
        self._stopped_reported = False

    @property
    def last_position_ticks(self) -> int:
        if self._last_reported_second is None:
            return self.context.start_position_ticks
        return self._last_reported_second * EMBY_TICKS_PER_SECOND

    def update_active_tracks(
        self,
        *,
        audio_track_id: int | None = None,
        subtitle_track_id: int | None = None,
    ) -> None:
        if audio_track_id is not None:
            self._current_audio_track_id = audio_track_id
        if subtitle_track_id is not None:
            self._current_subtitle_track_id = subtitle_track_id

    def started(self):
        payload = self._base_payload(self.context.start_position_ticks)
        response = self._client.notify_playback_started(payload)
        self._log_response("started", payload, response)
        return response

    def report_event(
        self,
        event_name: str,
        *,
        position_ticks: int,
        runtime_ticks: int = 0,
        is_paused: bool = False,
        is_muted: bool = False,
        audio_track_id: int | None = None,
        subtitle_track_id: int | None = None,
    ):
        self.update_active_tracks(
            audio_track_id=audio_track_id, subtitle_track_id=subtitle_track_id
        )
        payload = self._base_payload(
            position_ticks,
            runtime_ticks=runtime_ticks,
            is_paused=is_paused,
            is_muted=is_muted,
        )
        payload["EventName"] = event_name
        response = self._client.report_playback_progress(payload)
        logging.debug(
            "Emby playback progress payload | event=%s | item_id=%s | "
            "media_source_id=%s | position_ticks=%s | audio=%s | subtitle=%s | is_paused=%s",
            event_name,
            payload["ItemId"],
            payload["MediaSourceId"],
            payload["PositionTicks"],
            payload["AudioStreamIndex"],
            payload["SubtitleStreamIndex"],
            payload["IsPaused"],
        )
        if event_name != "TimeUpdate":
            logging.info(
                "Emby playback interaction event accepted | event=%s | status=%s",
                event_name,
                response.status_code,
            )
        else:
            self._log_response("progress", payload, response)
        return response

    def progress(
        self,
        *,
        position_seconds: int,
        duration_seconds: int,
        is_paused: bool = False,
        is_muted: bool = False,
        force: bool = False,
    ):
        if not force and not self._should_report_progress(position_seconds):
            return None

        position_ticks = position_seconds * EMBY_TICKS_PER_SECOND
        runtime_ticks = duration_seconds * EMBY_TICKS_PER_SECOND
        response = self.report_event(
            "TimeUpdate",
            position_ticks=position_ticks,
            runtime_ticks=runtime_ticks,
            is_paused=is_paused,
            is_muted=is_muted,
        )
        self._last_reported_second = position_seconds
        return response

    def stopped(
        self,
        *,
        position_seconds: int,
        duration_seconds: int = 0,
        is_paused: bool = False,
        is_muted: bool = False,
        played: bool = True,
    ):
        if self._stopped_reported:
            logging.info(
                "Skipping duplicate media-server playback stopped event | "
                "media_library_item_id=%s | media_server_playback_id=%s",
                self.context.media_library_item_id,
                self.context.media_server_playback_id,
            )
            return None

        position_ticks = position_seconds * EMBY_TICKS_PER_SECOND
        runtime_ticks = duration_seconds * EMBY_TICKS_PER_SECOND
        payload = self._base_payload(
            position_ticks,
            runtime_ticks=runtime_ticks,
            is_paused=is_paused,
            is_muted=is_muted,
        )
        response = self._client.notify_playback_stopped(payload)
        if not played and position_ticks > 0:
            self._mark_item_unplayed_preserving_resume_position(position_ticks)
        self._stopped_reported = True
        self._log_response("stopped", payload, response)
        self._stop_stale_source_client_session()
        return response

    def _stop_stale_source_client_session(self) -> None:
        """Best-effort cleanup of the original TV/app session's player screen.

        Runs for every `PlaybackOrigin`, not just `OBSERVED_TV_CLIENT` — for a
        `REMOTE_CONTROL_COMMAND` cast, this is the *only* Stop the source
        client (e.g. the phone) ever receives, so it needs the same delivery
        redundancy as the handoff-time Stop
        (`stop_source_client_before_handoff` in `playback/application.py`),
        not just a single send. See `send_stop_with_delivery_reliability` for
        why a single send isn't enough on its own.
        """
        send_stop_with_delivery_reliability(
            lambda session_id: self._client.stop_session_playback(
                session_id, {"Command": "Stop"}
            ),
            self.context.source_client_session_id,
        )

    def _mark_item_unplayed_preserving_resume_position(self, position_ticks: int) -> None:
        """Keep manual stops unwatched without destroying the resume point.

        Emby can mark ISO / full Blu-ray items as watched after a non-natural stop.
        We still clear the watched flag for that case, but DELETE /PlayedItems also
        clears PlaybackPositionTicks. Restore the last known position immediately
        afterwards so regular files, ISOs and Blu-ray folders can resume.
        """
        if not self._mark_item_unplayed_after_manual_stop(position_ticks):
            return

        self._restore_resume_position_after_manual_stop(position_ticks)

    def _mark_item_unplayed_after_manual_stop(self, position_ticks: int) -> bool:
        try:
            response = self._client.mark_item_unplayed(
                self.context.media_server_user_id,
                self.context.media_library_item_id,
            )
        except Exception:
            logging.exception(
                "Unable to mark media-server item unplayed after non-natural stop | "
                "media_library_item_id=%s | position_ticks=%s",
                self.context.media_library_item_id,
                position_ticks,
            )
            return False

        logging.info(
            "Media server item marked unplayed after non-natural stop | "
            "media_library_item_id=%s | position_ticks=%s | status=%s | body=%s",
            self.context.media_library_item_id,
            position_ticks,
            response.status_code,
            response.text,
        )
        return True

    def _restore_resume_position_after_manual_stop(self, position_ticks: int) -> None:
        payload = {
            "ItemId": self.context.media_library_item_id,
            "PlaybackPositionTicks": position_ticks,
            "Played": False,
        }
        try:
            response = self._client.set_item_playback_position(
                self.context.media_server_user_id,
                self.context.media_library_item_id,
                payload,
            )
        except Exception:
            logging.exception(
                "Unable to restore media-server resume position after clearing played state | "
                "media_library_item_id=%s | position_ticks=%s",
                self.context.media_library_item_id,
                position_ticks,
            )
            return

        logging.info(
            "Media server resume position restored after non-natural stop | "
            "media_library_item_id=%s | position_ticks=%s | status=%s | body=%s",
            self.context.media_library_item_id,
            position_ticks,
            response.status_code,
            response.text,
        )

    def _should_report_progress(self, position_seconds: int) -> bool:
        if position_seconds <= 0:
            return False

        if self._last_reported_second is None:
            return True

        if position_seconds < self._last_reported_second:
            return True

        return position_seconds - self._last_reported_second >= self.progress_interval_seconds

    def _base_payload(
        self,
        position_ticks: int,
        *,
        runtime_ticks: int = 0,
        is_paused: bool = False,
        is_muted: bool = False,
    ):
        payload = {
            "QueueableMediaTypes": ["Video"],
            "CanSeek": True,
            "ItemId": self.context.media_library_item_id,
            "SessionId": self._bridge_session_id,
            "MediaSourceId": self.context.media_source_file_id,
            "AudioStreamIndex": self._current_audio_track_id,
            "SubtitleStreamIndex": self._current_subtitle_track_id,
            "IsPaused": is_paused,
            "IsMuted": is_muted,
            "PositionTicks": position_ticks,
            "PlayMethod": "DirectPlay",
            "PlaySessionId": self.context.media_server_playback_id,
            "RepeatMode": "RepeatNone",
        }

        if runtime_ticks > 0:
            payload["RunTimeTicks"] = runtime_ticks

        return payload

    def _log_response(self, event_name, payload, response):
        logging.debug(
            "Media server playback lifecycle %s | media_library_item_id=%s | media_server_playback_id=%s | position_ticks=%s | status=%s | body=%s",
            event_name,
            self.context.media_library_item_id,
            self.context.media_server_playback_id,
            payload.get("PositionTicks"),
            response.status_code,
            response.text,
        )



def _selected_media_library_item_id(data):
    item_ids = data["ItemIds"]
    start_index = int(data.get("StartIndex", 0))

    if isinstance(item_ids, list):
        if not item_ids:
            raise ValueError("Emby playback event has no ItemIds.")

        if start_index > 0 and start_index < len(item_ids):
            return item_ids[start_index]

        return item_ids[0]

    return item_ids


def _start_position_ticks(data):
    start_at = data.get("StartPositionTicks")

    if start_at is None:
        start_at = data.get("SavedPlaybackPositionTicks")

    if start_at is None:
        return -1

    return int(start_at)
