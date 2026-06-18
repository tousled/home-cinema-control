import logging

from home_cinema_control.devices.av.base import BaseAvReceiver
from home_cinema_control.network.http import get_http_session
from home_cinema_control.playback.startup.models import DeviceCommandResult


class YamahaAvReceiver(BaseAvReceiver):
    def list_hdmi_inputs(self):
        return [
            {"Id": 1, "Name": "HDMI1", "Param": "HDMI1"},
            {"Id": 2, "Name": "HDMI2", "Param": "HDMI2"},
            {"Id": 3, "Name": "HDMI3", "Param": "HDMI3"},
            {"Id": 4, "Name": "HDMI4", "Param": "HDMI4"},
            {"Id": 5, "Name": "HDMI5", "Param": "HDMI5"},
            {"Id": 6, "Name": "HDMI6", "Param": "HDMI6"},
            {"Id": 7, "Name": "HDMI7", "Param": "HDMI7"},
            {"Id": 8, "Name": "HDMI8", "Param": "HDMI8"},
            {"Id": 9, "Name": "HDMI9", "Param": "HDMI9"},
        ]

    def power_on(self) -> DeviceCommandResult:
        logging.info("Llamada a av_power_on")
        return self._execute_av_operation("powering on Yamaha", self._power_on)

    def switch_to_input(self, input_id: str) -> DeviceCommandResult:
        logging.info("Switching Yamaha AV receiver to configured player input")
        return self._execute_av_operation(
            "switching Yamaha input",
            lambda: self._post(
                f"<Main_Zone><Input><Input_Sel>{input_id}</Input_Sel></Input></Main_Zone>"
            ),
        )

    def restore_tv_audio(self) -> DeviceCommandResult:
        tv_input = self.config["av"]["tv_connected_input"]
        if not tv_input:
            logging.debug("Yamaha tv_connected_input not configured; skipping TV audio restore")
            return DeviceCommandResult.skipped("TV audio restore not configured.")
        logging.info("Restoring Yamaha to TV audio input | input=%s", tv_input)
        return self._execute_av_operation(
            "restoring Yamaha TV audio",
            lambda: self._post(
                f"<Main_Zone><Input><Input_Sel>{tv_input}</Input_Sel></Input></Main_Zone>"
            ),
        )

    def power_off(self) -> DeviceCommandResult:
        logging.info("Powering off Yamaha AV receiver")
        return self._execute_av_operation(
            "powering off Yamaha",
            lambda: self._post(
                '<YAMAHA_AV cmd="PUT"><System><Power_Control><Power>Standby</Power></Power_Control></System></YAMAHA_AV>'
            ),
        )

    def _power_on(self) -> None:
        self._post(
            '<YAMAHA_AV cmd="PUT"><System><Power_Control><Power>On</Power></Power_Control></System></YAMAHA_AV>'
        )
        self._wait_after_power_on()

    def _post(self, message_data):
        url = "http://" + self.config["av"]["ip"] + "/YamahaRemoteControl/ctrl"
        get_http_session("yamaha-av").post(url, data=message_data, headers="")
