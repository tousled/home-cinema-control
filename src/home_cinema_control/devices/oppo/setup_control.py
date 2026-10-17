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
    folder_names = _parse_oppo_listing_records(response_content)
    if folder_names is not None:
        files = [{"Id": 0, "Foldername": ".."}]
        files.extend(
            {"Id": index, "Foldername": folder_name}
            for index, folder_name in enumerate(folder_names, start=1)
        )
        return files

    return _parse_oppo_folder_entries_by_markers(response_content)


_OPPO_LISTING_HEADER = b"FLAG"
_OPPO_ENTRY_FOLDER = 1
_OPPO_ENTRY_FILE = 2
_OPPO_MAX_NAME_LENGTH = 4096
_OPPO_NAME_LENGTH_FIELD_BYTES = 4
_OPPO_ENTRY_TYPE_FIELD_BYTES = 4
_OPPO_ENTRY_EXTRA_FIELD_BYTES = 4
_OPPO_LISTING_RECORD_FIXED_BYTES = (
    _OPPO_NAME_LENGTH_FIELD_BYTES
    + _OPPO_ENTRY_TYPE_FIELD_BYTES
    + _OPPO_ENTRY_EXTRA_FIELD_BYTES
)
_OPPO_LISTING_TRAILER_MAX_BYTES = 8


def _parse_oppo_listing_records(response_content: bytes) -> list[str] | None:
    """Parse [length][name][type][extra] records and an optional counter trailer."""
    data = response_content
    offset = len(_OPPO_LISTING_HEADER) if data.startswith(_OPPO_LISTING_HEADER) else 0
    folder_names: list[str] = []
    record_count = 0

    while len(data) - offset > _OPPO_LISTING_TRAILER_MAX_BYTES:
        remaining = len(data) - offset
        if remaining < _OPPO_LISTING_RECORD_FIXED_BYTES:
            return None

        name_length_end = offset + _OPPO_NAME_LENGTH_FIELD_BYTES
        name_length = int.from_bytes(data[offset:name_length_end], "little")
        if not 0 < name_length <= _OPPO_MAX_NAME_LENGTH:
            return None

        name_start = name_length_end
        name_end = name_start + name_length
        entry_type_end = name_end + _OPPO_ENTRY_TYPE_FIELD_BYTES
        record_end = entry_type_end + _OPPO_ENTRY_EXTRA_FIELD_BYTES
        if record_end > len(data):
            return None

        entry_type = int.from_bytes(data[name_end:entry_type_end], "little")
        if entry_type not in (_OPPO_ENTRY_FOLDER, _OPPO_ENTRY_FILE):
            return None

        try:
            folder_name = data[name_start:name_end].decode("utf-8")
        except UnicodeDecodeError:
            return None

        if entry_type == _OPPO_ENTRY_FOLDER:
            folder_names.append(folder_name)
        record_count += 1
        offset = record_end

    if record_count == 0:
        return None

    return folder_names


def _parse_oppo_folder_entries_by_markers(response_content: bytes) -> list[dict]:
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
