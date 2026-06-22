import json
import unittest
from unittest.mock import patch

from home_cinema_control.devices.oppo.models import OppoCommandResponse
from home_cinema_control.devices.oppo.network_mount_service import (
    OppoNetworkFolder,
    OppoNetworkFolderProtocol,
    OppoNetworkMountService,
    resolve_network_folder_protocol,
)


class FakeControlApiClient:
    def __init__(
        self,
        *,
        device_list_payload=None,
        nfs_mount_responses=None,
        samba_mount_responses=None,
        samba_mount_with_id_responses=None,
        login_response='{"success":true}',
    ):
        self.calls = []
        self._device_list_payload = device_list_payload or {"devicelist": [{"name": "NAS"}]}
        self._login_response = login_response
        self._nfs_mount_responses = list(
            nfs_mount_responses or ['{"success":true,"nfsMntPath":"/mnt/nfs1"}']
        )
        self._samba_mount_responses = list(
            samba_mount_responses or ['{"success":true,"cifsMntPath":"/mnt/cifs1"}']
        )
        self._samba_mount_with_id_responses = list(
            samba_mount_with_id_responses or ['{"success":true,"cifsMntPath":"/mnt/cifs1"}']
        )

    def sign_in(self):
        self.calls.append("sign_in")
        return OppoCommandResponse.from_text('{"success":true}')

    def get_device_list(self):
        self.calls.append("get_device_list")
        return OppoCommandResponse.from_text(json.dumps(self._device_list_payload))

    def send_remote_key(self, key):
        self.calls.append(("send_remote_key", key))
        return OppoCommandResponse.from_text("{}")

    def login_nfs_server(self, server):
        self.calls.append(("login_nfs_server", server))
        return OppoCommandResponse.from_text(self._login_response)

    def login_samba_without_id(self, server):
        self.calls.append(("login_samba_without_id", server))
        return OppoCommandResponse.from_text(self._login_response)

    def mount_nfs_folder(self, *, server, folder, timeout):
        self.calls.append(("mount_nfs_folder", server, folder, timeout))
        return OppoCommandResponse.from_text(self._next(self._nfs_mount_responses))

    def mount_samba_folder(self, *, server, folder, timeout):
        self.calls.append(("mount_samba_folder", server, folder, timeout))
        return OppoCommandResponse.from_text(self._next(self._samba_mount_responses))

    def mount_samba_folder_with_id(self, server, folder, username, password, *, timeout):
        self.calls.append(
            ("mount_samba_folder_with_id", server, folder, username, password, timeout)
        )
        return OppoCommandResponse.from_text(self._next(self._samba_mount_with_id_responses))

    def _build_url(self, endpoint):
        return f"http://oppo.test/{endpoint}"

    @staticmethod
    def _next(responses):
        if len(responses) > 1:
            return responses.pop(0)
        return responses[0]


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


def _config(**oppo_overrides):
    oppo = {"nfs_mount_timeout_seconds": 30, "connection_timeout_seconds": 3, **oppo_overrides}
    return {"oppo": oppo, "smb": {}}


def _nfs_folder(server="NAS", folder="Movies") -> OppoNetworkFolder:
    return OppoNetworkFolder(
        server_name=server, folder_path=folder, protocol=OppoNetworkFolderProtocol.NFS
    )


def _smb_folder(server="NAS", folder="Movies") -> OppoNetworkFolder:
    return OppoNetworkFolder(
        server_name=server, folder_path=folder, protocol=OppoNetworkFolderProtocol.CIFS
    )


@patch("home_cinema_control.devices.oppo.network_mount_service.check_oppo_control_api")
class MountControlApiAndDeviceListTest(unittest.TestCase):
    def test_fails_at_control_api_stage_without_touching_the_device(self, check_control_api):
        check_control_api.return_value = 1
        client = FakeControlApiClient()
        service = OppoNetworkMountService(_config(), control_api_client=client)

        result = service.mount(_nfs_folder())

        self.assertFalse(result.successful)
        self.assertEqual("control_api", result.failure_stage)
        self.assertEqual([], client.calls)

    @patch("home_cinema_control.devices.oppo.network_mount_service.time.sleep")
    def test_fails_at_device_list_stage_when_list_never_populates(
        self, sleep, check_control_api
    ):
        check_control_api.return_value = 0
        client = FakeControlApiClient(device_list_payload={"devicelist": []})
        service = OppoNetworkMountService(_config(), control_api_client=client)

        result = service.mount(_nfs_folder())

        self.assertFalse(result.successful)
        self.assertEqual("device_list", result.failure_stage)
        self.assertEqual(10, client.calls.count("get_device_list"))
        self.assertEqual(10, sleep.call_count)

    @patch("home_cinema_control.devices.oppo.network_mount_service.time.sleep")
    def test_login_failure_stops_before_mounting(self, sleep, check_control_api):
        check_control_api.return_value = 0
        client = FakeControlApiClient(login_response='{"success":false,"retInfo":"no_such_server"}')
        service = OppoNetworkMountService(_config(), control_api_client=client)

        result = service.mount(_nfs_folder())

        self.assertFalse(result.successful)
        self.assertEqual("login", result.failure_stage)
        self.assertEqual("no_such_server", result.detail)
        self.assertNotIn(("mount_nfs_folder", "NAS", "Movies", 30), client.calls)


