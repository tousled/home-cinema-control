from __future__ import annotations

import logging
import socket
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from home_cinema_control.devices.oppo.constants import OPPO_TELNET_PORT

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OppoVerboseEvent:
    """One parsed OPPO verbose-mode line from the TCP control stream.

    `code` is the upper-case OPPO event code such as `UPL`, `UAT`, `UST`, or
    `UTC`. `payload` is intentionally left as raw protocol text for downstream
    translators to interpret.
    """

    raw: str
    code: str
    payload: str


def parse_verbose_event(raw: str) -> OppoVerboseEvent:
    normalized = raw.strip()

    if normalized.startswith("@"):
        normalized = normalized[1:]

    parts = normalized.split(maxsplit=1)
    code = parts[0] if parts else ""
    payload = parts[1] if len(parts) > 1 else ""

    return OppoVerboseEvent(
        raw=raw.strip(),
        code=code.upper(),
        payload=payload,
    )


def normalize_oppo_tcp_command(command: str) -> bytes:
    command = command.strip().upper()

    if not command.startswith("#"):
        command = f"#{command}"

    if not command.endswith("\r"):
        command = f"{command}\r"

    return command.encode("ascii")


class OppoVerboseEventListener:
    """Reads unsolicited OPPO status lines from the TCP control protocol.

    This is a device adapter. It opens the TCP session, enables SVM verbose
    mode, yields parsed events, optionally sends keepalive commands, and restores
    SVM 0 on exit. It does not decide playback state, report to Emby, or choose
    fallback behaviour; orchestrators own those workflow decisions.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int = OPPO_TELNET_PORT,
        connect_timeout_seconds: float = 3.0,
        read_timeout_seconds: float = 0.5,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self.host = host
        self.port = port
        self.connect_timeout_seconds = connect_timeout_seconds
        self.read_timeout_seconds = read_timeout_seconds
        self._now = now

    def listen(
        self,
        *,
        verbose_mode: int = 2,
        duration_seconds: float | None = None,
        initial_commands: list[str] | None = None,
        keepalive_command: str | None = None,
        keepalive_interval_seconds: float = 10.0,
        restore_verbose_mode: bool = True,
        utc_idle_timeout_seconds: float | None = None,
        stop_requested: Callable[[], bool] | None = None,
    ) -> Iterator[OppoVerboseEvent]:
        deadline = (
            None
            if duration_seconds is None
            else self._now() + max(0.0, duration_seconds)
        )
        utc_idle_timeout_seconds = (
            None
            if utc_idle_timeout_seconds is None
            else max(0.1, utc_idle_timeout_seconds)
        )
        last_utc_at = self._now()
        pending = ""
        next_keepalive_at = (
            None
            if keepalive_command is None
            else self._now() + max(0.1, keepalive_interval_seconds)
        )

        with socket.create_connection(
            (self.host, self.port),
            timeout=self.connect_timeout_seconds,
        ) as session:
            try:
                session.settimeout(self.read_timeout_seconds)
                self._send_command(session, f"SVM {int(verbose_mode)}")

                for command in initial_commands or []:
                    self._send_command(session, command)

                while (
                    (deadline is None or self._now() < deadline)
                    and (
                        utc_idle_timeout_seconds is None
                        or self._now() - last_utc_at < utc_idle_timeout_seconds
                    )
                    and not (stop_requested and stop_requested())
                ):
                    if (
                        keepalive_command is not None
                        and next_keepalive_at is not None
                        and self._now() >= next_keepalive_at
                    ):
                        self._send_command(session, keepalive_command)
                        next_keepalive_at = self._now() + max(
                            0.1,
                            keepalive_interval_seconds,
                        )

                    try:
                        chunk = session.recv(4096)
                    except TimeoutError:
                        continue
                    except socket.timeout:
                        continue

                    if not chunk:
                        logger.info(
                            "OPPO verbose listener connection closed | "
                            "host=%s | port=%s",
                            self.host,
                            self.port,
                        )
                        break

                    pending += chunk.decode("utf-8", errors="replace")
                    lines, pending = _split_complete_lines(pending)

                    for line in lines:
                        if line.strip():
                            event = parse_verbose_event(line)
                            if event.code == "UTC":
                                last_utc_at = self._now()
                            yield event

                if pending.strip():
                    event = parse_verbose_event(pending)
                    if event.code == "UTC":
                        last_utc_at = self._now()
                    yield event
            finally:
                if restore_verbose_mode:
                    try:
                        self._send_command(session, "SVM 0")
                    except OSError:
                        logger.warning(
                            "Could not restore OPPO SVM mode on existing "
                            "connection | host=%s | port=%s",
                            self.host,
                            self.port,
                            exc_info=True,
                        )

    def _send_command(self, session: socket.socket, command: str) -> None:
        payload = normalize_oppo_tcp_command(command)
        logger.debug(
            "OPPO verbose listener send | host=%s | port=%s | payload=%r",
            self.host,
            self.port,
            payload,
        )
        session.sendall(payload)


def _split_complete_lines(text: str) -> tuple[list[str], str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    if not normalized.endswith("\n"):
        parts = normalized.split("\n")
        return parts[:-1], parts[-1]

    return normalized.splitlines(), ""
