import logging
from dataclasses import dataclass
from enum import StrEnum

from home_cinema_control.network.http import get_http_session
from home_cinema_control.devices.oppo.control_api_client import OppoControlApiClient
from home_cinema_control.devices.oppo.models import OppoCommandResponse


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


class OppoNetworkPlaybackStarter:
    def __init__(
        self, config: dict, control_api_client: OppoControlApiClient | None = None
    ):
        self.config = config
        self.control_api_client = (
            control_api_client or OppoControlApiClient.from_config(config)
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

    def prime_samba_mount(self, server: str, folder: str) -> None:
        response = self.login_samba_server(server)

        if response.is_successful:
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
