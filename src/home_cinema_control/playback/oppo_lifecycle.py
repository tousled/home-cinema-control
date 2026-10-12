from __future__ import annotations

from typing import Any

from home_cinema_control.playback.device_runtime import (
    ensure_oppo_control_api_available,
    log_oppo_qpl_state,
    power_down_after_playback_if_configured,
    prepare_oppo_observation_mode,
    stop_active_player_playback_before_replacement,
)
from home_cinema_control.playback.observed_event_adapter import (
    configure_oppo_observed_event_reporting,
)
from home_cinema_control.playback.state import BridgePlaybackState


class OppoPlaybackLifecycleService:
    """Own the OPPO-specific actions around the playback lifecycle.

    Low-level OPPO clients remain in the device adapters. This service owns
    when those operations happen relative to playback startup, observation,
    replacement, and cleanup.
    """

    def prepare_playback_start(self, config: dict[str, Any]) -> None:
        prepare_oppo_observation_mode(config)
        log_oppo_qpl_state(config, "playback_application_start")

    def ensure_control_api_available(self, config: dict[str, Any]) -> bool:
        return ensure_oppo_control_api_available(config)

    def stop_active_playback_before_replacement(
        self,
        state: BridgePlaybackState,
        config: dict[str, Any],
    ) -> None:
        stop_active_player_playback_before_replacement(state, config)

    def configure_observed_event_reporting(
        self,
        *,
        playback_wiring,
        media_server_services,
        playback_session,
        playback_state: BridgePlaybackState,
    ) -> bool:
        observed_event_sink = media_server_services.create_observed_playback_consumer(
            playback_state=playback_state,
            publisher=playback_wiring.playback_event_publisher,
        )
        track_mapper = media_server_services.create_observed_track_mapper(
            playback_session,
            playback_state=playback_state,
        )
        return configure_oppo_observed_event_reporting(
            playback_wiring=playback_wiring,
            observed_event_sink=observed_event_sink,
            track_mapper=track_mapper,
        )

    def record_playback_started(self, config: dict[str, Any]) -> None:
        log_oppo_qpl_state(config, "after_oppo_playback_start")

    def finish_playback(self, config: dict[str, Any]) -> None:
        power_down_after_playback_if_configured(config)
