import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests
from pydantic import BaseModel

SMARTTHINGS_AUTH_URL = "https://account.smartthings.com/oauth/authorize"
SMARTTHINGS_TOKEN_URL = "https://auth-global.api.smartthings.com/oauth/token"
_SECRETS_KEY = "samsung_smartthings"
_OAUTH_TIMEOUT = 10.0


class SmartThingsSecrets(BaseModel):
    client_id: str = ""
    client_secret: str = ""
    access_token: str = ""
    refresh_token: str = ""
    token_expires_at: datetime | None = None


class SmartThingsTokenStore:
    def __init__(self, secrets_path: Path) -> None:
        self._path = secrets_path

    def load(self) -> SmartThingsSecrets | None:
        if not self._path.exists():
            return None
        data = json.loads(self._path.read_text(encoding="utf-8"))
        section = data.get(_SECRETS_KEY)
        if not isinstance(section, dict):
            return None
        return SmartThingsSecrets.model_validate(section)

    def save(self, secrets: SmartThingsSecrets) -> None:
        data: dict = {}
        if self._path.exists():
            data = json.loads(self._path.read_text(encoding="utf-8"))
        data[_SECRETS_KEY] = secrets.model_dump(mode="json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(data, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


class SmartThingsOAuthClient:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    def authorization_url(self, redirect_uri: str, state: str) -> str:
        return (
            f"{SMARTTHINGS_AUTH_URL}?"
            + urlencode({
                "client_id": self._client_id,
                "response_type": "code",
                "redirect_uri": redirect_uri,
                "scope": "r:devices:* x:devices:*",
                "state": state,
            })
        )

    def exchange_code(self, code: str, redirect_uri: str) -> SmartThingsSecrets:
        response = requests.post(
            SMARTTHINGS_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            timeout=_OAUTH_TIMEOUT,
        )
        response.raise_for_status()
        parsed = self._parse_token_response(response.json())
        return parsed.model_copy(update={
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        })

    def refresh(self, secrets: SmartThingsSecrets) -> SmartThingsSecrets:
        response = requests.post(
            SMARTTHINGS_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": secrets.refresh_token,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            timeout=_OAUTH_TIMEOUT,
        )
        response.raise_for_status()
        parsed = self._parse_token_response(response.json())
        return parsed.model_copy(update={
            "client_id": secrets.client_id,
            "client_secret": secrets.client_secret,
            "refresh_token": parsed.refresh_token or secrets.refresh_token,
        })

    @staticmethod
    def _parse_token_response(data: dict) -> SmartThingsSecrets:
        expires_in = data.get("expires_in")
        expires_at = None
        if expires_in is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        return SmartThingsSecrets(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", ""),
            token_expires_at=expires_at,
        )
