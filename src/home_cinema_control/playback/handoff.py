from __future__ import annotations

import logging
from collections.abc import Callable

from home_cinema_control.media_servers.common.playback import MediaServerPlaybackServices
from home_cinema_control.playback.active_context import ActivePlaybackRuntimeContext
from home_cinema_control.playback.content_kind import MediaContentKind
from home_cinema_control.playback.diagnostics import (
    diagnose_media_server_item_unavailable,
    diagnose_oppo_unavailable,
    diagnose_orchestration_result,
    diagnose_path_error,
)
from home_cinema_control.playback.events import (
    PlaybackEventContext,
    PlaybackHandoffFinalizedEvent,
    PlaybackObservation,
    PlaybackObservedState,
    new_playback_handoff_id,
    new_playback_event_id,
    new_playback_session_id,
)
from home_cinema_control.playback.factory import create_playback_orchestrator_wiring
from home_cinema_control.playback.intent import PlaybackIntent, PlaybackOrigin
from home_cinema_control.playback.notification_sender import (
    playback_start_messages,
    send_playback_message,
    send_stop_with_delivery_reliability,
)
from home_cinema_control.playback.oppo_lifecycle import OppoPlaybackLifecycleService
from home_cinema_control.playback.orchestrator import PlaybackOrchestrationRequest
from home_cinema_control.playback.request_preparation import prepare_playback_requests
from home_cinema_control.playback.result_reporting import report_orchestration_result
from home_cinema_control.playback.startup import PlaybackStartupRequest
from home_cinema_control.playback.startup.messaging import PlaybackStartupMessagingService
from home_cinema_control.playback.state import BridgePlaybackState
from home_cinema_control.playback.state_detector import PlaybackStateDetector
from home_cinema_control.playback.timing import PlaybackStartupTimer
from home_cinema_control.playback.media_location import PlayerMediaFileLocationError
from home_cinema_control.telemetry.startup_metrics import build_startup_metrics


logger = logging.getLogger(__name__)
NORMAL_FINISH_IDLE_CONFIRMATION_POLLS = 5
REPLACEMENT_FINISH_IDLE_CONFIRMATION_POLLS = 60


