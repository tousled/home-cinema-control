from dataclasses import dataclass
from collections.abc import Callable

from home_cinema_control.devices.oppo.playback_state import (
    OppoPlaybackCategory,
    classify_oppo_status,
    OppoPlaybackStatus,
    parse_oppo_playback_status,
)
from home_cinema_control.network.tcp import LoggingTcpClient


@dataclass(frozen=True)
class OppoCommandResult:
    command: str
    raw_response: str
    ok: bool
    status: OppoPlaybackStatus
    category: OppoPlaybackCategory


class OppoPlaybackStatusClient:
    """
    Reads OPPO playback/power status using the OPPO TCP command interface.

    Examples:
      #QPW -> @OK ON
      #QPL -> @OK PLAY / @OK HOME MENU / @OK DISC MENU / ...
    """

    def __init__(
        self,
        host: str,
        port: int = 23,
        timeout: float = 3.0,
        on_verbose_response: Callable[[str], None] | None = None,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._on_verbose_response = on_verbose_response
        self._tcp = LoggingTcpClient(name="oppo-status")

    def query_power_state(self) -> OppoCommandResult:
        return self.query("QPW")

    def query_playback_state(self) -> OppoCommandResult:
        return self.query("QPL")

    def query(self, command: str) -> OppoCommandResult:
        normalized_command = self._normalize_command(command)
        raw_response = self._send(normalized_command)
        if self._on_verbose_response is not None:
            self._on_verbose_response(raw_response)
        status = parse_oppo_playback_status(raw_response)

        return OppoCommandResult(
            command=command.strip().lstrip("#").upper(),
            raw_response=raw_response,
            ok=_tcp_status_response_is_complete(raw_response),
            status=status,
            category=classify_oppo_status(status),
        )

    def _send(self, payload: bytes) -> str:
        return self._tcp.request(
            host=self.host,
            port=self.port,
            payload=payload,
            timeout=self.timeout,
            encoding="utf-8",
            complete=_tcp_status_response_is_complete,
        )

    @staticmethod
    def _normalize_command(command: str) -> bytes:
        command = command.strip().upper()

        if not command.startswith("#"):
            command = f"#{command}"

        if not command.endswith("\r"):
            command = f"{command}\r"

        return command.encode("ascii")


def _tcp_status_response_is_complete(response: str) -> bool:
    for line in response.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        line = line.strip()
        if line.startswith("@OK"):
            return True
        if line.startswith("@QPL OK"):
            return True
        if line.startswith("@QPW OK"):
            return True

    return False
