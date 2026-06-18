from home_cinema_control.devices.av.adapters.denon import DenonAvReceiver
from home_cinema_control.devices.av.adapters.marantz import MarantzAvReceiver
from home_cinema_control.devices.av.adapters.nad import NadAvReceiver
from home_cinema_control.devices.av.adapters.onkyo import OnkyoAvReceiver
from home_cinema_control.devices.av.adapters.scripts import ScriptsAvReceiver
from home_cinema_control.devices.av.adapters.yamaha import YamahaAvReceiver


AV_RECEIVERS = {
    "DENON": DenonAvReceiver,
    "MARANTZ": MarantzAvReceiver,
    "NAD": NadAvReceiver,
    "ONKYO": OnkyoAvReceiver,
    "SCRIPTS": ScriptsAvReceiver,
    "YAMAHA": YamahaAvReceiver,
}


def normalize_av_model(model):
    return str(model or "").upper()


def get_supported_av_models():
    return sorted(AV_RECEIVERS.keys())


def create_av_receiver(config):
    model = normalize_av_model((config.get("av") or {}).get("model"))
    receiver_class = AV_RECEIVERS.get(model)

    if receiver_class is None:
        raise ValueError(f"Unsupported AV model: {model}")

    return receiver_class(config)


def create_av_receiver_or_none(config):
    """Returns None when AV control is disabled; raises ValueError for unknown model when enabled."""
    if not (config.get("av") or {}).get("enabled"):
        return None
    return create_av_receiver(config)
