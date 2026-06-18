from __future__ import annotations

import logging
from typing import Any

from home_cinema_control.devices.oppo.constants import OPPO_TELNET_PORT
from home_cinema_control.network.tcp import LoggingTcpClient
from home_cinema_control.playback.startup.models import DeviceCommandResult

logger = logging.getLogger(__name__)


class OppoSVMModeClient:
    """Sets OPPO verbose/event mode through the telnet command protocol."""

    def __init__(
        self,
        config: dict[str, Any],
        *,
        tcp_client: LoggingTcpClient | None = None,
        name: str = "oppo-svm-mode",
    ) -> None:
        self._config = config
        self._tcp_client = tcp_client or LoggingTcpClient(name=name)

    def set_mode(self, mode: int) -> DeviceCommandResult:
        oppo = self._config.get("oppo") or {}
        oppo_ip = oppo.get("ip")
        if not oppo_ip:
            return DeviceCommandResult.skipped("OPPO IP is not configured.")

        try:
            response = self._tcp_client.request(
                host=oppo_ip,
                port=int(self._config.get("OPPO_Port", OPPO_TELNET_PORT)),
                payload=f"#SVM {int(mode)}\r".encode("ascii"),
                timeout=float(oppo.get("connection_timeout_seconds", 3)),
                encoding="utf-8",
                complete=lambda data: svm_response_is_complete(data, mode=mode),
            )
        except Exception as exc:
            logger.warning(
                "Could not set OPPO SVM mode | mode=%s | error=%s: %s",
                mode,
                type(exc).__name__,
                exc,
            )
            return DeviceCommandResult.failed(
                f"OPPO SVM {mode} failed: {type(exc).__name__}: {exc}"
            )

        if not svm_response_is_successful(response, mode=mode):
            logger.warning(
                "OPPO SVM mode returned unexpected response | mode=%s | response=%r",
                mode,
                response,
            )
            return DeviceCommandResult.failed(
                f"OPPO SVM {mode} returned unexpected response: {response!r}"
            )

        logger.info("OPPO SVM mode set | mode=%s | response=%r", mode, response)
        return DeviceCommandResult.success(f"OPPO SVM {mode}: {response}")


def svm_response_is_successful(response: str, *, mode: int) -> bool:
    expected_suffix = f"OK {int(mode)}"
    for raw_line in response.splitlines():
        line = raw_line.strip().upper()
        if line in {f"@SVM {expected_suffix}", f"@{expected_suffix}", expected_suffix}:
            return True
    return False


def svm_response_is_complete(response: str, *, mode: int) -> bool:
    if svm_response_is_successful(response, mode=mode):
        return True

    for raw_line in response.splitlines():
        line = raw_line.strip().upper()
        if line.startswith("@SVM ER") or line.startswith("@ER"):
            return True
        if line.startswith("ER"):
            return True
    return False
