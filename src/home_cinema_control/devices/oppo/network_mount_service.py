import logging
import threading
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from home_cinema_control.config.manager import is_smb_active
from home_cinema_control.network.http import get_http_session
from home_cinema_control.devices.oppo.control_api_activation import OppoControlApiActivator
from home_cinema_control.devices.oppo.control_api_client import (
    TIMEOUT_IN_MOUNT_REQUEST_ERROR,
    OppoControlApiClient,
)
from home_cinema_control.devices.oppo.models import OppoCommandResponse
from home_cinema_control.devices.oppo.mounted_share import (
    OppoMountedShare,
    parse_mounted_share_response,
)

# The OPPO's embedded HTTP server (port 436) cannot handle two concurrent
# login/mount sequences against the same server: one call hangs until the
# client-side timeout while the other gets an immediate id_error. This lock
# serializes all OPPO device communication so a second request (e.g. an
# impatient re-click before the first one resolved) queues instead of racing.
# Reentrant: mount() acquires it internally, and callers that already hold it
# for a wider operation (e.g. browsing) may call into mount() from the same
# thread without deadlocking.
OPPO_DEVICE_LOCK = threading.RLock()

DEVICE_LIST_WAIT_ATTEMPTS = 10
DEVICE_LIST_WAIT_SECONDS = 1

MountFailureStage = Literal["control_api", "device_list", "login", "mount"]


class OppoNetworkFolderProtocol(StrEnum):
    NFS = "nfs"
    CIFS = "cifs"

    @classmethod
    def from_device_type(cls, device_type: str) -> "OppoNetworkFolderProtocol":
        if device_type.lower() == cls.NFS.value:
            return cls.NFS

        return cls.CIFS


@dataclass(frozen=True)
class OppoNetworkFolder:
    server_name: str
    folder_path: str
    protocol: OppoNetworkFolderProtocol

    @property
    def is_nfs(self) -> bool:
        return self.protocol == OppoNetworkFolderProtocol.NFS


@dataclass(frozen=True)
class OppoMountResult:
    successful: bool
    mounted_share: OppoMountedShare | None
    failure_stage: MountFailureStage | None
    detail: str


def resolve_network_folder_protocol(
    config: dict, protocol: str | None = None
) -> OppoNetworkFolderProtocol:
    normalized = str(protocol or "").strip().lower()

    if normalized == OppoNetworkFolderProtocol.NFS.value:
        return OppoNetworkFolderProtocol.NFS

    if normalized in {OppoNetworkFolderProtocol.CIFS.value, "smb"}:
        return OppoNetworkFolderProtocol.CIFS

    return (
        OppoNetworkFolderProtocol.CIFS
        if is_smb_active(config)
        else OppoNetworkFolderProtocol.NFS
    )


def check_oppo_control_api(config: dict) -> int:
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


def _control_api_attempts(config: dict) -> int:
    configured_attempts = int(config.get("oppo", {}).get("api_retry_attempts", 3))
    return max(1, configured_attempts)


