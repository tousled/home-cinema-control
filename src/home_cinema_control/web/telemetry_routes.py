from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from home_cinema_control.telemetry.events import RoadmapInterest
from home_cinema_control.telemetry.service import TelemetryService
from home_cinema_control.web.api_runtime import WebApiRuntime


class TelemetryDisableBody(BaseModel):
    reset_identity: bool = False


class RoadmapInterestBody(BaseModel):
    interests: list[RoadmapInterest] = Field(default_factory=list)
    comment: str = ""


def build_telemetry_router(api_runtime: WebApiRuntime) -> APIRouter:
    router = APIRouter(prefix="/api/v1/telemetry")

    def service() -> TelemetryService:
        return TelemetryService(
            config_file=api_runtime.config_file,
            load_config=api_runtime.config_service.load_config,
            save_config=api_runtime.config_service.save_config,
        )

    @router.get("")
    def telemetry_status():
        return service().status()

    @router.post("/enable")
    def telemetry_enable():
        try:
            return service().enable()
        except Exception as exc:
            logging.exception("telemetry_enable failed")
            raise HTTPException(status_code=400, detail=str(exc))

    @router.post("/disable")
    def telemetry_disable(body: TelemetryDisableBody | None = None):
        try:
            return service().disable(
                reset_identity=body.reset_identity if body is not None else False
            )
        except Exception as exc:
            logging.exception("telemetry_disable failed")
            raise HTTPException(status_code=400, detail=str(exc))

    @router.post("/clear-queue")
    def telemetry_clear_queue():
        return service().clear_queue()

    @router.post("/reset-installation-id")
    def telemetry_reset_installation_id():
        try:
            return service().reset_installation_id()
        except Exception as exc:
            logging.exception("telemetry_reset_installation_id failed")
            raise HTTPException(status_code=400, detail=str(exc))

    @router.post("/roadmap-interest")
    def telemetry_roadmap_interest(body: RoadmapInterestBody):
        try:
            telemetry_service = service()
            event: dict = {"interests": body.interests}
            if body.comment:
                event["comment"] = body.comment[:200].strip()
            telemetry_service.emit(
                "roadmap_interest_submitted",
                event=event,
            )
            return telemetry_service.status()
        except Exception as exc:
            logging.exception("telemetry_roadmap_interest failed")
            raise HTTPException(status_code=400, detail=str(exc))

    @router.post("/dismiss-prompt")
    def telemetry_dismiss_prompt():
        return service().dismiss_prompt()

    return router