@patch("home_cinema_control.devices.oppo.network_mount_service.check_oppo_control_api", return_value=0)
class MountSuccessTest(unittest.TestCase):
    def test_mounts_nfs_folder(self, _check_control_api):
        client = FakeControlApiClient()
        service = OppoNetworkMountService(_config(), control_api_client=client)

        result = service.mount(_nfs_folder())

        self.assertTrue(result.successful)
        self.assertEqual("/mnt/nfs1", result.mounted_share.mount_path)
        self.assertIn(("mount_nfs_folder", "NAS", "Movies", 30), client.calls)

    def test_mounts_smb_folder_with_credentials(self, _check_control_api):
        client = FakeControlApiClient()
        config = _config()
        config["smb"] = {"username": "user", "password": "pass"}
        service = OppoNetworkMountService(config, control_api_client=client)

        result = service.mount(_smb_folder())

        self.assertTrue(result.successful)
        self.assertIn(
            ("mount_samba_folder_with_id", "NAS", "Movies", "user", "pass", 30),
            client.calls,
        )

    def test_mounts_smb_folder_anonymously_without_credentials(self, _check_control_api):
        client = FakeControlApiClient()
        service = OppoNetworkMountService(_config(), control_api_client=client)

        result = service.mount(_smb_folder())

        self.assertTrue(result.successful)
        self.assertIn(("mount_samba_folder", "NAS", "Movies", 30), client.calls)


@patch("home_cinema_control.devices.oppo.network_mount_service.check_oppo_control_api", return_value=0)
@patch("home_cinema_control.devices.oppo.network_mount_service.time.sleep")
class MountRetryTest(unittest.TestCase):
    def test_retries_nfs_mount_once_on_timeout(self, sleep, _check_control_api):
        client = FakeControlApiClient(
            nfs_mount_responses=[
                '{"success":false,"retInfo":"Timeout in Mount Request"}',
                '{"success":true,"nfsMntPath":"/mnt/nfs1"}',
            ]
        )
        service = OppoNetworkMountService(_config(), control_api_client=client)

        result = service.mount(_nfs_folder())

        self.assertTrue(result.successful)
        sleep.assert_called_once_with(2)
        self.assertEqual(
            2, client.calls.count(("mount_nfs_folder", "NAS", "Movies", 30))
        )

    def test_retries_smb_mount_once_on_id_error(self, sleep, _check_control_api):
        client = FakeControlApiClient(
            samba_mount_responses=[
                '{"success":false,"retInfo":"id_error"}',
                '{"success":true,"cifsMntPath":"/mnt/cifs1"}',
            ]
        )
        service = OppoNetworkMountService(_config(), control_api_client=client)

        result = service.mount(_smb_folder())

        self.assertTrue(result.successful)
        sleep.assert_called_once_with(2)

    def test_does_not_retry_non_retryable_mount_failure(self, sleep, _check_control_api):
        client = FakeControlApiClient(
            nfs_mount_responses=['{"success":false,"retInfo":"server_not_existed"}'],
        )
        service = OppoNetworkMountService(_config(), control_api_client=client)

        result = service.mount(_nfs_folder())

        self.assertFalse(result.successful)
        self.assertEqual("mount", result.failure_stage)
        self.assertEqual("server_not_existed", result.detail)
        sleep.assert_not_called()
        self.assertEqual(1, client.calls.count(("mount_nfs_folder", "NAS", "Movies", 30)))

    def test_reports_mount_failure_detail_after_exhausting_retry(self, sleep, _check_control_api):
        client = FakeControlApiClient(
            nfs_mount_responses=[
                '{"success":false,"retInfo":"Timeout in Mount Request"}',
                '{"success":false,"retInfo":"Timeout in Mount Request"}',
            ]
        )
        service = OppoNetworkMountService(_config(), control_api_client=client)

        result = service.mount(_nfs_folder())

        self.assertFalse(result.successful)
        self.assertEqual("mount", result.failure_stage)
        self.assertEqual("Timeout in Mount Request", result.detail)


