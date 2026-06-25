import logging
import time

import requests as _requests
from fastapi import APIRouter, BackgroundTasks, Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response

from home_cinema_control import __version__
from home_cinema_control.config.models import HccConfig
from home_cinema_control.devices.av.setup_control import (
    list_av_hdmi_inputs,
    power_off_av_receiver,
    power_on_av_receiver,
    switch_av_to_player_input,
)
from home_cinema_control.config.models import OppoConfig
from home_cinema_control.devices.oppo.control_api_client import OppoControlApiClient
from home_cinema_control.devices.oppo.setup_control import (
    check_oppo_control_api,
    browse_network_folder,
    send_remote_login_notification,
)
from home_cinema_control.devices.tv.setup_control import (
    detect_tv_sources,
    restore_tv_media_server_app,
    switch_tv_to_player_input,
    test_tv_connection,
)
from home_cinema_control.media_servers.common.models import MediaServerLoginCredentials
from home_cinema_control.media_servers.common.provider import MediaServerProviderFactory
from home_cinema_control.playback.diagnostics import (
    diagnose_device_action_failed,
    diagnose_media_server_library_paths_unavailable,
    diagnose_path_inference_failed,
    diagnose_path_test_failed,
)
from home_cinema_control.playback.path_mapping_inference import infer_player_paths
from home_cinema_control.network.devices import discover_local_devices
from home_cinema_control.runtime import configure_logging
from home_cinema_control.config.manager import (
    active_media_server_config,
    active_media_server_type,
    clear_smb_credentials,
    get_media_server_provider,
    set_active_media_server,
    upsert_media_server_provider,
)
from home_cinema_control.web.api_runtime import WebApiRuntime
from home_cinema_control.web.config_sections import apply_config_section
from home_cinema_control.web.migration import (
    apply_migration,
    import_legacy_config,
    is_migration_available,
    start_fresh,
)
from home_cinema_control.web.config_readiness import compute_config_readiness
from home_cinema_control.web.path_config import check_path_configuration, preview_path_mapping
from home_cinema_control.web.setup_actions import (
    persist_verification_if_submitted_matches_saved,
    sanitized_submitted_section,
)
from home_cinema_control.web.setup_verification import mark_section_verified
from home_cinema_control.web.static_assets import read_binary_asset
from home_cinema_control.web.version_routes import check_version_response, rollback_version_response, update_version_response


def _media_server_setup_service(media_server_provider_factory, config: dict):
    validated_config = HccConfig(**config)
    return media_server_provider_factory.create(validated_config).setup_service()


