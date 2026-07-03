import unittest
from unittest.mock import MagicMock, patch

from home_cinema_control.config.manager import sanitize_config_for_web
from home_cinema_control.config.models import SonyTvConfig, TvConfig
from home_cinema_control.devices.tv.adapters.sony import SonyTvController
from home_cinema_control.devices.tv.factory import create_tv_controller
from home_cinema_control.devices.tv.models import TvInputTarget
from home_cinema_control.playback.startup.models import DeviceCommandStatus


def _config(**tv_overrides):
    tv = {"model": "SONY", "ip": "10.0.0.5", "sony_psk": "psk123", "enabled": True}
    tv.update(tv_overrides)
    return {"tv": tv}


def _response(payload, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.raise_for_status = MagicMock()
    response.json.return_value = payload
    return response


class SonyConfigSchemaTest(unittest.TestCase):
    def test_sony_tv_config_inherits_generic_fields(self):
        config = SonyTvConfig(ip="10.0.0.5", mac="aa:bb", available_hdmi_inputs=[{"id": "x"}])
        self.assertEqual("10.0.0.5", config.ip)
        self.assertEqual("aa:bb", config.mac)
        self.assertEqual({}, config.sony_app_uris)

    def test_plain_tv_config_has_no_sony_app_uris_attribute(self):
        config = TvConfig(ip="10.0.0.6")
        self.assertFalse(hasattr(config, "sony_app_uris"))

    def test_sony_tv_config_round_trips_app_uris(self):
        config = SonyTvConfig.model_validate({
            "ip": "10.0.0.5",
            "sony_app_uris": {"emby": "com.sony.dtv.tv.emby.embyatv.MainActivity"},
        })
        self.assertEqual(
            "com.sony.dtv.tv.emby.embyatv.MainActivity",
            config.sony_app_uris["emby"],
        )


class SonyFactoryTest(unittest.TestCase):
    def test_factory_produces_sony_tv_controller(self):
        controller = create_tv_controller(_config())
        self.assertIsInstance(controller, SonyTvController)


class SonyCallTest(unittest.TestCase):
    def test_call_raises_before_any_http_request_when_ip_missing(self):
        controller = SonyTvController(_config(ip=""))
        with patch("home_cinema_control.devices.tv.adapters.sony.requests.post") as post:
            with self.assertRaises(ValueError):
                controller._call("system", "getPowerStatus")
            post.assert_not_called()

    def test_call_raises_before_any_http_request_when_psk_missing(self):
        controller = SonyTvController(_config(sony_psk=""))
        with patch("home_cinema_control.devices.tv.adapters.sony.requests.post") as post:
            with self.assertRaises(ValueError):
                controller._call("system", "getPowerStatus")
            post.assert_not_called()

    def test_call_attaches_psk_header(self):
        controller = SonyTvController(_config())
        with patch(
            "home_cinema_control.devices.tv.adapters.sony.requests.post",
            return_value=_response({"result": []}),
        ) as post:
            controller._call("system", "getPowerStatus")

        self.assertEqual("psk123", post.call_args.kwargs["headers"]["X-Auth-PSK"])

    def test_call_raises_oserror_on_json_rpc_error(self):
        controller = SonyTvController(_config())
        with patch(
            "home_cinema_control.devices.tv.adapters.sony.requests.post",
            return_value=_response({"error": [1, "Illegal State"]}),
        ):
            with self.assertRaises(OSError):
                controller._call("avContent", "getPlayingContentInfo")


class SonyTestConnectionTest(unittest.TestCase):
    def test_success(self):
        controller = SonyTvController(_config())
        with patch(
            "home_cinema_control.devices.tv.adapters.sony.requests.post",
            return_value=_response({"result": [{}]}),
        ):
            result = controller.test_connection()
        self.assertEqual(DeviceCommandStatus.SUCCESS, result.status)

    def test_missing_ip_fails_without_http_call(self):
        controller = SonyTvController(_config(ip=""))
        with patch("home_cinema_control.devices.tv.adapters.sony.requests.post") as post:
            result = controller.test_connection()
        self.assertEqual(DeviceCommandStatus.FAILED, result.status)
        post.assert_not_called()


class SonyRetrieveHdmiInputsTest(unittest.TestCase):
    def test_filters_to_hdmi_sources_only(self):
        payload = {
            "result": [[
                {"uri": "extInput:hdmi?port=1", "title": "HDMI 1", "connectivity": True},
                {"uri": "extInput:hdmi?port=2", "title": "HDMI 2", "connectivity": False},
                {"uri": "extInput:component?port=1", "title": "Component 1"},
            ]]
        }
        config = _config()
        controller = SonyTvController(config)
        with patch(
            "home_cinema_control.devices.tv.adapters.sony.requests.post",
            return_value=_response(payload),
        ):
            result = controller.retrieve_hdmi_inputs()

        self.assertEqual(DeviceCommandStatus.SUCCESS, result.status)
        inputs = config["tv"]["available_hdmi_inputs"]
        self.assertEqual(2, len(inputs))
        self.assertEqual("extInput:hdmi?port=1", inputs[0]["id"])
        self.assertEqual("HDMI 2", inputs[1]["nombre"])
        self.assertFalse(inputs[1]["connected"])


class SonySwitchToInputTest(unittest.TestCase):
    def test_sends_exact_uri_and_confirms(self):
        target = TvInputTarget(input_id="extInput:hdmi?port=2")
        controller = SonyTvController(_config())

        confirm_response = _response({"result": [{"uri": "extInput:hdmi?port=2"}]})
        with patch(
            "home_cinema_control.devices.tv.adapters.sony.requests.post",
            return_value=confirm_response,
        ) as post:
            result = controller.switch_to_input(target)

        self.assertEqual(DeviceCommandStatus.SUCCESS, result.status)
        set_play_content_call = post.call_args_list[0]
        self.assertEqual(
            [{"uri": "extInput:hdmi?port=2"}],
            set_play_content_call.kwargs["json"]["params"],
        )

    def test_illegal_state_during_confirmation_does_not_fail_successful_switch(self):
        target = TvInputTarget(input_id="extInput:hdmi?port=3")
        controller = SonyTvController(_config())

        switched = _response({"result": [{}]})
        illegal_state = _response({"error": [7, "Illegal State"]})
        with patch(
            "home_cinema_control.devices.tv.adapters.sony.requests.post",
            side_effect=[switched, illegal_state],
        ), self.assertLogs(level="INFO") as logs:
            result = controller.switch_to_input(target)

        self.assertEqual(DeviceCommandStatus.SUCCESS, result.status)
        self.assertIn(
            "Sony HDMI input confirmation unavailable after switch",
            "\n".join(logs.output),
        )

    def test_missing_input_id_fails(self):
        controller = SonyTvController(_config())
        result = controller.switch_to_input(TvInputTarget(input_id=""))
        self.assertEqual(DeviceCommandStatus.FAILED, result.status)


class SonyLaunchAppTest(unittest.TestCase):
    def test_none_app_id_is_skipped_without_http_call(self):
        controller = SonyTvController(_config())
        with patch("home_cinema_control.devices.tv.adapters.sony.requests.post") as post:
            result = controller.launch_app(None)
        self.assertEqual(DeviceCommandStatus.SKIPPED, result.status)
        post.assert_not_called()

    def test_launches_with_discovered_uri(self):
        controller = SonyTvController(_config())
        app_uri = "com.sony.dtv.tv.emby.embyatv.MainActivity"
        with patch(
            "home_cinema_control.devices.tv.adapters.sony.requests.post",
            return_value=_response({"result": [{}]}),
        ) as post:
            result = controller.launch_app(app_uri)

        self.assertEqual(DeviceCommandStatus.SUCCESS, result.status)
        self.assertEqual([{"uri": app_uri}], post.call_args.kwargs["json"]["params"])


class SonyGetCurrentAppIdTest(unittest.TestCase):
    def test_returns_none_when_on_hdmi_input(self):
        controller = SonyTvController(_config())
        payload = {"result": [{"uri": "extInput:hdmi?port=2"}]}
        with patch(
            "home_cinema_control.devices.tv.adapters.sony.requests.post",
            return_value=_response(payload),
        ):
            self.assertIsNone(controller.get_current_app_id())

    def test_returns_uri_when_an_app_is_active(self):
        controller = SonyTvController(_config())
        app_uri = "com.sony.dtv.tv.emby.embyatv.MainActivity"
        payload = {"result": [{"uri": app_uri}]}
        with patch(
            "home_cinema_control.devices.tv.adapters.sony.requests.post",
            return_value=_response(payload),
        ):
            self.assertEqual(app_uri, controller.get_current_app_id())

    def test_returns_none_when_on_live_tv_channel(self):
        # "tv:..." uris (broadcast tuner) are treated the same as extInput —
        # verified against Home Assistant's coordinator.py, which checks
        # media_uri[:2] == "tv" the same way it checks the extInput prefix.
        controller = SonyTvController(_config())
        payload = {"result": [{"uri": "tv:dvbt?trip=1.2.3&srvName=Some+Channel"}]}
        with patch(
            "home_cinema_control.devices.tv.adapters.sony.requests.post",
            return_value=_response(payload),
        ):
            self.assertIsNone(controller.get_current_app_id())

    def test_falls_back_when_result_has_no_uri(self):
        app_config = _config(sony_app_uris={
            "emby": "com.sony.dtv.tv.emby.embyatv.MainActivity",
        })
        app_config["media_servers"] = {
            "active": "emby",
            "providers": {"emby": {"server_url": "http://emby.local"}},
        }
        controller = SonyTvController(app_config)
        with patch(
            "home_cinema_control.devices.tv.adapters.sony.requests.post",
            return_value=_response({"result": [{}]}),
        ):
            self.assertEqual(
                "com.sony.dtv.tv.emby.embyatv.MainActivity",
                controller.get_current_app_id(),
            )

    def test_returns_none_on_illegal_state_error_when_no_provider_configured(self):
        controller = SonyTvController(_config())
        with patch(
            "home_cinema_control.devices.tv.adapters.sony.requests.post",
            return_value=_response({"error": [7, "Illegal State"]}),
        ):
            self.assertIsNone(controller.get_current_app_id())

    def test_returns_none_on_network_error_when_no_provider_configured(self):
        controller = SonyTvController(_config())
        with patch(
            "home_cinema_control.devices.tv.adapters.sony.requests.post",
            side_effect=ConnectionError("unreachable"),
        ):
            self.assertIsNone(controller.get_current_app_id())

    def test_falls_back_to_configured_provider_app_id_on_illegal_state_error(self):
        # There is no orchestrator-level fallback for this — startup/orchestrator.py
        # calls get_current_app_id() once and threads a None straight through to a
        # skipped restore. The adapter must fall back itself, unlike LG which reads
        # the current app reliably via a single call.
        app_config = _config(sony_app_uris={
            "emby": "com.sony.dtv.tv.emby.embyatv.MainActivity",
        })
        app_config["media_servers"] = {
            "active": "emby",
            "providers": {"emby": {"server_url": "http://emby.local"}},
        }
        controller = SonyTvController(app_config)
        with patch(
            "home_cinema_control.devices.tv.adapters.sony.requests.post",
            return_value=_response({"error": [7, "Illegal State"]}),
        ):
            self.assertEqual(
                "com.sony.dtv.tv.emby.embyatv.MainActivity",
                controller.get_current_app_id(),
            )

    def test_does_not_fall_back_when_previously_on_hdmi_input(self):
        # Already on the OPPO/HDMI input before switching — correctly nothing to
        # restore, must not be conflated with the ambiguous/error case above.
        app_config = _config(sony_app_uris={
            "emby": "com.sony.dtv.tv.emby.embyatv.MainActivity",
        })
        app_config["media_servers"] = {
            "active": "emby",
            "providers": {"emby": {"server_url": "http://emby.local"}},
        }
        controller = SonyTvController(app_config)
        payload = {"result": [{"uri": "extInput:hdmi?port=2"}]}
        with patch(
            "home_cinema_control.devices.tv.adapters.sony.requests.post",
            return_value=_response(payload),
        ):
            self.assertIsNone(controller.get_current_app_id())


class SonyMediaServerAppIdTest(unittest.TestCase):
    def test_returns_none_when_not_yet_discovered(self):
        controller = SonyTvController(_config())
        self.assertIsNone(controller.media_server_app_id("emby"))

    def test_returns_discovered_uri(self):
        controller = SonyTvController(_config(sony_app_uris={
            "emby": "com.sony.dtv.tv.emby.embyatv.MainActivity",
        }))
        self.assertEqual(
            "com.sony.dtv.tv.emby.embyatv.MainActivity",
            controller.media_server_app_id("emby"),
        )


class SonyGetApplicationListTest(unittest.TestCase):
    def test_populates_available_apps(self):
        config = _config()
        controller = SonyTvController(config)
        payload = {"result": [[
            {"title": "Emby", "uri": "com.sony.dtv.tv.emby.embyatv.MainActivity"},
            {"title": "", "uri": ""},
        ]]}
        with patch(
            "home_cinema_control.devices.tv.adapters.sony.requests.post",
            return_value=_response(payload),
        ):
            result = controller.get_application_list()

        self.assertEqual(DeviceCommandStatus.SUCCESS, result.status)
        apps = config["tv"]["sony_available_apps"]
        self.assertEqual([{"title": "Emby", "uri": "com.sony.dtv.tv.emby.embyatv.MainActivity"}], apps)


class SonyPskSanitizationTest(unittest.TestCase):
    def test_sanitize_exposes_psk_configured_without_leaking_value(self):
        result = sanitize_config_for_web({"tv": {"sony_psk": "psk123"}})

        self.assertTrue(result["tv"]["sony_psk_configured"])
        self.assertNotIn("sony_psk", result["tv"])

    def test_sanitize_exposes_no_psk_state(self):
        result = sanitize_config_for_web({"tv": {}})

        self.assertFalse(result["tv"]["sony_psk_configured"])

    def test_sanitize_exposes_no_psk_state_when_tv_absent(self):
        result = sanitize_config_for_web({})

        self.assertFalse(result["tv"]["sony_psk_configured"])


if __name__ == "__main__":
    unittest.main()
