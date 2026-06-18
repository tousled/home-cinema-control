import logging

import eiscp

from home_cinema_control.devices.av.base import BaseAvReceiver
from home_cinema_control.playback.startup.models import DeviceCommandResult


class OnkyoAvReceiver(BaseAvReceiver):
    def list_hdmi_inputs(self):
        return [
            {"Id": 1, "Name": "VIDEO1 VCR/DVR STB/DVR", "Param": "SLI00"},
            {"Id": 2, "Name": "VIDEO2 CBL/SAT", "Param": "SLI01"},
            {"Id": 3, "Name": "VIDEO3 GAME/TV GAME GAME1", "Param": "SLI02"},
            {"Id": 4, "Name": "VIDEO4 AUX1(AUX)", "Param": "SLI03"},
            {"Id": 5, "Name": "VIDEO5 AUX2", "Param": "SLI04"},
            {"Id": 6, "Name": "VIDEO6 PC", "Param": "SLI05"},
            {"Id": 7, "Name": "VIDEO7", "Param": "SLI06"},
            {"Id": 11, "Name": "DVD BD/DVD", "Param": "SLI10"},
        ]

    def power_on(self) -> DeviceCommandResult:
        logging.info("Onkyo power_on")
        return self._execute_av_operation("powering on Onkyo", self._power_on)

    def switch_to_input(self, input_id: str) -> DeviceCommandResult:
        logging.info("Onkyo change HDMI Input")
        return self._execute_av_operation(
            "switching Onkyo input",
            lambda: self._switch_to_input(input_id),
        )

    def power_off(self) -> DeviceCommandResult:
        logging.info("Onkyo power_off")
        return self._execute_av_operation("powering off Onkyo", self._power_off)

    def _power_on(self) -> None:
        receiver = eiscp.eISCP(self.config["av"]["ip"])
        onk_status = receiver.command("power query")
        logging.info("Onkyo Power Status: %s", onk_status[1])

        if onk_status[1] == ("standby", "off"):
            logging.info("Cambiamos a on")
            receiver.command("power on")
            receiver.disconnect()
            self._wait_after_power_on()
        else:
            receiver.disconnect()

    def _switch_to_input(self, input_id: str) -> None:
        receiver = eiscp.eISCP(self.config["av"]["ip"])
        receiver.raw(input_id)
        receiver.disconnect()

    def _power_off(self) -> None:
        receiver = eiscp.eISCP(self.config["av"]["ip"])
        onk_status = receiver.command("power query")
        logging.info("Onkyo Power Status: %s", onk_status[1])
        receiver.raw("PWR00")
        receiver.disconnect()
