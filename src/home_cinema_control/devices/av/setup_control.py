from home_cinema_control.config.models import AvInputSource

from .factory import create_av_receiver


def _result_to_status(result) -> str:
    return "OK" if result.successful else "FAILURE"


def power_on_av_receiver(config):
    return _result_to_status(create_av_receiver(config).power_on())


def list_av_hdmi_inputs(config) -> list[AvInputSource]:
    return create_av_receiver(config).list_hdmi_inputs()


def switch_av_to_player_input(config):
    av = config.get("av") or {}
    input_id = av.get("player_hdmi_input", "")
    return _result_to_status(create_av_receiver(config).switch_to_input(input_id))


def power_off_av_receiver(config):
    return _result_to_status(create_av_receiver(config).power_off())
