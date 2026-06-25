import time

from fastapi import APIRouter, HTTPException

from home_cinema_control.config.models import OppoConfig
from home_cinema_control.devices.oppo.control_api_client import OppoControlApiClient
from home_cinema_control.devices.oppo.setup_control import (
    check_oppo_control_api,
    send_remote_login_notification,
)
from home_cinema_control.playback.diagnostics import diagnose_device_action_failed
from home_cinema_control.web.api_runtime import WebApiRuntime
from home_cinema_control.web.setup_actions import (
    persist_verification_if_submitted_matches_saved,
)


def build_oppo_router(api_runtime: WebApiRuntime) -> APIRouter:
    router = APIRouter(prefix="/api/v1/oppo")

    @router.post("/check")
    def oppo_check(body: dict):
        if check_oppo_control_api(body) == 0:
            _, persisted = persist_verification_if_submitted_matches_saved(
                config_service=api_runtime.config_service,
                submitted_config=body,
                section="media_player",
            )
            return {"status": "ok", "verification_persisted": persisted}
        api_runtime.runtime.set_last_diagnostic(diagnose_device_action_failed(
            component="oppo",
            action="connection check",
            detail="OPPO connection failed",
            severity="error",
        ))
        raise HTTPException(status_code=400, detail="OPPO connection failed")

    @router.get("/advanced-defaults")
    def oppo_advanced_defaults():
        defaults = OppoConfig()
        return {
            "connection_timeout_seconds": defaults.connection_timeout_seconds,
            "playback_start_timeout_seconds": defaults.playback_start_timeout_seconds,
            "nfs_mount_timeout_seconds": defaults.nfs_mount_timeout_seconds,
            "autoscript": defaults.autoscript,
        }

    @router.get("/key/{key}")
    def oppo_send_key(key: str):
        config = api_runtime.config_service.load_config()
        send_remote_login_notification(config["oppo"]["ip"])
        result = check_oppo_control_api(config)
        client = OppoControlApiClient.from_config(config)
        if key == "PON":
            if result == 0:
                client.sign_in()
                client.get_device_list()
                client.send_remote_key("EJT")
                if config["oppo"].get("br_disc") is True:
                    time.sleep(1)
                    client.send_remote_key("EJT")
                time.sleep(1)
                client.get_playing_time()
        else:
            client.send_remote_key(key)
        return {"ok": True}

    return router
