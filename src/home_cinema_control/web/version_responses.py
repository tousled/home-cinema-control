from home_cinema_control.versioning.checker import (
    VersionInfo,
    get_cached_version_info,
    get_rollback_info,
    trigger_configured_update,
)


def check_version_response(config, current_version, *, force=False):
    version_info = get_cached_version_info(config, current_version, force=force)
    return _as_legacy_response(version_info)


def update_version_response(config, current_version):
    return trigger_configured_update(config, current_version)


def rollback_version_response(config, current_version=""):
    return get_rollback_info(config, current_version)


def _as_legacy_response(version_info: VersionInfo) -> dict:
    return {
        "version": version_info.latest_version,
        "file": version_info.asset_url,
        "new_version": version_info.new_version,
        "current_version": version_info.current_version,
        "latest_tag": version_info.latest_tag,
        "release_url": version_info.release_url,
        "error": version_info.error,
    }
