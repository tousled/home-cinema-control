import unittest
from unittest.mock import MagicMock, patch

import home_cinema_control.devices.tv.adapters.samsung as samsung_mod
from home_cinema_control.devices.tv.adapters.samsung import (
    EMBY_APP_IDS,
    JELLYFIN_APP_ID,
    SAMSUNG_TOKEN_FILE_PATH,
    SamsungTvController,
    _STATIC_HDMI_INPUTS,
)
from home_cinema_control.devices.tv.factory import TV_CONTROLLERS, create_tv_controller
from home_cinema_control.playback.startup.models import DeviceCommandStatus


def _controller(ip="192.168.1.50"):
    return SamsungTvController({"tv": {"ip": ip}})


class SamsungFactoryTest(unittest.TestCase):
    def test_samsung_registered_in_tv_controllers(self):
        self.assertIn("SAMSUNG", TV_CONTROLLERS)
        self.assertIs(TV_CONTROLLERS["SAMSUNG"], SamsungTvController)

    def test_create_tv_controller_returns_samsung_instance(self):
        controller = create_tv_controller({"tv": {"model": "SAMSUNG", "ip": "192.168.1.50"}})
        self.assertIsInstance(controller, SamsungTvController)


class SamsungRetrieveHdmiInputsTest(unittest.TestCase):
    def test_writes_four_static_inputs_to_config(self):
        config = {"tv": {"ip": "192.168.1.50"}}
        controller = SamsungTvController(config)
        result = controller.retrieve_hdmi_inputs()
        self.assertTrue(result.successful)
        inputs = config["tv"]["available_hdmi_inputs"]
        self.assertEqual(4, len(inputs))

    def test_static_inputs_have_key_codes_and_names(self):
        config = {"tv": {"ip": "192.168.1.50"}}
        SamsungTvController(config).retrieve_hdmi_inputs()
        inputs = config["tv"]["available_hdmi_inputs"]
        ids = [i["id"] for i in inputs]
        self.assertEqual(["KEY_HDMI1", "KEY_HDMI2", "KEY_HDMI3", "KEY_HDMI4"], ids)
        for entry in inputs:
            self.assertIn("nombre", entry)

    def test_does_not_mutate_shared_constant(self):
        config = {"tv": {"ip": "192.168.1.50"}}
        SamsungTvController(config).retrieve_hdmi_inputs()
        config["tv"]["available_hdmi_inputs"].append({"id": "extra"})
        self.assertEqual(4, len(_STATIC_HDMI_INPUTS))


class SamsungMediaServerAppIdTest(unittest.TestCase):
    def test_emby_returns_primary_id(self):
        self.assertEqual(EMBY_APP_IDS[0], _controller().media_server_app_id("emby"))

    def test_jellyfin_returns_id(self):
        self.assertEqual(JELLYFIN_APP_ID, _controller().media_server_app_id("jellyfin"))

    def test_unknown_provider_returns_none(self):
        self.assertIsNone(_controller().media_server_app_id("plex"))


class SamsungLaunchAppTest(unittest.TestCase):
    def test_none_app_id_returns_skipped(self):
        result = _controller().launch_app(None)
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.status)

    def test_none_app_id_does_not_call_rest(self):
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            _controller().launch_app(None)
            mock_cls.assert_not_called()

    def test_emby_primary_id_succeeds(self):
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            result = _controller().launch_app(EMBY_APP_IDS[0])
        self.assertTrue(result.successful)
        mock_instance.rest_app_run.assert_called_once_with(EMBY_APP_IDS[0])

    def test_emby_falls_back_to_secondary_id_on_failure(self):
        calls = []

        def fake_rest_app_run(app_id):
            calls.append(app_id)
            if app_id == EMBY_APP_IDS[0]:
                raise Exception("not found")

        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.rest_app_run.side_effect = fake_rest_app_run
            mock_cls.return_value = mock_instance
            result = _controller().launch_app(EMBY_APP_IDS[0])

        self.assertTrue(result.successful)
        self.assertEqual([EMBY_APP_IDS[0], EMBY_APP_IDS[1]], calls)

    def test_jellyfin_failure_does_not_fallback(self):
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.rest_app_run.side_effect = Exception("not found")
            mock_cls.return_value = mock_instance
            result = _controller().launch_app(JELLYFIN_APP_ID)

        self.assertFalse(result.successful)
        mock_instance.rest_app_run.assert_called_once_with(JELLYFIN_APP_ID)


