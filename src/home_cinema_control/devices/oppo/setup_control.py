import json
import logging
import socket
import threading
import time
import urllib.parse

from home_cinema_control.devices.oppo.constants import (
    OPPO_HTTP_PORT,
    OPPO_REMOTE_LOGIN_MESSAGE,
    OPPO_REMOTE_LOGIN_PORT,
)
from home_cinema_control.config.manager import is_smb_active
from home_cinema_control.network.http import get_http_session
from home_cinema_control.devices.oppo.control_api_activation import OppoControlApiActivator
from home_cinema_control.devices.oppo.control_api_client import OppoControlApiClient
from home_cinema_control.devices.oppo.models import OppoCommandResponse
from home_cinema_control.devices.oppo.network_playback_starter import (
    OppoNetworkPlaybackStarter,
)
from home_cinema_control.devices.oppo.mounted_share import (
    OppoMountedShare,
    parse_mounted_share_response,
)


# The OPPO's embedded HTTP server (port 436) cannot handle two concurrent
# login/mount sequences against the same server: one call hangs until the
# client-side timeout while the other gets an immediate id_error. This lock
# serializes all OPPO device communication so a second request (e.g. an
# impatient re-click before the first one resolved) queues instead of racing.
OPPO_DEVICE_LOCK = threading.Lock()


def create_oppo_control_client(config) -> OppoControlApiClient:
    return OppoControlApiClient.from_config(config)


def send_remote_login_notification(host: str) -> int:
    logging.debug("UDP target IP: %s", host)
    logging.debug("UDP target port: %s", OPPO_REMOTE_LOGIN_PORT)
    logging.debug("message: %s", OPPO_REMOTE_LOGIN_MESSAGE)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(bytes(OPPO_REMOTE_LOGIN_MESSAGE, "utf-8"), (host, OPPO_REMOTE_LOGIN_PORT))

    return 0


def check_oppo_control_api(config) -> int:
    activator = OppoControlApiActivator.from_config(config)
    result = activator.ensure_control_api_available(
        max_attempts=_control_api_attempts(config)
    )

    if result.available:
        logging.debug(
            "OPPO control API available | host=%s | port=%s | attempts=%s",
            result.host,
            result.port,
            result.attempts,
        )
        return 0

    logging.error(
        "Timeout waiting for OPPO control API | host=%s | port=%s | attempts=%s | error=%s",
        result.host,
        result.port,
        result.attempts,
        result.error,
    )
    return 1


def _control_api_attempts(config) -> int:
    configured_attempts = int(config.get("oppo", {}).get("api_retry_attempts", 3))
    return max(1, configured_attempts)


def get_oppo_device_list(config) -> OppoCommandResponse:
    return create_oppo_control_client(config).get_device_list()


def mount_smb_share(server: str, folder: str, config: dict, *, prime_smb: bool = True):
    logging.debug("*** mount_smb_share ***")

    oppo = config["oppo"]
    if oppo["pre_mount_smb"] is True and prime_smb is True:
        OppoNetworkPlaybackStarter(config).prime_samba_mount(server, folder)

    client = create_oppo_control_client(config)
    smb = config.get("smb", {})
    username = str(smb.get("username", "")).strip()
    password = str(smb.get("password", "")).strip()
    timeout = oppo["nfs_mount_timeout_seconds"]

    response_text = _mount_samba_folder_once(client, server, folder, username, password, timeout)

    if response_text.error_message == "id_error":
        logging.info(
            "OPPO SMB mount returned id_error on first attempt; "
            "retrying after brief wait (OPPO SMB state warm-up)."
        )
        time.sleep(2)
        response_text = _mount_samba_folder_once(client, server, folder, username, password, timeout)

    logging.debug("*** Mount Response: %s", response_text)
    return response_text


def _mount_samba_folder_once(client, server, folder, username, password, timeout):
    if username or password:
        return client.mount_samba_folder_with_id(
            server=server,
            folder=folder,
            username=username,
            password=password,
            timeout=timeout,
        )

    return client.mount_samba_folder(server=server, folder=folder, timeout=timeout)


def mount_nfs_share(server: str, folder: str, config: dict):
    logging.debug("*** mount_nfs_share ***")

    response_text = create_oppo_control_client(config).mount_nfs_folder(
        server=server,
        folder=folder,
        timeout=config["oppo"]["nfs_mount_timeout_seconds"],
    )

    logging.debug("*** Mount Response: %s", response_text)
    return response_text


def build_oppo_mounted_folder_path(mounted_share: OppoMountedShare, folder: str) -> str:
    mount_path = mounted_share.mount_path.rstrip("/")

    if not folder or folder == "/":
        return mount_path + "/"

    return mount_path + "/" + folder.lstrip("/")


