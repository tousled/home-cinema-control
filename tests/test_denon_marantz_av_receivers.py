import unittest
from unittest.mock import MagicMock, patch

from home_cinema_control.devices.av.adapters.denon import DenonAvReceiver
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

    def test_list_hdmi_inputs_returns_brand_specific_data(self):
        receiver = self._make_receiver()
        self.assertTrue(len(receiver.list_hdmi_inputs()) > 0)


class DenonAvReceiverTest(_SharedDenonMarantzBehaviorTest, unittest.TestCase):
    RECEIVER_CLASS = DenonAvReceiver
    EXPECTED_NAME = "Denon"


class MarantzAvReceiverTest(_SharedDenonMarantzBehaviorTest, unittest.TestCase):
    RECEIVER_CLASS = MarantzAvReceiver
    EXPECTED_NAME = "Marantz"


if __name__ == "__main__":
    unittest.main()
