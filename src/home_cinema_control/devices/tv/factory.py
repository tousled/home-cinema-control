from home_cinema_control.devices.tv.adapters.lg import LgTvController
from home_cinema_control.devices.tv.adapters.samsung import SamsungTvController
from home_cinema_control.devices.tv.adapters.scripts import ScriptsTvController

TV_CONTROLLERS = {
    "LG": LgTvController,
    "SAMSUNG": SamsungTvController,
    "SCRIPTS": ScriptsTvController,
}


def normalize_tv_model(model):
    return str(model or "").upper()


def get_supported_tv_models():
    return sorted(TV_CONTROLLERS.keys())


def create_tv_controller(config):
    model = normalize_tv_model((config.get("tv") or {}).get("model"))
    controller_class = TV_CONTROLLERS.get(model)

    if controller_class is None:
        raise ValueError(f"Unsupported TV model: {model}")

    if model == "SAMSUNG":
        return SamsungTvController(config, smartthings_client=_build_smartthings_client(config))

    return controller_class(config)


def create_tv_controller_or_none(config):
    """Returns None when TV control is disabled; raises ValueError for unknown model when enabled."""
    if not (config.get("tv") or {}).get("enabled"):
        return None
    return create_tv_controller(config)


def _build_smartthings_client(config: dict):
    """Build a SmartThingsInputClient from the secrets file, or None if not configured."""
    from home_cinema_control.config.manager import get_config_path, get_secrets_path
    from home_cinema_control.devices.tv.adapters.smartthings_client import make_smartthings_client
    from home_cinema_control.devices.tv.adapters.smartthings_oauth import (
        SmartThingsOAuthClient,
        SmartThingsTokenStore,
    )

    secrets_path = get_secrets_path(get_config_path())
    store = SmartThingsTokenStore(secrets_path)
    secrets = store.load()
    if not secrets or not secrets.client_id or not secrets.client_secret:
        return None
    oauth = SmartThingsOAuthClient(secrets.client_id, secrets.client_secret)
    return make_smartthings_client(config, store, oauth)
