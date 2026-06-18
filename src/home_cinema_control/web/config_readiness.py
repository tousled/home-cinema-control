from __future__ import annotations

from home_cinema_control.web.setup_verification import verified_status


def compute_config_readiness(config: dict) -> dict:
    """Compute per-section setup readiness from a sanitized config dict."""
    return {
        "media_server": _media_server_readiness(config),
        "media_player": _media_player_readiness(config),
        "media_paths": _media_paths_readiness(config),
        "tv": _tv_readiness(config),
        "av": _av_readiness(config),
    }


def _media_server_readiness(config: dict) -> dict:
    ms = config.get("media_server") or {}
    if ms.get("access_token_configured") or ms.get("access_token"):
        return {
            "status": verified_status(config, "media_server"),
            "detail": ms.get("display_name") or ms.get("server_url") or "",
        }
    if ms.get("server_url"):
        return {"status": "incomplete", "detail": "Token not configured"}
    return {"status": "incomplete", "detail": "Server URL not set"}


def _media_player_readiness(config: dict) -> dict:
    oppo = config.get("oppo") or {}
    if oppo.get("ip"):
        return {"status": verified_status(config, "media_player"), "detail": oppo["ip"]}
    return {"status": "incomplete", "detail": "OPPO IP not set"}


def _media_paths_readiness(config: dict) -> dict:
    paths = (config.get("playback") or {}).get("path_mappings") or []
    total = len(paths)
    if total == 0:
        return {"status": "incomplete", "detail": "No paths configured"}
    verified = sum(1 for p in paths if p.get("verified"))
    if verified == total:
        return {"status": "configured", "detail": f"{verified}/{total} verified"}
    return {"status": "incomplete", "detail": f"{verified}/{total} verified"}


def _tv_readiness(config: dict) -> dict:
    tv = config.get("tv") or {}
    if not tv.get("enabled", False):
        return {"status": "disabled", "detail": "TV control disabled (optional)"}
    model = tv.get("model", "")
    if model == "LG":
        if tv.get("ip"):
            return {"status": verified_status(config, "tv"), "detail": f"{model} · {tv['ip']}"}
        return {"status": "incomplete", "detail": "IP address not set"}
    if model == "SCRIPTS":
        if tv.get("startup_script"):
            return {"status": verified_status(config, "tv"), "detail": model}
        return {"status": "incomplete", "detail": "Startup script not set"}
    if model:
        return {"status": verified_status(config, "tv"), "detail": model}
    return {"status": "incomplete", "detail": "Model not selected"}


def _av_readiness(config: dict) -> dict:
    av = config.get("av") or {}
    if not av.get("enabled", False):
        return {"status": "disabled", "detail": "AV control disabled (optional)"}
    model = av.get("model", "")
    if model == "SCRIPTS":
        if av.get("power_on_command"):
            return {"status": verified_status(config, "av"), "detail": model}
        return {"status": "incomplete", "detail": "Power on script not set"}
    if model:
        if av.get("ip"):
            return {"status": verified_status(config, "av"), "detail": f"{model} · {av['ip']}"}
        return {"status": "incomplete", "detail": "IP address not set"}
    return {"status": "incomplete", "detail": "Model not selected"}
