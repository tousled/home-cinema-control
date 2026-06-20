from __future__ import annotations

from typing import Protocol

from home_cinema_control.config.models import HccConfig, MediaServerConfig
from home_cinema_control.media_servers.common.listener import (
    MediaServerPlaybackListener,
)
from home_cinema_control.media_servers.common.models import MediaServerLoginCredentials
from home_cinema_control.media_servers.common.playback import MediaServerPlaybackServices


class MediaServerSetupService(Protocol):
    def configure_token(
        self,
        config: dict,
        credentials: MediaServerLoginCredentials,
    ) -> dict: ...

    def check_connection(self, config: dict): ...

    def load_devices(self, config: dict) -> dict: ...

    def load_libraries(self, config: dict) -> dict: ...

    def load_selectable_folders(self, config: dict) -> dict: ...

    def fetch_library_paths(self, config: dict) -> list[dict]: ...


class MediaServerProvider(Protocol):
    def playback_services(self) -> MediaServerPlaybackServices: ...

    def create_playback_listener(
        self,
        *,
        config: dict,
        config_file: str,
        language: dict,
    ) -> MediaServerPlaybackListener: ...

    def setup_service(self) -> MediaServerSetupService: ...


class MediaServerProviderFactory:
    def create(
        self,
        config: dict | HccConfig | MediaServerConfig,
    ) -> MediaServerProvider:
        return create_media_server_provider(config)


def create_media_server_provider(
    config: dict | HccConfig | MediaServerConfig,
) -> MediaServerProvider:
    provider_type = _media_server_config(config).type
    if provider_type == "emby":
        from home_cinema_control.media_servers.emby.provider import EmbyProvider

        return EmbyProvider()
    if provider_type == "jellyfin":
        from home_cinema_control.media_servers.jellyfin.provider import JellyfinProvider

        return JellyfinProvider()

    raise ValueError(f"Unsupported media server provider: {provider_type}")


def _media_server_config(config: dict | HccConfig | MediaServerConfig) -> MediaServerConfig:
    if isinstance(config, MediaServerConfig):
        return config
    if isinstance(config, HccConfig):
        return config.media_server
    return HccConfig(**config).media_server
