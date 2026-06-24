from __future__ import annotations

import json
import logging
import urllib.parse
from dataclasses import dataclass, replace
from typing import Any
from urllib.parse import urlparse

import requests

from home_cinema_control.config.manager import active_media_server_config
from home_cinema_control.devices.oppo.constants import (
    OPPO_HTTP_PORT,
    DEFAULT_OPPO_SIGN_IN_TIMEOUT_SECONDS,
    DEFAULT_OPPO_REQUEST_TIMEOUT_SECONDS,
)
from home_cinema_control.playback.time_units import ticks_to_hms
from home_cinema_control.network.http import get_http_session
from home_cinema_control.devices.oppo.models import OppoCommandResponse
from home_cinema_control.devices.oppo.mounted_share import OppoMountedShare

TIMEOUT_IN_PLAY_REQUEST_ERROR_MESSAGE = "Timeout in Play Request"
TIMEOUT_IN_MOUNT_REQUEST_ERROR = "Timeout in Mount Request"


@dataclass(frozen=True)
class OppoControlApiClient:
    player_host: str
    player_port: int = OPPO_HTTP_PORT
    media_server_host: str = ""
    http_session: Any | None = None

    @classmethod
    def from_config(cls, config: dict) -> "OppoControlApiClient":
        return cls(
            player_host=str(config["oppo"]["ip"]),
            player_port=int(config.get("OPPO_HTTP_Port", OPPO_HTTP_PORT)),
            media_server_host=extract_host_from_url(
                active_media_server_config(config).server_url
            ),
        )

    def get_main_firmware_version(self) -> OppoCommandResponse:
        return self._call_player_endpoint("getmainfirmwareversion")

    def with_http_session(self, http_session: Any) -> "OppoControlApiClient":
        return replace(self, http_session=http_session)

    def get_setup_menu(self) -> OppoCommandResponse:
        return self._call_player_endpoint("getsetupmenu")

    def sign_in(self, app_ip_address: str | None = None) -> OppoCommandResponse:
        effective_app_ip_address = (
            str(app_ip_address or "").strip()
            or self.media_server_host
        )

        payload = self._encode_json_payload(
            {
                "appIconType": 1,
                "appIpAddress": effective_app_ip_address,
            }
        )

        return self._call_player_endpoint_or_error(
            "signin",
            payload,
            timeout=DEFAULT_OPPO_SIGN_IN_TIMEOUT_SECONDS,
            error_message="Timeout in OPPO sign-in request",
        )

    def get_device_list(self) -> OppoCommandResponse:
        return self._call_player_endpoint("getdevicelist")

    def get_global_info(self) -> OppoCommandResponse:
        return self._call_player_endpoint("getglobalinfo")

    def get_playing_time(self) -> OppoCommandResponse:
        return self._call_player_endpoint("getplayingtime")

    def set_play_time(self, position_ticks: int) -> OppoCommandResponse:
        hours, minutes, seconds = ticks_to_hms(position_ticks)

        payload = self._encode_json_payload(
            {
                "h": hours,
                "m": minutes,
                "s": seconds,
            }
        )

        return self._call_player_endpoint("setplaytime", payload)

    def select_audio_track(self, audio_index: int) -> OppoCommandResponse:
        payload = self._encode_json_payload(
            {
                "cur_index": int(audio_index),
            }
        )

        return self._call_player_endpoint("setaudiomenulist", payload)

    def get_audio_menu(
        self, *, timeout: int | float | None = None
    ) -> OppoCommandResponse:
        return self._call_player_endpoint("getaudiomenulist", "", timeout=timeout)

    def get_subtitle_menu(
        self, *, timeout: int | float | None = None
    ) -> OppoCommandResponse:
        return self._call_player_endpoint(
            "getsubtitlemenulist",
            "",
            timeout=timeout,
            suppress_exception_log=timeout is not None,
        )

    def select_subtitle_track(self, subtitle_index: int) -> OppoCommandResponse:
        payload = self._encode_json_payload(
            {
                "cur_index": int(subtitle_index),
            }
        )

        return self._call_player_endpoint("setsubttmenulist", payload)

    def send_remote_key(self, key: str) -> OppoCommandResponse:
        payload = self._encode_json_payload(
            {
                "key": key,
            }
        )

        return self._call_player_endpoint("sendremotekey", payload)

    def login_nfs_server(self, server: str) -> OppoCommandResponse:
        payload = self._encode_json_payload(
            {
                "serverName": server,
            }
        )

        return self._call_player_endpoint("loginNfsServer", payload)

    def login_samba_without_id(self, server: str) -> OppoCommandResponse:
        payload = self._encode_json_payload(
            {
                "serverName": server,
            }
        )

        return self._call_player_endpoint("loginSambaWithOutID", payload)

    def mount_samba_folder_with_id(
        self,
        server: str,
        folder: str,
        username: str,
        password: str,
        *,
        timeout: int | float,
    ) -> OppoCommandResponse:
        payload = self._encode_json_payload(
            {
                "server": server,
                "bWithID": 1,
                "folder": folder,
                "userName": username,
                "password": password,
                "bRememberID": 1,
            }
        )

        return self._call_player_endpoint_or_error(
            "mountSharedFolder",
            payload,
            timeout=timeout,
            error_message=TIMEOUT_IN_MOUNT_REQUEST_ERROR,
        )

    def mount_samba_folder(
        self,
        server: str,
        folder: str,
        *,
        timeout: int | float,
    ) -> OppoCommandResponse:
        payload = self._encode_json_payload(
            {
                "server": server,
                "bWithID": 0,
                "folder": folder,
                "userName": "",
                "password": "",
                "bRememberID": 0,
            }
        )

        return self._call_player_endpoint_or_error(
            "mountSharedFolder",
            payload,
            timeout=timeout,
            error_message="Timeout in Mount Request",
        )

    def mount_nfs_folder(
        self,
        server: str,
        folder: str,
        *,
        timeout: int | float,
    ) -> OppoCommandResponse:
        payload = self._encode_json_payload(
            {
                "server": server,
                "folder": folder,
            }
        )

        response = self._call_player_endpoint_or_error(
            "mountNfsSharedFolder",
            payload,
            timeout=timeout,
            error_message=TIMEOUT_IN_MOUNT_REQUEST_ERROR,
        )

        return response

    def play_normal_file(
        self,
        mounted_share: OppoMountedShare,
        filename: str,
        index: str,
        timeout: int | float,
    ) -> OppoCommandResponse:
        file_path = f"{mounted_share.mount_path.rstrip('/')}/{filename}"

        payload = self._encode_json_payload(
            {
                "path": file_path,
                "index": int(index),
                "type": 1,
                "appDeviceType": 2,
                "extraNetPath": mounted_share.server,
                "playMode": 0,
            }
        )

        return self._call_player_endpoint_or_error(
            "playnormalfile",
            payload,
            timeout=timeout,
            error_message=TIMEOUT_IN_PLAY_REQUEST_ERROR_MESSAGE,
        )

    def mounted_folder_contains_blu_ray_structure(
        self,
        mounted_share: OppoMountedShare,
        relative_folder_path: str,
        *,
        timeout: int | float,
    ) -> OppoCommandResponse:
        mounted_root = mounted_share.mount_path.rstrip("/")
        relative_path = relative_folder_path.strip("/")

        folder_path = (
            mounted_root if not relative_path else f"{mounted_root}/{relative_path}"
        )

        payload = self._encode_json_payload(
            {
                "folderpath": folder_path,
            }
        )

        return self._call_player_endpoint_or_error(
            "checkfolderhasBDMV",
            payload,
            timeout=timeout,
            error_message=TIMEOUT_IN_PLAY_REQUEST_ERROR_MESSAGE,
        )

    def _call_player_endpoint(
        self,
        endpoint: str,
        query: str | None = None,
        *,
        timeout: int | float | None = None,
        suppress_exception_log: bool = False,
    ) -> OppoCommandResponse:
        url = self._build_url(endpoint, query)

        response = self._http_session().get(
            url,
            headers={"Connection": "close"},
            timeout=timeout or DEFAULT_OPPO_REQUEST_TIMEOUT_SECONDS,
            suppress_exception_log=suppress_exception_log,
        )

        return OppoCommandResponse.from_text(
            response.text,
            status_code=response.status_code,
        )

    def _call_player_endpoint_or_error(
        self,
        endpoint: str,
        query: str,
        *,
        timeout: int | float,
        error_message: str,
    ) -> OppoCommandResponse:
        try:
            return self._call_player_endpoint(
                endpoint,
                query,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            # Don't log str(exc): requests/urllib3 render it with the full
            # request URL embedded, including query-string credentials
            # (e.g. mountSharedFolder's password). The exception type name
            # is enough to distinguish timeout vs. connection-refused, etc.
            logging.warning(
                "OPPO request failed | endpoint=%s | error_type=%s",
                endpoint,
                type(exc).__name__,
            )
            return OppoCommandResponse.failed(error_message)

    def _build_url(self, endpoint: str, query: str | None = None) -> str:
        url = f"http://{self.player_host}:{self.player_port}/{endpoint}"

        if query is not None:
            url = f"{url}?{query}"

        return url

    def _encode_json_payload(self, payload: dict) -> str:
        return urllib.parse.quote(
            json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            safe="",
        )

    def _http_session(self):
        return self.http_session or get_http_session("oppo-media-control")


def extract_host_from_url(url: str) -> str:
    if not url:
        return ""

    parsed_url = urlparse(url)

    if parsed_url.hostname:
        return parsed_url.hostname

    if "://" not in url:
        parsed_url = urlparse(f"http://{url}")

        if parsed_url.hostname:
            return parsed_url.hostname

    return ""
