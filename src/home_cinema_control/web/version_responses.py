from home_cinema_control.web.version_update import (
    get_cached_version_info,
    get_rollback_info,
    trigger_configured_update,
)


def check_version_response(config, current_version, *, force=False):
    return get_cached_version_info(config, current_version, force=force).as_legacy_response()


def update_version_response(config, current_version):
    return trigger_configured_update(config, current_version)


def rollback_version_response(config):
    return get_rollback_info(config)
