import unittest
from unittest.mock import MagicMock, patch

from home_cinema_control.config.models import AvConfig, AvInputSource
from home_cinema_control.devices.av.adapters.denon import DenonAvReceiver
from home_cinema_control.devices.av.adapters.denon_marantz import (
    SOURCES_END_MARKER,
    _parse_sssod_response,
)
from home_cinema_control.devices.av.adapters.marantz import MarantzAvReceiver


class _SharedDenonMarantzBehaviorTest:
    """Mixed into one TestCase per brand so the shared base's behavior is
    proven for both Denon and Marantz, not just whichever one is read first.
    """

    RECEIVER_CLASS = None
    EXPECTED_NAME = None

    def _make_receiver(self):
        return self.RECEIVER_CLASS({"av": {}})

    def test_receiver_name_is_set(self):
        receiver = self._make_receiver()
        self.assertEqual(self.EXPECTED_NAME, receiver.receiver_name)

    def test_is_in_standby_true_when_power_query_reports_standby(self):
        receiver = self._make_receiver()
        receiver.query_command = MagicMock(return_value="PWSTANDBY")

        self.assertTrue(receiver._is_in_standby())

    def test_is_in_standby_false_when_power_query_reports_on(self):
        receiver = self._make_receiver()
        receiver.query_command = MagicMock(return_value="PWON")

        self.assertFalse(receiver._is_in_standby())

    def test_is_in_standby_assumes_standby_on_network_error(self):
        receiver = self._make_receiver()
        receiver.query_command = MagicMock(side_effect=OSError("unreachable"))

        self.assertTrue(receiver._is_in_standby())

    def test_get_current_input_extracts_si_line(self):
        receiver = self._make_receiver()
        receiver.query_command = MagicMock(return_value="SIMPLAY")

        self.assertEqual("SIMPLAY", receiver._get_current_input())

    def test_get_current_input_returns_none_on_network_error(self):
        receiver = self._make_receiver()
        receiver.query_command = MagicMock(side_effect=OSError("unreachable"))

        self.assertIsNone(receiver._get_current_input())

    @patch("home_cinema_control.devices.av.adapters.denon_marantz.wait_until_receiver_responsive")
    @patch("home_cinema_control.devices.av.adapters.denon_marantz.wait_until_input_stable")
    def test_power_on_waits_for_stable_input_when_was_in_standby(
            self, mock_wait_stable, mock_wait_responsive
    ):
        receiver = self._make_receiver()
        receiver._is_in_standby = MagicMock(return_value=True)
        receiver.send_command = MagicMock()

        result = receiver.power_on()

        receiver.send_command.assert_called_once_with("ZMON\n")
        mock_wait_stable.assert_called_once()
        mock_wait_responsive.assert_not_called()
        self.assertTrue(result.successful)

    @patch("home_cinema_control.devices.av.adapters.denon_marantz.wait_until_receiver_responsive")
    @patch("home_cinema_control.devices.av.adapters.denon_marantz.wait_until_input_stable")
    def test_power_on_waits_for_responsive_when_not_in_standby(
            self, mock_wait_stable, mock_wait_responsive
    ):
        receiver = self._make_receiver()
        receiver._is_in_standby = MagicMock(return_value=False)
        receiver.send_command = MagicMock()

        result = receiver.power_on()

        mock_wait_responsive.assert_called_once()
        mock_wait_stable.assert_not_called()
        self.assertTrue(result.successful)

    def test_power_on_fails_on_network_error(self):
        receiver = self._make_receiver()
        receiver._is_in_standby = MagicMock(side_effect=OSError("unreachable"))

        result = receiver.power_on()

        self.assertFalse(result.successful)
        self.assertIn("AV network error", result.detail)

    def test_power_off_sends_zmoff(self):
        receiver = self._make_receiver()
        receiver.send_command = MagicMock()

        result = receiver.power_off()

        receiver.send_command.assert_called_once_with("ZMOFF\n")
        self.assertTrue(result.successful)

    def test_restore_tv_audio_sends_sitv(self):
        receiver = self._make_receiver()
        receiver.send_command = MagicMock()

        result = receiver.restore_tv_audio()

        receiver.send_command.assert_called_once_with("SITV\n")
        self.assertTrue(result.successful)

    @patch("home_cinema_control.devices.av.adapters.denon_marantz.AVInputRetrier")
    def test_switch_to_input_delegates_to_av_input_retrier(self, mock_retrier_cls):
        receiver = self._make_receiver()
        mock_retrier = MagicMock()
        mock_retrier_cls.return_value = mock_retrier

        result = receiver.switch_to_input("SIMPLAY\n")

        kwargs = mock_retrier_cls.call_args.kwargs
        self.assertEqual(self.EXPECTED_NAME, kwargs["receiver_name"])
        self.assertEqual("SIMPLAY\n", kwargs["input_command"])
        self.assertEqual("SITV", kwargs["redirected_input"])
        mock_retrier.change_input.assert_called_once()
        self.assertTrue(result.successful)

    def test_list_hdmi_inputs_falls_back_when_ip_not_configured(self):
        receiver = self._make_receiver()
        result = receiver.list_hdmi_inputs()
        self.assertGreater(len(result), 0)
        self.assertIsInstance(result[0], AvInputSource)

    def test_list_hdmi_inputs_includes_aux1_and_aux2_in_fallback(self):
        receiver = self._make_receiver()
        result = receiver.list_hdmi_inputs()
        params = [src.param for src in result]
        self.assertIn("SIAUX1\n", params)
        self.assertIn("SIAUX2\n", params)

    def test_list_hdmi_inputs_uses_sssod_when_available(self):
        receiver = self._make_receiver()
        receiver.config = {"av": {"ip": "192.168.1.1", "port": "23",
                                  "connection_timeout_seconds": "5",
                                  "command_timeout_seconds": "1"}}
        raw = _sssod("SSSOD DVD USE", "SSSOD BD USE", "SSSOD AUX2 USE", "SSSOD MPLAY DEL")
        receiver.query_command = MagicMock(return_value=raw)

        result = receiver.list_hdmi_inputs()

        self.assertEqual(3, len(result))
        self.assertEqual("DVD", result[0].name)
        self.assertEqual("SIAUX2\n", result[2].param)


