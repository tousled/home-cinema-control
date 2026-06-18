import logging

from home_cinema_control.devices.av.base import BaseAvReceiver
from home_cinema_control.devices.av.tcp import TcpCommandSender
from home_cinema_control.playback.startup.models import DeviceCommandResult


class NadAvReceiver(BaseAvReceiver, TcpCommandSender):
    def power_on(self) -> DeviceCommandResult:
        logging.info("llamada a av_power_on")
        return self._execute_av_operation(
            "powering on NAD",
            lambda: self._power_on(),
        )

    def list_hdmi_inputs(self):
        return [
            {"Id": 1, "Name": "HDMI 1", "Param": "Main.Source=1\n"},
            {"Id": 2, "Name": "HDMI 2", "Param": "Main.Source=2\n"},
            {"Id": 3, "Name": "HDMI 3", "Param": "Main.Source=3\n"},
        ]

    def switch_to_input(self, input_id: str) -> DeviceCommandResult:
        logging.info("Switching NAD AV receiver to configured player input")
        return self._execute_av_operation(
            "switching NAD input",
            lambda: self.send_command(input_id),
        )

    def restore_tv_audio(self) -> DeviceCommandResult:
        tv_input = self.config["av"]["tv_connected_input"]
        if not tv_input:
            logging.debug("NAD tv_connected_input not configured; skipping TV audio restore")
            return DeviceCommandResult.skipped("TV audio restore not configured.")
        logging.info("Restoring NAD to TV audio input | input=%s", tv_input.strip())
        return self._execute_av_operation(
            "restoring NAD TV audio",
            lambda: self.send_command(tv_input),
        )

    def power_off(self) -> DeviceCommandResult:
        logging.info("Powering off NAD AV receiver")
        return self._execute_av_operation(
            "powering off NAD",
            lambda: self.send_command("Main.Power=Off\n"),
        )

    def _power_on(self) -> None:
        self.send_command("Main.Power=On\n")
        self._wait_after_power_on()
