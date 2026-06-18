from __future__ import annotations

from enum import StrEnum
from typing import Any


class OppoObservationMode(StrEnum):
    AUTO = "auto"
    POLLING = "polling"


def resolve_oppo_observation_mode(config: dict[str, Any]) -> OppoObservationMode:
    oppo = config.get("oppo") or {}
    raw_mode = str(oppo.get("observation_mode") or OppoObservationMode.AUTO.value)
    normalized = raw_mode.strip().lower()

    if normalized in {"auto", "stable", "svm3", "oppo_verbose", "verbose"}:
        return OppoObservationMode.AUTO

    if normalized in {"polling", "qpl"}:
        return OppoObservationMode.POLLING

    return OppoObservationMode.AUTO
