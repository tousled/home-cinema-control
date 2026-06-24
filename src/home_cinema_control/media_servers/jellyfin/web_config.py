from __future__ import annotations

import logging
from typing import Any

from home_cinema_control.config.manager import (
    active_media_server_config,
    set_active_media_server,
    upsert_media_server_provider,
)
from home_cinema_control.media_servers.common.constants import DEVICE_ID
from home_cinema_control.media_servers.common.models import (
    LibraryPath,
    MediaServerDevice,
    MediaServerLibrary,
    MediaServerLoginCredentials,
    is_library_active,
)
from home_cinema_control.media_servers.common.web_config import (
    build_library_config,
    items_from_response,
    public_config_with_existing_secrets,
)
from home_cinema_control.media_servers.jellyfin.client import JellyfinClient
from home_cinema_control.network.http import get_http_session


BRIDGE_DEVICE_IDS = {DEVICE_ID}
BRIDGE_APP_NAMES = {DEVICE_ID, "Home Cinema Control"}


def configure_jellyfin_token(
    config: dict, credentials: MediaServerLoginCredentials
) -> dict:
    config = public_config_with_existing_secrets(config)

    server_url = active_media_server_config(config).server_url.strip().rstrip("/")
    user_name = credentials.user_name.strip()
    password = credentials.password

    if not server_url:
        raise RuntimeError("Missing media_server.server_url")

    if not user_name:
        raise RuntimeError("Missing temporary Jellyfin user name")

    if not password:
        raise RuntimeError("Missing temporary Jellyfin password")

    auth_response = _authenticate_with_temporary_password(
        server_url=server_url,
        user_name=user_name,
        password=password,
    )

    access_token = auth_response.get("AccessToken", "")
    user = auth_response.get("User") or {}
    user_id = user.get("Id", "")
    display_name = user.get("Name") or user_name

    if not access_token or not user_id:
        raise RuntimeError(
            "Jellyfin authentication response did not include AccessToken/User.Id"
        )

    updated = upsert_media_server_provider(
        config,
        "jellyfin",
        server_url=server_url,
        display_name=display_name,
        access_token=access_token,
        user_id=user_id,
    )
    return set_active_media_server(updated, "jellyfin").model_dump()


def check_jellyfin_connection(config: dict):
    client = _authenticated_client(config)
    return client.set_capabilities(_client_capabilities_payload())


def load_devices(config: dict) -> dict:
    try:
        client = _authenticated_client(config)
        devices = client.get_devices()
        config["devices"] = [
            device.model_dump()
            for device in build_control_device_config(items_from_response(devices))
        ]
    except Exception:
        logging.exception("Error loading Jellyfin control devices")
    return config


def load_libraries(config: dict) -> dict:
    try:
        client = _authenticated_client(config)
        user_id = _authenticated_user_id(client)
        views = client.get_user_views(user_id)
        playback = config.setdefault("playback", {})
        playback["libraries"] = [
            library.model_dump()
            for library in build_library_config(
                items_from_response(views),
                existing_libraries=playback.get("libraries", []),
            )
        ]
    except Exception:
        logging.exception("Error loading Jellyfin libraries")
    return config


def load_selectable_folders(config: dict) -> dict:
    try:
        client = _authenticated_client(config)
        media_folders = client.get_virtual_folders()
        playback = config.setdefault("playback", {})
        playback["path_mappings"] = build_virtual_folder_servers(
            media_folders,
            libraries=playback.get("libraries", []),
            existing_servers=playback.get("path_mappings", []),
            enable_all_libraries=bool(playback.get("use_all_libraries", False)),
        )
    except Exception:
        logging.exception("Error loading Jellyfin virtual folders")
    return config


def fetch_library_paths(config: dict) -> list[dict]:
    client = _authenticated_client(config)
    return [
        LibraryPath.model_validate(path).model_dump()
        for path in client.get_library_paths()
    ]


def build_control_device_config(
    devices: list[dict[str, Any]],
) -> list[MediaServerDevice]:
    control_devices = []

    for device in devices:
        reported_device_id = str(
            device.get("ReportedDeviceId") or device.get("Id") or ""
        ).strip()
        if not reported_device_id or reported_device_id in BRIDGE_DEVICE_IDS:
            continue

        app_name = str(device.get("AppName", "")).strip()
        if app_name in BRIDGE_APP_NAMES:
            continue

        name = str(device.get("Name", "")).strip()
        if not name:
            continue

        display_name = f"{name} / {app_name}" if app_name else name
        control_devices.append(
            MediaServerDevice(
                id=reported_device_id, name=display_name, app_name=app_name
            )
        )

    return control_devices


def build_virtual_folder_servers(
    virtual_folders: list[dict[str, Any]],
    *,
    libraries: list[dict[str, Any]],
    existing_servers: list[dict[str, Any]],
    enable_all_libraries: bool,
) -> list[dict[str, Any]]:
    existing_by_source_path = {
        str(server.get("source_path", "")): server
        for server in existing_servers
        if server.get("source_path")
    }
    library_vos = [MediaServerLibrary.model_validate(item) for item in libraries]

    servers = []
    for folder in virtual_folders:
        folder_name = str(folder.get("Name", ""))
        if not enable_all_libraries and not is_library_active(library_vos, folder_name):
            continue

        for index, source_path in enumerate(folder.get("Locations", []), start=1):
            if not source_path:
                continue

            server = {
                "Id": f"{folder_name}:{index}",
                "name": folder_name if index == 1 else f"{folder_name}({index})",
                "source_path": str(source_path),
                "player_path": "/",
            }

            existing_server = existing_by_source_path.get(str(source_path))
            if existing_server:
                server.update(
                    {
                        "name": existing_server.get("name", server["name"]),
                        "player_path": existing_server.get(
                            "player_path", server["player_path"]
                        ),
                    }
                )
                if "verified" in existing_server:
                    server["verified"] = existing_server["verified"]

            servers.append(server)

    return servers


def _authenticated_client(config: dict) -> JellyfinClient:
    effective_config = public_config_with_existing_secrets(config)

    client = JellyfinClient.from_config(effective_config)
    client.authenticate()

    return client


def _authenticated_user_id(client: JellyfinClient) -> str:
    user_info = client.user_info or {}
    user = user_info.get("User") or {}
    user_id = user.get("Id", "")

    if not user_id:
        raise RuntimeError(
            "Jellyfin authentication is not configured: missing media_server.user_id"
        )

    return user_id


def _authenticate_with_temporary_password(
    *,
    server_url: str,
    user_name: str,
    password: str,
) -> dict:
    response = get_http_session("jellyfin").post(
        f"{server_url}/Users/AuthenticateByName",
        json={
            "Username": user_name,
            "Pw": password,
        },
        headers={
            "X-Emby-Authorization": (
                f'MediaBrowser Client="Home Cinema Control",'
                f'Device="Home Cinema Control",'
                f'DeviceId="{DEVICE_ID}",'
                f'Version="1.0.0"'
            )
        },
    )

    response.raise_for_status()
    return response.json()


def _client_capabilities_payload() -> dict:
    return {
        "SupportsMediaControl": True,
        "PlayableMediaTypes": [
            "Video",
            "Audio",
        ],
        "SupportedCommands": [
            "Play",
            "Playstate",
            "SetAudioStreamIndex",
            "SetSubtitleStreamIndex",
            "DisplayMessage",
            "PlayMediaSource",
        ],
        "DeviceProfile": {},
    }


configure_token = configure_jellyfin_token
check_connection = check_jellyfin_connection
