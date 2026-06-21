from __future__ import annotations

import logging
from typing import Any

from home_cinema_control.devices.oppo.constants import OPPO_TELNET_PORT
from home_cinema_control.devices.oppo.control_api_client import OppoControlApiClient
from home_cinema_control.devices.oppo.media_control_playback import (
    OppoMediaControlPlayback,
)
from home_cinema_control.devices.oppo.playback_status_client import (
    OppoPlaybackStatusClient,
)
from home_cinema_control.devices.oppo.telnet_shell import unmount_oppo_path
from home_cinema_control.playback.ports import OppoPlaybackPort
from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    OppoPlaybackPosition,
    OppoPlaybackStartRequest,
    OppoPlaybackStartResult,
    OppoPlaybackState,
)

logger = logging.getLogger(__name__)


def create_oppo_playback_adapter(config: dict[str, Any]) -> OppoPlaybackPort:
    logger.info("Creating OPPO stable MediaControl playback adapter.")
    return OppoStableMediaControlPlaybackAdapter(config)


class OppoStableMediaControlPlaybackAdapter(OppoPlaybackPort):
    """Stable OPPO playback adapter backed by MediaControl HTTP + QPL."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._playback = OppoMediaControlPlayback(config)
        self._last_mounted_path: str | None = None

    def start_playback(
        self,
        request: OppoPlaybackStartRequest,
        *,
        on_waiting=None,
    ) -> OppoPlaybackStartResult:
        result = self._playback.start_playback(request, on_waiting=on_waiting)
        self._last_mounted_path = result.mounted_path
        return result

    def get_playback_state(self) -> OppoPlaybackState:
        result = self._playback_status_client().query_playback_state()
        return OppoPlaybackState(
            status=result.status,
            category=result.category,
            raw_response=result.raw_response,
            ok=result.ok,
        )

    def get_playback_position(self) -> OppoPlaybackPosition:
        return self._playback.get_playback_position()

    def seek_to(self, position_ticks: int) -> DeviceCommandResult:
        return self._playback.seek_to(position_ticks)

    def select_audio_track(self, audio_index: int) -> DeviceCommandResult:
        return self._playback.select_audio_track(audio_index)

    def select_subtitle_track(self, subtitle_index: int) -> DeviceCommandResult:
        return self._playback.select_subtitle_track(subtitle_index)

    def stop_playback(self) -> DeviceCommandResult:
        try:
            response = OppoControlApiClient.from_config(self._config).send_remote_key(
                "STP"
            )
            return DeviceCommandResult.success(f"OPPO playback stop sent: {response}")
        except Exception as exc:
            logger.exception("Unable to stop OPPO playback.")
            return DeviceCommandResult.failed(
                f"OPPO playback stop failed: {type(exc).__name__}: {exc}"
            )

    def cleanup_after_playback_finish(self) -> DeviceCommandResult:
        oppo = self._config["oppo"]

        if not oppo.get("autoscript", False):
            return DeviceCommandResult.skipped(
                "Autoscript is disabled; no unmount needed after playback finish."
            )

        mount_path = self._last_mounted_path
        if not mount_path:
            return DeviceCommandResult.skipped(
                "No mounted share recorded for this playback session."
            )

        if not mount_path.startswith("/mnt/cifs"):
            return DeviceCommandResult.skipped(
                "Autoscript unmount only applies to CIFS/SMB mounts; leaving "
                f"{mount_path} in place."
            )

        try:
            # unmount_oppo_path catches its own connection/telnet errors and
            # reports them as a `False` return rather than raising; only an
            # unexpected mount_path shape raises (defends against unmounting
            # something other than what we just mounted).
            unmounted = unmount_oppo_path(
                host=oppo["ip"],
                port=int(self._config.get("OPPO_Port", OPPO_TELNET_PORT)),
                mount_path=mount_path,
                timeout=oppo.get("autoscript_unmount_timeout_seconds", 3),
            )
        except Exception as exc:
            logger.exception("Unable to unmount OPPO share after playback finish.")
            return DeviceCommandResult.failed(
                f"OPPO autoscript unmount failed: {type(exc).__name__}: {exc}"
            )

        if not unmounted:
            logger.warning(
                "OPPO autoscript unmount reported failure | mount_path=%s",
                mount_path,
            )
            return DeviceCommandResult.failed(
                f"OPPO autoscript unmount failed for {mount_path}."
            )

        logger.info(
            "Unmounted OPPO share after playback finish (autoscript) | "
            "mount_path=%s",
            mount_path,
        )
        return DeviceCommandResult.success(
            f"Unmounted {mount_path} after playback finish (autoscript)."
        )

    def _playback_status_client(self) -> OppoPlaybackStatusClient:
        oppo = self._config["oppo"]
        return OppoPlaybackStatusClient(
            host=oppo["ip"],
            port=int(self._config.get("OPPO_Port", OPPO_TELNET_PORT)),
            timeout=float(oppo.get("connection_timeout_seconds", 3)),
        )
