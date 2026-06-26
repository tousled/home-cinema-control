_AV_FLAT_KEY_MAP = {
    "AV": "enabled",
    "AV_Ip": "ip",
    "AV_Port": "port",
    "AV_model": "model",
    "AV_Always_ON": "always_on",
    "av_delay_hdmi": "hdmi_switch_delay_seconds",
    "AV_CMD_POW_ON": "power_on_command",
    "AV_CMD_CHANGE_HDMI": "hdmi_input_command",
    "AV_CMD_POW_OFF": "power_off_command",
    "AV_SOURCES": "available_hdmi_inputs",
    "AV_Input": "player_hdmi_input",
    "AV_Timeout": "connection_timeout_seconds",
    "AV_Query_Timeout": "command_timeout_seconds",
    "AV_TV_Input": "tv_connected_input",
}

_TV_FLAT_KEY_MAP = {
    "TV": "enabled",
    "TV_IP": "ip",
    "TV_MAC": "mac",
    "TV_model": "model",
    "TV_SOURCES": "available_hdmi_inputs",
    "Source": "player_hdmi_input_id",
    "TV_script_init": "startup_script",
    "TV_script_end": "shutdown_script",
}

_APP_FLAT_KEY_MAP = {
    "output_path": "backup_path",
    "language": "language",
    "refresh_time": "status_refresh_interval_seconds",
    "check_beta": "include_prerelease",
    "release_repository": "release_repository",
    "version_check_timeout": "version_check_timeout_seconds",
    "DebugLevel": "log_level",
}

_PLAYBACK_FLAT_KEY_MAP = {
    "MonitoredDevice": "hcc_controlled_device",
    "enable_all_libraries": "use_all_libraries",
    "servers": "path_mappings",
    "Libraries": "libraries",
}

_OPPO_FLAT_KEY_MAP = {
    "Oppo_IP": "ip",
    "timeout_oppo_conection": "connection_timeout_seconds",
    "timeout_oppo_playitem": "playback_start_timeout_seconds",
    "timeout_oppo_mount": "nfs_mount_timeout_seconds",
    "oppo_control_api_connect_timeout": "api_connect_timeout_seconds",
    "oppo_web_control_api_attempts": "api_retry_attempts",
    "Autoscript": "autoscript",
    "Always_ON": "always_on",
    "BRDisc": "bluray_disc_mode",
    "smbtrick": "pre_mount_smb",
    "default_nfs": "use_smb",
}

LEGACY_FLAT_CONFIG_KEYS = (
    set(_AV_FLAT_KEY_MAP)
    | set(_TV_FLAT_KEY_MAP)
    | set(_APP_FLAT_KEY_MAP)
    | set(_PLAYBACK_FLAT_KEY_MAP)
    | set(_OPPO_FLAT_KEY_MAP)
    | {
        "emby_server",
        "user_name",
        "user_password",
        "user_password_configured",
        "emby_access_token",
        "emby_user_id",
        "emby_access_token_configured",
        "resume_on",
        # XNOPPO-era LG fields with no current equivalent: pairing now goes
        # through a different library with its own key store
        # (devices/tv/adapters/lg.py), and the device name was never read.
        "TV_KEY",
        "TV_DeviceName",
    }
)

# Top-level flat keys whose presence signals an unmigrated config.
LEGACY_DETECTION_KEYS = (
    set(_AV_FLAT_KEY_MAP)
    | set(_TV_FLAT_KEY_MAP)
    | set(_APP_FLAT_KEY_MAP)
    | set(_PLAYBACK_FLAT_KEY_MAP)
    | set(_OPPO_FLAT_KEY_MAP)
)


def apply_all_migrations(config: dict) -> None:
    """Transform any legacy config dict in-place into the current canonical form."""
    _migrate_oppo_flat_keys(config)
    _migrate_tv_flat_keys(config)
    _migrate_av_flat_keys(config)
    _migrate_app_flat_keys(config)
    _migrate_playback_flat_keys(config)
    _migrate_emby_flat_keys(config)
    _migrate_app_to_playback_keys(config)
    _rename_app_keys(config)
    _rename_playback_keys(config)
    _rename_av_keys(config)
    _rename_tv_keys(config)
    _rename_oppo_keys(config)
    _remove_legacy_flat_keys(config)


def _remove_legacy_flat_keys(config: dict) -> None:
    for key in LEGACY_FLAT_CONFIG_KEYS:
        config.pop(key, None)


# ---------------------------------------------------------------------------
# Flat → nested migrations (very old format, pre-sections)
# ---------------------------------------------------------------------------

def _migrate_av_flat_keys(config: dict) -> None:
    av = config.setdefault("av", {})
    for flat_key, nested_key in _AV_FLAT_KEY_MAP.items():
        if flat_key in config:
            if nested_key not in av:
                value = config.pop(flat_key)
                if nested_key == "enabled":
                    if value == "True":
                        value = True
                    elif value == "False":
                        value = False
                av[nested_key] = value
            else:
                config.pop(flat_key)


def _migrate_oppo_flat_keys(config: dict) -> None:
    oppo = config.setdefault("oppo", {})
    for flat_key, nested_key in _OPPO_FLAT_KEY_MAP.items():
        if flat_key in config:
            if nested_key not in oppo:
                value = config.pop(flat_key)
                if flat_key == "default_nfs":
                    if value == "True":
                        value = False
                    elif value == "False":
                        value = True
                    else:
                        value = not value
                oppo[nested_key] = value
            else:
                config.pop(flat_key)


def _migrate_tv_flat_keys(config: dict) -> None:
    tv = config.setdefault("tv", {})
    for flat_key, nested_key in _TV_FLAT_KEY_MAP.items():
        if flat_key in config:
            if nested_key not in tv:
                value = config.pop(flat_key)
                if nested_key == "enabled":
                    if value == "True":
                        value = True
                    elif value == "False":
                        value = False
                tv[nested_key] = value
            else:
                config.pop(flat_key)


