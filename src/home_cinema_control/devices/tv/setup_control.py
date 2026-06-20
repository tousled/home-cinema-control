from .factory import create_tv_controller
from .models import TvInputTarget


def _result_to_status(result) -> str:
    return "OK" if result.successful else "FAILURE"


def test_tv_connection(config):
    return _result_to_status(create_tv_controller(config).test_connection())


def detect_tv_sources(config):
    return _result_to_status(create_tv_controller(config).retrieve_hdmi_inputs())


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
    provider_type = (config.get("media_server") or {}).get("type", "")
    controller = create_tv_controller(config)
    return _result_to_status(controller.launch_app(controller.media_server_app_id(provider_type)))