class OppoNetworkMountService:
    """Ensures the OPPO is ready, then mounts a network folder.

    The single shared place for the OPPO network-mount handshake: control-API
    activation, sign-in, waiting for the device list, logging into the
    network server, SMB priming, mounting, and retrying once on a transient
    failure. Real playback, "probar ruta", and the folder browser all call
    mount() instead of each keeping their own copy of this sequence.
    """

    def __init__(
        self, config: dict, control_api_client: OppoControlApiClient | None = None
    ):
        self.config = config
        self.control_api_client = (
            control_api_client or OppoControlApiClient.from_config(config)
        )

    def mount(self, network_folder: OppoNetworkFolder) -> OppoMountResult:
        if check_oppo_control_api(self.config) != 0:
            return OppoMountResult(
                successful=False,
                mounted_share=None,
                failure_stage="control_api",
                detail="OPPO control API is not reachable",
            )

        with OPPO_DEVICE_LOCK:
            self.control_api_client.sign_in()

            if not self._wait_for_device_list():
                return OppoMountResult(
                    successful=False,
                    mounted_share=None,
                    failure_stage="device_list",
                    detail="OPPO device list did not become available",
                )

            login_response = self._login(network_folder)
            if not login_response.is_successful:
                return OppoMountResult(
                    successful=False,
                    mounted_share=None,
                    failure_stage="login",
                    detail=login_response.payload.get("retInfo", "unknown error"),
                )

            if not network_folder.is_nfs and self.config["oppo"].get("pre_mount_smb"):
                logging.info(
                    "OPPO pre_mount_smb enabled; priming SMB session before real mount | "
                    "server=%s | folder=%s",
                    network_folder.server_name,
                    network_folder.folder_path,
                )
                self._prime_samba_mount(network_folder.server_name, network_folder.folder_path)

            mount_response = self._mount(network_folder)

            retryable_error = (
                TIMEOUT_IN_MOUNT_REQUEST_ERROR if network_folder.is_nfs else "id_error"
            )
            if mount_response.error_message == retryable_error:
                logging.info(
                    "OPPO %s mount failed on first attempt (%s); "
                    "retrying after brief wait (OPPO state warm-up).",
                    "NFS" if network_folder.is_nfs else "SMB",
                    retryable_error,
                )
                time.sleep(2)
                mount_response = self._mount(network_folder)

            logging.info(
                "OPPO mount response | server=%s | folder=%s | response=%s",
                network_folder.server_name,
                network_folder.folder_path,
                mount_response.raw_text,
            )

            _, mounted_share = parse_mounted_share_response(
                mount_response,
                server=network_folder.server_name,
                folder=network_folder.folder_path,
                is_nfs=network_folder.is_nfs,
            )

            if mounted_share is None:
                detail = (
                    mount_response.error_message
                    or "OPPO mount request did not return a mounted path."
                )
                return OppoMountResult(
                    successful=False,
                    mounted_share=None,
                    failure_stage="mount",
                    detail=detail,
                )

            return OppoMountResult(
                successful=True,
                mounted_share=mounted_share,
                failure_stage=None,
                detail="",
            )

    def login_nfs_server(self, server: str) -> OppoCommandResponse:
        logging.debug("LoginNFS")
        response = self.control_api_client.login_nfs_server(server)
        logging.debug("*** LoginNFS Response: %s", response.raw_text)
        return response

    def login_samba_server(self, server: str) -> OppoCommandResponse:
        logging.debug("LoginSambaWithOutID")
        response = self.control_api_client.login_samba_without_id(server)
        logging.debug("*** LoginSambaWithOutID Response: %s", response.raw_text)
        return response

    def _wait_for_device_list(self) -> list[dict]:
        device_list: list[dict] = []

        for attempt in range(1, DEVICE_LIST_WAIT_ATTEMPTS + 1):
            response = self.control_api_client.get_device_list()
            device_list = _extract_device_list(response.payload)

            if device_list:
                return device_list

            logging.debug(
                "OPPO device list is empty | attempt=%s/%s | error=%s | payload=%s",
                attempt,
                DEVICE_LIST_WAIT_ATTEMPTS,
                response.error_message,
                response.payload,
            )

            self.control_api_client.send_remote_key("QPW")
            time.sleep(DEVICE_LIST_WAIT_SECONDS)

        return device_list

    def _login(self, network_folder: OppoNetworkFolder) -> OppoCommandResponse:
        if network_folder.is_nfs:
            return self.login_nfs_server(network_folder.server_name)

        return self.login_samba_server(network_folder.server_name)

    def _mount(self, network_folder: OppoNetworkFolder) -> OppoCommandResponse:
        timeout = self.config["oppo"]["nfs_mount_timeout_seconds"]

        if network_folder.is_nfs:
            return self.control_api_client.mount_nfs_folder(
                server=network_folder.server_name,
                folder=network_folder.folder_path,
                timeout=timeout,
            )

        smb = self.config.get("smb", {})
        username = str(smb.get("username", "")).strip()
        password = str(smb.get("password", "")).strip()

        if username or password:
            return self.control_api_client.mount_samba_folder_with_id(
                network_folder.server_name,
                network_folder.folder_path,
                username,
                password,
                timeout=timeout,
            )

        return self.control_api_client.mount_samba_folder(
            server=network_folder.server_name,
            folder=network_folder.folder_path,
            timeout=timeout,
        )

    def _refresh_nfs_share_folder_list(self) -> list[dict]:
        return self._refresh_share_folder_list("getNfsShareFolderlist")

    def _refresh_samba_share_folder_list(self) -> list[dict]:
        return self._refresh_share_folder_list("getSambaShareFolderlist")

    def _refresh_share_folder_list(self, endpoint: str) -> list[dict]:
        logging.debug("*** %s ***", endpoint)

        url = self.control_api_client._build_url(endpoint)
        logging.debug(url)

        response = get_http_session("oppo-network-playback").get(
            url,
            headers={},
            timeout=self.config["oppo"].get("connection_timeout_seconds", 3),
        )
        files = parse_network_folder_list_response(response.content)

        logging.debug("*** %s Response: %s", endpoint, response.text)
        return files

    def _prime_samba_mount(self, server: str, folder: str) -> None:
        """Mount a throwaway folder on `server` to warm up its SMB session.

        Assumes the caller already logged into `server` (mount() does this via
        _login() immediately before calling here) — does not log in again. The
        OPPO's embedded HTTP server tolerates a normal mount sequence but not
        an extra redundant login on top of it; see OPPO_DEVICE_LOCK's docstring.
        """
        for share_folder in self._refresh_samba_share_folder_list():
            folder_name = share_folder["Foldername"]

            if folder_name != ".." and folder_name.upper() != folder.upper():
                self.control_api_client.mount_samba_folder(
                    server=server,
                    folder=folder_name,
                    timeout=self.config["oppo"]["nfs_mount_timeout_seconds"],
                )

                logging.info("primed samba mount: %s/%s", server, folder_name)
                return

        device_list = self.control_api_client.get_device_list().payload

        for device in device_list["devicelist"]:
            if device["name"].upper() == server.upper():
                continue

            if device["sub_type"] != OppoNetworkFolderProtocol.CIFS.value:
                continue

            self.login_samba_server(device["name"])

            for share_folder in self._refresh_samba_share_folder_list():
                folder_name = share_folder["Foldername"]

                if folder_name != "..":
                    self.control_api_client.mount_samba_folder(
                        server=device["name"],
                        folder=folder_name,
                        timeout=self.config["oppo"]["nfs_mount_timeout_seconds"],
                    )
                    return


def _extract_device_list(payload: dict) -> list[dict]:
    device_list = payload.get("devicelist")

    if isinstance(device_list, list):
        return device_list

    return []


def parse_network_folder_list_response(response_content: bytes) -> list[dict]:
    chunks = response_content.rsplit(b"\x01")
    files = [{"Id": 0, "Foldername": ".."}]
    file_id = 1

    for chunk in chunks:
        if chunk.find(b"\x02") != -1:
            continue

        folder_name = _extract_share_folder_name(chunk)

        if folder_name:
            files.append({"Id": file_id, "Foldername": folder_name})
            file_id += 1

    return files


def _extract_share_folder_name(chunk: bytes) -> str:
    index = 0
    last_offset = 0
    folder_data = chunk

    while index != -1:
        index = chunk.find(b"\x00", index)

        if index == -1:
            folder_data = folder_data[last_offset:]
        else:
            last_offset = index + 1
            index += 1

    return folder_data.decode("utf-8")
