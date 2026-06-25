import hashlib
import logging
from typing import Any

from home_cinema_control import __version__
from home_cinema_control.config.manager import (
    active_media_server_config,
    get_media_server_provider,
    set_active_media_server,
    upsert_media_server_provider,
    upsert_provider_playback,
)
from home_cinema_control.config.models import PathMappingConfig
from home_cinema_control.media_servers.emby.constants import DEVICE_ID
from home_cinema_control.media_servers.emby.client import EmbyClient
from home_cinema_control.network.http import get_http_session
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


BRIDGE_DEVICE_IDS = {DEVICE_ID}
BRIDGE_APP_NAMES = {DEVICE_ID, "Home Cinema Control"}


def check_emby_connection(config: dict):
    client = _authenticated_client(config)
    response = client.set_capabilities(_client_capabilities_payload())
    return response


def load_devices(config: dict) -> dict:
    try:
        client = _authenticated_client(config)
        devices = client.get_devices()
        config["devices"] = [
            device.model_dump()
            for device in build_control_device_config(items_from_response(devices))
        ]
    except Exception as exc:
        logging.exception("Error loading Emby control devices")
        raise RuntimeError("Could not read Emby devices") from exc
    return config


def load_libraries(config: dict) -> dict:
    try:
        client = _authenticated_client(config)
        user_id = _authenticated_user_id(client)
        views = client.get_user_views(user_id)
        existing = get_media_server_provider(config, "emby").playback.libraries
        libraries = build_library_config(items_from_response(views), existing_libraries=existing)
        config = upsert_provider_playback(config, "emby", libraries=libraries).model_dump()
    except Exception:
        logging.exception("Error loading Emby libraries")
    return config


def load_selectable_folders(config: dict) -> dict:
    try:
        client = _authenticated_client(config)
        media_folders = client.get_selectable_media_folders()
        playback = get_media_server_provider(config, "emby").playback
        raw_servers = build_selectable_folder_servers(
            items_from_response(media_folders),
            libraries=playback.libraries,
            existing_servers=playback.path_mappings,
            enable_all_libraries=bool(playback.use_all_libraries),
        )
        path_mappings = [PathMappingConfig.model_validate(s) for s in raw_servers]
        config = upsert_provider_playback(config, "emby", path_mappings=path_mappings).model_dump()
    except Exception:
        logging.exception("Error loading Emby selectable folders")
    return config


def load_selectable_media_folders(config: dict) -> dict:
    return load_selectable_folders(config)


def fetch_library_paths(config: dict) -> list[dict]:
    """Return [{library_name, source_path}] from Emby virtual folders. config must include secrets."""
    client = _authenticated_client(config)
    return [
        LibraryPath.model_validate(path).model_dump()
        for path in client.get_library_paths()
    ]


def build_selectable_folder_servers(
    media_folders: list[dict[str, Any]],
    *,
        libraries: list[MediaServerLibrary | dict],
        existing_servers: list[PathMappingConfig | dict],
    enable_all_libraries: bool,
) -> list[dict[str, Any]]:
    existing_server_vos = [PathMappingConfig.model_validate(item) for item in existing_servers]
    existing_by_emby_path = {
        server.source_path: server for server in existing_server_vos if server.source_path
    }
    library_vos = [MediaServerLibrary.model_validate(item) for item in libraries]

    servers = []
    for folder in media_folders:
        folder_name = str(folder.get("Name", ""))
        if not enable_all_libraries and not is_library_active(library_vos, folder_name):
            continue

        for index, subfolder in enumerate(folder.get("SubFolders", []), start=1):
            emby_path = str(subfolder.get("Path", ""))
            if not emby_path:
                continue

            server = {
                "Id": subfolder.get("Id", ""),
                "name": folder_name if index == 1 else f"{folder_name}({index})",
                "source_path": emby_path,
                "player_path": "/",
            }

            existing_server = existing_by_emby_path.get(emby_path)
            if existing_server:
                server["name"] = existing_server.name or server["name"]
                server["player_path"] = existing_server.player_path or server["player_path"]
                server["verified"] = existing_server.verified

            servers.append(server)

    return servers


