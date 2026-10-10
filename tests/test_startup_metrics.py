from home_cinema_control.playback.player_state import PlayerPlaybackStartResult
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    PlaybackOutputSwitchResult,
    PlaybackStartupResult,
)
from home_cinema_control.playback.timing import (
    PlaybackStartupStepTiming,
    PlaybackStartupTimingSnapshot,
)
from home_cinema_control.telemetry.startup_metrics import build_startup_metrics


def _startup_result(*, tv_enabled=True, av_enabled=True):
    return PlaybackStartupResult(
        output_switch_result=PlaybackOutputSwitchResult(
            previous_tv_app_id=None,
            tv_input_result=(
                DeviceCommandResult.success()
                if tv_enabled
                else DeviceCommandResult.skipped()
            ),
            av_power_result=(
                DeviceCommandResult.success()
                if av_enabled
                else DeviceCommandResult.skipped()
            ),
            av_input_result=(
                DeviceCommandResult.success()
                if av_enabled
                else DeviceCommandResult.skipped()
            ),
        ),
        media_player_start_result=PlayerPlaybackStartResult(
            media_mounted=True,
            playback_command_accepted=True,
            playback_started_on_device=True,
        ),
    )


def _snapshot():
    durations = {
        "process_media_server_payload": 0.1,
        "resolve_media_path": 0.045,
        "read_current_tv_app": 0.2,
        "switch_tv_to_oppo_input": 0.3,
        "power_on_av_receiver": 0.4,
        "switch_av_receiver_to_oppo_input": 0.1,
        "ensure_oppo_control_api_available": 0.5,
        "mount_oppo_network_share": 0.6,
        "commit_oppo_playback": 0.19,
        "wait_for_oppo_playback_active": 0.305,
        "notify_media_server_playback_started": 0.01,
        "apply_resume_position": 0.02,
        "apply_audio_track": 0.03,
        "apply_subtitle_track": 0.04,
    }
    return PlaybackStartupTimingSnapshot(
        total_elapsed_seconds=2.847,
        steps=tuple(
            PlaybackStartupStepTiming(name=name, elapsed_seconds=duration)
            for name, duration in durations.items()
        ),
    )


def test_build_startup_metrics_aggregates_allowlisted_steps():
    metrics = build_startup_metrics(_snapshot(), _startup_result())

    assert metrics == {
        "schema_version": 1,
        "strategy": "sequential",
        "total_ms": 2847,
        "media_prepare_ms": 145,
        "tv_prepare_ms": 500,
        "av_prepare_ms": 500,
        "oppo_prepare_ms": 1100,
        "oppo_commit_ms": 190,
        "oppo_confirm_ms": 305,
        "post_start_ms": 100,
    }


def test_build_startup_metrics_marks_disabled_devices_as_not_applicable():
    metrics = build_startup_metrics(
        _snapshot(), _startup_result(tv_enabled=False, av_enabled=False)
    )

    assert metrics["tv_prepare_ms"] is None
    assert metrics["av_prepare_ms"] is None
