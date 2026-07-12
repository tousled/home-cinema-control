from fastapi import APIRouter, HTTPException

from home_cinema_control.devices.av.setup_control import (
    list_av_hdmi_inputs,
    power_off_av_receiver,
    power_on_av_receiver,
    switch_av_to_player_input,
)
from home_cinema_control.playback.diagnostics import diagnose_device_action_failed
from home_cinema_control.web.api_runtime import WebApiRuntime
from home_cinema_control.web.setup_actions import (
    persist_verification_if_submitted_matches_saved,
)


def build_av_router(api_runtime: WebApiRuntime) -> APIRouter:
    router = APIRouter(prefix="/api/v1/av")

    def _detect_av_sources(config: dict):
        result = list_av_hdmi_inputs(config)
        config.setdefault("av", {})["available_hdmi_inputs"] = [src.model_dump() for src in result]
        api_runtime.config_service.save_config(config)
        return api_runtime.config_service.sanitize(config)

    @router.get("/sources")
    def av_get_sources():
        return _detect_av_sources(api_runtime.config_service.load_config())

    @router.post("/sources")
    def av_detect_sources(body: dict):
        return _detect_av_sources(body)

    @router.post("/power-on")
    def av_power_on(body: dict):
        result = power_on_av_receiver(body)
        if result == "OK":
            _, persisted = persist_verification_if_submitted_matches_saved(
                config_service=api_runtime.config_service,
                submitted_config=body,
                section="av",
            )
            return {"status": "ok", "verification_persisted": persisted}
        api_runtime.runtime.set_last_diagnostic(diagnose_device_action_failed(
            component="av", action="power on", detail=str(result)
        ))
        raise HTTPException(status_code=400, detail=result)

    @router.post("/power-off")
    def av_power_off_route(body: dict):
        result = power_off_av_receiver(body)
        if result == "OK":
            _, persisted = persist_verification_if_submitted_matches_saved(
                config_service=api_runtime.config_service,
                submitted_config=body,
                section="av",
            )
            return {"status": "ok", "verification_persisted": persisted}
        api_runtime.runtime.set_last_diagnostic(diagnose_device_action_failed(
            component="av", action="power off", detail=str(result)
        ))
        raise HTTPException(status_code=400, detail=result)

    @router.post("/switch-input")
    def av_switch_input(body: dict):
        result = switch_av_to_player_input(body)
        if result == "OK":
            _, persisted = persist_verification_if_submitted_matches_saved(
                config_service=api_runtime.config_service,
                submitted_config=body,
                section="av",
            )
            return {"status": "ok", "verification_persisted": persisted}
        api_runtime.runtime.set_last_diagnostic(diagnose_device_action_failed(
            component="av", action="switch input", detail=str(result)
        ))
        raise HTTPException(status_code=400, detail=result)

    return router
