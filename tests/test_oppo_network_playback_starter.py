import json
import unittest
from unittest.mock import patch

from home_cinema_control.devices.oppo.models import OppoCommandResponse
from home_cinema_control.devices.oppo.network_playback_starter import (
    OppoNetworkPlaybackStarter,
)


class FakeControlApiClient:
    def __init__(self, *, device_list_payload=None):
        self.calls = []
        self._device_list_payload = device_list_payload or {"devicelist": []}

    def login_samba_without_id(self, server):
        self.calls.append(("login_samba_without_id", server))
        return OppoCommandResponse.from_text('{"success":true}')

    def get_device_list(self):
        self.calls.append("get_device_list")
        return OppoCommandResponse.from_text(json.dumps(self._device_list_payload))

    def mount_samba_folder(self, *, server, folder, timeout):
        self.calls.append(("mount_samba_folder", server, folder, timeout))
        return OppoCommandResponse.from_text('{"success":true,"cifsMntPath":"/mnt"}')

    def _build_url(self, endpoint):
        return f"http://oppo.test/{endpoint}"


class FakeHttpResponse:
    def __init__(self, folder_names):
        self.content = b"\x01".join(
            b"\x00" + name.encode("utf-8") for name in folder_names
        )
        self.text = self.content.decode("utf-8", errors="replace")


class FakeHttpSession:
    def __init__(self, responses):
        self._responses = list(responses)

    def get(self, url, **kwargs):
        return self._responses.pop(0)


def _config():
    return {"oppo": {"nfs_mount_timeout_seconds": 30, "connection_timeout_seconds": 3}}


class PrimeSambaMountTest(unittest.TestCase):
    def test_mounts_a_different_folder_on_the_same_server_when_one_exists(self):
        client = FakeControlApiClient()
        starter = OppoNetworkPlaybackStarter(_config(), control_api_client=client)

        with patch(
            "home_cinema_control.devices.oppo.network_playback_starter.get_http_session",
            return_value=FakeHttpSession([FakeHttpResponse(["Video", "Music"])]),
        ):
            starter.prime_samba_mount("NAS", "Video")

        self.assertEqual(
            [
                ("login_samba_without_id", "NAS"),
                ("mount_samba_folder", "NAS", "Music", 30),
            ],
            client.calls,
        )

    def test_falls_back_to_another_cifs_device_when_no_alternate_folder_exists(self):
        client = FakeControlApiClient(
            device_list_payload={
                "devicelist": [
                    {"name": "NAS", "sub_type": "cifs"},
                    {"name": "OTHERNAS", "sub_type": "cifs"},
                ]
            }
        )
        starter = OppoNetworkPlaybackStarter(_config(), control_api_client=client)

        with patch(
            "home_cinema_control.devices.oppo.network_playback_starter.get_http_session",
            return_value=FakeHttpSession(
                [
                    FakeHttpResponse(["Video"]),  # only the target folder on NAS
                    FakeHttpResponse(["Movies"]),  # OTHERNAS has an alternate
                ]
            ),
        ):
            starter.prime_samba_mount("NAS", "Video")

        self.assertEqual(
            [
                ("login_samba_without_id", "NAS"),
                "get_device_list",
                ("login_samba_without_id", "OTHERNAS"),
                ("mount_samba_folder", "OTHERNAS", "Movies", 30),
            ],
            client.calls,
        )

    def test_skips_non_cifs_devices_when_falling_back(self):
        client = FakeControlApiClient(
            device_list_payload={
                "devicelist": [
                    {"name": "NAS", "sub_type": "cifs"},
                    {"name": "NFS-BOX", "sub_type": "nfs"},
                    {"name": "OTHERNAS", "sub_type": "cifs"},
                ]
            }
        )
        starter = OppoNetworkPlaybackStarter(_config(), control_api_client=client)

        with patch(
            "home_cinema_control.devices.oppo.network_playback_starter.get_http_session",
            return_value=FakeHttpSession(
                [
                    FakeHttpResponse(["Video"]),
                    FakeHttpResponse(["Movies"]),
                ]
            ),
        ):
            starter.prime_samba_mount("NAS", "Video")

        self.assertNotIn(("login_samba_without_id", "NFS-BOX"), client.calls)
        self.assertEqual(
            [
                ("login_samba_without_id", "NAS"),
                "get_device_list",
                ("login_samba_without_id", "OTHERNAS"),
                ("mount_samba_folder", "OTHERNAS", "Movies", 30),
            ],
            client.calls,
        )


if __name__ == "__main__":
    unittest.main()
