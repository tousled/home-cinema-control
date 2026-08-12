from __future__ import annotations

import logging
import socket
import time
from dataclasses import dataclass, field

from home_cinema_control.devices.av.adapters.trinnov_mapper import (
    is_terminal_error,
    is_terminal_success,
)
from home_cinema_control.network.tcp import LoggingTcpClient

TRINNOV_DEFAULT_PORT = 44100
TRINNOV_CLIENT_ID = "Home Cinema Control"
IDENTIFY_COMMAND = f"id {TRINNOV_CLIENT_ID}\n"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TrinnovCommandResponse:
    successful: bool
    terminal_line: str
    lines: list[str] = field(default_factory=list)

    @property
    def detail(self) -> str:
        return self.terminal_line


class TrinnovTcpClient:
    def __init__(
        self,
        *,
        host: str,
        port: int = TRINNOV_DEFAULT_PORT,
        connection_timeout_seconds: float = 5.0,
        command_timeout_seconds: float = 1.0,
    ) -> None:
        self.host = host
        self.port = int(port or TRINNOV_DEFAULT_PORT)
        self.connection_timeout_seconds = float(connection_timeout_seconds)
        self.command_timeout_seconds = float(command_timeout_seconds)
        self._tcp = LoggingTcpClient(name="trinnov-altitude")

    def identify(self) -> TrinnovCommandResponse:
        with self._connected_session() as session:
            return self._identify(session)

    def send_command(self, command: str) -> TrinnovCommandResponse:
        with self._connected_session() as session:
            identify_response = self._identify(session)
            if not identify_response.successful:
                return identify_response

            session.sendall(command.encode("ascii"))
            response = self._read_until_terminal(session, operation=command.strip())
            self._send_bye(session)
            return response

    def _connected_session(self):
        if not self.host:
            raise ValueError("av.ip is not configured")
        return self._tcp.connect(
            host=self.host,
            port=self.port,
            timeout=self.connection_timeout_seconds,
        )

    def _identify(self, session: socket.socket) -> TrinnovCommandResponse:
        welcome = self._read_welcome(session)
        logger.debug(
            "Trinnov welcome | host=%s | port=%s | line=%r",
            self.host,
            self.port,
            welcome,
        )
        session.sendall(IDENTIFY_COMMAND.encode("ascii"))
        return self._read_until_terminal(session, operation="identify")

    def _read_welcome(self, session: socket.socket) -> str:
        lines = self._read_available_lines(
            session,
            timeout=self.command_timeout_seconds,
            stop_after_first_line=True,
        )
        if not lines:
            raise TimeoutError("Trinnov did not send a welcome line.")
        return lines[0]

    def _read_until_terminal(
        self,
        session: socket.socket,
        *,
        operation: str,
    ) -> TrinnovCommandResponse:
        lines: list[str] = []
        deadline = time.monotonic() + self.command_timeout_seconds
        buffer = b""

        while time.monotonic() < deadline:
            remaining = max(0.01, deadline - time.monotonic())
            session.settimeout(min(0.2, remaining))
            try:
                chunk = session.recv(4096)
            except (TimeoutError, socket.timeout):
                continue

            if not chunk:
                raise ConnectionError(
                    f"Trinnov closed the connection before {operation} completed."
                )

            buffer += chunk
            parsed, buffer = _pop_lines(buffer)
            for line in parsed:
                lines.append(line)
                if is_terminal_success(line):
                    return TrinnovCommandResponse(True, line, lines)
                if is_terminal_error(line):
                    return TrinnovCommandResponse(False, line, lines)

        raise TimeoutError(f"Trinnov timed out waiting for {operation} response.")

    def _read_available_lines(
        self,
        session: socket.socket,
        *,
        timeout: float,
        stop_after_first_line: bool = False,
    ) -> list[str]:
        deadline = time.monotonic() + timeout
        buffer = b""
        lines: list[str] = []

        while time.monotonic() < deadline:
            remaining = max(0.01, deadline - time.monotonic())
            session.settimeout(min(0.2, remaining))
            try:
                chunk = session.recv(4096)
            except (TimeoutError, socket.timeout):
                continue
            if not chunk:
                break

            buffer += chunk
            parsed, buffer = _pop_lines(buffer)
            lines.extend(parsed)
            if stop_after_first_line and lines:
                break

        if buffer:
            lines.append(buffer.decode("ascii", errors="replace").strip())
        return [line for line in lines if line]

    def _send_bye(self, session: socket.socket) -> None:
        try:
            session.sendall(b"bye\n")
        except OSError:
            logger.debug("Unable to send Trinnov bye; socket already closed", exc_info=True)


def _pop_lines(buffer: bytes) -> tuple[list[str], bytes]:
    normalized = buffer.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    if b"\n" not in normalized:
        return [], buffer

    parts = normalized.split(b"\n")
    complete = parts[:-1]
    remainder = parts[-1]
    lines = []
    for part in complete:
        line = part.decode("ascii", errors="replace").strip()
        if line:
            lines.append(line)
    return lines, remainder
