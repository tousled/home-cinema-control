from __future__ import annotations

from home_cinema_control.playback.startup.models import PlaybackStartupResult
from home_cinema_control.playback.timing import PlaybackStartupTimingSnapshot


STARTUP_METRICS_SCHEMA_VERSION = 1
STARTUP_STRATEGY = "sequential"
_ALLOWED_STRATEGIES = {"sequential", "instantplay"}
_DURATION_FIELDS = (
    "total_ms",
    "media_prepare_ms",
    "tv_prepare_ms",
    "av_prepare_ms",
    "oppo_prepare_ms",
    "oppo_commit_ms",
    "oppo_confirm_ms",
    "post_start_ms",
)

_MEDIA_STEPS = ("process_media_server_payload", "resolve_media_path")
_TV_STEPS = ("read_current_tv_app", "switch_tv_to_oppo_input")
_AV_STEPS = ("power_on_av_receiver", "switch_av_receiver_to_oppo_input")
_OPPO_PREPARE_STEPS = (
    "ensure_oppo_control_api_available",
    "mount_oppo_network_share",
)
_POST_START_STEPS = (
    "notify_media_server_playback_started",
    "apply_resume_position",
    "apply_audio_track",
    "apply_subtitle_track",
)


def build_startup_metrics(
    snapshot: PlaybackStartupTimingSnapshot,
    startup_result: PlaybackStartupResult,
) -> dict[str, int | str | None]:
    """Build the allowlisted, device-level metrics sent with playback_started."""
    durations = _durations_by_name(snapshot)
    output = startup_result.output_switch_result

    return {
        "schema_version": STARTUP_METRICS_SCHEMA_VERSION,
        "strategy": STARTUP_STRATEGY,
        "total_ms": _milliseconds(snapshot.total_elapsed_seconds),
        "media_prepare_ms": _sum_steps(durations, _MEDIA_STEPS),
        "tv_prepare_ms": (
            _sum_steps(durations, _TV_STEPS)
            if output.tv_input_result.status.value != "skipped"
            else None
        ),
        "av_prepare_ms": (
            _sum_steps(durations, _AV_STEPS)
            if (
                output.av_power_result.status.value != "skipped"
                or output.av_input_result.status.value != "skipped"
            )
            else None
        ),
        "oppo_prepare_ms": _sum_steps(durations, _OPPO_PREPARE_STEPS),
        "oppo_commit_ms": _sum_steps(durations, ("commit_oppo_playback",)),
        "oppo_confirm_ms": _sum_steps(
            durations, ("wait_for_oppo_playback_active",)
        ),
        "post_start_ms": _sum_steps(durations, _POST_START_STEPS),
    }


def normalize_startup_metrics(value: object) -> dict[str, int | str | None]:
    """Keep only the versioned startup metric vocabulary and safe scalars."""
    if not isinstance(value, dict):
        return {}

    schema_version = value.get("schema_version")
    strategy = value.get("strategy")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != STARTUP_METRICS_SCHEMA_VERSION
        or not isinstance(strategy, str)
        or strategy not in _ALLOWED_STRATEGIES
    ):
        return {}

    normalized: dict[str, int | str | None] = {
        "schema_version": schema_version,
        "strategy": strategy,
    }
    for field in _DURATION_FIELDS:
        duration = value.get(field)
        if duration is None and field in {"tv_prepare_ms", "av_prepare_ms"}:
            normalized[field] = None
        elif isinstance(duration, int) and not isinstance(duration, bool) and duration >= 0:
            normalized[field] = duration
    return normalized


def _durations_by_name(snapshot: PlaybackStartupTimingSnapshot) -> dict[str, float]:
    durations: dict[str, float] = {}
    for step in snapshot.steps:
        durations[step.name] = durations.get(step.name, 0.0) + step.elapsed_seconds
    return durations


def _sum_steps(durations: dict[str, float], names: tuple[str, ...]) -> int:
    return _milliseconds(sum(durations.get(name, 0.0) for name in names))


def _milliseconds(seconds: float) -> int:
    return max(0, int(round(seconds * 1000)))
