from __future__ import annotations

from collections.abc import Callable
from typing import Any

from home_cinema_control.devices.oppo.control_api_client import OppoControlApiClient


ControlClientFactory = Callable[[dict[str, Any]], OppoControlApiClient]


def send_stop_playback(
    config: dict[str, Any],
    *,
    control_client_factory: ControlClientFactory = OppoControlApiClient.from_config,
):
    return control_client_factory(config).send_remote_key("STP")


def send_power_off(
    config: dict[str, Any],
    *,
    control_client_factory: ControlClientFactory = OppoControlApiClient.from_config,
):
    return control_client_factory(config).send_remote_key("POF")
