from __future__ import annotations

import json
import logging
import urllib.parse
from collections.abc import Mapping
from typing import Any

import requests

logger = logging.getLogger(__name__)

_REDACTED = "***"
# requests has no default timeout — without this, a call to an unreachable
# or non-responding host (e.g. a stopped Emby/Jellyfin server) blocks forever
# instead of surfacing as an error. (connect timeout, read timeout) in seconds.
_DEFAULT_TIMEOUT = (5, 8)
_SENSITIVE_KEYS = {
    "authorization",
    "password",
    "pw",
    "token",
    "x-emby-authorization",
    "x-mediabrowser-token",
}
_MAX_ERROR_BODY_LENGTH = 4000


class LoggingHttpSession:
    """Small requests-compatible HTTP wrapper with centralized diagnostics."""

    def __init__(self, *, name: str, session=requests) -> None:
        self._name = name
        self._session = session

    def get(self, url: str, **kwargs: Any):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any):
        return self.request("POST", url, **kwargs)

    def delete(self, url: str, **kwargs: Any):
        return self.request("DELETE", url, **kwargs)

    def request(self, method: str, url: str, **kwargs: Any):
        method = method.upper()
        suppress_exception_log = bool(kwargs.pop("suppress_exception_log", False))
        kwargs.setdefault("timeout", _DEFAULT_TIMEOUT)
        safe_kwargs = _safe_request_kwargs(kwargs)
        safe_url = _redact_url(url)

        logger.debug(
            "HTTP request | client=%s | method=%s | url=%s",
            self._name,
            method,
            safe_url,
        )

        try:
            response = self._session.request(method, url, **kwargs)
        except requests.RequestException:
            if suppress_exception_log:
                logger.debug(
                    "HTTP request raised suppressed exception | client=%s | "
                    "method=%s | url=%s | kwargs=%s",
                    self._name,
                    method,
                    safe_url,
                    safe_kwargs,
                )
            else:
                logger.exception(
                    "HTTP request raised exception | client=%s | method=%s | "
                    "url=%s | kwargs=%s",
                    self._name,
                    method,
                    safe_url,
                    safe_kwargs,
                )
            raise

        status_code = getattr(response, "status_code", None)
        if status_code is not None and status_code >= 400:
            logger.warning(
                "HTTP response failed | client=%s | method=%s | url=%s | "
                "status=%s | request=%s | body=%s",
                self._name,
                method,
                safe_url,
                status_code,
                safe_kwargs,
                _truncate(getattr(response, "text", "")),
            )
            return response

        logger.debug(
            "HTTP response | client=%s | method=%s | url=%s | status=%s | body=%s",
            self._name,
            method,
            safe_url,
            status_code,
            _success_body_summary(response),
        )
        return response


def _success_body_summary(response) -> str:
    text = getattr(response, "text", "")
    if not text:
        return ""
    return f"<{len(text)} chars>"


def _truncate(value: str) -> str:
    if len(value) <= _MAX_ERROR_BODY_LENGTH:
        return value
    return value[:_MAX_ERROR_BODY_LENGTH] + "...<truncated>"


def get_http_session(name: str):
    return LoggingHttpSession(name=name)


def _safe_request_kwargs(kwargs: Mapping[str, Any]) -> dict[str, Any]:
    safe = dict(kwargs)
    if "headers" in safe:
        safe["headers"] = _redact_mapping(safe["headers"])
    if "data" in safe:
        safe["data"] = _redact_value(safe["data"])
    if "json" in safe:
        safe["json"] = _redact_value(safe["json"])
    return safe


def _redact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _redact_mapping(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    return value


def _redact_url(url: str) -> str:
    """Redact sensitive values from a URL's query string before logging.

    The OPPO MediaControl API encodes its whole query as a single
    URL-encoded JSON blob (e.g. mountSharedFolder's `password`), which
    `_safe_request_kwargs` can't see since it only inspects request kwargs,
    not the URL string itself.
    """
    parts = urllib.parse.urlsplit(url)
    if not parts.query:
        return url

    return urllib.parse.urlunsplit(parts._replace(query=_redact_query(parts.query)))


def _redact_query(query: str) -> str:
    try:
        payload = json.loads(urllib.parse.unquote(query))
    except (ValueError, TypeError):
        payload = None

    if isinstance(payload, dict):
        return urllib.parse.quote(json.dumps(_redact_mapping(payload)))

    pairs = urllib.parse.parse_qsl(query, keep_blank_values=True)
    if not any(key.lower() in _SENSITIVE_KEYS for key, _ in pairs):
        return query

    redacted_pairs = [
        (key, _REDACTED if key.lower() in _SENSITIVE_KEYS else value)
        for key, value in pairs
    ]
    return urllib.parse.urlencode(redacted_pairs)


def _redact_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    redacted = {}
    for key, item in value.items():
        if str(key).lower() in _SENSITIVE_KEYS:
            redacted[key] = _REDACTED
        else:
            redacted[key] = _redact_value(item)
    return redacted
