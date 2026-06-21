import json
import logging
import socket
import urllib.parse

from home_cinema_control.devices.oppo.constants import (
    OPPO_HTTP_PORT,
    OPPO_REMOTE_LOGIN_MESSAGE,
    OPPO_REMOTE_LOGIN_PORT,
)
from home_cinema_control.network.http import get_http_session
from home_cinema_control.devices.oppo.control_api_client import OppoControlApiClient
from home_cinema_control.devices.oppo.models import OppoCommandResponse
from home_cinema_control.devices.oppo.network_mount_service import (
    OPPO_DEVICE_LOCK,
    OppoNetworkFolder,
    OppoNetworkFolderProtocol,
    OppoNetworkMountService,
    check_oppo_control_api,
    resolve_network_folder_protocol,
)
from home_cinema_control.devices.oppo.mounted_share import OppoMountedShare


def create_oppo_control_client(config) -> OppoControlApiClient:
    return OppoControlApiClient.from_config(config)


def send_remote_login_notification(host: str) -> int:
    logging.debug("UDP target IP: %s", host)
    logging.debug("UDP target port: %s", OPPO_REMOTE_LOGIN_PORT)
    logging.debug("message: %s", OPPO_REMOTE_LOGIN_MESSAGE)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(bytes(OPPO_REMOTE_LOGIN_MESSAGE, "utf-8"), (host, OPPO_REMOTE_LOGIN_PORT))

    return 0


def get_oppo_device_list(config) -> OppoCommandResponse:
    return create_oppo_control_client(config).get_device_list()


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

    if check_oppo_control_api(config) != 0:
        raise RuntimeError("OPPO_UNAVAILABLE: OPPO control API is not reachable")

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
        network_protocol = resolve_network_folder_protocol(config, protocol)
        mount_service = OppoNetworkMountService(config)

        if len(path_parts) == 1 or not path_parts[1]:
            if network_protocol == OppoNetworkFolderProtocol.NFS:
                response_login = mount_service.login_nfs_server(server)

                if response_login.is_successful:
                    return list_nfs_share_folders(config)

                raise RuntimeError(
                    "Login failed: " + response_login.payload.get("retInfo", "unknown error")
                )

            response_login = mount_service.login_samba_server(server)

            if response_login.is_successful:
                return list_smb_share_folders(config)

            raise RuntimeError(
                "Login failed: " + response_login.payload.get("retInfo", "unknown error")
            )

        folder = path_parts[1]
        last_folder = "/"

        result = mount_service.mount(
            OppoNetworkFolder(
                server_name=server, folder_path=folder, protocol=network_protocol
            )
        )

        if not result.successful:
            if result.failure_stage == "login":
                raise RuntimeError(f"Login failed: {result.detail}")

            raise RuntimeError(f"Mount failed: {result.detail}")

        return list_mounted_folder_files(config, last_folder, result.mounted_share)
