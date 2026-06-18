import logging
import time

from home_cinema_control.config.manager import is_smb_active
from home_cinema_control.devices.oppo.constants import OPPO_TELNET_PORT
from home_cinema_control.devices.oppo.setup_control import (
    OPPO_DEVICE_LOCK,
    check_oppo_control_api,
    mount_smb_share,
    mount_nfs_share,
)
from home_cinema_control.devices.oppo.control_api_client import OppoControlApiClient
from home_cinema_control.devices.oppo.mounted_share import parse_mounted_share_response
from home_cinema_control.devices.oppo.telnet_shell import unmount_oppo_path


DEVICE_LIST_WAIT_ATTEMPTS = 10
DEVICE_LIST_WAIT_SECONDS = 1


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
    if not _oppo_socket_is_available(config):
        logging.warning("Cannot connect to OPPO; check config or that OPPO is on or in standby")
        return "OPPO_UNAVAILABLE: OPPO socket is not reachable."

    with OPPO_DEVICE_LOCK:
        client = OppoControlApiClient.from_config(config)
        client.sign_in()
        device_list = _wait_for_device_list(client)

        if not device_list:
            logging.warning("OPPO device list did not become available during path test.")
            return "OPPO_DEVICE_LIST_UNAVAILABLE: OPPO device list did not become available."

        logging.info("OPPO device list: %s", device_list)

        use_nfs = _protocol_uses_nfs(config, protocol)
        mount_response = _login_and_mount(
            client=client,
            config=config,
            server=servidor,
            folder=carpeta,
            use_nfs=use_nfs,
            oppo=config["oppo"],
        )

        _unmount_after_test_if_needed(
            config=config,
            response=mount_response,
            server=servidor,
            folder=carpeta,
            is_nfs=use_nfs,
        )

        if mount_response.is_successful:
            return "OK"

        logging.warning(
            "OPPO mount path test failed | server=%s | folder=%s | error=%s | payload=%s",
            servidor,
            carpeta,
            mount_response.error_message,
            mount_response.payload,
        )
        error = mount_response.error_message or "OPPO mount request did not return a mounted path."
        return f"OPPO_MOUNT_FAILED: {error}"


def _protocol_uses_nfs(config, protocol=None) -> bool:
    normalized = str(protocol or "").strip().lower()

    if normalized in {"nfs"}:
        return True

    if normalized in {"cifs", "smb"}:
        return False

    return not is_smb_active(config)


def _oppo_socket_is_available(config) -> bool:
    return check_oppo_control_api(config) == 0


def _wait_for_device_list(client: OppoControlApiClient) -> list[dict]:
    device_list = []

    for attempt in range(1, DEVICE_LIST_WAIT_ATTEMPTS + 1):
        response = client.get_device_list()
        device_list = _extract_device_list(response.payload)

        if device_list:
            return device_list

        logging.debug(
            "OPPO device list is empty during path test | attempt=%s/%s | error=%s | payload=%s",
            attempt,
            DEVICE_LIST_WAIT_ATTEMPTS,
            response.error_message,
            response.payload,
        )

        client.send_remote_key("QPW")
        time.sleep(DEVICE_LIST_WAIT_SECONDS)

    return device_list


def _extract_device_list(payload: dict) -> list[dict]:
    device_list = payload.get("devicelist")

    if isinstance(device_list, list):
        return device_list

    return []


def _login_and_mount(
    *,
    client: OppoControlApiClient,
    config: dict,
    server: str,
    folder: str,
    use_nfs: bool,
    oppo: dict,
):
    _login_server(client, server, use_nfs)

    if not oppo.get("always_on", False):
        time.sleep(5)

    return _mount_folder(
        config=config,
        server=server,
        folder=folder,
        use_nfs=use_nfs,
    )


def _login_server(
    client: OppoControlApiClient,
    server_name: str,
    use_nfs: bool,
) -> None:
    if use_nfs:
        client.login_nfs_server(server_name)
    else:
        client.login_samba_without_id(server_name)


def _mount_folder(
    *,
    config: dict,
    server: str,
    folder: str,
    use_nfs: bool,
):
    """Mount via the same setup-control functions the folder browser uses.

    Routing through mount_smb_share/mount_nfs_share (instead of calling the
    OppoControlApiClient directly) means "Probar ruta" gets the SMBTrick priming
    (pre_mount_smb) and the id_error retry for free, instead of silently missing both.
    """
    if use_nfs:
        return mount_nfs_share(server, folder, config)

    return mount_smb_share(server, folder, config)


def _unmount_after_test_if_needed(
    *,
    config: dict,
    response,
    server: str,
    folder: str,
    is_nfs: bool,
) -> None:
    oppo = config.get("oppo", {})
    if not oppo.get("autoscript", False):
        return

    _, mounted_share = parse_mounted_share_response(
        response=response,
        server=server,
        folder=folder,
        is_nfs=is_nfs,
    )

    if not mounted_share:
        return

    unmount_oppo_path(
        host=oppo["ip"],
        port=int(config.get("OPPO_Port", OPPO_TELNET_PORT)),
        mount_path=mounted_share.mount_path,
        timeout=oppo["nfs_mount_timeout_seconds"],
    )
