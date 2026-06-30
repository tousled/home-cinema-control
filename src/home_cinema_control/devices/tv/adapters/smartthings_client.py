import requests

SMARTTHINGS_API_BASE = "https://api.smartthings.com/v1"
SMARTTHINGS_REQUEST_TIMEOUT = 10.0


class SmartThingsInputClient:
    """HTTP transport adapter for the SmartThings mediaInputSource capability.

    Owns the SmartThings wire format: endpoint URLs, auth header, capability
    payload shape, and raw response parsing.  Returns HCC-neutral values so
    callers never see SmartThings field names.
    """

    def __init__(self, token: str, device_id: str) -> None:
        self._token = token
        self._device_id = device_id

    def set_input(self, input_id: str) -> None:
        """Send setInputSource command to the TV via SmartThings cloud API."""
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
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=SMARTTHINGS_REQUEST_TIMEOUT,
        )
        response.raise_for_status()

    def get_supported_inputs(self) -> list[str]:
        """Return the input source IDs the TV exposes via SmartThings."""
        url = (
            f"{SMARTTHINGS_API_BASE}/devices/{self._device_id}"
            "/components/main/capabilities/mediaInputSource/status"
        )
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=SMARTTHINGS_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        return (data.get("supportedInputSources") or {}).get("value") or []
