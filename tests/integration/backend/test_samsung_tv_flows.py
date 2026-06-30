"""
Integration tests for the Samsung TV adapter.

These tests verify complete operation flows — multiple methods working together
with realistic state (port cache, config propagation, retry/fallback chains).
SamsungTVWS is mocked because there is no Samsung hardware in CI, but the
mock behaviour mirrors what the real library does (WebSocket open/close,
REST status responses, token file argument passing).
"""

import pytest
from unittest.mock import MagicMock, patch

import home_cinema_control.devices.tv.adapters.samsung as samsung_mod
from home_cinema_control.devices.tv.adapters.samsung import (
    EMBY_APP_IDS,
    JELLYFIN_APP_ID,
    SAMSUNG_PORT_SSL,
    SAMSUNG_TOKEN_FILE_PATH,
    SamsungTvController,
)
from home_cinema_control.devices.tv.models import TvInputTarget

pytestmark = pytest.mark.integration

IP = "192.168.1.50"


def _controller(config=None):
    return SamsungTvController(config or {"tv": {"ip": IP}})


def _controller_with_smartthings(config=None):
    base = config or {}
    base.setdefault("tv", {}).update({
        "ip": IP,
        "smartthings_token": "integration-test-token",
        "smartthings_device_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    })
    return SamsungTvController(base)


def _config_with_provider(provider: str) -> dict:
    return {
        "tv": {"ip": IP},
        "media_servers": {"active": provider},
    }


@pytest.fixture(autouse=True)
def clear_port_cache():
    samsung_mod._port_cache.clear()
    yield
    samsung_mod._port_cache.clear()


# ---------------------------------------------------------------------------
# Full switch-to-input flow
# ---------------------------------------------------------------------------


class TestSwitchToInputFlow:
    def test_websocket_fallback_sends_key_code(self):
        """Without SmartThings: switch_to_input connects via WS and derives KEY_HDMIx."""
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            ws = MagicMock()
            mock_cls.return_value = ws
            result = _controller().switch_to_input(TvInputTarget(input_id="HDMI2"))

        assert result.successful
        ws.send_key.assert_called_once_with("KEY_HDMI2")

    def test_each_hdmi_input_derives_correct_key_code(self):
        """All four SmartThings input IDs map to the correct KEY_HDMIx fallback."""
        for n in range(1, 5):
            samsung_mod._port_cache.clear()
            with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
                ws = MagicMock()
                mock_cls.return_value = ws
                result = _controller().switch_to_input(TvInputTarget(input_id=f"HDMI{n}"))

            assert result.successful, f"Failed for HDMI{n}"
            ws.send_key.assert_called_once_with(f"KEY_HDMI{n}")

    def test_token_file_passed_to_websocket_client(self):
        """The WS client must carry token_file so the pairing token persists."""
        samsung_mod._port_cache[IP] = SAMSUNG_PORT_SSL
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_cls.return_value = MagicMock()
            _controller().switch_to_input(TvInputTarget(input_id="HDMI1"))

        _, kwargs = mock_cls.call_args
        assert kwargs.get("token_file") == SAMSUNG_TOKEN_FILE_PATH


# ---------------------------------------------------------------------------
# Port cache — reduces SamsungTVWS instantiation count across operations
# ---------------------------------------------------------------------------


class TestPortCacheAcrossOperations:
    def test_first_operation_probes_then_connects(self):
        """Without cache: detect_port creates one instance, _connected_client another."""
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_cls.return_value = MagicMock()
            _controller().switch_to_input(TvInputTarget(input_id="KEY_HDMI1"))

        assert mock_cls.call_count == 2  # 1 probe + 1 actual

    def test_second_operation_skips_port_probe(self):
        """With cache populated: detect_port is skipped, only one instance created."""
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_cls.return_value = MagicMock()
            controller = _controller()
            controller.switch_to_input(TvInputTarget(input_id="HDMI1"))
            first_count = mock_cls.call_count  # 2 (probe + actual)

            controller.switch_to_input(TvInputTarget(input_id="HDMI2"))
            second_op_count = mock_cls.call_count - first_count  # 1 (actual only)

        assert second_op_count == 1


# ---------------------------------------------------------------------------
# get_current_app_id: visible app found
# ---------------------------------------------------------------------------


class TestGetCurrentAppIdVisibleApp:
    def test_returns_jellyfin_when_it_is_visible(self):
        def fake_status(app_id):
            return {"result": {"visible": app_id == JELLYFIN_APP_ID}}

        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_cls.return_value = MagicMock(rest_app_status=fake_status)
            result = _controller().get_current_app_id()

        assert result == JELLYFIN_APP_ID

    def test_returns_primary_emby_id_when_it_is_visible(self):
        def fake_status(app_id):
            return {"result": {"visible": app_id == EMBY_APP_IDS[0]}}

        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_cls.return_value = MagicMock(rest_app_status=fake_status)
            result = _controller().get_current_app_id()

        assert result == EMBY_APP_IDS[0]

    def test_polls_jellyfin_before_emby(self):
        """Jellyfin is checked first; if visible it wins even if Emby also would be."""
        checked = []

        def fake_status(app_id):
            checked.append(app_id)
            return {"result": {"visible": True}}

        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_cls.return_value = MagicMock(rest_app_status=fake_status)
            result = _controller().get_current_app_id()

        assert result == JELLYFIN_APP_ID
        assert checked[0] == JELLYFIN_APP_ID


# ---------------------------------------------------------------------------
# get_current_app_id: fallback to configured provider
# ---------------------------------------------------------------------------


class TestGetCurrentAppIdFallback:
    def test_falls_back_to_configured_jellyfin_when_nothing_visible(self):
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_cls.return_value = MagicMock(
                rest_app_status=lambda _: {"result": {"visible": False}}
            )
            result = _controller(_config_with_provider("jellyfin")).get_current_app_id()

        assert result == JELLYFIN_APP_ID

    def test_falls_back_to_configured_emby_when_nothing_visible(self):
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_cls.return_value = MagicMock(
                rest_app_status=lambda _: {"result": {"visible": False}}
            )
            result = _controller(_config_with_provider("emby")).get_current_app_id()

        assert result == EMBY_APP_IDS[0]

    def test_falls_back_when_all_rest_checks_raise(self):
        """Network errors during status check still trigger the configured fallback."""
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_cls.return_value = MagicMock(
                rest_app_status=MagicMock(side_effect=OSError("refused"))
            )
            result = _controller(_config_with_provider("jellyfin")).get_current_app_id()

        assert result == JELLYFIN_APP_ID

    def test_returns_none_when_no_provider_configured(self):
        """No media_servers config → no fallback → None (same as before)."""
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_cls.return_value = MagicMock(
                rest_app_status=lambda _: {"result": {"visible": False}}
            )
            result = _controller().get_current_app_id()

        assert result is None


# ---------------------------------------------------------------------------
# Full restore-app chain (get_current_app_id → launch_app)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# SmartThings HDMI switch — full flow
# ---------------------------------------------------------------------------


_ST_PATCH = "home_cinema_control.devices.tv.adapters.samsung.SmartThingsInputClient"


class TestSwitchToInputSmartThings:
    def test_calls_set_input_on_client_with_correct_id(self):
        """Full flow: controller delegates to SmartThingsInputClient.set_input."""
        controller = _controller_with_smartthings()
        with patch(_ST_PATCH) as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            result = controller.switch_to_input(TvInputTarget(input_id="HDMI1"))

        assert result.successful
        mock_client.set_input.assert_called_once_with("HDMI1")

    def test_routes_each_hdmi_id_to_client(self):
        """Each of the four inputs calls set_input with the matching argument."""
        for n in range(1, 5):
            controller = _controller_with_smartthings()
            with patch(_ST_PATCH) as mock_cls:
                mock_client = MagicMock()
                mock_cls.return_value = mock_client
                result = controller.switch_to_input(TvInputTarget(input_id=f"HDMI{n}"))
            assert result.successful, f"Failed for HDMI{n}"
            mock_client.set_input.assert_called_once_with(f"HDMI{n}")

    def test_client_error_returns_failed_result(self):
        """Exception from the client surfaces as a failed DeviceCommandResult."""
        controller = _controller_with_smartthings()
        with patch(_ST_PATCH) as mock_cls:
            mock_client = MagicMock()
            mock_client.set_input.side_effect = OSError("connection refused")
            mock_cls.return_value = mock_client
            result = controller.switch_to_input(TvInputTarget(input_id="HDMI2"))

        assert not result.successful

    def test_smartthings_does_not_open_websocket(self):
        """SmartThings path must not open a WebSocket connection at all."""
        controller = _controller_with_smartthings()
        with patch(_ST_PATCH) as mock_cls, \
                patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_ws:
            mock_cls.return_value = MagicMock()
            controller.switch_to_input(TvInputTarget(input_id="HDMI3"))

        mock_ws.assert_not_called()

    def test_retrieve_inputs_uses_smartthings_dynamic_list(self):
        """With SmartThings configured, retrieve_hdmi_inputs returns the real TV inputs."""
        controller = _controller_with_smartthings()
        with patch(_ST_PATCH) as mock_cls:
            mock_client = MagicMock()
            mock_client.get_supported_inputs.return_value = ["HDMI1", "HDMI2", "digitalTv"]
            mock_cls.return_value = mock_client
            result = controller.retrieve_hdmi_inputs()

        assert result.successful
        assert result.detail == "smartthings"
        inputs = controller.config["tv"]["available_hdmi_inputs"]
        assert len(inputs) == 3
        assert inputs[0]["id"] == "HDMI1"
        assert inputs[2]["id"] == "digitalTv"
        assert inputs[2]["nombre"] == "Digital TV"


# ---------------------------------------------------------------------------
# Full restore-app chain (get_current_app_id → launch_app)
# ---------------------------------------------------------------------------


class TestRestoreAppChain:
    def test_detected_app_is_relaunched_after_playback(self):
        """Simulates the orchestrator capturing the app before playback and restoring it after."""
        controller = _controller()

        # Before playback: detect visible app
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_cls.return_value = MagicMock(
                rest_app_status=lambda app_id: {"result": {"visible": app_id == JELLYFIN_APP_ID}}
            )
            previous_app = controller.get_current_app_id()

        assert previous_app == JELLYFIN_APP_ID

        # After playback: launch the previously detected app
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_rest = MagicMock()
            mock_cls.return_value = mock_rest
            restore_result = controller.launch_app(previous_app)

        assert restore_result.successful
        mock_rest.rest_app_run.assert_called_once_with(JELLYFIN_APP_ID)

    def test_fallback_app_is_launched_when_no_app_was_visible(self):
        """If nothing was visible before playback, fallback ID is used to restore."""
        controller = _controller(_config_with_provider("emby"))

        # Before playback: nothing visible, fallback kicks in
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_cls.return_value = MagicMock(
                rest_app_status=lambda _: {"result": {"visible": False}}
            )
            previous_app = controller.get_current_app_id()

        assert previous_app == EMBY_APP_IDS[0]

        # After playback: launch the fallback app
        with patch("home_cinema_control.devices.tv.adapters.samsung.SamsungTVWS") as mock_cls:
            mock_rest = MagicMock()
            mock_cls.return_value = mock_rest
            restore_result = controller.launch_app(previous_app)

        assert restore_result.successful
        mock_rest.rest_app_run.assert_called_once_with(EMBY_APP_IDS[0])
