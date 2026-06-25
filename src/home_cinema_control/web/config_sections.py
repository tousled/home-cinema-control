from __future__ import annotations

from typing import Any

from home_cinema_control.config.manager import (
    active_media_server_type,
    set_active_media_server,
    upsert_media_server_provider,
    upsert_provider_playback,
)
from home_cinema_control.config.models import PathMappingConfig
from home_cinema_control.media_servers.common.models import MediaServerLibrary


def apply_config_section(config: dict[str, Any], section: str, body: dict[str, Any]) -> dict[str, Any]:
    updated = {**config}

    if section in {"app", "oppo", "tv", "av", "smb"}:
        source = body.get(section) if section in body else body
        updated[section] = {**(config.get(section) or {}), **(source or {})}
        return updated

    if section == "media-server":
        # Merges into media_servers.providers[target_type] (and makes it the
        # active provider) rather than a single media_server dict — see
        # .agents/specs/2026-06-23-media-server-multi-provider-config-design.md's
        # Provider Switch Flow. Never touches access_token/user_id: those only
        # ever come from configure_token/check_connection, not this generic
        # field-merge path.
        submitted = body.get("media_server") or body
        target_type = submitted.get("type") or active_media_server_type(config)
        provider_fields = {
            key: submitted[key] for key in ("server_url", "display_name") if key in submitted
        }
        merged = upsert_media_server_provider(config, target_type, **provider_fields)
        merged = set_active_media_server(merged, target_type)

        if "playback" in body:
            # The monitored-device selector — its body shape has always been
            # {"playback": {"hcc_controlled_device": ...}}, kept unchanged on
            # the wire even though it now lands in the provider's nested
            # playback record instead of a flat playback block. There is no
            # caller sending a bare top-level hcc_controlled_device (confirmed
            # against the frontend and tests), so that shape is not handled.
            device = (body.get("playback") or {}).get("hcc_controlled_device", "")
            merged = upsert_provider_playback(merged, target_type, hcc_controlled_device=device)

        return merged.model_dump()

    if section == "playback-libraries":
        active_type = active_media_server_type(config)
        libraries = [MediaServerLibrary.model_validate(item) for item in body.get("libraries", [])]
        merged = upsert_provider_playback(
            config,
            active_type,
            libraries=libraries,
            use_all_libraries=body.get("use_all_libraries", True),
        )
        return merged.model_dump()

    if section == "path-mappings":
        active_type = active_media_server_type(config)
        path_mappings = [
            PathMappingConfig.model_validate(item) for item in body.get("path_mappings", [])
        ]
        merged = upsert_provider_playback(config, active_type, path_mappings=path_mappings)
        return merged.model_dump()

    if section == "network-access":
        updated["oppo"] = {
            **(config.get("oppo") or {}),
            **(body.get("oppo") or {}),
        }
        updated["smb"] = {
            **(config.get("smb") or {}),
            **(body.get("smb") or {}),
        }
        if "path_mappings" in body:
            active_type = active_media_server_type(updated)
            path_mappings = [
                PathMappingConfig.model_validate(item) for item in body["path_mappings"]
            ]
            updated = upsert_provider_playback(
                updated, active_type, path_mappings=path_mappings
            ).model_dump()
        return updated

    raise ValueError(f"Unsupported config section: {section}")