def build_control_device_config(
        devices: list[dict[str, Any]],
) -> list[MediaServerDevice]:
    control_devices = []

    for device in devices:
        reported_device_id = str(device.get("ReportedDeviceId", "")).strip()
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


def configure_emby_token(
        config: dict, credentials: MediaServerLoginCredentials
) -> dict:
    config = public_config_with_existing_secrets(config)

    server_url = active_media_server_config(config).server_url.strip().rstrip("/")
    user_name = credentials.user_name.strip()
    password = credentials.password

    if not server_url:
        raise RuntimeError("Missing media_server.server_url")

    if not user_name:
        raise RuntimeError("Missing temporary Emby user name")

    if not password:
        raise RuntimeError("Missing temporary Emby password")

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
        raise RuntimeError("Emby authentication response did not include AccessToken/User.Id")

    updated = upsert_media_server_provider(
        config,
        "emby",
        server_url=server_url,
        display_name=display_name,
        access_token=access_token,
        user_id=user_id,
    )
    config = set_active_media_server(updated, "emby").model_dump()

    _remove_legacy_emby_keys(config)

    return config

def _authenticated_client(config: dict) -> EmbyClient:
    effective_config = public_config_with_existing_secrets(config)

    client = EmbyClient.from_config(effective_config)
    client.authenticate()

    return client


def _authenticated_user_id(client: EmbyClient) -> str:
    user_info = client.user_info or {}
    user = user_info.get("User") or {}
    user_id = user.get("Id", "")

    if not user_id:
        raise RuntimeError("Emby authentication is not configured: missing media_server.user_id")

    return user_id


def _authenticate_with_temporary_password(
    *,
    server_url: str,
    user_name: str,
    password: str,
) -> dict:
    password_bytes = password.encode("utf-8")
    password_sha = hashlib.sha1(password_bytes).hexdigest()

    response = get_http_session("emby").post(
        f"{server_url}/Users/AuthenticateByName?format=json",
        data={
            "username": user_name,
            "password": password_sha,
            "pw": password,
        },
        headers={
            "X-Emby-Authorization": (
                f'MediaBrowser Client="Home Cinema Control",'
                f'Device="Home Cinema Control",'
                f'DeviceId="{DEVICE_ID}",'
                f'Version="{__version__}"'
            )
        },
    )

    response.raise_for_status()
    return response.json()


def _client_capabilities_payload() -> dict:
    return {
        "IconUrl": "https://img.alicdn.com/imgextra/i1/1840220527/O1CN018lXYlv1FlPES6Bgcw_!!1840220527.png",
        "SupportsMediaControl": True,
        "PlayableMediaTypes": [
            "Video",
            "Audio",
        ],
        "SupportedCommands": [
            "Play",
            "Playstate",
            "MoveUp",
            "MoveDown",
            "MoveLeft",
            "MoveRight",
            "Select",
            "Back",
            "ToggleContextMenu",
            "ToggleFullscreen",
            "ToggleOsdMenu",
            "GoHome",
            "PageUp",
            "NextLetter",
            "GoToSearch",
            "GoToSettings",
            "PageDown",
            "PreviousLetter",
            "TakeScreenshot",
            "VolumeUp",
            "VolumeDown",
            "ToggleMute",
            "SendString",
            "DisplayMessage",
            "SetAudioStreamIndex",
            "SetSubtitleStreamIndex",
            "SetRepeatMode",
            "Mute",
            "Unmute",
            "SetVolume",
            "PlayNext",
            "PlayMediaSource",
        ],
        "DeviceProfile": {},
    }


def _remove_legacy_emby_keys(config: dict) -> None:
    for key in [
        "emby_server",
        "user_name",
        "user_password",
        "user_password_configured",
        "emby_access_token",
        "emby_user_id",
        "emby_access_token_configured",
        "media_server_login",
    ]:
        config.pop(key, None)


configure_token = configure_emby_token
check_connection = check_emby_connection