def _sssod(*lines):
    """Build a SSSOD response string terminated with the real end marker."""
    return "\r\n".join(lines) + "\r\n" + SOURCES_END_MARKER + "\r\n"


class ParseSssodResponseTest(unittest.TestCase):
    def test_parses_use_lines(self):
        raw = _sssod("SSSOD DVD USE", "SSSOD BD USE", "SSSOD AUX2 USE")
        result = _parse_sssod_response(raw)
        self.assertEqual(3, len(result))
        self.assertEqual("DVD", result[0].name)
        self.assertEqual("SIDVD\n", result[0].param)
        self.assertEqual("SIAUX2\n", result[2].param)

    def test_excludes_del_lines(self):
        raw = _sssod("SSSOD MPLAY USE", "SSSOD GAME DEL")
        result = _parse_sssod_response(raw)
        self.assertEqual(1, len(result))
        self.assertEqual("MPLAY", result[0].name)

    def test_returns_empty_for_none(self):
        self.assertEqual([], _parse_sssod_response(None))

    def test_returns_empty_for_empty_string(self):
        self.assertEqual([], _parse_sssod_response(""))

    def test_skips_malformed_lines(self):
        raw = _sssod("SSSOD", "SSSOD BD", "SSSOD BD USE")
        result = _parse_sssod_response(raw)
        self.assertEqual(1, len(result))

    def test_skips_end_marker(self):
        raw = _sssod("SSSOD CD USE")
        result = _parse_sssod_response(raw)
        self.assertEqual(1, len(result))
        self.assertEqual("CD", result[0].name)


class AvInputSourceValidatorTest(unittest.TestCase):
    def test_coerces_pascal_case_dict(self):
        config = AvConfig(available_hdmi_inputs=[
            {"Id": 1, "Name": "BD", "Param": "SIBD\n"},
        ])
        self.assertEqual(1, config.available_hdmi_inputs[0].id)
        self.assertEqual("BD", config.available_hdmi_inputs[0].name)
        self.assertEqual("SIBD\n", config.available_hdmi_inputs[0].param)

    def test_passthrough_snake_case_dict(self):
        config = AvConfig(available_hdmi_inputs=[
            {"id": 2, "name": "AUX2", "param": "SIAUX2\n"},
        ])
        self.assertEqual(2, config.available_hdmi_inputs[0].id)
        self.assertEqual("SIAUX2\n", config.available_hdmi_inputs[0].param)

    def test_empty_list(self):
        config = AvConfig(available_hdmi_inputs=[])
        self.assertEqual([], config.available_hdmi_inputs)


class DenonAvReceiverTest(_SharedDenonMarantzBehaviorTest, unittest.TestCase):
    RECEIVER_CLASS = DenonAvReceiver
    EXPECTED_NAME = "Denon"


class MarantzAvReceiverTest(_SharedDenonMarantzBehaviorTest, unittest.TestCase):
    RECEIVER_CLASS = MarantzAvReceiver
    EXPECTED_NAME = "Marantz"


if __name__ == "__main__":
    unittest.main()
