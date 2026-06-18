from __future__ import annotations

from typing import Any


def apply_config_section(config: dict[str, Any], section: str, body: dict[str, Any]) -> dict[str, Any]:
    updated = {**config}

    if section in {"app", "oppo", "tv", "av", "smb"}:
        source = body.get(section) if section in body else body
        updated[section] = {**(config.get(section) or {}), **(source or {})}
        return updated

    if section == "media-server":
        media_server = body.get("media_server") or body
        updated["media_server"] = {
            **(config.get("media_server") or {}),
            **(media_server or {}),
        }
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
