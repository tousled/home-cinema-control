import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable

from home_cinema_control.playback.startup.models import DeviceCommandResult


class BaseAvReceiver(ABC):
    uses_observed_input_recovery = False

    def __init__(self, config):
        self.config = config

    @abstractmethod
    def list_hdmi_inputs(self):
        pass

    @abstractmethod
    def power_on(self) -> DeviceCommandResult:
        pass

    @abstractmethod
    def switch_to_input(self, input_id: str) -> DeviceCommandResult:
        pass

    @abstractmethod
    def power_off(self) -> DeviceCommandResult:
        pass

    def restore_tv_audio(self) -> DeviceCommandResult:
        return DeviceCommandResult.skipped("TV audio restore not configured for this receiver.")

    def _execute_av_operation(
        self,
        operation_name: str,
        operation: Callable[[], None],
    ) -> DeviceCommandResult:
        try:
            operation()
            return DeviceCommandResult.success()
        except OSError as exc:
            logging.warning("AV receiver network error while %s: %s", operation_name, exc)
            return DeviceCommandResult.failed(f"AV network error: {exc}")
        except Exception:
            logging.exception("Unexpected AV receiver error while %s", operation_name)
            return DeviceCommandResult.failed(f"Unexpected AV error during {operation_name}.")

    def _wait_after_power_on(self):
        """Fallback delay for receivers that cannot query their own state.

        Uses the av_delay_hdmi config value (set in the web UI). Receivers
        that implement query-based readiness detection (e.g. Denon, Marantz)
        should override power_on() instead of relying on this.
        """
        delay = float(self.config["av"]["hdmi_switch_delay_seconds"])
        if delay > 0:
            logging.info(
                "Waiting %.1fs for AV receiver after power-on (av_delay_hdmi)",
                delay,
            )
            time.sleep(delay)