def list_mounted_folder_files(config, folder, mounted_share: OppoMountedShare):
    logging.debug("*** list_mounted_folder_files ***")

    mounted_folder_path = build_oppo_mounted_folder_path(mounted_share, folder)

    payload = urllib.parse.quote(
        json.dumps(
            {
                "path": mounted_folder_path,
                "fileType": 1,
                "mediaType": 3,
                "flag": 1,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )

    url = f"http://{config['oppo']['ip']}:{OPPO_HTTP_PORT}/getfilelist?{payload}"
    headers = {}

    logging.debug(url)

    response = get_http_session("oppo-setup").get(url, headers=headers)
    files = _parse_oppo_folder_entries(response.content)
    logging.debug("*** list_mounted_folder_files Response: %s", response.text)
    return files


def list_nfs_share_folders(config):
    logging.debug("*** list_nfs_share_folders ***")
    url = f"http://{config['oppo']['ip']}:{OPPO_HTTP_PORT}/getNfsShareFolderlist"
    headers = {}
    logging.debug(url)
    response = get_http_session("oppo-setup").get(url, headers=headers)
    files = _parse_oppo_folder_entries(response.content)
    logging.debug("*** list_nfs_share_folders Response: %s", response.text)
    return files


def list_smb_share_folders(config):
    logging.debug("*** list_smb_share_folders ***")
    url = f"http://{config['oppo']['ip']}:{OPPO_HTTP_PORT}/getSambaShareFolderlist"
    headers = {}
    logging.debug(url)
    response = get_http_session("oppo-setup").get(url, headers=headers)
    files = _parse_oppo_folder_entries(response.content)
    logging.debug("*** list_smb_share_folders Response: %s", response.text)
    return files


def _parse_oppo_folder_entries(response_content: bytes) -> list[dict]:
    files = [{"Id": 0, "Foldername": ".."}]

    for chunk in response_content.rsplit(b"\x01"):
        if b"\x02" in chunk:
            continue

        folder_name = _extract_oppo_folder_name(chunk)
        if folder_name:
            files.append({"Id": len(files), "Foldername": folder_name})

    return files


def _extract_oppo_folder_name(chunk: bytes) -> str:
    last_offset = 0
    offset = 0

    while offset != -1:
        offset = chunk.find(b"\x00", offset)
        if offset == -1:
            return chunk[last_offset:].decode("utf-8")

        last_offset = offset + 1
        offset += 1

    return ""


def browse_network_folder(path, config, protocol=None):
    path = path.replace("\\\\", "\\")
    path = path.replace("\\", "/")
    path = path.replace("//", "/")

    with OPPO_DEVICE_LOCK:
        oppo_command_response: OppoCommandResponse = get_oppo_device_list(config)
        devices = oppo_command_response.raw_text
        device_list = json.loads(devices)

        if path == "/":
            files = []
            indice = 1

            for device in device_list["devicelist"]:
                file = {}
                file["Id"] = indice
                file["Foldername"] = device["name"]
                files.append(file)
                indice = indice + 1

            return files

        path_parts = path.strip("/").split("/", 1)
        server = path_parts[0]
        nfs = _protocol_uses_nfs(config, protocol)

        if len(path_parts) == 1 or not path_parts[1]:
            if nfs:
                response_login = OppoNetworkPlaybackStarter(config).login_nfs_server(server)

                if response_login.is_successful:
                    return list_nfs_share_folders(config)

                raise RuntimeError(
                    "Login failed: " + response_login.payload.get("retInfo", "unknown error")
                )

            response_login = OppoNetworkPlaybackStarter(config).login_samba_server(server)

            if response_login.is_successful:
                return list_smb_share_folders(config)

            raise RuntimeError(
                "Login failed: " + response_login.payload.get("retInfo", "unknown error")
            )

        folder = path_parts[1]
        last_folder = "/"

        if nfs:
            response_login = OppoNetworkPlaybackStarter(config).login_nfs_server(server)

            if not response_login.is_successful:
                raise RuntimeError(
                    "Login failed: " + response_login.payload.get("retInfo", "unknown error")
                )

            mount_response = mount_nfs_share(server, folder, config)

        else:
            response_login = OppoNetworkPlaybackStarter(config).login_samba_server(server)

            if not response_login.is_successful:
                raise RuntimeError(
                    "Login failed: " + response_login.payload.get("retInfo", "unknown error")
                )

            mount_response = mount_smb_share(server, folder, config)

        response_mount, mounted_share = parse_mounted_share_response(
            mount_response,
            server=server,
            folder=folder,
            is_nfs=nfs,
        )

        if mounted_share is None:
            raise RuntimeError(
                "Mount failed: " + response_mount.get("retInfo", "OPPO command did not report success")
            )

        return list_mounted_folder_files(config, last_folder, mounted_share)


def _protocol_uses_nfs(config, protocol=None) -> bool:
    normalized = str(protocol or "").strip().lower()

    if normalized == "nfs":
        return True

    if normalized in {"cifs", "smb"}:
        return False

    return not is_smb_active(config)
