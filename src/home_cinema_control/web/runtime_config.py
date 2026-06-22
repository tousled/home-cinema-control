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
    config["Version"] = version
    app = config.setdefault("app", {})
    app.setdefault("backup_path", "backup")
    app.setdefault("language", "es-ES")
    app.setdefault("status_refresh_interval_seconds", 5)
    app.setdefault("include_prerelease", False)
    app.setdefault("release_repository", "tousled/home-cinema-control")
    app.setdefault("version_check_timeout_seconds", 10)
    app.setdefault("log_level", 0)
    playback = config.setdefault("playback", {})
    playback.setdefault("hcc_controlled_device", "")
    playback.setdefault("use_all_libraries", False)
    playback.setdefault("path_mappings", [])
    playback.setdefault("libraries", [])
    av = config.setdefault("av", {})
    av.setdefault("enabled", False)
    av.setdefault("ip", "")
    av.setdefault("port", 23)
    av.setdefault("model", "")
    av.setdefault("always_on", True)
    av.setdefault("hdmi_switch_delay_seconds", 0)
    av.setdefault("power_on_command", "")
    av.setdefault("hdmi_input_command", "")
    av.setdefault("power_off_command", "")
    av.setdefault("available_hdmi_inputs", [])
    av.setdefault("player_hdmi_input", "")
    av.setdefault("connection_timeout_seconds", 5)
    av.setdefault("command_timeout_seconds", 1)
    av.setdefault("tv_connected_input", "")

    tv = config.setdefault("tv", {})
    tv.setdefault("enabled", False)
    tv.setdefault("ip", "")
    tv.setdefault("mac", "")
    tv.setdefault("model", "")
    tv.setdefault("available_hdmi_inputs", [])
    tv.setdefault("player_hdmi_input_id", 0)
    tv.setdefault("startup_script", "")
    tv.setdefault("shutdown_script", "")

    oppo = config.setdefault("oppo", {})
    oppo.setdefault("ip", "")
    oppo.setdefault("observation_mode", "auto")
    oppo.setdefault("connection_timeout_seconds", 10)
    oppo.setdefault("playback_start_timeout_seconds", 30)
    oppo.setdefault("nfs_mount_timeout_seconds", 30)
    oppo.setdefault("track_menu_ready_timeout_seconds", 8.0)
    oppo.setdefault("track_menu_ready_poll_interval_seconds", 0.5)
    oppo.setdefault("track_menu_query_timeout_seconds", 1.0)
    oppo.setdefault("track_selection_applied_timeout_seconds", 2.0)
    oppo.setdefault("track_selection_applied_poll_interval_seconds", 0.25)
    oppo.setdefault("api_connect_timeout_seconds", 1.0)
    oppo.setdefault("api_retry_attempts", 3)
    oppo.setdefault("autoscript", False)
    oppo.setdefault("autoscript_unmount_timeout_seconds", 3.0)
    oppo.setdefault("always_on", True)
    oppo.setdefault("bluray_disc_mode", False)
    oppo.setdefault("pre_mount_smb", False)
    oppo.setdefault("use_smb", False)

    for server in playback["path_mappings"]:
        server["verified"] = server.get("verified", False)

    config["tv_dirs"] = get_supported_tv_models()
    config["av_dirs"] = get_supported_av_models()
    config["langs"] = get_dir_folders(_LANG_PATH)
    config["arp_available"] = ARP_TABLE_PATH.exists()

    return config


def get_dir_folders(directory):
    return sorted(path.name for path in Path(directory).iterdir() if path.is_dir())