def _migrate_app_flat_keys(config: dict) -> None:
    app = config.setdefault("app", {})
    for flat_key, nested_key in _APP_FLAT_KEY_MAP.items():
        if flat_key in config:
            if nested_key not in app:
                app[nested_key] = config.pop(flat_key)
            else:
                config.pop(flat_key)


def _migrate_playback_flat_keys(config: dict) -> None:
    playback = config.setdefault("playback", {})
    for flat_key, nested_key in _PLAYBACK_FLAT_KEY_MAP.items():
        if flat_key in config:
            if nested_key not in playback:
                playback[nested_key] = config.pop(flat_key)
            else:
                config.pop(flat_key)


def _migrate_emby_flat_keys(config: dict) -> None:
    """Move the XNOPPO-era flat emby_server into media_servers, in place.

    user_name/user_password are deliberately left untouched here: turning
    them into a stored access_token needs a live login call, which this pure
    dict-transform must not make (see web/migration.py, which reads them
    before calling apply_all_migrations and performs that login separately).
    LEGACY_FLAT_CONFIG_KEYS already lists both, so _remove_legacy_flat_keys
    still drops them from the config afterward.
    """
    server_url = str(config.get("emby_server", "")).strip()
    if not server_url:
        return

    media_servers = config.setdefault("media_servers", {})
    providers = media_servers.setdefault("providers", {})
    provider = providers.setdefault("emby", {})
    if not provider.get("server_url"):
        provider["server_url"] = server_url

    if "active" not in media_servers:
        media_servers["active"] = "emby"

    config.pop("emby_server", None)


def _migrate_app_to_playback_keys(config: dict) -> None:
    """Move playback keys that were temporarily stored under app.*."""
    app = config.get("app")
    if not app:
        return
    playback = config.setdefault("playback", {})
    for nested_key in _PLAYBACK_FLAT_KEY_MAP.values():
        if nested_key in app and nested_key not in playback:
            playback[nested_key] = app.pop(nested_key)


# ---------------------------------------------------------------------------
# Nested key renames (intermediate naming era → final canonical names)
# ---------------------------------------------------------------------------

def _rename_key(d: dict, old: str, new: str) -> None:
    if old in d:
        if new not in d:
            d[new] = d.pop(old)
        else:
            d.pop(old)


def _rename_app_keys(config: dict) -> None:
    app = config.get("app")
    if not app:
        return
    _rename_key(app, "output_path", "backup_path")
    _rename_key(app, "refresh_time", "status_refresh_interval_seconds")
    _rename_key(app, "check_beta", "include_prerelease")
    _rename_key(app, "debug_level", "log_level")
    _rename_key(app, "version_check_timeout", "version_check_timeout_seconds")


def _rename_playback_keys(config: dict) -> None:
    playback = config.get("playback")
    if not playback:
        return
    _rename_key(playback, "servers", "path_mappings")
    _rename_key(playback, "monitored_device", "hcc_controlled_device")
    _rename_key(playback, "enable_all_libraries", "use_all_libraries")
    playback.pop("resume_on", None)
    for mapping in playback.get("path_mappings", []):
        _rename_key(mapping, "Emby_Path", "source_path")
        _rename_key(mapping, "Oppo_Path", "player_path")
        _rename_key(mapping, "Test_OK", "verified")
    for library in playback.get("libraries", []):
        _rename_key(library, "Name", "name")
        _rename_key(library, "Id", "id")
        _rename_key(library, "Active", "active")


def _rename_av_keys(config: dict) -> None:
    av = config.get("av")
    if not av:
        return
    _rename_key(av, "cmd_pow_on", "power_on_command")
    _rename_key(av, "cmd_change_hdmi", "hdmi_input_command")
    _rename_key(av, "cmd_pow_off", "power_off_command")
    _rename_key(av, "delay_hdmi", "hdmi_switch_delay_seconds")
    _rename_key(av, "media_player_hdmi_input_name", "player_hdmi_input")
    _rename_key(av, "timeout", "connection_timeout_seconds")
    _rename_key(av, "query_timeout", "command_timeout_seconds")
    _rename_key(av, "tv_input", "tv_connected_input")


def _rename_tv_keys(config: dict) -> None:
    tv = config.get("tv")
    if not tv:
        return
    _rename_key(tv, "media_player_hdmi_input_id", "player_hdmi_input_id")
    _rename_key(tv, "script_init", "startup_script")
    _rename_key(tv, "script_end", "shutdown_script")


_OPPO_RENAME_MAP = {
    "timeout_connection": "connection_timeout_seconds",
    "timeout_playitem": "playback_start_timeout_seconds",
    "timeout_mount": "nfs_mount_timeout_seconds",
    "control_api_connect_timeout": "api_connect_timeout_seconds",
    "web_control_api_attempts": "api_retry_attempts",
    "br_disc": "bluray_disc_mode",
    "smb_trick": "pre_mount_smb",
}

# Old nested key names that signal an oppo section needs `_rename_oppo_keys`,
# even though the config already moved past the flat (pre-sections) format.
NESTED_OPPO_LEGACY_KEYS = set(_OPPO_RENAME_MAP) | {"default_nfs"}


def _rename_oppo_keys(config: dict) -> None:
    oppo = config.get("oppo")
    if not oppo:
        return
    for old_key, new_key in _OPPO_RENAME_MAP.items():
        _rename_key(oppo, old_key, new_key)
    if "default_nfs" in oppo:
        oppo["use_smb"] = not oppo.pop("default_nfs")
    oppo.pop("wait_nfs", None)
