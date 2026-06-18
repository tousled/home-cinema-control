from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OppoCommandResponse:
    """
    Typed response returned by the OPPO control API client.

    The OPPO HTTP client boundary is responsible for converting raw HTTP text
    and transport failures into this object. Callers should use payload and
    helper properties instead of json.loads(response.raw_text).
    """

    raw_text: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    status_code: int | None = None
    parse_error: str = ""
    transport_error: str = ""

    @classmethod
    def from_text(
        cls,
        response_text: str | bytes | None,
        *,
        status_code: int | None = None,
    ) -> "OppoCommandResponse":
        if response_text is None:
            return cls(
                raw_text="",
                payload={},
                status_code=status_code,
                parse_error="Empty OPPO response",
            )

        if isinstance(response_text, bytes):
            response_text = response_text.decode("utf-8", errors="replace")

        raw_text = str(response_text)

        if not raw_text.strip():
            return cls(
                raw_text=raw_text,
                payload={},
                status_code=status_code,
                parse_error="Empty OPPO response",
            )

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as error:
            return cls(
                raw_text=raw_text,
                payload={},
                status_code=status_code,
                parse_error=f"Invalid OPPO JSON response: {error}",
            )

        if not isinstance(parsed, dict):
            return cls(
                raw_text=raw_text,
                payload={},
                status_code=status_code,
                parse_error=f"Unexpected OPPO response type: {type(parsed).__name__}",
            )

        return cls(
            raw_text=raw_text,
            payload=parsed,
            status_code=status_code,
        )

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        raw_text: str = "",
        status_code: int | None = None,
    ) -> "OppoCommandResponse":
        return cls(
            raw_text=raw_text,
            payload=dict(payload),
            status_code=status_code,
        )

    @classmethod
    def failed(
        cls,
        message: str,
        *,
        raw_text: str = "",
        status_code: int | None = None,
    ) -> "OppoCommandResponse":
        return cls(
            raw_text=raw_text,
            payload={},
            status_code=status_code,
            transport_error=message,
        )

    @property
    def is_valid_json(self) -> bool:
        return not self.parse_error

    @property
    def is_transport_failure(self) -> bool:
        return bool(self.transport_error)

    @property
    def has_error(self) -> bool:
        return bool(self.transport_error or self.parse_error or self.ret_info)

    @property
    def is_successful(self) -> bool:
        success = self.payload.get("success")

        if isinstance(success, bool):
            return success

        if isinstance(success, str):
            return success.lower() == "true"

        return False

    @property
    def ret_info(self) -> str:
        value = (
            self.payload.get("retInfo")
            or self.payload.get("error")
            or self.payload.get("message")
            or ""
        )

        return str(value)

    @property
    def error_message(self) -> str:
        if self.transport_error:
            return self.transport_error

        if self.parse_error:
            return self.parse_error

        return self.ret_info

    def require_success(self) -> "OppoCommandResponse":
        if not self.is_successful:
            message = self.error_message or "OPPO command did not report success"
            raise OppoCommandError(message, response=self)

        return self

    def get(self, key: str, default: Any = None) -> Any:
        return self.payload.get(key, default)


class OppoCommandError(RuntimeError):
    def __init__(self, message: str, *, response: OppoCommandResponse):
        super().__init__(message)
        self.response = response