import logging

from home_cinema_control.devices.oppo.constants import OPPO_TELNET_PORT
from home_cinema_control.devices.oppo.network_mount_service import (
    OPPO_DEVICE_LOCK,
    OppoMountResult,
    OppoNetworkFolder,
    OppoNetworkMountService,
    resolve_network_folder_protocol,
)
from home_cinema_control.devices.oppo.telnet_shell import unmount_oppo_path


def preview_path_mapping(server_data: dict) -> dict:
    """Return path preview components without contacting OPPO.

    Returns a dict with server, folder, source_prefix and player_prefix.
    Raises ValueError if the paths are structurally invalid.
    """
    test_path = build_test_media_path(server_data)
    parts = get_mount_path(test_path, server_data)

    source = normalize_config_path(server_data.get("source_path", ""))
    player = normalize_config_path(server_data.get("player_path", ""))

    return {
        "server": parts["Servidor"],
        "folder": parts["Carpeta"],
        "source_prefix": source,
        "player_prefix": player.rstrip("/"),
    }


def check_path_configuration(config, server):
    try:
        test_media_path = build_test_media_path(server)
        mount_path = get_mount_path(test_media_path, server)
    except ValueError as exc:
        logging.warning(
            "Invalid path test configuration: %s | payload=%s",
            exc,
            server,
        )
        return str(exc)

    return test_mount_path(
        config,
        mount_path["Servidor"],
        mount_path["Carpeta"],
        protocol=server.get("protocol"),
    )


def build_test_media_path(server_data):
    emby_path = normalize_config_path(server_data.get("source_path", ""))

    if not emby_path:
        raise ValueError("INVALID PATH CONFIG: source_path is required.")

    return emby_path.rstrip("/") + "/test.mkv"


def get_mount_path(movie, server_data):
    emby_path = normalize_config_path(server_data.get("source_path", ""))
    oppo_path = normalize_config_path(server_data.get("player_path", ""))

    if not emby_path:
        raise ValueError("INVALID PATH CONFIG: source_path is required.")

    if not oppo_path or oppo_path == "/":
        raise ValueError("INVALID PATH CONFIG: player_path is required.")

    movie = normalize_config_path(movie)
    emby_prefix = emby_path.rstrip("/")
    oppo_prefix = oppo_path.rstrip("/")

    if movie != emby_prefix and not movie.startswith(emby_prefix + "/"):
        raise ValueError("INVALID PATH CONFIG: Emby_Path does not match the test path.")

    movie = oppo_prefix + movie[len(emby_prefix):]
    path_parts = movie.strip("/").split("/")

    if len(path_parts) < 3:
        raise ValueError(
            "INVALID PATH CONFIG: player_path must include server and folder."
        )

    return {
        "Servidor": path_parts[0],
        "Carpeta": "/".join(path_parts[1:-1]),
        "Fichero": path_parts[-1],
    }


def normalize_config_path(path):
    return str(path or "").strip().replace("\\\\", "\\").replace("\\", "/")


def test_mount_path(config, servidor, carpeta, protocol=None):
    network_folder = OppoNetworkFolder(
        server_name=servidor,
        folder_path=carpeta,
        protocol=resolve_network_folder_protocol(config, protocol),
    )

    with OPPO_DEVICE_LOCK:
        result = OppoNetworkMountService(config).mount(network_folder)

        _unmount_after_test_if_needed(config=config, result=result)

        if result.successful:
            return "OK"

        logging.warning(
            "OPPO mount path test failed | server=%s | folder=%s | stage=%s | detail=%s",
            servidor,
            carpeta,
            result.failure_stage,
            result.detail,
        )

        if result.failure_stage == "control_api":
            return f"OPPO_UNAVAILABLE: {result.detail}"

        if result.failure_stage == "device_list":
            return f"OPPO_DEVICE_LIST_UNAVAILABLE: {result.detail}"

        return f"OPPO_MOUNT_FAILED: {result.detail}"


def _unmount_after_test_if_needed(*, config: dict, result: OppoMountResult) -> None:
    oppo = config.get("oppo", {})
    if not oppo.get("autoscript", False):
        return

    if not result.mounted_share:
        return

    unmount_oppo_path(
        host=oppo["ip"],
        port=int(config.get("OPPO_Port", OPPO_TELNET_PORT)),
        mount_path=result.mounted_share.mount_path,
        timeout=oppo["nfs_mount_timeout_seconds"],
    )
