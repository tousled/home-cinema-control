from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from home_cinema_control.devices.tv.adapters.smartthings_oauth import (
        SmartThingsOAuthClient,
        SmartThingsTokenStore,
    )

SMARTTHINGS_API_BASE = "https://api.smartthings.com/v1"
SMARTTHINGS_DEVICES_URL = f"{SMARTTHINGS_API_BASE}/devices"
SMARTTHINGS_REQUEST_TIMEOUT = 10.0
_TOKEN_REFRESH_BUFFER_SECONDS = 60
_MEDIA_INPUT_CAPABILITY = "mediaInputSource"


class SmartThingsInputClient:
    """HTTP transport adapter for the SmartThings mediaInputSource capability.

    Owns the SmartThings wire format: endpoint URLs, auth header, capability
    payload shape, and raw response parsing.  Returns HCC-neutral values so
    callers never see SmartThings field names.
    """

    def __init__(self, token_provider: Callable[[], str], device_id: str) -> None:
        self._token_provider = token_provider
        self._device_id = device_id

    def set_input(self, input_id: str) -> None:
        """Send setInputSource command to the TV via SmartThings cloud API."""
        token = self._token_provider()
        url = f"{SMARTTHINGS_API_BASE}/devices/{self._device_id}/commands"
        payload = {
            "commands": [{
                "component": "main",
                "capability": "mediaInputSource",
                "command": "setInputSource",
                "arguments": [input_id],
            }]
        }
        response = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=SMARTTHINGS_REQUEST_TIMEOUT,
        )
        response.raise_for_status()

    def get_supported_inputs(self) -> list[str]:
        """Return the input source IDs the TV exposes via SmartThings."""
        token = self._token_provider()
        url = (
            f"{SMARTTHINGS_API_BASE}/devices/{self._device_id}"
            "/components/main/capabilities/mediaInputSource/status"
        )
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=SMARTTHINGS_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        return (data.get("supportedInputSources") or {}).get("value") or []

    def list_devices(self) -> list[dict]:
        """Return [{id, label}] for devices with mediaInputSource capability, sorted by label."""
        token = self._token_provider()
        response = requests.get(
            SMARTTHINGS_DEVICES_URL,
            params={"capability": _MEDIA_INPUT_CAPABILITY},
            headers={"Authorization": f"Bearer {token}"},
            timeout=SMARTTHINGS_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
        return sorted(
            [
                {"id": d["deviceId"], "label": d.get("label") or d.get("name", "")}
                for d in items
            ],
            key=lambda d: d["label"],
        )


def _make_token_provider(
    store: "SmartThingsTokenStore",
    oauth: "SmartThingsOAuthClient",
) -> Callable[[], str]:
    from home_cinema_control.devices.tv.adapters.smartthings_oauth import (
        SmartThingsSecrets,
    )

    def token_provider() -> str:
        current = store.load() or SmartThingsSecrets()
        now = datetime.now(timezone.utc)
        expires_at = current.token_expires_at
        if not current.access_token or (
            expires_at is not None
            and expires_at - now < timedelta(seconds=_TOKEN_REFRESH_BUFFER_SECONDS)
        ):
            updated = oauth.refresh(current)
            store.save(updated)
            return updated.access_token
        return current.access_token

    return token_provider


def make_smartthings_client(
    config: dict,
    store: "SmartThingsTokenStore",
    oauth: "SmartThingsOAuthClient",
) -> SmartThingsInputClient | None:
    """Build a SmartThingsInputClient with auto-refreshing token, or None if not configured."""
    tv = config.get("tv") or {}
    device_id = tv.get("smartthings_device_id")
    if not device_id:
        return None
    secrets = store.load()
    if not secrets or not secrets.refresh_token:
        return None
    return SmartThingsInputClient(
        token_provider=_make_token_provider(store, oauth),
        device_id=device_id,
    )


def make_smartthings_devices_client(
    store: "SmartThingsTokenStore",
    oauth: "SmartThingsOAuthClient",
) -> SmartThingsInputClient | None:
    """Build a client for listing devices (no device_id required)."""
    secrets = store.load()
    if not secrets or not secrets.refresh_token:
        return None
    return SmartThingsInputClient(
        token_provider=_make_token_provider(store, oauth),
        device_id="",
    )