def create_api_app(api_runtime: WebApiRuntime) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None)
    media_server_provider_factory = MediaServerProviderFactory()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    router = APIRouter(prefix="/api")

    # --- config ---

    @router.get("/config")
    def get_config():
        config = api_runtime.config_service.load_config()
        return api_runtime.config_service.sanitize(config)

    @router.get("/config/readiness")
    def get_config_readiness():
        config = api_runtime.config_service.load_config()
        sanitized = api_runtime.config_service.sanitize(config)
        return compute_config_readiness(sanitized)

    def _config_with_media_server_libraries():
        config = api_runtime.config_service.load_config()
        config = _media_server_setup_service(
            media_server_provider_factory,
            config,
        ).load_libraries(config)
        return api_runtime.config_service.sanitize(config)

    @router.get("/config/libraries")
    def get_config_with_libraries():
        return _config_with_media_server_libraries()

    @router.get("/media-server/libraries")
    def get_media_server_libraries():
        return _config_with_media_server_libraries()

    def _config_with_media_server_devices():
        config = api_runtime.config_service.load_config()
        config = _media_server_setup_service(
            media_server_provider_factory,
            config,
        ).load_devices(config)
        return api_runtime.config_service.sanitize(config)

    @router.get("/config/devices")
    def get_config_with_devices():
        return _config_with_media_server_devices()

    @router.get("/media-server/devices")
    def get_media_server_devices():
        return _config_with_media_server_devices()

    @router.patch("/config/{section}")
    def save_config_section(section: str, body: dict):
        try:
            if section == "media-server":
                return _save_media_server_section(body)

            config = api_runtime.config_service.load_config()
            updated = apply_config_section(config, section, body)
            updated = api_runtime.config_service.prepare_submitted_config(updated)
            api_runtime.config_service.save_config(updated)
            if section == "app":
                # Logging is configured once at startup; re-apply it here so a
                # log-level change from the web takes effect live, not only after
                # a restart.
                try:
                    configure_logging(updated, api_runtime.log_file)
                except Exception:
                    logging.exception(
                        "Failed to re-apply logging configuration after config change"
                    )
            return api_runtime.config_service.sanitize(updated)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except HTTPException:
            raise
        except Exception as exc:
            logging.exception("save_config_section failed")
            raise HTTPException(status_code=400, detail=str(exc))

    @router.post("/config/smb/clear")
    def clear_smb_creds():
        try:
            clear_smb_credentials(api_runtime.config_file)
            return {"ok": True}
        except Exception as exc:
            logging.exception("clear_smb_creds failed")
            raise HTTPException(status_code=400, detail=str(exc))

    # --- system ---

    @router.get("/state")
    def get_state():
        return api_runtime.config_service.sanitize(api_runtime.runtime.get_state())

    @router.get("/logs")
    def get_logs():
        try:
            body = read_binary_asset(api_runtime.log_file)
        except FileNotFoundError:
            body = b""
        return PlainTextResponse(body.decode("utf-8", errors="replace"))

    @router.post("/diagnostics/clear")
    def clear_diagnostics():
        api_runtime.runtime.clear_last_diagnostic()
        return {"ok": True}

    @router.get("/support/summary")
    def support_summary():
        config = api_runtime.config_service.sanitize(api_runtime.config_service.load_config())
        summary = api_runtime.runtime.get_support_summary()
        summary["config_readiness"] = compute_config_readiness(config)
        return api_runtime.config_service.sanitize(summary)

    @router.post("/restart")
    def restart(background_tasks: BackgroundTasks):
        background_tasks.add_task(api_runtime.runtime.restart_process)
        return {"ok": True}

    # --- version ---

    @router.get("/version/check")
    def version_check(
        include_prerelease: bool | None = Query(default=None),
        force: bool = Query(default=False),
    ):
        config = api_runtime.config_service.load_config()
        if include_prerelease is not None:
            config = {**config, "app": {**(config.get("app") or {}), "include_prerelease": include_prerelease}}
        response = check_version_response(config, __version__, force=force)
        return api_runtime.config_service.sanitize(response)

    @router.post("/version/update")
    def version_update():
        config = api_runtime.config_service.load_config()
        updated = {**config, "app": {**(config.get("app") or {}), "previous_version": __version__}}
        api_runtime.config_service.save_config(updated)
        return update_version_response(config, __version__)

    @router.get("/version/rollback")
    def version_rollback():
        config = api_runtime.config_service.load_config()
        return rollback_version_response(config)

    # --- migration ---

    @router.get("/migration/status")
    def migration_status():
        return {"available": is_migration_available(api_runtime.config_file)}

    @router.post("/migration/apply")
    def migration_apply():
        try:
            apply_migration(api_runtime.config_file)
            return {"ok": True}
        except Exception:
            logging.exception("Migration apply failed")
            raise HTTPException(status_code=500, detail="Migration failed")

    @router.post("/migration/skip")
    def migration_skip():
        try:
            start_fresh(api_runtime.config_file)
            return {"ok": True}
        except Exception:
            logging.exception("Migration skip failed")
            raise HTTPException(status_code=500, detail="Could not create fresh config")

    @router.post("/migration/import-legacy")
    def migration_import_legacy(payload: dict = Body(...)):
        try:
            import_legacy_config(api_runtime.config_file, payload)
            return {"ok": True}
        except ValueError:
            raise HTTPException(status_code=400, detail="Not a recognizable legacy config")
        except Exception:
            logging.exception("Legacy config import failed")
            raise HTTPException(status_code=500, detail="Import failed")

    # --- media server ---

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
        # device action failure (oppo_check, tv/av routes below) — instead of
        # only being visible as a transient toast in the Media Server screen.
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
        pattern below (paths_navigate).
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

        setup_service = _media_server_setup_service(media_server_provider_factory, merged)
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

        setup_service = _media_server_setup_service(
            media_server_provider_factory,
            config,
        )
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
            return _media_server_setup_service(
                media_server_provider_factory,
                config,
            ).fetch_library_paths(config)
        except Exception as exc:
            api_runtime.runtime.set_last_diagnostic(
                diagnose_media_server_library_paths_unavailable(str(exc))
            )
            raise HTTPException(
                status_code=502,
                detail="Media server library paths unavailable",
            )

    @router.post("/path-mapping-suggestions")
    def post_path_mapping_suggestions(body: dict):
        anchor = body.get("anchor") or {}
        candidates = body.get("candidates") or []
        anchor_source = anchor.get("source_path", "")
        anchor_share = anchor.get("share_path", "")
        try:
            pairs = infer_player_paths(anchor_source, anchor_share, candidates)
            return [
                {"source_path": src, "share_path": share}
                for src, share in pairs
            ]
        except ValueError as exc:
            api_runtime.runtime.set_last_diagnostic(diagnose_path_inference_failed())
            raise HTTPException(status_code=422, detail=str(exc))

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
        setup_service = _media_server_setup_service(
            media_server_provider_factory,
            config,
        )
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

    # --- oppo ---

    @router.post("/oppo/check")
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

    @router.get("/oppo/advanced-defaults")
    def oppo_advanced_defaults():
        defaults = OppoConfig()
        return {
            "connection_timeout_seconds": defaults.connection_timeout_seconds,
            "playback_start_timeout_seconds": defaults.playback_start_timeout_seconds,
            "nfs_mount_timeout_seconds": defaults.nfs_mount_timeout_seconds,
            "autoscript": defaults.autoscript,
        }

    @router.get("/oppo/key/{key}")
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

    # --- paths ---

    @router.get("/paths/refresh")
    def paths_refresh():
        config = api_runtime.config_service.load_config()
        config = _media_server_setup_service(
            media_server_provider_factory,
            config,
        ).load_selectable_folders(config)
        return api_runtime.config_service.sanitize(config)

    @router.post("/paths/preview")
    def paths_preview(body: dict):
        try:
            return preview_path_mapping(body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @router.post("/paths/test")
    def paths_test(body: dict):
        config = api_runtime.config_service.load_config()
        result = check_path_configuration(config, body)
        if result == "OK":
            return body
        diagnostic = diagnose_path_test_failed(result, config)
        api_runtime.runtime.set_last_diagnostic(diagnostic)
        return JSONResponse(
            status_code=400,
            content={"detail": diagnostic.reason, "diagnostic": diagnostic.to_dict()},
        )

    @router.post("/paths/navigate")
    def paths_navigate(body: dict):
        config = api_runtime.config_service.load_config()
        path = body.get("path", "/")
        protocol = body.get("protocol")
        try:
            result = browse_network_folder(path, config, protocol=protocol)
            logging.debug("paths_navigate | chars=%s", len(str(result)))
            return result
        except (_requests.exceptions.ConnectTimeout, _requests.exceptions.ConnectionError) as exc:
            logging.warning("paths_navigate: OPPO unreachable | path=%s | error=%s", path, exc)
            raise HTTPException(status_code=503, detail="OPPO unreachable")
        except Exception as exc:
            logging.warning("paths_navigate failed | path=%s | error=%s", path, exc)
            raise HTTPException(status_code=502, detail=str(exc))

    # --- tv ---

    @router.post("/tv/test-connection")
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

    @router.post("/tv/sources")
    def tv_get_sources(body: dict):
        result = detect_tv_sources(body)
        if result == "OK":
            return api_runtime.config_service.sanitize(
                api_runtime.config_service.prepare_submitted_config(body)
            )
        raise HTTPException(status_code=400, detail=result)

    @router.post("/tv/switch-input")
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

    @router.post("/tv/restore-input")
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

    # --- av ---

    @router.post("/av/sources")
    def av_get_sources(body: dict):
        result = list_av_hdmi_inputs(body)
        if result is not None:
            body.setdefault("av", {})["available_hdmi_inputs"] = result
            return api_runtime.config_service.sanitize(
                api_runtime.config_service.prepare_submitted_config(body)
            )
        raise HTTPException(status_code=400, detail="Could not retrieve AV sources")

    @router.post("/av/power-on")
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

    @router.post("/av/power-off")
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

    @router.post("/av/switch-input")
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

    # --- network ---

    @router.get("/network/devices")
    def network_devices():
        return discover_local_devices()

    # --- now playing ---

    @router.get("/now-playing/backdrop")
    def now_playing_backdrop():
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
        params = {"maxWidth": "1920", "quality": "80"}
        if token:
            params["api_key"] = token
        try:
            resp = _requests.get(
                f"{server_url}/Items/{item_id}/Images/Backdrop",
                params=params,
                timeout=8,
            )
        except Exception:
            raise HTTPException(status_code=502, detail="Could not fetch backdrop")
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Backdrop not available")
        return Response(
            content=resp.content,
            media_type=resp.headers.get("content-type", "image/jpeg"),
        )

    @router.get("/now-playing/poster")
    def now_playing_poster():
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
        params = {"maxHeight": "600", "maxWidth": "400", "quality": "90"}
        if token:
            params["api_key"] = token
        try:
            resp = _requests.get(
                f"{server_url}/Items/{item_id}/Images/Primary",
                params=params,
                timeout=8,
            )
        except Exception:
            raise HTTPException(status_code=502, detail="Could not fetch poster")
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Poster not available")
        return Response(
            content=resp.content,
            media_type=resp.headers.get("content-type", "image/jpeg"),
        )

    # --- playback ---

    @router.post("/playback/start")
    def playback_start(body: dict):
        api_runtime.runtime.start_movie(body)
        return {"ok": True}

    app.include_router(router)

    # --- SPA static files ---
    dist_dir = api_runtime.frontend_dist_dir

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if dist_dir.exists():
            candidate = dist_dir / full_path
            if candidate.exists() and candidate.is_file():
                return FileResponse(str(candidate))
            return FileResponse(str(dist_dir / "index.html"))
        return Response("Frontend not built. Run: cd frontend && npm run build", status_code=503)

    return app
