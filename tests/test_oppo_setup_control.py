import unittest
from unittest.mock import patch

from home_cinema_control.devices.oppo.models import OppoCommandResponse
from home_cinema_control.devices.oppo.mounted_share import OppoMountedShare
from home_cinema_control.devices.oppo.setup_control import (
    _control_api_attempts,
    list_mounted_folder_files,
    list_nfs_share_folders,
    mount_smb_share,
)


class OppoSetupControlTest(unittest.TestCase):
    def test_control_api_attempts_default_to_three_when_not_configured(self):
        self.assertEqual(3, _control_api_attempts({"oppo": {"connection_timeout_seconds": 10}}))

    def test_control_api_attempts_can_be_configured(self):
        self.assertEqual(5, _control_api_attempts({"oppo": {"api_retry_attempts": 5}}))

    def test_control_api_attempts_never_go_below_one(self):
        self.assertEqual(1, _control_api_attempts({"oppo": {"api_retry_attempts": 0}}))


class FakeSambaMountClient:
    def __init__(self, responses):
        self.calls = []
        self._responses = list(responses)

    def mount_samba_folder(self, *, server, folder, timeout):
        self.calls.append(("mount_samba_folder", server, folder, timeout))
        return OppoCommandResponse.from_text(self._next_response())

    def mount_samba_folder_with_id(self, *, server, folder, username, password, timeout):
        self.calls.append(
            ("mount_samba_folder_with_id", server, folder, username, password, timeout)
        )
        return OppoCommandResponse.from_text(self._next_response())

    def _next_response(self):
        if len(self._responses) > 1:
            return self._responses.pop(0)
        return self._responses[0]


class FakeHttpResponse:
    content = b"\x00Movies\x01\x00Series\x01"
    text = "Movies Series"


class FakeHttpSession:
    def __init__(self):
        self.urls = []

    def get(self, url, headers):
        self.urls.append(url)
        return FakeHttpResponse()


class OppoFolderBrowsingTest(unittest.TestCase):
    @patch("home_cinema_control.devices.oppo.setup_control.get_http_session")
    def test_lists_nfs_share_folders_via_oppo_endpoint(self, get_http_session):
        session = FakeHttpSession()
        get_http_session.return_value = session

        result = list_nfs_share_folders({"oppo": {"ip": "192.168.1.20"}})

        self.assertEqual(
            [
                {"Id": 0, "Foldername": ".."},
                {"Id": 1, "Foldername": "Movies"},
                {"Id": 2, "Foldername": "Series"},
            ],
            result,
        )
        self.assertEqual("oppo-setup", get_http_session.call_args.args[0])
        self.assertIn("/getNfsShareFolderlist", session.urls[0])

    @patch("home_cinema_control.devices.oppo.setup_control.get_http_session")
    def test_lists_mounted_folder_files_via_getfilelist_endpoint(self, get_http_session):
        session = FakeHttpSession()
        get_http_session.return_value = session

        result = list_mounted_folder_files(
            {"oppo": {"ip": "192.168.1.20"}},
            "/",
            OppoMountedShare(server="NAS", folder="Video", mount_path="/mnt/nfs1", is_nfs=True),
        )

        self.assertEqual("Movies", result[1]["Foldername"])
        self.assertEqual("oppo-setup", get_http_session.call_args.args[0])
        self.assertIn("/getfilelist?", session.urls[0])


class MountSmbShareIdErrorRetryTest(unittest.TestCase):
    @patch("home_cinema_control.devices.oppo.setup_control.time.sleep")
    @patch("home_cinema_control.devices.oppo.setup_control.create_oppo_control_client")
    def test_retries_once_on_id_error_with_credentials(self, get_client, sleep):
        client = FakeSambaMountClient(
            [
                '{"success":false,"retInfo":"id_error"}',
                '{"success":true,"cifsMntPath":"/mnt/cifs1"}',
            ]
        )
        get_client.return_value = client
        config = {
            "oppo": {"pre_mount_smb": False, "nfs_mount_timeout_seconds": 30},
            "smb": {"username": "guest", "password": ""},
        }

        result = mount_smb_share("NAS-SERVER", "Video", config)

        self.assertTrue(result.is_successful)
        sleep.assert_called_once_with(2)
        self.assertEqual(
            [
                ("mount_samba_folder_with_id", "NAS-SERVER", "Video", "guest", "", 30),
                ("mount_samba_folder_with_id", "NAS-SERVER", "Video", "guest", "", 30),
            ],
            client.calls,
        )

    @patch("home_cinema_control.devices.oppo.setup_control.time.sleep")
    @patch("home_cinema_control.devices.oppo.setup_control.create_oppo_control_client")
    def test_retries_once_on_id_error_for_anonymous_mount(self, get_client, sleep):
        client = FakeSambaMountClient(
            [
                '{"success":false,"retInfo":"id_error"}',
                '{"success":true,"cifsMntPath":"/mnt/cifs1"}',
            ]
        )
        get_client.return_value = client
        config = {
            "oppo": {"pre_mount_smb": False, "nfs_mount_timeout_seconds": 30},
            "smb": {"username": "", "password": ""},
        }

        result = mount_smb_share("NAS-SERVER", "Video", config)

        self.assertTrue(result.is_successful)
        sleep.assert_called_once_with(2)
        self.assertEqual(
            [
                ("mount_samba_folder", "NAS-SERVER", "Video", 30),
                ("mount_samba_folder", "NAS-SERVER", "Video", 30),
            ],
            client.calls,
        )

    @patch("home_cinema_control.devices.oppo.setup_control.time.sleep")
    @patch("home_cinema_control.devices.oppo.setup_control.create_oppo_control_client")
    def test_does_not_retry_for_non_id_error_failures(self, get_client, sleep):
        client = FakeSambaMountClient(['{"success":false,"retInfo":"server_not_existed"}'])
        get_client.return_value = client
        config = {
            "oppo": {"pre_mount_smb": False, "nfs_mount_timeout_seconds": 30},
            "smb": {"username": "guest", "password": ""},
        }

        result = mount_smb_share("NAS-SERVER", "Video", config)

        self.assertFalse(result.is_successful)
        sleep.assert_not_called()
        self.assertEqual(
            [("mount_samba_folder_with_id", "NAS-SERVER", "Video", "guest", "", 30)],
            client.calls,
        )


if __name__ == "__main__":
    unittest.main()
