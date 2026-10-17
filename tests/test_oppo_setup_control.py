import unittest
from unittest.mock import patch

from home_cinema_control.devices.oppo.models import OppoCommandResponse
from home_cinema_control.devices.oppo.mounted_share import OppoMountedShare
from home_cinema_control.devices.oppo.network_mount_service import OppoMountResult
from home_cinema_control.devices.oppo.setup_control import (
    _parse_oppo_folder_entries,
    _parse_oppo_listing_records,
    browse_network_folder,
    list_mounted_folder_files,
    list_nfs_share_folders,
)


class FakeHttpResponse:
    content = b"\x00Movies\x01\x00Series\x01"
    text = "Movies Series"


class FakeHttpSession:
    def __init__(self):
        self.urls = []

    def get(self, url, headers):
        self.urls.append(url)
        return FakeHttpResponse()


def _oppo_record(name, entry_type, extra=1):
    raw_name = name.encode("utf-8")
    return (
        len(raw_name).to_bytes(4, "little")
        + raw_name
        + entry_type.to_bytes(4, "little")
        + extra.to_bytes(4, "little")
    )


class OppoListingRecordsTest(unittest.TestCase):
    def _folder_names(self, content):
        return [
            entry["Foldername"]
            for entry in _parse_oppo_folder_entries(content)
        ]

    def test_lists_one_and_two_character_folder_names(self):
        listing = (
            b"FLAG"
            + _oppo_record("BR", 1)
            + _oppo_record("DVD", 1)
            + _oppo_record("HD", 1)
            + _oppo_record("X", 1)
            + _oppo_record("movie.mkv", 2)
            + (4).to_bytes(4, "little")
            + (4).to_bytes(4, "little")
        )

        self.assertEqual(
            ["..", "BR", "DVD", "HD", "X"],
            self._folder_names(listing),
        )

    def test_parses_share_listing_without_optional_header(self):
        listing = (
            b"\t\x00\x00\x00e/library"
            + b"\x01\x00\x00\x00\x05\x00\x00\x00"
        )

        self.assertEqual(["..", "e/library"], self._folder_names(listing))

    def test_falls_back_to_marker_parser_for_unknown_payloads(self):
        self.assertEqual(
            ["..", "Movies", "Series"],
            self._folder_names(b"\x00Movies\x01\x00Series\x01"),
        )

    def test_falls_back_when_structured_record_is_truncated(self):
        malformed_listing = b"FLAG" + (3).to_bytes(4, "little") + b"BR"

        self.assertIsNone(_parse_oppo_listing_records(malformed_listing))
        self.assertEqual(["..", "BR"], self._folder_names(malformed_listing))


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


class BrowseNetworkFolderControlApiActivationTest(unittest.TestCase):
    @patch("home_cinema_control.devices.oppo.setup_control.get_oppo_device_list")
    @patch("home_cinema_control.devices.oppo.setup_control.check_oppo_control_api")
    def test_raises_without_calling_oppo_when_control_api_is_unavailable(
            self, check_control_api, get_device_list
    ):
        check_control_api.return_value = 1

        with self.assertRaises(RuntimeError):
            browse_network_folder("/", {"oppo": {"ip": "192.168.1.20"}})

        get_device_list.assert_not_called()

    @patch("home_cinema_control.devices.oppo.setup_control.get_oppo_device_list")
    @patch("home_cinema_control.devices.oppo.setup_control.check_oppo_control_api")
    def test_lists_devices_once_control_api_is_available(
            self, check_control_api, get_device_list
    ):
        check_control_api.return_value = 0
        get_device_list.return_value = OppoCommandResponse.from_text(
            '{"devicelist":[{"name":"NAS"}]}'
        )

        result = browse_network_folder("/", {"oppo": {"ip": "192.168.1.20"}})

        self.assertEqual([{"Id": 1, "Foldername": "NAS"}], result)
        get_device_list.assert_called_once()


class BrowseNetworkFolderMountTest(unittest.TestCase):
    """The deepest browse level (navigating into a folder) delegates the full
    activate/login/mount/retry sequence to OppoNetworkMountService — covered
    in detail in test_oppo_network_mount_service.py. These tests only check
    that browse_network_folder wires into it correctly."""

    @patch("home_cinema_control.devices.oppo.setup_control.list_mounted_folder_files")
    @patch("home_cinema_control.devices.oppo.setup_control.OppoNetworkMountService")
    @patch("home_cinema_control.devices.oppo.setup_control.get_oppo_device_list")
    @patch("home_cinema_control.devices.oppo.setup_control.check_oppo_control_api", return_value=0)
    def test_lists_mounted_folder_files_on_successful_mount(
            self, _check_control_api, get_device_list, mount_service_cls, list_files
    ):
        get_device_list.return_value = OppoCommandResponse.from_text(
            '{"devicelist":[{"name":"NAS"}]}'
        )
        mounted_share = OppoMountedShare(
            server="NAS", folder="Movies", mount_path="/mnt/nfs1", is_nfs=True
        )
        mount_service = mount_service_cls.return_value
        mount_service.mount.return_value = OppoMountResult(
            successful=True, mounted_share=mounted_share, failure_stage=None, detail=""
        )
        list_files.return_value = ["Movie.mkv"]

        result = browse_network_folder(
            "/NAS/Movies", {"oppo": {"ip": "192.168.1.20", "use_smb": False}}
        )

        self.assertEqual(["Movie.mkv"], result)
        mount_service.mount.assert_called_once()
        called_folder = mount_service.mount.call_args.args[0]
        self.assertEqual("NAS", called_folder.server_name)
        self.assertEqual("Movies", called_folder.folder_path)

    @patch("home_cinema_control.devices.oppo.setup_control.OppoNetworkMountService")
    @patch("home_cinema_control.devices.oppo.setup_control.get_oppo_device_list")
    @patch("home_cinema_control.devices.oppo.setup_control.check_oppo_control_api", return_value=0)
    def test_raises_login_failed_when_login_stage_fails(
            self, _check_control_api, get_device_list, mount_service_cls
    ):
        get_device_list.return_value = OppoCommandResponse.from_text(
            '{"devicelist":[{"name":"NAS"}]}'
        )
        mount_service = mount_service_cls.return_value
        mount_service.mount.return_value = OppoMountResult(
            successful=False, mounted_share=None, failure_stage="login", detail="unknown error"
        )

        with self.assertRaisesRegex(RuntimeError, "Login failed"):
            browse_network_folder(
                "/NAS/Movies", {"oppo": {"ip": "192.168.1.20", "use_smb": False}}
            )

    @patch("home_cinema_control.devices.oppo.setup_control.OppoNetworkMountService")
    @patch("home_cinema_control.devices.oppo.setup_control.get_oppo_device_list")
    @patch("home_cinema_control.devices.oppo.setup_control.check_oppo_control_api", return_value=0)
    def test_raises_mount_failed_when_mount_stage_fails(
            self, _check_control_api, get_device_list, mount_service_cls
    ):
        get_device_list.return_value = OppoCommandResponse.from_text(
            '{"devicelist":[{"name":"NAS"}]}'
        )
        mount_service = mount_service_cls.return_value
        mount_service.mount.return_value = OppoMountResult(
            successful=False,
            mounted_share=None,
            failure_stage="mount",
            detail="Timeout in Mount Request",
        )

        with self.assertRaisesRegex(RuntimeError, "Mount failed"):
            browse_network_folder(
                "/NAS/Movies", {"oppo": {"ip": "192.168.1.20", "use_smb": False}}
            )


if __name__ == "__main__":
    unittest.main()