class PlaybackHandoffService:
    """Own the synchronous lifecycle of one playback handoff.

    Thread creation and replacement admission remain in
    :class:`PlaybackThreadLifecycle`. This service owns what happens inside a
    handoff, including the final cleanup that must happen before the worker
    thread is considered finished.
    """

    def __init__(
        self,
        *,
        playback_session,
        playback_state: BridgePlaybackState,
        media_server_playback_services: MediaServerPlaybackServices | None,
        oppo_lifecycle: OppoPlaybackLifecycleService,
        playback_event_publisher=None,
        playback_state_detector: PlaybackStateDetector | None = None,
        active_context: ActivePlaybackRuntimeContext | None = None,
        replacement_requested: Callable[[], bool],
    ) -> None:
        self._playback_session = playback_session
        self._state = playback_state
        self._media_server_playback_services = media_server_playback_services
        self._oppo_lifecycle = oppo_lifecycle
        self._playback_event_publisher = playback_event_publisher
        self._playback_state_detector = playback_state_detector or PlaybackStateDetector()
        self._active_context = active_context or ActivePlaybackRuntimeContext()
        self._replacement_requested = replacement_requested
        self._playback_return_tv_app_id: str | None = None

    @property
    def active_publisher(self):
        return self._active_context.publisher

    @property
    def active_media_player(self):
        return self._active_context.media_player

    def stop_active_playback_before_replacement(self) -> None:
        self._oppo_lifecycle.stop_active_playback_before_replacement(
            self._state,
            self._playback_session.config,
        )

    def run(
        self,
        intent: PlaybackIntent,
        *,
        origin: PlaybackOrigin,
    ):
        handoff_id = new_playback_handoff_id()
        movie = ""
        lifecycle = {"orchestration_started": False}
        result = None

        self._state.start_loading(intent)
        try:
            result, movie = self._run_handoff(
                intent,
                origin=origin,
                lifecycle=lifecycle,
            )
            return result
        finally:
            self._finalize_handoff(
                handoff_id=handoff_id,
                intent=intent,
                origin=origin,
                movie=movie,
                result=result,
                orchestration_started=lifecycle["orchestration_started"],
            )

    def observe_playback_state(self, state: PlaybackObservedState) -> None:
        self._playback_state_detector.observe(
            PlaybackObservation(state=state, source="player-observation"),
            publish=self._publish_playback_event,
        )

    def _run_handoff(
        self,
        intent: PlaybackIntent,
        *,
        origin: PlaybackOrigin,
        lifecycle: dict[str, bool],
    ) -> tuple[object | None, str]:
        playback_session = self._playback_session
        startup_timer = PlaybackStartupTimer()
        session_id = intent.source_client_session_id
        messages = playback_start_messages(playback_session.lang)
        messaging = PlaybackStartupMessagingService(
            playback_session=playback_session,
            origin=origin,
            session_id=session_id,
            lang=playback_session.lang,
        )
        with startup_timer.measure_step("notify_received"):
            messaging.received()

        self._oppo_lifecycle.prepare_playback_start(playback_session.config)
        logger.info("playback origin: %s", origin.value)

        media_server_services = self._media_server_services()
        media_server_playback_context = media_server_services.playback_context_from_intent(
            intent
        )

        movie = ""
        with startup_timer.measure_step("process_media_server_payload"):
            try:
                item_info = playback_session.get_media_source_info(
                    playback_session.user_info["User"]["Id"],
                    intent.media_item_id,
                    intent.media_source_id,
                )
            except Exception as exc:
                logger.exception("Could not load media server item for playback handoff.")
                diagnostic = diagnose_media_server_item_unavailable(str(exc))
                self._record_diagnostic(diagnostic)
                return None, movie

        with startup_timer.measure_step("ensure_oppo_control_api_available"):
            control_api_available = self._oppo_lifecycle.ensure_control_api_available(
                playback_session.config
            )

        if not control_api_available:
            diagnostic = diagnose_oppo_unavailable()
            self._record_diagnostic(diagnostic)
            send_playback_message(
                playback_session,
                origin,
                session_id,
                messages.error_no_oppo,
            )
            return None, movie

        if _should_stop_source_client_before_handoff(origin):
            with startup_timer.measure_step("stop_source_client_before_handoff"):
                response_data = send_stop_with_delivery_reliability(
                    playback_session.stop_session_playback,
                    session_id,
                )
            logger.debug("stop source client response: %s", response_data)

        playback_wiring = create_playback_orchestrator_wiring(
            config=playback_session.config,
            media_server_client=playback_session.client,
            bridge_session_id=playback_session.user_info["SessionInfo"]["Id"],
            playback_context=media_server_playback_context,
            playback_event_publisher_factory=(
                media_server_services.create_playback_event_publisher
            ),
            track_resolver=media_server_services.create_track_resolver(playback_session),
            playback_state=self._state,
            step_timer=startup_timer,
            playback_state_observer=self.observe_playback_state,
        )

        with startup_timer.measure_step("notify_locating"):
            messaging.locating()

        try:
            with startup_timer.measure_step("resolve_media_path"):
                prepared_requests = prepare_playback_requests(
                    config=playback_session.config,
                    intent=intent,
                    item_info=item_info,
                    previous_tv_app_id_override=self._playback_return_tv_app_id,
                )
                media_location = prepared_requests.media_location
                movie = prepared_requests.movie_path
        except PlayerMediaFileLocationError as exc:
            logger.warning("Media path resolution failed: %s", exc)
            diagnostic = diagnose_path_error(exc)
            self._record_diagnostic(diagnostic)
            return None, movie

        logger.info("Servidor               : %s", media_location.content_server)
        logger.info("Fichero                : %s", media_location.playback_file_name)
        logger.info("Carpeta                : %s", media_location.content_directory)
        logger.info("-----------------------------------------------------------")
        self._state.set_active_media_location(
            media_location=media_location,
            item_info=item_info,
        )
        self._active_context.activate(playback_wiring)

        lifecycle["orchestration_started"] = True
        playback_orchestration_result = playback_wiring.playback_orchestrator.play_until_stopped(
            PlaybackOrchestrationRequest(
                startup_request=PlaybackStartupRequest(
                    output_switch_request=prepared_requests.output_switch_request,
                    media_player_start_request=prepared_requests.media_player_start_request,
                ),
                startup_completion_request=prepared_requests.startup_completion_request,
                is_paused=False,
                is_muted=False,
                restore_outputs_on_finish=self._should_restore_outputs,
                finish_idle_confirmation_polls=self._finish_idle_confirmation_polls,
                on_startup_waiting=messaging.notify_waiting,
                on_tracks_applying=messaging.tracks_applying,
                on_startup_completed=lambda r: self._on_startup_completed(
                    r,
                    intent=intent,
                    movie=movie,
                    messaging=messaging,
                    content_kind=item_info.content_kind,
                    playback_wiring=playback_wiring,
                    startup_timer=startup_timer,
                ),
            )
        )

        report_orchestration_result(
            playback_session=playback_session,
            origin=origin,
            session_id=session_id,
            media_location=media_location,
            playback_orchestration_result=playback_orchestration_result,
            messages=messages,
            movie=movie,
        )
        diagnostic = diagnose_orchestration_result(
            playback_orchestration_result,
            playback_session.config,
        )
        if diagnostic is not None:
            self._record_diagnostic(diagnostic)
        self._remember_playback_return_tv_app_id(playback_orchestration_result)
        self._clear_playback_return_tv_app_id_after_final_finish(
            playback_orchestration_result
        )
        return playback_orchestration_result, movie

    def _finalize_handoff(
        self,
        *,
        handoff_id: str,
        intent: PlaybackIntent,
        origin: PlaybackOrigin,
        movie: str,
        result,
        orchestration_started: bool,
    ) -> None:
        playback_session_id = self._playback_state_detector.session_id
        cleanup_error = None
        try:
            if orchestration_started:
                try:
                    self._oppo_lifecycle.finish_playback(self._playback_session.config)
                except Exception as exc:
                    cleanup_error = exc
                    logger.exception("Playback OPPO cleanup failed.")
                try:
                    self._playback_state_detector.stop_session(
                        publish=self._publish_playback_event
                    )
                except Exception as exc:
                    cleanup_error = cleanup_error or exc
                    logger.exception("Playback event session cleanup failed.")
        finally:
            self._active_context.clear()
            _reset_bridge_playback_state(self._state, movie)
            self._publish_handoff_finalized(
                handoff_id=handoff_id,
                intent=intent,
                origin=origin,
                result=result,
                playback_session_id=playback_session_id,
                cleanup_error=cleanup_error,
            )

        if cleanup_error is not None:
            raise cleanup_error

    def _on_startup_completed(
        self,
        _result,
        *,
        intent: PlaybackIntent,
        movie: str,
        messaging: PlaybackStartupMessagingService,
        content_kind: MediaContentKind,
        playback_wiring,
        startup_timer: PlaybackStartupTimer,
    ) -> None:
        self._state.playstate = "Playing"
        self._state.last_diagnostic = None
        logger.debug("start_position_seconds: %s", intent.start_position_seconds)

        startup_metrics = None
        try:
            if _result is not None:
                startup_metrics = build_startup_metrics(
                    startup_timer.snapshot(),
                    _result,
                )
        except Exception:
            logger.debug("Could not build playback startup metrics", exc_info=True)

        active_session = self._state.active_session
        context = PlaybackEventContext(
            session_id=new_playback_session_id(),
            media_type=content_kind.value,
            title=active_session.title if active_session is not None else movie,
            source=_media_server_source_name(self._playback_session),
            player="oppo",
            startup_metrics=startup_metrics,
        )
        self._playback_state_detector.start_session(
            context,
            publish=self._publish_playback_event,
        )
        logger.info("Reprodución iniciada: %s", movie)

        self._oppo_lifecycle.record_playback_started(self._playback_session.config)
        startup_timer.log_summary()
        self._oppo_lifecycle.configure_observed_event_reporting(
            playback_wiring=playback_wiring,
            media_server_services=self._media_server_services(),
            playback_session=self._playback_session,
            playback_state=self._state,
        )
        messaging.action(content_kind)

    def _should_restore_outputs(self) -> bool:
        return not self._replacement_requested()

    def _finish_idle_confirmation_polls(self) -> int:
        return (
            REPLACEMENT_FINISH_IDLE_CONFIRMATION_POLLS
            if self._replacement_requested()
            else NORMAL_FINISH_IDLE_CONFIRMATION_POLLS
        )

    def _publish_playback_event(self, event) -> None:
        if event is None or self._playback_event_publisher is None:
            return
        try:
            self._playback_event_publisher.publish(event)
        except Exception:
            logger.exception(
                "Playback event dispatch failed | event_id=%s | event=%s",
                event.event_id,
                event.event_type,
            )

    def _publish_handoff_finalized(
        self,
        *,
        handoff_id: str,
        intent: PlaybackIntent,
        origin: PlaybackOrigin,
        result,
        playback_session_id: str | None,
        cleanup_error: Exception | None,
    ) -> None:
        if self._playback_event_publisher is None:
            return
        diagnostic = getattr(self._state, "last_diagnostic", None)
        event = PlaybackHandoffFinalizedEvent(
            event_id=new_playback_event_id(),
            handoff_id=handoff_id,
            origin=origin.value,
            successful=bool(result is not None and result.successful and cleanup_error is None),
            media_item_id=intent.media_item_id,
            media_source_id=intent.media_source_id,
            playback_session_id=playback_session_id,
            diagnostic_component=_telemetry_component(
                getattr(diagnostic, "component", "")
            ),
            diagnostic_code=getattr(diagnostic, "code", None),
        )
        try:
            self._playback_event_publisher.publish(event)
        except Exception:
            logger.exception("Playback handoff finalized event dispatch failed.")

    def _record_diagnostic(self, diagnostic) -> None:
        record = getattr(self._state, "record_diagnostic", None)
        if callable(record):
            record(diagnostic)
        else:
            self._state.last_diagnostic = diagnostic

    def _remember_playback_return_tv_app_id(self, result) -> None:
        previous_tv_app_id = result.startup_result.output_switch_result.previous_tv_app_id
        if previous_tv_app_id is None or _is_lg_hdmi_app_id(previous_tv_app_id):
            return
        self._playback_return_tv_app_id = previous_tv_app_id

    def _clear_playback_return_tv_app_id_after_final_finish(self, result) -> None:
        if self._replacement_requested() or result.finish_result is None:
            return
        self._playback_return_tv_app_id = None

    def _media_server_services(self) -> MediaServerPlaybackServices:
        if self._media_server_playback_services is None:
            raise RuntimeError("Media-server playback services are not configured.")
        return self._media_server_playback_services


def _is_lg_hdmi_app_id(app_id: str) -> bool:
    return app_id.startswith("com.webos.app.hdmi")


def _should_stop_source_client_before_handoff(origin: PlaybackOrigin) -> bool:
    return origin in (
        PlaybackOrigin.OBSERVED_TV_CLIENT,
        PlaybackOrigin.REMOTE_CONTROL_COMMAND,
    )


def _reset_bridge_playback_state(state: BridgePlaybackState, movie: str) -> None:
    state.finish()
    logger.info("Fin PlaybackHandoffService.run %s", movie)


def _media_server_source_name(playback_session) -> str:
    name = playback_session.__class__.__name__
    return name.removesuffix("Session").lower()


def _telemetry_component(component: str) -> str | None:
    if not component:
        return None
    if component in {"oppo", "tv", "av", "path", "cleanup", "system"}:
        return component
    if component in {"emby", "jellyfin", "media_server"}:
        return "media_server"
    return "system"
