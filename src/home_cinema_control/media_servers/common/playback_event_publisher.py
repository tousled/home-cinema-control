from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Protocol

from home_cinema_control.playback.time_units import TICKS_PER_SECOND

PLAYBACK_PROGRESS_INTERVAL_SECONDS = 10


@dataclass(frozen=True)
class MediaServerPlaybackContext:
    """Playback metadata translated from a handoff intent.

    Naming is intentionally project-domain oriented:

    - media_library_item_id: movie/episode/library entry being played.
    - media_source_file_id: concrete file/source/version selected for that item.
    - source_client_session_id: original TV/app client session that requested playback.
    - media_server_playback_id: server playback lifecycle id used for check-ins.
    - *_ticks: media-server time units (100ns ticks, shared by Emby and Jellyfin).
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
            start_position_ticks=intent.start_position_seconds * TICKS_PER_SECOND,
        )


class PlaybackPayloadMapper(Protocol):
    """Outbound mapper: HCC playback context -> provider playback payloads."""

    def lifecycle_payload(
        self,
        *,
        position_ticks: int,
        runtime_ticks: int,
        is_paused: bool,
        is_muted: bool,
        audio_track_id: int,
        subtitle_track_id: int,
    ) -> dict: ...

    def restore_resume_position_payload(self, *, position_ticks: int) -> dict: ...


class MediaServerPlaybackEventPublisher:
    """Publishes media-server playback lifecycle events for the external player.

    Provider-neutral: it operates on :class:`MediaServerPlaybackContext` and an
    injected :class:`PlaybackPayloadMapper`. Wire payload shape lives in the
    mapper, at the edge; this class only ever decides *when* to report and what
    domain values to report.
    """

    def __init__(
        self,
        client,
        *,
        provider_name: str,
        bridge_session_id: str,
        context: MediaServerPlaybackContext,
        payload_mapper: PlaybackPayloadMapper,
        progress_interval_seconds: int = PLAYBACK_PROGRESS_INTERVAL_SECONDS,
    ):
        self._client = client
        self._provider_name = provider_name
        self._bridge_session_id = bridge_session_id
        self.context = context
        self._payload_mapper = payload_mapper
        self.progress_interval_seconds = progress_interval_seconds
        self._last_reported_second: int | None = None
        self._current_audio_track_id = context.selected_audio_track_id
        self._current_subtitle_track_id = context.selected_subtitle_track_id
        self._stopped_reported = False

    @property
    def last_position_ticks(self) -> int:
        if self._last_reported_second is None:
            return self.context.start_position_ticks
        return self._last_reported_second * TICKS_PER_SECOND

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
            "%s playback progress payload | event=%s | item_id=%s | "
            "media_source_id=%s | position_ticks=%s | audio=%s | subtitle=%s | is_paused=%s",
            self._provider_name,
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
                "%s playback interaction event accepted | event=%s | status=%s",
                self._provider_name,
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

        response = self.report_event(
            "TimeUpdate",
            position_ticks=position_seconds * TICKS_PER_SECOND,
            runtime_ticks=duration_seconds * TICKS_PER_SECOND,
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
                "Skipping duplicate %s playback stopped event | "
                "media_library_item_id=%s | media_server_playback_id=%s",
                self._provider_name,
                self.context.media_library_item_id,
                self.context.media_server_playback_id,
            )
            return None

        position_ticks = position_seconds * TICKS_PER_SECOND
        runtime_ticks = duration_seconds * TICKS_PER_SECOND
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
        return response

    def _mark_item_unplayed_preserving_resume_position(self, position_ticks: int) -> None:
        """Keep manual stops unwatched without destroying the resume point.

        Marking an item unplayed after a non-natural stop can also clear its
        saved resume position server-side. Restore it immediately afterwards so
        the item can still resume from where playback was interrupted.
        """
        try:
            self._client.mark_item_unplayed(
                self.context.media_server_user_id,
                self.context.media_library_item_id,
            )
            self._client.set_item_playback_position(
                self.context.media_server_user_id,
                self.context.media_library_item_id,
                self._payload_mapper.restore_resume_position_payload(
                    position_ticks=position_ticks,
                ),
            )
        except Exception:
            logging.exception(
                "Unable to restore %s unwatched resume state | "
                "media_library_item_id=%s | position_ticks=%s",
                self._provider_name,
                self.context.media_library_item_id,
                position_ticks,
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
    ) -> dict:
        return self._payload_mapper.lifecycle_payload(
            position_ticks=position_ticks,
            runtime_ticks=runtime_ticks,
            is_paused=is_paused,
            is_muted=is_muted,
            audio_track_id=self._current_audio_track_id,
            subtitle_track_id=self._current_subtitle_track_id,
        )

    def _log_response(self, event_name, payload, response):
        logging.debug(
            "%s playback lifecycle %s | media_library_item_id=%s | "
            "media_server_playback_id=%s | position_ticks=%s | status=%s | body=%s",
            self._provider_name,
            event_name,
            self.context.media_library_item_id,
            self.context.media_server_playback_id,
            payload.get("PositionTicks"),
            response.status_code,
            response.text,
        )
