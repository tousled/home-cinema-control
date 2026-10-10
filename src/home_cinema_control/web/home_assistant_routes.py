from fastapi import APIRouter

from home_cinema_control.web.api_runtime import WebApiRuntime


def build_home_assistant_router(api_runtime: WebApiRuntime) -> APIRouter:
    router = APIRouter(prefix="/api/v1/home-assistant")

    @router.get("/status")
    def home_assistant_delivery_status():
        status = api_runtime.home_assistant_delivery_status
        if status is None:
            return {
                "status": "disabled",
                "last_event": None,
                "last_attempt_at": None,
                "detail": None,
            }
        return status.snapshot()

    return router
