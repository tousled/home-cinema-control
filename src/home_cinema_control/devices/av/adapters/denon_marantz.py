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

INPUT_QUERY_COMMAND = "SI?\n"
INPUT_QUERY_TIMEOUT_SECONDS = 1.0
INPUT_RESPONSE_PREFIX = "SI"
TV_AUDIO_INPUT_COMMAND = "SITV\n"
TV_AUDIO_INPUT_RESPONSE = "SITV"

POWER_QUERY_COMMAND = "PW?\n"
POWER_QUERY_TIMEOUT_SECONDS = 2.0
POWER_RESPONSE_PREFIX = "PW"
STANDBY_RESPONSE = "PWSTANDBY"


class BaseDenonMarantzAvReceiver(BaseAvReceiver, TcpCommandSender):
    """Denon and Marantz share the same D+M Group serial/IP command set
    (SI?/PW?/ZMON/ZMOFF) — confirmed identical, not just similar, so the
    seam sits here rather than in two copies. Subclasses only set
    receiver_name and their own list_hdmi_inputs().
    """

    uses_observed_input_recovery = True

    def power_on(self) -> DeviceCommandResult:
        return self._execute_av_operation(
            f"powering on {self.receiver_name}", self._power_on
        )

    def switch_to_input(self, input_id: str) -> DeviceCommandResult:
        logging.info(
            "Switching %s AV receiver to configured player input", self.receiver_name
        )
        return self._execute_av_operation(
            f"switching {self.receiver_name} input",
            lambda: self._switch_to_input(input_id),
        )

    def restore_tv_audio(self) -> DeviceCommandResult:
        logging.info("Restoring %s to TV audio input (SITV)", self.receiver_name)
        return self._execute_av_operation(
            f"restoring {self.receiver_name} TV audio",
            lambda: self.send_command(TV_AUDIO_INPUT_COMMAND),
        )

    def power_off(self) -> DeviceCommandResult:
        logging.info("Powering off %s AV receiver", self.receiver_name)
        return self._execute_av_operation(
            f"powering off {self.receiver_name}",
            lambda: self.send_command("ZMOFF\n"),
        )

    def _power_on(self) -> None:
        in_standby = self._is_in_standby()
        self.send_command("ZMON\n")
        if in_standby:
            logging.info(
                "%s was in standby — waiting for input to stabilize (ARC/CEC settle)",
                self.receiver_name,
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
            redirected_input=TV_AUDIO_INPUT_RESPONSE,
            max_retries=2,
        ).change_input()

    def _is_in_standby(self):
        try:
            response = self.query_command(
                POWER_QUERY_COMMAND,
                timeout=POWER_QUERY_TIMEOUT_SECONDS,
                expected_prefix=POWER_RESPONSE_PREFIX,
            )
            return STANDBY_RESPONSE in (response or "")
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
                INPUT_QUERY_COMMAND,
                timeout=INPUT_QUERY_TIMEOUT_SECONDS,
                expected_prefix=INPUT_RESPONSE_PREFIX,
            )
        except OSError as exc:
            logging.warning(
                "Unable to query %s input | error=%s", self.receiver_name, exc
            )
            return None

        return extract_prefixed_response(raw_response, INPUT_RESPONSE_PREFIX)
