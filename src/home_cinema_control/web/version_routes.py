from fastapi import APIRouter, Query

from home_cinema_control import __version__
from home_cinema_control.web.api_runtime import WebApiRuntime
from home_cinema_control.web.version_responses import (
    check_version_response,
    rollback_version_response,
    update_version_response,
)
from home_cinema_control.web.version_update import display_version


def build_version_router(api_runtime: WebApiRuntime) -> APIRouter:
    router = APIRouter(prefix="/api/v1/version")

    @router.get("/check")
    def version_check(
        include_prerelease: bool | None = Query(default=None),
        force: bool = Query(default=False),
    ):
        config = api_runtime.config_service.load_config()
        if include_prerelease is not None:
            config = api_runtime.config_service.with_app_updates(
                config, include_prerelease=include_prerelease
            )
        response = check_version_response(config, __version__, force=force)
        return api_runtime.config_service.sanitize(response)

    @router.post("/update")
    def version_update():
        config = api_runtime.config_service.load_config()
        updated = api_runtime.config_service.with_app_updates(
            config, previous_version=display_version(__version__)
        )
        api_runtime.config_service.save_config(updated)
        return update_version_response(config, __version__)

    @router.get("/rollback")
    def version_rollback():
        config = api_runtime.config_service.load_config()
        return rollback_version_response(config, __version__)

    return router
