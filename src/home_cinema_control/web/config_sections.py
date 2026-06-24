from __future__ import annotations

from typing import Any

from home_cinema_control.config.manager import (
    active_media_server_type,
    set_active_media_server,
    upsert_media_server_provider,
)


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
        updated = merged.model_dump()

        if "playback" in body:
            updated["playback"] = {
                **(config.get("playback") or {}),
                "hcc_controlled_device": (body.get("playback") or {}).get("hcc_controlled_device", ""),
            }
        elif "hcc_controlled_device" in body:
            updated["playback"] = {
                **(config.get("playback") or {}),
                "hcc_controlled_device": body.get("hcc_controlled_device", ""),
            }
        return updated

    if section == "playback-libraries":
        playback = dict(config.get("playback") or {})
        playback["libraries"] = body.get("libraries", [])
        playback["use_all_libraries"] = body.get("use_all_libraries", True)
        updated["playback"] = playback
        return updated

    if section == "path-mappings":
        playback = dict(config.get("playback") or {})
        playback["path_mappings"] = body.get("path_mappings", [])
        updated["playback"] = playback
        return updated

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
            playback = dict(config.get("playback") or {})
            playback["path_mappings"] = body.get("path_mappings", [])
            updated["playback"] = playback
        return updated

    raise ValueError(f"Unsupported config section: {section}")
