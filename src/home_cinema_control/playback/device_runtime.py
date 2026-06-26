from __future__ import annotations

import logging
from typing import Any

from home_cinema_control.devices.av.factory import create_av_receiver
from home_cinema_control.devices.oppo.constants import OPPO_TELNET_PORT
from home_cinema_control.devices.oppo.control_api_activation import (
    OppoControlApiActivator,
)
from home_cinema_control.devices.oppo.control_api_client import OppoControlApiClient
from home_cinema_control.devices.oppo.playback_status_client import (
    create_oppo_playback_status_client,
)
from home_cinema_control.devices.oppo.remote_control import (
    send_power_off,
    send_stop_playback,
)
from home_cinema_control.devices.oppo.svm_mode import OppoSVMModeClient
from home_cinema_control.playback.state import BridgePlaybackState

logger = logging.getLogger(__name__)


def stop_active_player_playback_before_replacement(
    state: BridgePlaybackState,
    config: dict[str, Any],
    *,
    control_client_factory=OppoControlApiClient.from_config,
) -> None:
    filename = (
        state.active_session.playback_file_name
        if state.active_session is not None
        else ""
    )
    logger.info(
        "Stopping active OPPO playback before replacement | filename=%s",
        filename,
    )
    send_stop_playback(config, control_client_factory=control_client_factory)


def ensure_oppo_control_api_available(
    config: dict[str, Any],
    *,
    activator_factory=OppoControlApiActivator.from_config,
) -> bool:
    activator = activator_factory(config)
    result = activator.ensure_control_api_available(
        max_attempts=int(config["oppo"]["connection_timeout_seconds"])
    )

    if result.available:
        logger.debug(
            "OPPO control API available | host=%s | port=%s | attempts=%s",
            result.host,
            result.port,
            result.attempts,
        )
        return True

    # OPPO_UNAVAILABLE is an "error"-severity diagnostic (see diagnostics.py) —
    # the player being unreachable at playback time is a real failure.
    logger.error(
        "Timeout waiting for OPPO control API | host=%s | port=%s | "
        "attempts=%s | error=%s",
        result.host,
        result.port,
        result.attempts,
        result.error,
    )
    return False


def prepare_oppo_observation_mode(
    config: dict[str, Any],
    *,
    svm_mode_client_factory=OppoSVMModeClient,
) -> None:
    _restore_oppo_svm0_before_startup(
        config,
        svm_mode_client_factory=svm_mode_client_factory,
    )


def power_down_after_playback_if_configured(
    config: dict[str, Any],
    *,
    av_receiver_factory=create_av_receiver,
    control_client_factory=OppoControlApiClient.from_config,
) -> None:
    av = config.get("av") or {}
    if av.get("enabled") is True and av.get("always_on") is not True:
        logger.info("powering off AV receiver")
        av_receiver_factory(config).power_off()

    if config["oppo"]["always_on"] is False:
        send_power_off(config, control_client_factory=control_client_factory)


def log_oppo_qpl_state(config: dict[str, Any], label: str) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return

    try:
        oppo = config.get("oppo", {})
        oppo_ip = oppo.get("ip")
        if not oppo_ip:
            logger.debug("QPL:%s skipped | oppo.ip is not configured", label)
            return

        client = create_oppo_playback_status_client(
            host=oppo_ip,
            port=int(config.get("OPPO_Port", OPPO_TELNET_PORT)),
            timeout=float(oppo.get("connection_timeout_seconds", 3)),
        )

        result = client.query_playback_state()
        logger.debug(
            "QPL:%s | raw=%r | status=%s | lifecycle_phase=%s | ok=%s",
            label,
            result.raw_response,
            result.status,
            result.lifecycle_phase.value,
            result.ok,
        )
    except Exception as exc:
        logger.warning("QPL:%s | ERROR %s: %s", label, type(exc).__name__, exc)


def _restore_oppo_svm0_before_startup(
    config: dict[str, Any],
    *,
    svm_mode_client_factory=OppoSVMModeClient,
) -> None:
    result = svm_mode_client_factory(
        config,
        name="oppo-startup-svm-mode",
    ).set_mode(0)
    if not result.successful:
        logger.warning(
            "Could not reset OPPO SVM 0 before startup; continuing stable "
            "startup | detail=%s",
            result.detail,
        )
        return

    logger.info("OPPO SVM 0 prepared before startup | detail=%s", result.detail)
