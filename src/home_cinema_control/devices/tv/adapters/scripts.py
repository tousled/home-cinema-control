import logging
import subprocess

from home_cinema_control.devices.tv.base import BaseTvController
from home_cinema_control.devices.tv.models import TvInputTarget
from home_cinema_control.playback.startup.models import DeviceCommandResult


class ScriptsTvController(BaseTvController):
    def test_connection(self) -> DeviceCommandResult:
        return DeviceCommandResult.success()

    def retrieve_hdmi_inputs(self) -> DeviceCommandResult:
        self.config.setdefault("tv", {})["available_hdmi_inputs"] = []
        return DeviceCommandResult.success()

    def switch_to_input(self, target: TvInputTarget) -> DeviceCommandResult:
        logging.info("Running TV init script")
        try:
            subprocess.Popen(self.config["tv"]["startup_script"])
            return DeviceCommandResult.success("TV init script launched.")
        except OSError as exc:
            logging.warning("Unable to run TV init script: %s", exc)
            return DeviceCommandResult.failed(f"Unable to run TV init script: {exc}")

    def launch_app(self, app_id: str | None) -> DeviceCommandResult:
        logging.info("Running TV end script")
        try:
            subprocess.Popen(self.config["tv"]["shutdown_script"])
            return DeviceCommandResult.success("TV end script launched.")
        except OSError as exc:
            logging.warning("Unable to run TV end script: %s", exc)
            return DeviceCommandResult.failed(f"Unable to run TV end script: {exc}")

    def get_current_app_id(self) -> str | None:
        logging.info("TV current app is not available for script-based TV control")
        return None
