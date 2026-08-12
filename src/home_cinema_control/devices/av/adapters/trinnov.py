import logging
import socket
import time

from wakeonlan import wake

from home_cinema_control.config.models import AvInputSource
from home_cinema_control.devices.av.adapters.trinnov_client import (
    TRINNOV_DEFAULT_PORT,
    TrinnovCommandResponse,
    TrinnovTcpClient,
)
from home_cinema_control.devices.av.adapters.trinnov_mapper import (
    fallback_profile_sources,
    normalize_profile_command,
    parse_profile_name,
)
from home_cinema_control.devices.av.base import BaseAvReceiver
from home_cinema_control.network.arp import find_mac_by_ip
from home_cinema_control.playback.startup.models import DeviceCommandResult

TRINNOV_POWER_OFF_COMMAND = "power_off_SECURED_FHZMCH48FE\n"
PROFILE_DISCOVERY_LIMIT = 32
WAKE_TIMEOUT_SECONDS = 30.0
WAKE_RETRY_INTERVAL_SECONDS = 1.0
FAST_CONNECT_TIMEOUT_SECONDS = 0.5
TRINNOV_MAC_CONFIG_KEY = "trinnov_mac"


class TrinnovAvReceiver(BaseAvReceiver):
    receiver_name = "Trinnov Altitude"

    def list_hdmi_inputs(self) -> list[AvInputSource]:
        try:
            discovered = self._discover_profile_sources()
        except Exception as exc:
            logging.warning(
                "Trinnov source/profile discovery failed; using fallback list: %s",
                exc,
            )
            return fallback_profile_sources(PROFILE_DISCOVERY_LIMIT)
        return discovered or fallback_profile_sources(PROFILE_DISCOVERY_LIMIT)

    def power_on(self) -> DeviceCommandResult:
        mac = self._get_mac_for_wake()
        if not mac:
            return DeviceCommandResult.skipped(
                "Trinnov power actions require a MAC address."
            )

        try:
            self._identify_if_reachable()
            return DeviceCommandResult.success("Trinnov is reachable.")
        except (OSError, TimeoutError, ConnectionError):
            logging.info(
                "Trinnov is not reachable; attempting Wake-on-LAN if MAC is configured."
            )

        try:
            logging.info("Sending Wake-on-LAN packet to Trinnov Altitude: %s", mac)
            wake(mac)
            self._wait_until_reachable()
            return DeviceCommandResult.success(
                "Trinnov woke and accepted TCP identification."
            )
        except Exception as exc:
            logging.warning("Unable to wake Trinnov Altitude: %s", exc)
            return DeviceCommandResult.failed(f"Unable to wake Trinnov Altitude: {exc}")

    def switch_to_input(self, input_id: str) -> DeviceCommandResult:
        try:
            command = normalize_profile_command(input_id)
        except ValueError as exc:
            return DeviceCommandResult.failed(str(exc))
        return self._send_trinnov_command(
            command,
            operation_name="switching Trinnov source/profile",
        )

    def restore_tv_audio(self) -> DeviceCommandResult:
        tv_input = (self.config.get("av") or {}).get("tv_connected_input", "")
        if not tv_input:
            logging.debug(
                "Trinnov tv_connected_input not configured; skipping TV audio restore"
            )
            return DeviceCommandResult.skipped("TV audio restore not configured.")
        return self.switch_to_input(tv_input)

    def power_off(self) -> DeviceCommandResult:
        if (self.config.get("av") or {}).get("always_on", True):
            return DeviceCommandResult.skipped(
                "Trinnov is configured as always on; power-off skipped."
            )
        if not self._get_mac_for_wake():
            return DeviceCommandResult.skipped(
                "Trinnov power actions require a MAC address."
            )
        return self._send_trinnov_command(
            TRINNOV_POWER_OFF_COMMAND,
            operation_name="powering off Trinnov Altitude",
        )

    def _send_trinnov_command(
        self,
        command: str,
        *,
        operation_name: str,
    ) -> DeviceCommandResult:
        try:
            response = self._client().send_command(command)
        except (OSError, TimeoutError, ConnectionError, ValueError) as exc:
            logging.warning("Trinnov error while %s: %s", operation_name, exc)
            return DeviceCommandResult.failed(str(exc))

        return _response_to_device_result(response)

    def _discover_profile_sources(self) -> list[AvInputSource]:
        client = self._client()
        sources = []
        for source in range(PROFILE_DISCOVERY_LIMIT):
            response = client.send_command(f"get_profile_name {source}\n")
            if not response.successful:
                continue
            parsed = parse_profile_name(source, response.lines)
            if parsed:
                sources.append(parsed)
        return sources

    def _identify_if_reachable(self) -> None:
        response = self._client(connect_timeout=FAST_CONNECT_TIMEOUT_SECONDS).identify()
        if not response.successful:
            raise ConnectionError(response.detail)
        self._refresh_mac_from_arp()

    def _wait_until_reachable(self) -> None:
        deadline = time.monotonic() + WAKE_TIMEOUT_SECONDS
        last_error = None
        while time.monotonic() < deadline:
            try:
                self._identify_if_reachable()
                return
            except (
                OSError,
                TimeoutError,
                ConnectionError,
                ValueError,
                socket.timeout,
            ) as exc:
                last_error = exc
                time.sleep(WAKE_RETRY_INTERVAL_SECONDS)
        raise TimeoutError(
            f"Trinnov did not become reachable after Wake-on-LAN: {last_error}"
        )

    def _client(self, *, connect_timeout: float | None = None) -> TrinnovTcpClient:
        av = self.config.get("av") or {}
        return TrinnovTcpClient(
            host=av.get("ip", ""),
            port=av.get("port") or TRINNOV_DEFAULT_PORT,
            connection_timeout_seconds=connect_timeout
            or av.get("connection_timeout_seconds", 5.0),
            command_timeout_seconds=av.get("command_timeout_seconds", 1.0),
        )

    def _get_mac_for_wake(self) -> str | None:
        av = self.config.get("av") or {}
        return av.get(TRINNOV_MAC_CONFIG_KEY) or self._refresh_mac_from_arp()

    def _refresh_mac_from_arp(self) -> str | None:
        av = self.config.get("av") or {}
        ip = av.get("ip", "")
        if not ip:
            return None

        detected_mac = find_mac_by_ip(ip)
        if not detected_mac:
            return None

        stored_mac = av.get(TRINNOV_MAC_CONFIG_KEY, "")
        if stored_mac != detected_mac:
            logging.info("Trinnov MAC learned from ARP: %s", detected_mac)
            self.config.setdefault("av", {})[TRINNOV_MAC_CONFIG_KEY] = detected_mac

        return detected_mac


def _response_to_device_result(
    response: TrinnovCommandResponse,
) -> DeviceCommandResult:
    if response.successful:
        return DeviceCommandResult.success()
    return DeviceCommandResult.failed(response.detail)
