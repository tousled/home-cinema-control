import logging

import requests as _requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from home_cinema_control.playback.diagnostics import (
    diagnose_media_server_library_paths_unavailable,
)
from home_cinema_control.web.api_runtime import WebApiRuntime
from home_cinema_control.web.media_server_configuration import (
    MediaServerConfigurationTransitionService,
)
from home_cinema_control.web.media_server_setup import media_server_setup_service
from home_cinema_control.telemetry.events import TelemetryEvent


def build_media_server_router(api_runtime: WebApiRuntime, media_server_provider_factory) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    def _setup_service(config: dict):
        return media_server_setup_service(media_server_provider_factory, config)

    transition_service = MediaServerConfigurationTransitionService(
        config_service=api_runtime.config_service,
        runtime=api_runtime.runtime,
        setup_service_factory=_setup_service,
        emit_telemetry=lambda: _emit_telemetry_async(api_runtime),
    )

    @router.patch("/config/media-server")
    def patch_media_server_section(body: dict):
        try:
            return transition_service.save_section(body)
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

    @router.post("/media-server/token")
    def media_server_configure_token(body: dict):
        return transition_service.configure_token(body)

    @router.post("/emby/token")
    def emby_configure_token(body: dict):
        return transition_service.configure_token(body)

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

    @router.post("/media-server/check")
    def media_server_check(body: dict):
        return transition_service.check_connection(body)

    def _proxy_now_playing_image(image_type: str, params: dict) -> Response:
        state = api_runtime.runtime.get_state()
        active = state.get("ActiveSession")
        if not active or not active.get("media_item_id"):
            raise HTTPException(status_code=404, detail="Nothing playing")
        config = api_runtime.config_service.load_config()
        ms = api_runtime.config_service.active_media_server(config)
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


def _emit_telemetry_async(api_runtime: WebApiRuntime) -> None:
    if api_runtime.telemetry is None:
        return
    api_runtime.runtime.application_event_bus.publish(
        TelemetryEvent(event_name="heartbeat")
    )