@patch("home_cinema_control.devices.oppo.network_mount_service.check_oppo_control_api", return_value=0)
class MountSmbPrimingTest(unittest.TestCase):
    def test_primes_smb_session_before_mount_when_pre_mount_smb_enabled(self, _check_control_api):
        client = FakeControlApiClient()
        service = OppoNetworkMountService(
            _config(pre_mount_smb=True), control_api_client=client
        )

        with patch(
            "home_cinema_control.devices.oppo.network_mount_service.get_http_session",
            return_value=FakeHttpSession([FakeHttpResponse(["Other"])]),
        ):
            result = service.mount(_smb_folder())

        self.assertTrue(result.successful)
        self.assertIn(("mount_samba_folder", "NAS", "Other", 30), client.calls)

    def test_does_not_prime_when_pre_mount_smb_disabled(self, _check_control_api):
        client = FakeControlApiClient()
        service = OppoNetworkMountService(
            _config(pre_mount_smb=False), control_api_client=client
        )

        result = service.mount(_smb_folder())

        self.assertTrue(result.successful)
        self.assertNotIn(("mount_samba_folder", "NAS", "Other", 30), client.calls)

    def test_does_not_prime_for_nfs_even_when_pre_mount_smb_enabled(self, _check_control_api):
        client = FakeControlApiClient()
        service = OppoNetworkMountService(
            _config(pre_mount_smb=True), control_api_client=client
        )

        result = service.mount(_nfs_folder())

        self.assertTrue(result.successful)
        self.assertEqual(
            [call for call in client.calls if "samba" in str(call).lower()], []
        )

    def test_does_not_log_in_twice_when_priming_the_same_server(self, _check_control_api):
        # Regression test: priming used to re-log-in to the same server it had
        # just logged into via _login(), doubling the OPPO HTTP round-trips for
        # every SMB mount. The OPPO's embedded HTTP server (port 436) cannot
        # reliably absorb that many back-to-back calls (see OPPO_DEVICE_LOCK's
        # docstring).
        client = FakeControlApiClient()
        service = OppoNetworkMountService(
            _config(pre_mount_smb=True), control_api_client=client
        )

        with patch(
                "home_cinema_control.devices.oppo.network_mount_service.get_http_session",
                return_value=FakeHttpSession([FakeHttpResponse(["Other"])]),
        ):
            result = service.mount(_smb_folder())

        self.assertTrue(result.successful)
        login_calls = [call for call in client.calls if call == ("login_samba_without_id", "NAS")]
        self.assertEqual(1, len(login_calls))


class PrimeSambaMountTest(unittest.TestCase):
    """_prime_samba_mount assumes the caller already logged into `server` —
    these tests call it directly without a prior login, matching that
    contract (see mount(), which calls _login() right before priming)."""

    def test_mounts_a_different_folder_on_the_same_server_when_one_exists(self):
        client = FakeControlApiClient()
        service = OppoNetworkMountService(_config(), control_api_client=client)

        with patch(
            "home_cinema_control.devices.oppo.network_mount_service.get_http_session",
            return_value=FakeHttpSession([FakeHttpResponse(["Video", "Music"])]),
        ):
            service._prime_samba_mount("NAS", "Video")

        self.assertEqual(
            [("mount_samba_folder", "NAS", "Music", 30)],
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
        service = OppoNetworkMountService(_config(), control_api_client=client)

        with patch(
            "home_cinema_control.devices.oppo.network_mount_service.get_http_session",
            return_value=FakeHttpSession(
                [
                    FakeHttpResponse(["Video"]),  # only the target folder on NAS
                    FakeHttpResponse(["Movies"]),  # OTHERNAS has an alternate
                ]
            ),
        ):
            service._prime_samba_mount("NAS", "Video")

        self.assertEqual(
            [
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
        service = OppoNetworkMountService(_config(), control_api_client=client)

        with patch(
            "home_cinema_control.devices.oppo.network_mount_service.get_http_session",
            return_value=FakeHttpSession(
                [
                    FakeHttpResponse(["Video"]),
                    FakeHttpResponse(["Movies"]),
                ]
            ),
        ):
            service._prime_samba_mount("NAS", "Video")

        self.assertNotIn(("login_samba_without_id", "NFS-BOX"), client.calls)
        self.assertEqual(
            [
                "get_device_list",
                ("login_samba_without_id", "OTHERNAS"),
                ("mount_samba_folder", "OTHERNAS", "Movies", 30),
            ],
            client.calls,
        )


class ResolveNetworkFolderProtocolTest(unittest.TestCase):
    def test_explicit_nfs_wins(self):
        self.assertEqual(
            OppoNetworkFolderProtocol.NFS,
            resolve_network_folder_protocol({"oppo": {"use_smb": True}}, "nfs"),
        )

    def test_explicit_smb_wins(self):
        self.assertEqual(
            OppoNetworkFolderProtocol.CIFS,
            resolve_network_folder_protocol({"oppo": {"use_smb": False}}, "smb"),
        )

    def test_falls_back_to_config_when_protocol_not_given(self):
        self.assertEqual(
            OppoNetworkFolderProtocol.CIFS,
            resolve_network_folder_protocol({"oppo": {"use_smb": True}}, None),
        )
        self.assertEqual(
            OppoNetworkFolderProtocol.NFS,
            resolve_network_folder_protocol({"oppo": {"use_smb": False}}, None),
        )


if __name__ == "__main__":
    unittest.main()
