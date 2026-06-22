from pydantic import BaseModel, ConfigDict, Field

from home_cinema_control.media_servers.common.models import (
    MediaServerLibrary,
    MediaServerProviderType,
)


class PathMappingConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = ""
    source_path: str = ""
    player_path: str = "/"
    protocol: str = ""
    verified: bool = False


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    backup_path: str = "backup"
    language: str = "es-ES"
    status_refresh_interval_seconds: int = 5
    include_prerelease: bool = False
    version_check_interval_hours: int = 24
    update_webhook_url: str = ""
    previous_version: str = ""
    release_repository: str = "tousled/home-cinema-control"
    version_check_timeout_seconds: int = 10
    log_level: int = 0


class PlaybackConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    hcc_controlled_device: str = ""
    use_all_libraries: bool = False
    path_mappings: list[PathMappingConfig] = Field(default_factory=list)
    libraries: list[MediaServerLibrary] = Field(default_factory=list)


class AvConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    ip: str = ""
    port: int = 23
    model: str = ""
    always_on: bool = True
    hdmi_switch_delay_seconds: float = 0.0
    power_on_command: str = ""
    hdmi_input_command: str = ""
    power_off_command: str = ""
    available_hdmi_inputs: list = Field(default_factory=list)
    player_hdmi_input: str = ""
    connection_timeout_seconds: float = 5.0
    command_timeout_seconds: float = 1.0
    tv_connected_input: str = ""


class TvConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    ip: str = ""
    mac: str = ""
    model: str = ""
    available_hdmi_inputs: list = Field(default_factory=list)
    player_hdmi_input_id: int = 0
    startup_script: str = ""
    shutdown_script: str = ""


class OppoConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    ip: str = ""
    observation_mode: str = "auto"
    connection_timeout_seconds: float = 10.0
    playback_start_timeout_seconds: float = 30.0
    nfs_mount_timeout_seconds: float = 30.0
    track_menu_ready_timeout_seconds: float = 8.0
    track_menu_ready_poll_interval_seconds: float = 0.5
    track_menu_query_timeout_seconds: float = 1.0
    track_selection_applied_timeout_seconds: float = 2.0
    track_selection_applied_poll_interval_seconds: float = 0.25
    api_connect_timeout_seconds: float = 1.0
    api_retry_attempts: int = 3
    autoscript: bool = False
    autoscript_unmount_timeout_seconds: float = 3.0
    always_on: bool = True
    bluray_disc_mode: bool = False
    pre_mount_smb: bool = False
    use_smb: bool = False


class SmbConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    username: str = ""
    password: str = ""


class MediaServerConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: MediaServerProviderType = "emby"
    server_url: str = ""
    display_name: str = ""
    access_token: str = ""
    user_id: str = ""


class HccConfig(BaseModel):
    """
    Validated user config loaded from disk. Does not include runtime-injected
    fields (Version, tv_dirs, av_dirs, langs, devices) — those are added by
    apply_runtime_defaults after loading.
    """

    model_config = ConfigDict(extra="allow")

    app: AppConfig = Field(default_factory=AppConfig)
    playback: PlaybackConfig = Field(default_factory=PlaybackConfig)
    av: AvConfig = Field(default_factory=AvConfig)
    tv: TvConfig = Field(default_factory=TvConfig)
    oppo: OppoConfig = Field(default_factory=OppoConfig)
    media_server: MediaServerConfig = Field(default_factory=MediaServerConfig)
    smb: SmbConfig = Field(default_factory=SmbConfig)
