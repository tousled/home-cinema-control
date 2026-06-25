import logging

import requests as _requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from home_cinema_control.config.manager import (
    active_media_server_config,
    active_media_server_type,
    get_media_server_provider,
    set_active_media_server,
    upsert_media_server_provider,
)
from home_cinema_control.media_servers.common.models import MediaServerLoginCredentials
from home_cinema_control.playback.diagnostics import (
    diagnose_device_action_failed,
    diagnose_media_server_library_paths_unavailable,
)
from home_cinema_control.web.api_runtime import WebApiRuntime
from home_cinema_control.web.config_sections import apply_config_section
from home_cinema_control.web.media_server_setup import media_server_setup_service
from home_cinema_control.web.setup_verification import mark_section_verified


def build_media_server_router(api_runtime: WebApiRuntime, media_server_provider_factory) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    def _setup_service(config: dict):
        return media_server_setup_service(media_server_provider_factory, config)

    def _media_server_switch_confirmation(body: dict, current_type: str):
        """None if the switch may proceed; otherwise the early response to
        return without changing anything. See
        .agents/specs/2026-06-23-media-server-multi-provider-config-design.md's
        "Listener swap on switch, and confirming active playback" — playback
        in progress on the currently-active provider must be confirmed before
        anything that would tear down and recreate the listener.
        """
        if bool(body.get("confirm_provider_switch")):
            return None
        if not api_runtime.runtime.has_active_playback():
            return None
        return {
            "switch_requires_confirmation": True,
            "active_session_provider": current_type,
        }

    def _set_media_server_connection_diagnostic(detail: str):
        # So a media-server connection failure shows up in /api/state's
        # LastDiagnostic/DiagnosticHistory — same convention as every other
        # device action failure (oppo_routes.py, tv_routes.py, av_routes.py)
        # — instead of only being visible as a transient toast in the Media
        # Server screen.
        api_runtime.runtime.set_last_diagnostic(diagnose_device_action_failed(
            component="media_server",
            action="connection check",
            detail=detail,
            severity="error",
        ))

    def _check_connection_or_503(setup_service, config: dict):
        """setup_service.check_connection() talks to a real, user-supplied
        host — distinguish "couldn't even reach it" (network/DNS/refused/
        timed out, now bounded by network/http.py's default timeout) from "it
        responded with an error," same as the existing OPPO unreachable
        pattern in paths_routes.py's paths_navigate.
        """
        try:
            return setup_service.check_connection(config)
        except _requests.exceptions.RequestException as exc:
            logging.warning("Media server connection check failed | error=%s", exc)
            _set_media_server_connection_diagnostic(f"Media server unreachable: {exc}")
            raise HTTPException(status_code=503, detail="Media server unreachable")

    def _save_and_restart_listener(config_dict: dict):
        """Persist config_dict as-is (already merged/prepared by the caller —
        this does not call prepare_submitted_config, since the one caller that
        needs to clear a token relies on that) and make the running listener
        match it. The only safe way to do that after a provider switch or
        re-login: stop whatever's running (waiting for active playback to
        finish cleanly first), then start fresh.
        """
        api_runtime.config_service.save_config(config_dict)
        api_runtime.runtime.restart_playback_listener()
        return api_runtime.config_service.sanitize(config_dict)

    def _save_media_server_draft(config_dict: dict, provider_type: str) -> dict:
        """Persist provider settings without making provider_type active.

        Used when the user selects/prepares a provider that cannot yet run the
        playback listener: no stored token, expired token, or failed check. The
        web UI can still render that provider's form via the response marker,
        while runtime keeps listening to the previously-active provider.
        """
        api_runtime.config_service.save_config(config_dict)
        sanitized = api_runtime.config_service.sanitize(config_dict)
        sanitized["media_server_pending_provider"] = provider_type
        return sanitized

    def _save_media_server_section(body: dict):
        config = api_runtime.config_service.load_config()
        submitted = body.get("media_server") or body
        current_type = active_media_server_type(config)
        target_type = submitted.get("type") or current_type

        if target_type == current_type:
            # Editing fields on the already-active provider (server_url,
            # display_name, hcc_controlled_device) — no switch, no listener
            # restart, matches today's plain "Guardar" behavior.
            updated = apply_config_section(config, "media-server", body)
            updated = api_runtime.config_service.prepare_submitted_config(updated)
            api_runtime.config_service.save_config(updated)
            return api_runtime.config_service.sanitize(updated)

        merged = apply_config_section(config, "media-server", body)
        merged = api_runtime.config_service.prepare_submitted_config(merged)
        target_provider = get_media_server_provider(merged, target_type)

        if not target_provider.access_token:
            # Target has no stored session yet. Save its public fields as a
            # draft, but keep the current runtime listener untouched; token
            # configuration is the first point where the provider can actually
            # become active.
            draft = set_active_media_server(merged, current_type).model_dump()
            return _save_media_server_draft(draft, target_type)

        setup_service = _setup_service(merged)
        response = _check_connection_or_503(setup_service, merged)

        if 200 <= response.status_code < 300:
            confirmation = _media_server_switch_confirmation(body, current_type)
            if confirmation is not None:
                return confirmation
            # This check_connection call is the same validity check the
            # "Probar conexión" button performs — a switch back to an
            # already-configured provider should mark it verified too,
            # instead of leaving readiness stuck on "configured" (yellow)
            # until the user separately clicks "Probar conexión".
            verified_config = mark_section_verified(merged, "media_server")
            return _save_and_restart_listener(verified_config)

        if response.status_code in (401, 403):
            # The server explicitly rejected the stored credentials (as
            # opposed to being unreachable) — clear only this provider's
            # token, leaving user_id/server_url/display_name so a re-login
            # doesn't make the user retype the server URL too. Keep runtime on
            # the current provider because the target cannot authenticate.
            # Skips prepare_submitted_config deliberately — it would refill
            # this exact blank from the still-on-disk secret we're clearing.
            cleared = upsert_media_server_provider(
                merged, target_type, access_token=""
            ).model_dump()
            draft = set_active_media_server(cleared, current_type).model_dump()
            sanitized = _save_media_server_draft(draft, target_type)
            sanitized["media_server_session_expired"] = True
            return sanitized

        # Connection failure (network/server error, not an auth rejection) —
        # leave the stored token and active provider untouched.
        _set_media_server_connection_diagnostic(
            f"Media server responded with status {response.status_code}"
        )
        raise HTTPException(status_code=400, detail="Media server connection failed")

    @router.patch("/config/media-server")
    def patch_media_server_section(body: dict):
        try:
            return _save_media_server_section(body)
        except HTTPException:
            raise
        except Exception as exc:
            logging.exception("save_media_server_section failed")
            raise HTTPException(status_code=400, detail=str(exc))

    def _config_with_media_server_libraries():
        config = api_runtime.config_service.load_config()
        config = _setup_service(config).load_libraries(config)
        return api_runtime.config_service.sanitize(config)

    @router.get("/config/libraries")
    def get_config_with_libraries():
        return _config_with_media_server_libraries()

    @router.get("/media-server/libraries")
    def get_media_server_libraries():
        return _config_with_media_server_libraries()

    def _config_with_media_server_devices():
        config = api_runtime.config_service.load_config()
        config = _setup_service(config).load_devices(config)
        return api_runtime.config_service.sanitize(config)

    @router.get("/config/devices")
    def get_config_with_devices():
        return _config_with_media_server_devices()

    @router.get("/media-server/devices")
    def get_media_server_devices():
        return _config_with_media_server_devices()

    def _configure_media_server_token_response(body: dict):
        submitted = body.get("config") or {}
        credentials = MediaServerLoginCredentials.model_validate(
            body.get("credentials") or {}
        )

        saved_config = api_runtime.config_service.load_config()
        # current_type comes from the real saved config, not the submitted
        # body — the submitted body's config already carries the *target*
        # type the user just selected, which would make the comparison below
        # always say "no switch."
        current_type = active_media_server_type(saved_config)
        confirmation = _media_server_switch_confirmation(body, current_type)
        if confirmation is not None:
            return confirmation

        # The frontend only ever sends the media_server wire shape
        # (type/server_url) here, not a complete config — merge it onto the
        # real saved config (resolving media_servers.active/providers so the
        # setup-service factory dispatches to the right provider) rather than
        # trusting the submitted body as the whole config. Saving a bare
        # {media_server: {...}} as-is would wipe every other section.
        config = apply_config_section(saved_config, "media-server", submitted)

        setup_service = _setup_service(config)
        try:
            config = setup_service.configure_token(config, credentials)
        except _requests.exceptions.RequestException as exc:
            logging.warning("Media server token request failed | error=%s", exc)
            _set_media_server_connection_diagnostic(f"Media server unreachable: {exc}")
            raise HTTPException(status_code=503, detail="Media server unreachable")
        except Exception:
            logging.exception("Media server token configuration failed")
            raise HTTPException(status_code=400, detail="Token configuration failed")
        return _save_and_restart_listener(config)

    @router.post("/media-server/token")
    def media_server_configure_token(body: dict):
        return _configure_media_server_token_response(body)

    @router.post("/emby/token")
    def emby_configure_token(body: dict):
        return _configure_media_server_token_response(body)

    @router.get("/media-server/library-paths")
    def get_library_paths():
        config = api_runtime.config_service.load_config()
        try:
            return _setup_service(config).fetch_library_paths(config)
        except Exception as exc:
            api_runtime.runtime.set_last_diagnostic(
                diagnose_media_server_library_paths_unavailable(str(exc))
            )
            raise HTTPException(
                status_code=502,
                detail="Media server library paths unavailable",
            )

    def _check_media_server_response(body: dict):
        saved_config = api_runtime.config_service.load_config()
        # current_type from the real saved config — body's media_server may
        # already carry the *target* type the user just selected (same reason
        # as _configure_media_server_token_response above).
        current_type = active_media_server_type(saved_config)
        # body only ever carries the media_server wire shape (type/server_url)
        # here too — merge it onto the real saved config (resolving
        # media_servers.active/providers so the setup-service factory
        # dispatches to the right provider) instead of trusting it as the
        # whole config; saving the bare submitted body would wipe every other
        # section.
        config = apply_config_section(saved_config, "media-server", body)
        config = api_runtime.config_service.prepare_submitted_config(config)
        setup_service = _setup_service(config)
        response = _check_connection_or_503(setup_service, config)

        if 200 <= response.status_code < 300:
            confirmation = _media_server_switch_confirmation(body, current_type)
            if confirmation is not None:
                return confirmation
            verified_config = mark_section_verified(config, "media_server")
            return _save_and_restart_listener(verified_config)

        _set_media_server_connection_diagnostic(
            f"Media server responded with status {response.status_code}"
        )
        raise HTTPException(status_code=400, detail="Media server connection failed")

    @router.post("/media-server/check")
    def media_server_check(body: dict):
        return _check_media_server_response(body)

    def _proxy_now_playing_image(image_type: str, params: dict) -> Response:
        state = api_runtime.runtime.get_state()
        active = state.get("ActiveSession")
        if not active or not active.get("media_item_id"):
            raise HTTPException(status_code=404, detail="Nothing playing")
        config = api_runtime.config_service.load_config()
        ms = active_media_server_config(config)
        server_url = ms.server_url.rstrip("/")
        token = ms.access_token
        item_id = active["media_item_id"]
        if not server_url or not item_id:
            raise HTTPException(status_code=404, detail="No media server configured")
        if token:
            params["api_key"] = token
        try:
            resp = _requests.get(
                f"{server_url}/Items/{item_id}/Images/{image_type}",
                params=params,
                timeout=8,
            )
        except Exception:
            raise HTTPException(status_code=502, detail="Could not fetch image")
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Image not available")
        return Response(
            content=resp.content,
            media_type=resp.headers.get("content-type", "image/jpeg"),
        )

    @router.get("/now-playing/backdrop")
    def now_playing_backdrop():
        return _proxy_now_playing_image("Backdrop", {"maxWidth": "1920", "quality": "80"})

    @router.get("/now-playing/poster")
    def now_playing_poster():
        return _proxy_now_playing_image("Primary", {"maxHeight": "600", "maxWidth": "400", "quality": "90"})

    return router
