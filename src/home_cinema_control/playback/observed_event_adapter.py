from __future__ import annotations

import logging

from home_cinema_control.playback.observed_event_reporter import (
    ObservedPlaybackEventReporter,
)

logger = logging.getLogger(__name__)


def configure_oppo_observed_event_reporting(
    *,
    playback_wiring,
    observed_event_sink,
    track_mapper,
) -> bool:
    """Wire OPPO observed-event reporting into the active during-playback flow."""
    reporter = ObservedPlaybackEventReporter(
        sink=observed_event_sink,
        track_mapper=track_mapper,
    )
    during_set_reporter = getattr(
        playback_wiring.during_playback_orchestrator,
        "set_observed_event_reporter",
        None,
    )
    if during_set_reporter is not None:
        during_set_reporter(reporter)
        logger.info("OPPO observed event reporting configured")
        return True

    logger.warning("OPPO observed event reporting is not supported by playback wiring.")
    return False
