import logging
import subprocess

from home_cinema_control.devices.av.base import BaseAvReceiver
from home_cinema_control.playback.startup.models import DeviceCommandResult


class ScriptsAvReceiver(BaseAvReceiver):
    def list_hdmi_inputs(self):
        return []

    def power_on(self) -> DeviceCommandResult:
        logging.info("Llamada a av_power_on")
        return self._execute_av_operation("running AV power-on script", self._power_on)

    def switch_to_input(self, input_id: str) -> DeviceCommandResult:
        logging.info("Running configured AV input switch script")
        return self._execute_av_operation(
            "running AV input script",
            lambda: subprocess.Popen(self.config["av"]["hdmi_input_command"]),
        )

    def power_off(self) -> DeviceCommandResult:
        logging.info("Running configured AV power off script")
        return self._execute_av_operation(
            "running AV power-off script",
            lambda: subprocess.Popen(self.config["av"]["power_off_command"]),
        )

    def _power_on(self) -> None:
        subprocess.Popen(self.config["av"]["power_on_command"])
        self._wait_after_power_on()
