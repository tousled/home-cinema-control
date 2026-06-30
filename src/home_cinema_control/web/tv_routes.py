import logging
import secrets
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from home_cinema_control.devices.tv.setup_control import (
    detect_tv_sources,
    restore_tv_media_server_app,
    switch_tv_to_player_input,
    test_tv_connection,
)
from home_cinema_control.playback.diagnostics import diagnose_device_action_failed
from home_cinema_control.web.api_runtime import WebApiRuntime
from home_cinema_control.web.setup_actions import (
    persist_verification_if_submitted_matches_saved,
    sanitized_submitted_section,
)

_OAUTH_STATE_STORE: dict[str, tuple[str, float]] = {}  # state -> (redirect_uri, expiry)
_STATE_TTL_SECONDS = 300


def _generate_state(redirect_uri: str) -> str:
    state = secrets.token_urlsafe(32)
    _OAUTH_STATE_STORE[state] = (redirect_uri, time.monotonic() + _STATE_TTL_SECONDS)
    return state


def _consume_state(state: str) -> str | None:
    entry = _OAUTH_STATE_STORE.pop(state, None)
    if entry is None:
        return None
    redirect_uri, expiry = entry
    if time.monotonic() >= expiry:
        return None
    return redirect_uri


def build_tv_router(api_runtime: WebApiRuntime) -> APIRouter:
    router = APIRouter(prefix="/api/v1/tv")

    @router.post("/test-connection")
    def tv_test_connection(body: dict):
        result = test_tv_connection(body)
        if result == "OK":
            tv = body.get("tv") or {}
            logging.info(
                "TV test connection succeeded | model=%s | ip=%s",
                tv.get("model", ""),
                tv.get("ip", ""),
            )
            _, persisted = persist_verification_if_submitted_matches_saved(
                config_service=api_runtime.config_service,
                submitted_config=body,
                section="tv",
            )
            return {
                "status": "ok",
                "verification_persisted": persisted,
                "tv": sanitized_submitted_section(
                    config_service=api_runtime.config_service,
                    submitted_config=body,
                    section_key="tv",
                ),
            }
        api_runtime.runtime.set_last_diagnostic(diagnose_device_action_failed(
            component="tv",
            action="connection test",
            detail=str(result),
            severity="error",
        ))
        raise HTTPException(status_code=400, detail=result)

    @router.post("/sources")
    def tv_get_sources(body: dict):
        result = detect_tv_sources(body)
        if result == "OK":
            return api_runtime.config_service.sanitize(
                api_runtime.config_service.prepare_submitted_config(body)
            )
        raise HTTPException(status_code=400, detail=result)

    @router.post("/switch-input")
    def tv_switch_input(body: dict):
        result = switch_tv_to_player_input(body)
        if result == "OK":
            _, persisted = persist_verification_if_submitted_matches_saved(
                config_service=api_runtime.config_service,
                submitted_config=body,
                section="tv",
            )
            return {"status": "ok", "verification_persisted": persisted}
        api_runtime.runtime.set_last_diagnostic(diagnose_device_action_failed(
            component="tv", action="switch input", detail=str(result)
        ))
        raise HTTPException(status_code=400, detail=result)

    @router.post("/restore-input")
    def tv_restore_input(body: dict):
        result = restore_tv_media_server_app(body)
        if result == "OK":
            _, persisted = persist_verification_if_submitted_matches_saved(
                config_service=api_runtime.config_service,
                submitted_config=body,
                section="tv",
            )
            return {"status": "ok", "verification_persisted": persisted}
        api_runtime.runtime.set_last_diagnostic(diagnose_device_action_failed(
            component="tv", action="restore app", detail=str(result)
        ))
        raise HTTPException(status_code=400, detail=result)

    @router.post("/samsung/oauth/start")
    def samsung_oauth_start(body: dict):
        from home_cinema_control.config.manager import get_config_path, get_secrets_path
        from home_cinema_control.devices.tv.adapters.smartthings_oauth import (
            SmartThingsOAuthClient,
            SmartThingsSecrets,
            SmartThingsTokenStore,
        )

        client_id = (body.get("client_id") or "").strip()
        client_secret = (body.get("client_secret") or "").strip()
        redirect_uri = (body.get("redirect_uri") or "").strip()

        if not client_id or not client_secret or not redirect_uri:
            raise HTTPException(
                status_code=422,
                detail="client_id, client_secret, and redirect_uri are required",
            )

        secrets_path = get_secrets_path(get_config_path())
        store = SmartThingsTokenStore(secrets_path)
        existing = store.load() or SmartThingsSecrets()
        store.save(existing.model_copy(update={
            "client_id": client_id,
            "client_secret": client_secret,
        }))

        state = _generate_state(redirect_uri)
        oauth = SmartThingsOAuthClient(client_id, client_secret)
        auth_url = oauth.authorization_url(redirect_uri, state)
        return {"auth_url": auth_url}

    @router.get("/samsung/oauth/callback")
    def samsung_oauth_callback(code: str = "", state: str = ""):
        from home_cinema_control.config.manager import get_config_path, get_secrets_path
        from home_cinema_control.devices.tv.adapters.smartthings_oauth import (
            SmartThingsOAuthClient,
            SmartThingsTokenStore,
        )

        redirect_uri = _consume_state(state)
        if redirect_uri is None:
            raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

        if not code:
            raise HTTPException(status_code=400, detail="Missing authorization code")

        secrets_path = get_secrets_path(get_config_path())
        store = SmartThingsTokenStore(secrets_path)
        existing = store.load()
        if not existing or not existing.client_id or not existing.client_secret:
            raise HTTPException(status_code=400, detail="SmartThings credentials not configured")

        try:
            oauth = SmartThingsOAuthClient(existing.client_id, existing.client_secret)
            tokens = oauth.exchange_code(code, redirect_uri)
            store.save(tokens)
            logging.info("SmartThings OAuth: authorization successful")
        except Exception as exc:
            logging.error("SmartThings OAuth: token exchange failed: %s", exc)
            raise HTTPException(status_code=400, detail=f"Token exchange failed: {exc}") from exc

        return RedirectResponse(url="/", status_code=302)

    @router.delete("/samsung/oauth/disconnect")
    def samsung_oauth_disconnect():
        from home_cinema_control.config.manager import get_config_path, get_secrets_path
        from home_cinema_control.devices.tv.adapters.smartthings_oauth import SmartThingsTokenStore

        secrets_path = get_secrets_path(get_config_path())
        store = SmartThingsTokenStore(secrets_path)
        existing = store.load()
        if existing:
            store.save(existing.model_copy(update={
                "access_token": "",
                "refresh_token": "",
                "token_expires_at": None,
            }))
        logging.info("SmartThings OAuth: disconnected")
        return {"status": "disconnected"}

    @router.get("/samsung/oauth/devices")
    def samsung_oauth_devices():
        import requests as req_lib
        from home_cinema_control.config.manager import get_config_path, get_secrets_path
        from home_cinema_control.devices.tv.adapters.smartthings_client import (
            make_smartthings_devices_client,
        )
        from home_cinema_control.devices.tv.adapters.smartthings_oauth import (
            SmartThingsOAuthClient,
            SmartThingsTokenStore,
        )
        from home_cinema_control.playback.diagnostics import (
            diagnose_smartthings_no_devices,
            diagnose_smartthings_token_rejected,
        )

        secrets_path = get_secrets_path(get_config_path())
        store = SmartThingsTokenStore(secrets_path)
        st = store.load()
        if not st or not st.refresh_token:
            raise HTTPException(status_code=400, detail="Not connected to SmartThings")
        oauth = SmartThingsOAuthClient(st.client_id, st.client_secret)
        client = make_smartthings_devices_client(store, oauth)
        if client is None:
            raise HTTPException(status_code=400, detail="Not connected to SmartThings")

        try:
            devices = client.list_devices()
        except req_lib.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else 0
            if status_code in (401, 403):
                api_runtime.runtime.set_last_diagnostic(diagnose_smartthings_token_rejected())
                raise HTTPException(status_code=401, detail="SmartThings token rejected")
            raise HTTPException(status_code=502, detail="SmartThings API error")

        if not devices:
            api_runtime.runtime.set_last_diagnostic(diagnose_smartthings_no_devices())

        return devices

    @router.get("/samsung/oauth/status")
    def samsung_oauth_status():
        from home_cinema_control.config.manager import get_config_path, get_secrets_path
        from home_cinema_control.devices.tv.adapters.smartthings_oauth import SmartThingsTokenStore

        secrets_path = get_secrets_path(get_config_path())
        store = SmartThingsTokenStore(secrets_path)
        st = store.load()
        connected = bool(st and st.refresh_token)
        return {
            "connected": connected,
            "client_id": st.client_id if st else "",
            "client_secret_configured": bool(st and st.client_secret),
        }

    return router