class SamsungConnectedClientTokenTest(unittest.TestCase):
    """_connected_client must pass token_file so the token is persisted after first pairing."""

    def setUp(self):
        samsung_mod._port_cache["192.168.1.50"] = samsung_mod.SAMSUNG_PORT_SSL

    def tearDown(self):
        samsung_mod._port_cache.clear()

    def test_connected_client_passes_token_file(self):
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            controller = SamsungTvController({"tv": {"ip": "192.168.1.50"}})
            with controller._connected_client():
                pass
        _, kwargs = mock_cls.call_args
        self.assertEqual(SAMSUNG_TOKEN_FILE_PATH, kwargs.get("token_file"))


class SamsungPortDetectTokenTest(unittest.TestCase):
    """_detect_port must pass token_file so the TV doesn't show a pairing dialog every time."""

    def setUp(self):
        samsung_mod._port_cache.clear()

    def tearDown(self):
        samsung_mod._port_cache.clear()

    def test_detect_port_passes_token_file(self):
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            controller = SamsungTvController({"tv": {"ip": "192.168.1.50"}})
            controller._detect_port("192.168.1.50")
        _, kwargs = mock_cls.call_args
        self.assertEqual(SAMSUNG_TOKEN_FILE_PATH, kwargs.get("token_file"))

    def test_detect_port_caches_result(self):
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            controller = SamsungTvController({"tv": {"ip": "192.168.1.50"}})
            controller._detect_port("192.168.1.50")
            controller._detect_port("192.168.1.50")
        # SamsungTVWS should only be instantiated once despite two calls
        self.assertEqual(1, mock_cls.call_count)

    def test_detect_port_falls_back_when_both_fail(self):
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.open.side_effect = OSError("refused")
            mock_cls.return_value = mock_instance
            controller = SamsungTvController({"tv": {"ip": "192.168.1.50"}})
            port = controller._detect_port("192.168.1.50")
        from home_cinema_control.devices.tv.adapters.samsung import SAMSUNG_PORT_SSL
        self.assertEqual(SAMSUNG_PORT_SSL, port)


class SamsungMissingIpTest(unittest.TestCase):
    def test_test_connection_with_empty_ip_returns_failure(self):
        controller = SamsungTvController({"tv": {}})
        result = controller.test_connection()
        self.assertFalse(result.successful)
        self.assertIn("tv.ip", result.detail)

    def test_switch_to_input_with_empty_ip_returns_failure(self):
        from home_cinema_control.devices.tv.models import TvInputTarget
        controller = SamsungTvController({"tv": {}})
        result = controller.switch_to_input(TvInputTarget(input_id="KEY_HDMI1"))
        self.assertFalse(result.successful)
        self.assertIn("tv.ip", result.detail)

    def test_launch_app_with_empty_ip_returns_failure(self):
        controller = SamsungTvController({"tv": {}})
        result = controller.launch_app(JELLYFIN_APP_ID)
        self.assertFalse(result.successful)
        self.assertIn("tv.ip", result.detail)

    def test_switch_to_input_with_empty_input_id_returns_failure(self):
        from home_cinema_control.devices.tv.models import TvInputTarget
        controller = SamsungTvController({"tv": {"ip": "192.168.1.50"}})
        result = controller.switch_to_input(TvInputTarget(input_id=""))
        self.assertFalse(result.successful)


if __name__ == "__main__":
    unittest.main()
