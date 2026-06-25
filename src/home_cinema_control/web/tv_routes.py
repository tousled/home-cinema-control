import logging

from fastapi import APIRouter, HTTPException

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

    return router
