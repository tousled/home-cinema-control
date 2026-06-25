from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any, Protocol

from home_cinema_control.playback.startup.models import (
    DeviceCommandResult,
    OppoPlaybackPosition,
    OppoPlaybackStartRequest,
    OppoPlaybackStartResult,
    OppoPlaybackState,
    PlayerMediaFileLocation,
)
from home_cinema_control.devices.oppo.control_api_client import OppoControlApiClient
from home_cinema_control.devices.oppo.models import OppoCommandResponse
from home_cinema_control.devices.oppo.network_mount_service import (
    OppoNetworkFolder,
    OppoNetworkFolderProtocol,
    OppoNetworkMountService,
    resolve_network_folder_protocol,
)
from home_cinema_control.devices.oppo.playback_state_waiter import (
    PlaybackStartupWaitResult,
    wait_until_oppo_reports_active_playback,
)

logger = logging.getLogger(__name__)

DEFAULT_TRACK_MENU_READY_TIMEOUT_SECONDS = 8.0
DEFAULT_TRACK_MENU_READY_POLL_INTERVAL_SECONDS = 0.5
DEFAULT_TRACK_MENU_QUERY_TIMEOUT_SECONDS = 1.0
DEFAULT_TRACK_SELECTION_APPLIED_TIMEOUT_SECONDS = 2.0
DEFAULT_TRACK_SELECTION_APPLIED_POLL_INTERVAL_SECONDS = 0.25


class StartupStepTimer(Protocol):
    def measure_step(self, step_name: str): ...


