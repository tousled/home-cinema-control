import logging

from home_cinema_control.devices.av.base import BaseAvReceiver
from home_cinema_control.devices.av.input_retrier import (
    AVInputRetrier,
    extract_prefixed_response,
    wait_until_input_stable,
    wait_until_receiver_responsive,
)
from home_cinema_control.devices.av.tcp import TcpCommandSender
from home_cinema_control.playback.startup.models import DeviceCommandResult

MARANTZ_INPUT_QUERY_COMMAND = "SI?\n"
MARANTZ_INPUT_QUERY_TIMEOUT_SECONDS = 1.0
MARANTZ_INPUT_RESPONSE_PREFIX = "SI"
MARANTZ_TV_AUDIO_INPUT = "SITV"

MARANTZ_POWER_QUERY_COMMAND = "PW?\n"
MARANTZ_POWER_QUERY_TIMEOUT_SECONDS = 2.0
MARANTZ_POWER_RESPONSE_PREFIX = "PW"
MARANTZ_STANDBY_RESPONSE = "PWSTANDBY"


class MarantzAvReceiver(BaseAvReceiver, TcpCommandSender):
    receiver_name = "Marantz"
    uses_observed_input_recovery = True

    def power_on(self) -> DeviceCommandResult:
        logging.info("llamada a av_power_on")
        return self._execute_av_operation("powering on Marantz", self._power_on)

    def list_hdmi_inputs(self):
        return [
            {"Id": 1, "Name": "CD", "Param": "SICD\n"},
            {"Id": 2, "Name": "DVD", "Param": "SIDVD\n"},
            {"Id": 3, "Name": "Blu-ray (BD)", "Param": "SIBD\n"},
            {"Id": 4, "Name": "TV AUDIO(TV)", "Param": "SITV\n"},
            {"Id": 5, "Name": "CBL/SAT", "Param": "SISAT/CBL\n"},
            {"Id": 5, "Name": "SAT", "Param": "SISAT\n"},
            {"Id": 5, "Name": "PEPE", "Param": "SICBL\n"},
            {"Id": 6, "Name": "GAME", "Param": "SIGAME\n"},
        ]

    def switch_to_input(self, input_id: str) -> DeviceCommandResult:
        logging.info("Switching Marantz AV receiver to configured player input")
        return self._execute_av_operation(
            "switching Marantz input",
            lambda: self._switch_to_input(input_id),
        )

    def restore_tv_audio(self) -> DeviceCommandResult:
        logging.info("Restoring Marantz to TV audio input (SITV)")
        return self._execute_av_operation(
            "restoring Marantz TV audio",
            lambda: self.send_command("SITV\n"),
        )

    def power_off(self) -> DeviceCommandResult:
        logging.info("Powering off Marantz AV receiver")
        return self._execute_av_operation(
            "powering off Marantz",
            lambda: self.send_command("ZMOFF\n"),
        )

    def _power_on(self) -> None:
        in_standby = self._is_in_standby()
        self.send_command("ZMON\n")
        if in_standby:
            logging.info(
                "Marantz was in standby — waiting for input to stabilize (ARC/CEC settle)"
            )
            wait_until_input_stable(
                self._get_current_input,
                receiver_name=self.receiver_name,
            )
        else:
            wait_until_receiver_responsive(
                self._get_current_input,
                receiver_name=self.receiver_name,
            )

    def _switch_to_input(self, input_id: str) -> None:
        AVInputRetrier(
            receiver_name=self.receiver_name,
            input_command=input_id,
            send_input_command=self.send_command,
            get_current_input=self._get_current_input,
            redirected_input=MARANTZ_TV_AUDIO_INPUT,
            max_retries=2,
        ).change_input()

    def _is_in_standby(self):
        try:
            response = self.query_command(
                MARANTZ_POWER_QUERY_COMMAND,
                timeout=MARANTZ_POWER_QUERY_TIMEOUT_SECONDS,
                expected_prefix=MARANTZ_POWER_RESPONSE_PREFIX,
            )
            return MARANTZ_STANDBY_RESPONSE in (response or "")
        except OSError as exc:
            logging.warning(
                "Unable to query %s power state | error=%s — assuming standby",
                self.receiver_name,
                exc,
            )
            return True

    def _get_current_input(self):
        try:
            raw_response = self.query_command(
                MARANTZ_INPUT_QUERY_COMMAND,
                timeout=MARANTZ_INPUT_QUERY_TIMEOUT_SECONDS,
                expected_prefix=MARANTZ_INPUT_RESPONSE_PREFIX,
            )
        except OSError as exc:
            logging.warning(
                "Unable to query %s input | error=%s", self.receiver_name, exc
            )
            return None

        return extract_prefixed_response(raw_response, MARANTZ_INPUT_RESPONSE_PREFIX)
