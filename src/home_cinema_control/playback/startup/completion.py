from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from home_cinema_control.playback.ports import MediaPlayerPort
from home_cinema_control.playback.time_units import TICKS_PER_SECOND
from home_cinema_control.playback.startup.models import DeviceCommandResult

logger = logging.getLogger(__name__)


class PlaybackStartedReporter(Protocol):
    def started(self): ...


class PlaybackTrackResolver(Protocol):
    def resolve_audio_track(
        self,
        *,
        source_user_id: str,
        media_item_id: str,
        selected_source_track_id: int,
    ) -> int: ...

    def resolve_subtitle_track(
        self,
        *,
        source_user_id: str,
        media_item_id: str,
        selected_source_track_id: int,
    ) -> int: ...


class PlaybackStartupCompletionPlayer(Protocol):
    def seek_to_seconds(self, position_seconds: int) -> DeviceCommandResult: ...

    def prepare_track_menu_readiness(
        self,
        *,
        audio_track_id: int | None,
        subtitle_track_id: int | None,
    ) -> DeviceCommandResult: ...

    def select_audio_track(self, audio_track_id: int) -> DeviceCommandResult: ...

    def select_subtitle_track(self, subtitle_track_id: int) -> DeviceCommandResult: ...


class StartupStepTimer(Protocol):
    def measure_step(self, step_name: str): ...


@dataclass(frozen=True)
class PlayMediaItemRequest:
    start_position_seconds: int
    source_user_id: str
    media_item_id: str
    media_source_id: str = ""
    expected_duration_seconds: int = 0
    selected_source_audio_track_id: int | None = None
    selected_source_subtitle_track_id: int | None = None


@dataclass(frozen=True)
class PlayMediaItemResponse:
    start_position_seconds: int
    started_reported: bool
    seek_result: DeviceCommandResult
    audio_result: DeviceCommandResult
    subtitle_result: DeviceCommandResult
    expected_duration_seconds: int = 0
    pending_audio_track_index: int | None = None


class MediaPlayerStartupCompletionPlayer:
    """Adapts the media-player port to post-start playback controls."""

    def __init__(self, media_player: MediaPlayerPort) -> None:
        self._media_player = media_player

    def seek_to_seconds(self, position_seconds: int) -> DeviceCommandResult:
        position_units = max(0, position_seconds) * TICKS_PER_SECOND
        return self._media_player.seek_to(position_units)

    def prepare_track_menu_readiness(
        self,
        *,
        audio_track_id: int | None,
        subtitle_track_id: int | None,
    ) -> DeviceCommandResult:
        prepare = getattr(self._media_player, "prepare_track_menu_readiness", None)
        if prepare is None:
            return DeviceCommandResult.skipped(
                "Media player has no track-menu readiness capability."
            )
        return prepare(
            audio_track_id=audio_track_id,
            subtitle_track_id=subtitle_track_id,
        )

    def select_audio_track(self, audio_track_id: int) -> DeviceCommandResult:
        return self._media_player.select_audio_track(audio_track_id)

    def select_subtitle_track(self, subtitle_track_id: int) -> DeviceCommandResult:
        return self._media_player.select_subtitle_track(subtitle_track_id)