class OppoMediaControlPlayback:
    def __init__(
        self,
        config: dict[str, Any],
        *,
        client: OppoControlApiClient | None = None,
        playback_state_waiter: Callable[..., PlaybackStartupWaitResult]
        | None = None,
        sleep: Callable[[float], None] | None = None,
            network_mount_service: OppoNetworkMountService | None = None,
            step_timer: StartupStepTimer | None = None,
    ) -> None:
        self._config = config
        self._client = client or OppoControlApiClient.from_config(config)
        self._playback_state_waiter = (
            playback_state_waiter or wait_until_oppo_reports_active_playback
        )
        self._sleep = sleep or time.sleep
        self._network_mount_service = network_mount_service or (
            OppoNetworkMountService(config, control_api_client=self._client)
        )
        self._step_timer = step_timer

    def _measure(self, step_name: str, operation):
        if self._step_timer is None:
            return operation()

        with self._step_timer.measure_step(step_name):
            return operation()

    def start_playback(
        self,
        request: OppoPlaybackStartRequest,
        *,
        on_waiting: Callable[[int], None] | None = None,
    ) -> OppoPlaybackStartResult:
        try:
            location = request.media_location
            network_folder = OppoNetworkFolder(
                server_name=location.content_server,
                folder_path=location.content_directory,
                protocol=self._resolve_network_protocol(request.network_protocol),
            )

            mount_result = self._measure(
                "mount_oppo_network_share",
                lambda: self._network_mount_service.mount(network_folder),
            )

            if not mount_result.successful:
                mount_reconciliation = self._reconcile_optical_mount_failure(
                    request=request,
                    failure_detail=mount_result.detail,
                    on_waiting=on_waiting,
                )
                if mount_reconciliation is not None:
                    return mount_reconciliation

                return OppoPlaybackStartResult(
                    media_mounted=False,
                    playback_command_accepted=False,
                    playback_started_on_device=False,
                    detail=mount_result.detail,
                    mount_protocol=network_folder.protocol.value,
                )

            mounted_share = mount_result.mounted_share
            playback_response = self._start_mounted_share_playback(
                request=request,
                mounted_share=mounted_share,
            )
            logger.info(
                "OPPO MediaControl playback command response | mounted_path=%s | filename=%s | response=%s",
                mounted_share.mount_path,
                location.playback_file_name,
                playback_response.raw_text,
            )

            if not playback_response.is_successful:
                return OppoPlaybackStartResult(
                    media_mounted=True,
                    playback_command_accepted=False,
                    playback_started_on_device=False,
                    detail=playback_response.error_message,
                    mounted_path=mounted_share.mount_path,
                )

            startup_result = self._measure(
                "wait_for_oppo_playback_active",
                lambda: self._playback_state_waiter(
                    config=self._config,
                    timeout=request.startup_timeout_seconds,
                    interval=request.poll_interval_seconds,
                    on_playback_waiting=on_waiting,
                ),
            )

            playback_state = OppoPlaybackState(
                status=startup_result.status,
                category=startup_result.category,
                raw_response=startup_result.raw_response,
                ok=startup_result.raw_response.startswith("@OK"),
            )

            return OppoPlaybackStartResult(
                media_mounted=True,
                playback_command_accepted=True,
                playback_started_on_device=startup_result.started,
                detail=None
                if startup_result.started
                else "Timed out waiting for OPPO active playback.",
                mounted_path=mounted_share.mount_path,
                playback_state=playback_state,
            )
        except Exception as exc:
            logger.exception("OPPO MediaControl playback startup failed.")
            return OppoPlaybackStartResult(
                media_mounted=False,
                playback_command_accepted=False,
                playback_started_on_device=False,
                detail=(
                    "OPPO MediaControl playback startup failed: "
                    f"{type(exc).__name__}: {exc}"
                ),
            )

    def get_playback_position(self) -> OppoPlaybackPosition:
        response = self._client.get_playing_time()

        return OppoPlaybackPosition(
            current_seconds=int(response.payload.get("cur_time", 0)),
            total_seconds=int(response.payload.get("total_time", 0)),
            raw_response=response.raw_text,
        )

    def seek_to(self, position_ticks: int) -> DeviceCommandResult:
        try:
            response = self._client.set_play_time(position_ticks)
            return _command_sent_result("set OPPO playback time", response)
        except Exception as exc:
            logger.exception("OPPO seek failed.")
            return DeviceCommandResult.failed(
                f"OPPO seek failed: {type(exc).__name__}: {exc}"
            )

    def select_audio_track(self, audio_index: int) -> DeviceCommandResult:
        try:
            menu_result = self._wait_for_menu_track(
                menu_name="audio",
                payload_key="audio_list",
                requested_index=audio_index,
                get_menu=self._client.get_audio_menu,
            )
            if isinstance(menu_result, DeviceCommandResult):
                return menu_result

            before_menu = menu_result
            logger.info(
                "OPPO audio menu before selection | requested_index=%s | response=%s",
                audio_index,
                before_menu.raw_text,
            )
            current_audio_index = _selected_menu_index(
                before_menu.payload.get("audio_list", [])
            )
            if current_audio_index == audio_index:
                return DeviceCommandResult.success(
                    f"OPPO audio track already selected: {audio_index}"
                )
            response = self._client.select_audio_track(audio_index)
            result = _command_sent_result("select OPPO audio track", response)
            if not result.successful:
                return result

            after_menu = self._wait_for_menu_selection(
                menu_name="audio",
                payload_key="audio_list",
                requested_index=audio_index,
                get_menu=self._client.get_audio_menu,
            )
            if isinstance(after_menu, DeviceCommandResult):
                return after_menu

            selected_audio_index = _selected_menu_index(
                after_menu.payload.get("audio_list", [])
            )
            logger.info(
                "OPPO audio menu after selection | requested_index=%s | command_response=%s | response=%s",
                audio_index,
                response.raw_text,
                after_menu.raw_text,
            )
            if result.successful and selected_audio_index != audio_index:
                return DeviceCommandResult.failed(
                    "OPPO audio track selection was not applied | "
                    f"requested={audio_index} | selected={selected_audio_index}"
                )
            return result
        except Exception as exc:
            logger.exception("OPPO audio track selection failed.")
            return DeviceCommandResult.failed(
                f"OPPO audio track selection failed: {type(exc).__name__}: {exc}"
            )

    def select_subtitle_track(self, subtitle_index: int) -> DeviceCommandResult:
        try:
            menu_result = self._wait_for_menu_track(
                menu_name="subtitle",
                payload_key="subtitle_list",
                requested_index=subtitle_index,
                get_menu=self._client.get_subtitle_menu,
            )
            if isinstance(menu_result, DeviceCommandResult):
                return menu_result

            before_menu = menu_result
            logger.info(
                "OPPO subtitle menu before selection | requested_index=%s | response=%s",
                subtitle_index,
                before_menu.raw_text,
            )
            current_subtitle_index = _selected_menu_index(
                before_menu.payload.get("subtitle_list", [])
            )

            if current_subtitle_index == subtitle_index:
                return DeviceCommandResult.success(
                    f"OPPO subtitle track already selected: {subtitle_index}"
                )
            response = self._client.select_subtitle_track(subtitle_index)
            result = _command_sent_result("select OPPO subtitle track", response)
            if not result.successful:
                return result

            after_menu = self._wait_for_menu_selection(
                menu_name="subtitle",
                payload_key="subtitle_list",
                requested_index=subtitle_index,
                get_menu=self._client.get_subtitle_menu,
            )
            if (
                isinstance(after_menu, DeviceCommandResult)
                and current_subtitle_index == 0
                and subtitle_index > 0
            ):
                retry_menu = self._retry_subtitle_selection_after_activation(
                    subtitle_index
                )
                if retry_menu is not None:
                    after_menu = retry_menu

            if isinstance(after_menu, DeviceCommandResult):
                return after_menu

            selected_subtitle_index = _selected_menu_index(
                after_menu.payload.get("subtitle_list", [])
            )
            logger.info(
                "OPPO subtitle menu after selection | requested_index=%s | command_response=%s | response=%s",
                subtitle_index,
                response.raw_text,
                after_menu.raw_text,
            )
            if result.successful and selected_subtitle_index != subtitle_index:
                return DeviceCommandResult.failed(
                    "OPPO subtitle track selection was not applied | "
                    f"requested={subtitle_index} | selected={selected_subtitle_index}"
                )
            return result
        except Exception as exc:
            logger.exception("OPPO subtitle track selection failed.")
            return DeviceCommandResult.failed(
                f"OPPO subtitle track selection failed: {type(exc).__name__}: {exc}"
            )

    def get_current_subtitle_track(self) -> int:
        response = self._client.get_subtitle_menu()
        return _selected_menu_index(response.payload.get("subtitle_list", []))

    def _wait_for_menu_track(
        self,
        *,
        menu_name: str,
        payload_key: str,
        requested_index: int,
        get_menu: Callable[..., OppoCommandResponse],
    ) -> OppoCommandResponse | DeviceCommandResult:
        timeout = self._track_menu_ready_timeout_seconds()
        poll_interval = self._track_menu_ready_poll_interval_seconds()
        query_timeout = self._track_menu_query_timeout_seconds()
        deadline = time.monotonic() + timeout
        attempts = 0
        last_raw_response = ""
        last_error = ""

        while True:
            attempts += 1

            try:
                response = get_menu(timeout=query_timeout)
                last_raw_response = response.raw_text
                menu_items = response.payload.get(payload_key, [])

                if _menu_contains_index(menu_items, requested_index):
                    if attempts > 1:
                        logger.info(
                            "OPPO %s menu became ready | requested_index=%s | attempts=%s | response=%s",
                            menu_name,
                            requested_index,
                            attempts,
                            response.raw_text,
                        )
                    return response

                logger.info(
                    "OPPO %s menu not ready for requested track | requested_index=%s | attempts=%s | response=%s",
                    menu_name,
                    requested_index,
                    attempts,
                    response.raw_text,
                )
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.info(
                    "OPPO %s menu query failed while waiting for requested track | "
                    "requested_index=%s | attempts=%s | error=%s",
                    menu_name,
                    requested_index,
                    attempts,
                    last_error,
                )

            remaining_seconds = deadline - time.monotonic()
            if remaining_seconds <= 0:
                detail = (
                    f"OPPO {menu_name} menu was not ready for requested track "
                    f"{requested_index} after {attempts} attempts"
                )
                if last_error:
                    detail = f"{detail}; last_error={last_error}"
                elif last_raw_response:
                    detail = f"{detail}; last_response={last_raw_response}"

                return DeviceCommandResult.failed(detail)

            self._sleep(min(poll_interval, remaining_seconds))

    def _wait_for_menu_selection(
        self,
        *,
        menu_name: str,
        payload_key: str,
        requested_index: int,
        get_menu: Callable[..., OppoCommandResponse],
    ) -> OppoCommandResponse | DeviceCommandResult:
        timeout = self._track_selection_applied_timeout_seconds()
        poll_interval = self._track_selection_applied_poll_interval_seconds()
        query_timeout = self._track_menu_query_timeout_seconds()
        deadline = time.monotonic() + timeout
        attempts = 0
        last_response: OppoCommandResponse | None = None
        last_error = ""
        selected_index = None

        while True:
            attempts += 1
            try:
                response = get_menu(timeout=query_timeout)
                last_response = response
                selected_index = _selected_menu_index(
                    response.payload.get(payload_key, [])
                )

                if selected_index == requested_index:
                    if attempts > 1:
                        logger.info(
                            "OPPO %s track selection became applied | requested_index=%s | attempts=%s | response=%s",
                            menu_name,
                            requested_index,
                            attempts,
                            response.raw_text,
                        )
                    return response
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.info(
                    "OPPO %s menu query failed while waiting for applied selection | "
                    "requested_index=%s | attempts=%s | error=%s",
                    menu_name,
                    requested_index,
                    attempts,
                    last_error,
                )

                if last_response is not None:
                    logger.debug(
                        "Last successful OPPO %s menu before transient selection "
                        "query failure | response=%s",
                        menu_name,
                        last_response.raw_text,
                    )

            remaining_seconds = deadline - time.monotonic()
            if remaining_seconds <= 0:
                detail = (
                    f"OPPO {menu_name} track selection was not applied | "
                    f"requested={requested_index} | selected={selected_index}"
                )
                if last_error:
                    detail = f"{detail}; last_error={last_error}"
                return DeviceCommandResult.failed(detail)

            self._sleep(min(poll_interval, remaining_seconds))

    def _retry_subtitle_selection_after_activation(
        self, subtitle_index: int
    ) -> OppoCommandResponse | None:
        logger.info(
            "Retrying OPPO subtitle selection after subtitle activation | requested_index=%s",
            subtitle_index,
        )
        response = self._client.select_subtitle_track(subtitle_index)
        retry_result = _command_sent_result("select OPPO subtitle track retry", response)
        if not retry_result.successful:
            logger.warning(
                "OPPO subtitle track retry failed | requested_index=%s | result=%s",
                subtitle_index,
                retry_result,
            )
            return None

        retry_menu = self._wait_for_menu_selection(
            menu_name="subtitle",
            payload_key="subtitle_list",
            requested_index=subtitle_index,
            get_menu=self._client.get_subtitle_menu,
        )
        if isinstance(retry_menu, DeviceCommandResult):
            logger.warning(
                "OPPO subtitle track retry was not applied | requested_index=%s | result=%s",
                subtitle_index,
                retry_menu,
            )
            return None

        return retry_menu

    def _track_menu_ready_timeout_seconds(self) -> float:
        return float(
            self._config.get("oppo", {}).get(
                "track_menu_ready_timeout_seconds",
                DEFAULT_TRACK_MENU_READY_TIMEOUT_SECONDS,
            )
        )

    def _track_menu_ready_poll_interval_seconds(self) -> float:
        return float(
            self._config.get("oppo", {}).get(
                "track_menu_ready_poll_interval_seconds",
                DEFAULT_TRACK_MENU_READY_POLL_INTERVAL_SECONDS,
            )
        )

    def _track_menu_query_timeout_seconds(self) -> float:
        return float(
            self._config.get("oppo", {}).get(
                "track_menu_query_timeout_seconds",
                DEFAULT_TRACK_MENU_QUERY_TIMEOUT_SECONDS,
            )
        )

    def _track_selection_applied_timeout_seconds(self) -> float:
        return float(
            self._config.get("oppo", {}).get(
                "track_selection_applied_timeout_seconds",
                DEFAULT_TRACK_SELECTION_APPLIED_TIMEOUT_SECONDS,
            )
        )

    def _track_selection_applied_poll_interval_seconds(self) -> float:
        return float(
            self._config.get("oppo", {}).get(
                "track_selection_applied_poll_interval_seconds",
                DEFAULT_TRACK_SELECTION_APPLIED_POLL_INTERVAL_SECONDS,
            )
        )

    def _resolve_network_protocol(
            self, protocol: str | None = None
    ) -> OppoNetworkFolderProtocol:
        return resolve_network_folder_protocol(self._config, protocol)

    def _reconcile_optical_mount_failure(
        self,
        *,
        request: OppoPlaybackStartRequest,
            failure_detail: str,
        on_waiting: Callable[[int], None] | None,
    ) -> OppoPlaybackStartResult | None:
        if not _is_optical_image_location(request.media_location):
            return None

        logger.warning(
            "OPPO mount request failed for optical media; checking whether "
            "the player completed startup asynchronously | server=%s | "
            "folder=%s | filename=%s | detail=%s",
            request.media_location.content_server,
            request.media_location.content_directory,
            request.media_location.playback_file_name,
            failure_detail,
        )

        startup_result = self._measure(
            "wait_for_oppo_playback_active",
            lambda: self._playback_state_waiter(
                config=self._config,
                timeout=request.startup_timeout_seconds,
                interval=request.poll_interval_seconds,
                on_playback_waiting=on_waiting,
            ),
        )

        playback_state = OppoPlaybackState(
            status=startup_result.status,
            category=startup_result.category,
            raw_response=startup_result.raw_response,
            ok=startup_result.raw_response.startswith("@OK"),
        )

        if not startup_result.started:
            logger.warning(
                "OPPO did not report active playback after optical mount failure | "
                "status=%s | category=%s | raw=%r",
                startup_result.status.value,
                startup_result.category.value,
                startup_result.raw_response,
            )
            return None

        logger.warning(
            "OPPO reported active playback after optical mount failure; treating "
            "startup as accepted by the player | status=%s | category=%s | raw=%r",
            startup_result.status.value,
            startup_result.category.value,
            startup_result.raw_response,
        )

        return OppoPlaybackStartResult(
            media_mounted=True,
            playback_command_accepted=True,
            playback_started_on_device=True,
            detail="Mount request failed, but OPPO reported active playback.",
            mounted_path=None,
            playback_state=playback_state,
        )

    def _start_mounted_share_playback(
        self, *, request, mounted_share
    ) -> OppoCommandResponse:
        location = request.media_location
        timeout = self._config["oppo"]["playback_start_timeout_seconds"]

        if location.playback_file_format == "bluray":
            return self._client.mounted_folder_contains_blu_ray_structure(
                mounted_share=mounted_share,
                relative_folder_path=location.playback_file_name,
                timeout=timeout,
            )
        else:
            return self._client.play_normal_file(
                mounted_share=mounted_share,
                filename=location.playback_file_name,
                index="0",
                timeout=timeout,
            )




def _is_optical_image_location(location: PlayerMediaFileLocation) -> bool:
    file_format = location.playback_file_format.lower()
    file_name = location.playback_file_name.lower()

    return "bluray" in file_format or file_format == "iso" or file_name.endswith(".iso")


def _command_sent_result(
    operation: str, response: OppoCommandResponse
) -> DeviceCommandResult:
    if response.payload.get("success") is False:
        message = response.error_message or response.raw_text
        return DeviceCommandResult.failed(
            f"{operation} command sent; OPPO returned success=false: {message}"
        )

    return DeviceCommandResult.success(f"{operation} response: {response.raw_text}")


def _selected_menu_index(menu_items: list[dict[str, Any]]) -> int:
    for item in menu_items:
        if item.get("selected") is True:
            return int(item.get("index", 0))

    return 0


def _menu_contains_index(menu_items: list[dict[str, Any]], requested_index: int) -> bool:
    for item in menu_items:
        try:
            if int(item.get("index", -1)) == requested_index:
                return True
        except (TypeError, ValueError):
            continue

    return False
