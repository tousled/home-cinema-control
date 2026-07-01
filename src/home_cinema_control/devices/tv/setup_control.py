from home_cinema_control.config.manager import (
    active_media_server_config,
    active_media_server_type,
)

from .factory import create_tv_controller
from .models import TvInputTarget


def _result_to_status(result) -> str:
    return "OK" if result.successful else "FAILURE"


def test_tv_connection(config):
    return _result_to_status(create_tv_controller(config).test_connection())


def detect_tv_sources(config):
    return _result_to_status(create_tv_controller(config).retrieve_hdmi_inputs())


def detect_tv_apps(config):
    """Sony-only setup step: get_application_list() is not part of BaseTvController,
    since only Sony needs per-TV app discovery (LG/Scripts hardcode or skip app ids)."""
    controller = create_tv_controller(config)
    get_application_list = getattr(controller, "get_application_list", None)

    if get_application_list is None:
        return "FAILURE"

    return _result_to_status(get_application_list())


def switch_tv_to_player_input(config):
    tv = config.get("tv") or {}
    source_index = int(tv.get("player_hdmi_input_id", 0))
    sources = tv.get("available_hdmi_inputs") or []

    if not sources or not (0 <= source_index < len(sources)):
        return "FAILURE"

    selected = sources[source_index]
    target = TvInputTarget(
        input_id=selected.get("id", ""),
        confirmation_app_id=selected.get("appId") or None,
    )
    return _result_to_status(create_tv_controller(config).switch_to_input(target))


def restore_tv_media_server_app(config):
    # No real server_url means no media server has been configured at all
    # (active_media_server_type alone can't tell that apart from "configured
    # as emby", since emby is its default) — nothing to restore to. The
    # frontend disables this action's button on the same signal so a real
    # user never hits this branch; it only guards a direct/API call.
    if not active_media_server_config(config).server_url:
        return _result_to_status(create_tv_controller(config).launch_app(None))

    provider_type = active_media_server_type(config)
    controller = create_tv_controller(config)
    return _result_to_status(controller.launch_app(controller.media_server_app_id(provider_type)))
