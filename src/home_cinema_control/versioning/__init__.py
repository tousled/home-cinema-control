"""Application version and release services."""

from home_cinema_control.versioning.checker import (
    DEFAULT_RELEASE_REPOSITORY,
    VersionInfo,
    check_application_version,
    display_version,
    find_latest_release,
    find_previous_version,
    get_cached_version_info,
    get_rollback_info,
    is_fallback_version,
    is_newer_version,
    trigger_configured_update,
)

__all__ = [
    "DEFAULT_RELEASE_REPOSITORY",
    "VersionInfo",
    "check_application_version",
    "display_version",
    "find_latest_release",
    "find_previous_version",
    "get_cached_version_info",
    "get_rollback_info",
    "is_fallback_version",
    "is_newer_version",
    "trigger_configured_update",
]