class PlaybackStartupCompletionService:
    """Completes the startup phase after the player has accepted playback."""

    def __init__(
        self,
        *,
        started_reporter: PlaybackStartedReporter,
        player: PlaybackStartupCompletionPlayer,
        track_resolver: PlaybackTrackResolver,
        step_timer: StartupStepTimer | None = None,
    ) -> None:
        self._started_reporter = started_reporter
        self._player = player
        self._track_resolver = track_resolver
        self._step_timer = step_timer

    def complete(
        self,
        request: PlayMediaItemRequest,
    ) -> PlayMediaItemResponse:
        self._measure(
            "notify_media_server_playback_started", self._started_reporter.started
        )

        start_position_seconds = max(0, request.start_position_seconds)
        seek_result = self._measure(
            "apply_resume_position",
            lambda: self._apply_resume_position(request, start_position_seconds),
        )
        resolved_audio_id, audio_resolution_result = self._resolve_audio_track(request)
        resolved_subtitle_id, subtitle_resolution_result = self._resolve_subtitle_track(
            request
        )
        self._prepare_track_menu_readiness(
            audio_track_id=resolved_audio_id,
            subtitle_track_id=resolved_subtitle_id,
        )
        audio_result = audio_resolution_result or self._measure(
            "apply_audio_track",
            lambda: self._apply_audio_track(resolved_audio_id),
        )
        subtitle_result = subtitle_resolution_result or self._measure(
            "apply_subtitle_track",
            lambda: self._apply_subtitle_track(resolved_subtitle_id),
        )

        return PlayMediaItemResponse(
            start_position_seconds=start_position_seconds,
            started_reported=True,
            seek_result=seek_result,
            audio_result=audio_result,
            subtitle_result=subtitle_result,
            expected_duration_seconds=max(0, request.expected_duration_seconds),
            pending_audio_track_index=(
                resolved_audio_id
                if resolved_audio_id is not None and not audio_result.successful
                else None
            ),
        )

    def _apply_resume_position(
        self,
        request: PlayMediaItemRequest,
        start_position_seconds: int,
    ) -> DeviceCommandResult:
        if start_position_seconds == 0:
            logger.info(
                "Skipping resume seek because requested position is zero."
            )
            return DeviceCommandResult.skipped(
                "Playback starts at beginning; no seek required."
            )

        return self._player.seek_to_seconds(start_position_seconds)

    def _resolve_audio_track(
        self,
        request: PlayMediaItemRequest,
    ) -> tuple[int | None, DeviceCommandResult | None]:
        if request.selected_source_audio_track_id is None:
            return None, DeviceCommandResult.skipped("No audio track selected.")

        try:
            audio_track_id = self._measure(
                "audio_resolve_media_server_to_player_index",
                lambda: self._track_resolver.resolve_audio_track(
                    source_user_id=request.source_user_id,
                    media_item_id=request.media_item_id,
                    selected_source_track_id=request.selected_source_audio_track_id,
                    media_source_id=request.media_source_id or None,
                ),
            )
            return audio_track_id, None
        except Exception as exc:
            logger.exception("Unable to resolve selected audio track.")
            return None, DeviceCommandResult.failed(
                f"Audio track resolution failed: {type(exc).__name__}: {exc}"
            )

    def _resolve_subtitle_track(
        self,
        request: PlayMediaItemRequest,
    ) -> tuple[int | None, DeviceCommandResult | None]:
        if request.selected_source_subtitle_track_id is None:
            return None, DeviceCommandResult.skipped("No subtitle track selected.")

        if request.selected_source_subtitle_track_id < 0:
            return None, DeviceCommandResult.skipped("Subtitles disabled.")

        try:
            subtitle_track_id = self._measure(
                "subtitle_resolve_media_server_to_player_index",
                lambda: self._track_resolver.resolve_subtitle_track(
                    source_user_id=request.source_user_id,
                    media_item_id=request.media_item_id,
                    selected_source_track_id=request.selected_source_subtitle_track_id,
                    media_source_id=request.media_source_id or None,
                ),
            )
            if subtitle_track_id is None or subtitle_track_id < 0:
                return None, DeviceCommandResult.skipped(
                    "No matching media-player subtitle track."
                )

            return subtitle_track_id, None
        except Exception as exc:
            logger.exception("Unable to resolve selected subtitle track.")
            return None, DeviceCommandResult.failed(
                f"Subtitle track resolution failed: {type(exc).__name__}: {exc}"
            )

    def _prepare_track_menu_readiness(
        self,
        *,
        audio_track_id: int | None,
        subtitle_track_id: int | None,
    ) -> DeviceCommandResult:
        try:
            return self._player.prepare_track_menu_readiness(
                audio_track_id=audio_track_id,
                subtitle_track_id=subtitle_track_id,
            )
        except Exception as exc:
            logger.exception("Unable to prepare track-menu readiness.")
            return DeviceCommandResult.failed(
                f"Track-menu readiness failed: {type(exc).__name__}: {exc}"
            )

    def _apply_audio_track(self, audio_track_id: int | None) -> DeviceCommandResult:
        if audio_track_id is None:
            return DeviceCommandResult.skipped("No audio track selected.")
        try:
            return self._player.select_audio_track(audio_track_id)
        except Exception as exc:
            logger.exception("Unable to apply selected audio track.")
            return DeviceCommandResult.failed(
                f"Audio track selection failed: {type(exc).__name__}: {exc}"
            )

    def _apply_subtitle_track(
        self, subtitle_track_id: int | None
    ) -> DeviceCommandResult:
        if subtitle_track_id is None:
            return DeviceCommandResult.skipped("No subtitle track selected.")
        try:
            return self._measure(
                "subtitle_set_media_player_track",
                lambda: self._player.select_subtitle_track(subtitle_track_id),
            )
        except Exception as exc:
            logger.exception("Unable to apply selected subtitle track.")
            return DeviceCommandResult.failed(
                f"Subtitle track selection failed: {type(exc).__name__}: {exc}"
            )

    def _measure(self, step_name: str, operation):
        if self._step_timer is None:
            return operation()

        with self._step_timer.measure_step(step_name):
            return operation()
