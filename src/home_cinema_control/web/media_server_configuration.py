from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import requests as _requests
from fastapi import HTTPException

from home_cinema_control.config.manager import (
    active_media_server_type,
    get_media_server_provider,
    set_active_media_server,
    upsert_media_server_provider,
)
from home_cinema_control.media_servers.common.models import MediaServerLoginCredentials
from home_cinema_control.playback.diagnostics import diagnose_device_action_failed
from home_cinema_control.web.config_sections import apply_media_server_section
from home_cinema_control.web.setup_verification import mark_section_verified


class MediaServerConfigurationTransitionService:
    """Apply media-server configuration changes and their runtime transitions.

    Routes translate HTTP requests into these operations. This service owns the
    policy that decides whether a change is a draft, a verified active
    configuration, or a rejected transition that must leave the runtime alone.
    """

    def __init__(
        self,
        *,
        config_service,
        runtime,
        setup_service_factory: Callable[[dict], Any],
        emit_telemetry: Callable[[], None],
    ) -> None:
        self._config_service = config_service
        self._runtime = runtime
        self._setup_service_factory = setup_service_factory
        self._emit_telemetry = emit_telemetry

    def save_section(self, body: dict):
        config = self._config_service.load_config()
        submitted = body.get("media_server") or body
        current_type = active_media_server_type(config)
        target_type = submitted.get("type") or current_type

        if target_type == current_type:
            # Editing fields on the already-active provider does not require a
            # listener transition, matching the existing Save behavior.
            updated = apply_media_server_section(config, body)
            updated = self._config_service.prepare_submitted_config(updated)
            self._config_service.save_config(updated)
            self._emit_telemetry()
            return self._config_service.sanitize(updated)

        merged = apply_media_server_section(config, body)
        merged = self._config_service.prepare_submitted_config(merged)
        target_provider = get_media_server_provider(merged, target_type)

        if not target_provider.access_token:
            # Store the selected provider as a draft while the current runtime
            # listener keeps serving the active provider.
            draft = set_active_media_server(merged, current_type).model_dump()
            return self._save_media_server_draft(draft, target_type)

        setup_service = self._setup_service_factory(merged)
        response = self._check_connection_or_503(setup_service, merged)

        if 200 <= response.status_code < 300:
            confirmation = self._switch_confirmation(body, current_type)
            if confirmation is not None:
                return confirmation
            verified_config = mark_section_verified(merged, "media_server")
            return self._save_and_restart_listener(verified_config)

        if response.status_code in (401, 403):
            # Clear only the rejected provider's token, keeping the runtime on
            # the current provider so the user can authenticate again.
            cleared = upsert_media_server_provider(
                merged, target_type, access_token=""
            ).model_dump()
            draft = set_active_media_server(cleared, current_type).model_dump()
            sanitized = self._save_media_server_draft(draft, target_type)
            sanitized["media_server_session_expired"] = True
            return sanitized

        self._set_media_server_connection_diagnostic(
            f"Media server responded with status {response.status_code}"
        )
        raise HTTPException(status_code=400, detail="Media server connection failed")

    def configure_token(self, body: dict):
        submitted = body.get("config") or {}
        credentials = MediaServerLoginCredentials.model_validate(
            body.get("credentials") or {}
        )

        saved_config = self._config_service.load_config()
        # Read the current provider from disk because submitted config carries
        # the target provider selected in the form.
        current_type = active_media_server_type(saved_config)
        confirmation = self._switch_confirmation(body, current_type)
        if confirmation is not None:
            return confirmation

        # The token endpoint receives only the media-server wire shape. Merge
        # it onto the complete saved config so unrelated sections survive.
        config = apply_media_server_section(saved_config, submitted)
        setup_service = self._setup_service_factory(config)
        try:
            config = setup_service.configure_token(config, credentials)
        except _requests.exceptions.RequestException as exc:
            logging.warning("Media server token request failed | error=%s", exc)
            self._set_media_server_connection_diagnostic(
                f"Media server unreachable: {exc}"
            )
            raise HTTPException(status_code=503, detail="Media server unreachable")
        except Exception:
            logging.exception("Media server token configuration failed")
            raise HTTPException(status_code=400, detail="Token configuration failed")
        return self._save_and_restart_listener(config)

    def check_connection(self, body: dict):
        saved_config = self._config_service.load_config()
        current_type = active_media_server_type(saved_config)
        config = apply_media_server_section(saved_config, body)
        config = self._config_service.prepare_submitted_config(config)
        setup_service = self._setup_service_factory(config)
        response = self._check_connection_or_503(setup_service, config)

        if 200 <= response.status_code < 300:
            confirmation = self._switch_confirmation(body, current_type)
            if confirmation is not None:
                return confirmation
            verified_config = mark_section_verified(config, "media_server")
            return self._save_and_restart_listener(verified_config)

        self._set_media_server_connection_diagnostic(
            f"Media server responded with status {response.status_code}"
        )
        raise HTTPException(status_code=400, detail="Media server connection failed")

    def _switch_confirmation(self, body: dict, current_type: str):
        if bool(body.get("confirm_provider_switch")):
            return None
        if not self._runtime.has_active_playback():
            return None
        return {
            "switch_requires_confirmation": True,
            "active_session_provider": current_type,
        }

    def _set_media_server_connection_diagnostic(self, detail: str) -> None:
        self._runtime.set_last_diagnostic(
            diagnose_device_action_failed(
                component="media_server",
                action="connection check",
                detail=detail,
                severity="error",
            )
        )

    def _check_connection_or_503(self, setup_service, config: dict):
        try:
            return setup_service.check_connection(config)
        except _requests.exceptions.RequestException as exc:
            logging.warning("Media server connection check failed | error=%s", exc)
            self._set_media_server_connection_diagnostic(
                f"Media server unreachable: {exc}"
            )
            raise HTTPException(status_code=503, detail="Media server unreachable")

    def _save_and_restart_listener(self, config_dict: dict):
        self._config_service.save_config(config_dict)
        self._runtime.restart_playback_listener()
        self._emit_telemetry()
        return self._config_service.sanitize(config_dict)

    def _save_media_server_draft(self, config_dict: dict, provider_type: str) -> dict:
        self._config_service.save_config(config_dict)
        sanitized = self._config_service.sanitize(config_dict)
        sanitized["media_server_pending_provider"] = provider_type
        return sanitized
