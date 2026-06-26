from pathlib import Path

from home_cinema_control.devices.av.factory import get_supported_av_models
from home_cinema_control.devices.tv.factory import get_supported_tv_models
from home_cinema_control.config.manager import load_effective_config
from home_cinema_control.network.arp import ARP_TABLE_PATH

_LANG_PATH = Path(__file__).parent.parent / "lang"


def load_runtime_config(config_file, *, version):
    config = load_effective_config(config_file)
    apply_runtime_defaults(config, version=version)
    return config


def apply_runtime_defaults(config, *, version):
    """Add runtime-only web fields to an already validated effective config.

    Persisted app config defaults belong to HccConfig at the load boundary.
    This function intentionally injects only values discovered at runtime.
    """
    config["Version"] = version
    config["tv_dirs"] = get_supported_tv_models()
    config["av_dirs"] = get_supported_av_models()
    config["langs"] = get_dir_folders(_LANG_PATH)
    config["arp_available"] = ARP_TABLE_PATH.exists()

    return config


def get_dir_folders(directory):
    return sorted(path.name for path in Path(directory).iterdir() if path.is_dir())
