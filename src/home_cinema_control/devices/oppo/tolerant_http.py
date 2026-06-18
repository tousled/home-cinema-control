from __future__ import annotations

import logging
import socket
from dataclasses import dataclass
from collections.abc import Callable
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TolerantHttpResponse:
    status_code: int
    text: str


class OppoTolerantHttpClient:
    """HTTP GET client that tolerates OPPO verbose lines before HTTP status."""

    def __init__(
        self,
        *,
        socket_factory=socket.create_connection,
        encoding: str = "utf-8",
        on_verbose_preamble: Callable[[str], None] | None = None,
    ) -> None:
        self._socket_factory = socket_factory
        self._encoding = encoding
        self._on_verbose_preamble = on_verbose_preamble

    def get(self, url: str, **kwargs) -> TolerantHttpResponse:
        timeout = float(kwargs.get("timeout", 5))
        parsed = urlparse(url)
        if parsed.scheme != "http":
            raise ValueError(
                f"Unsupported OPPO MediaControl URL scheme: {parsed.scheme}"
            )

        host = parsed.hostname or ""
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        logger.debug("OPPO tolerant HTTP request | url=%s", url)
        with self._socket_factory((host, port), timeout=timeout) as session:
            session.settimeout(timeout)
            session.sendall(_build_get_request(host=host, path=path))
            raw_response = _read_until_close(session)

        text_response = raw_response.decode(self._encoding, errors="replace")
        http_response = _strip_verbose_preamble(
            text_response,
            on_verbose_preamble=self._on_verbose_preamble,
        )
        status_code, body = _parse_http_response(http_response)
        logger.debug(
            "OPPO tolerant HTTP response | url=%s | status=%s | body=<%s chars>",
            url,
            status_code,
            len(body),
        )
        return TolerantHttpResponse(status_code=status_code, text=body)


def _build_get_request(*, host: str, path: str) -> bytes:
    return (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("ascii")


def _read_until_close(session) -> bytes:
    chunks = []
    while True:
        try:
            chunk = session.recv(4096)
        except TimeoutError:
            break
        except socket.timeout:
            break

        if not chunk:
            break
        chunks.append(chunk)

    return b"".join(chunks)


def _strip_verbose_preamble(
    response: str,
    *,
    on_verbose_preamble: Callable[[str], None] | None = None,
) -> str:
    http_start = response.find("HTTP/")
    if http_start < 0:
        raise ValueError(f"OPPO response did not contain HTTP status: {response!r}")

    if http_start > 0:
        preamble = response[:http_start]
        logger.debug(
            "OPPO verbose HTTP preamble | preamble=%r",
            preamble,
        )
        if on_verbose_preamble is not None:
            on_verbose_preamble(preamble)

    return response[http_start:]


def _parse_http_response(response: str) -> tuple[int, str]:
    header_separator = "\r\n\r\n"
    if header_separator not in response:
        raise ValueError(f"OPPO HTTP response did not contain headers: {response!r}")

    header_text, body = response.split(header_separator, maxsplit=1)
    status_line = header_text.splitlines()[0]
    parts = status_line.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit():
        raise ValueError(f"Invalid OPPO HTTP status line: {status_line!r}")

    return int(parts[1]), body
