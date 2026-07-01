import logging
import time

import requests
from wakeonlan import wake

from home_cinema_control.config.manager import (
    active_media_server_config,
    active_media_server_type,
)
from home_cinema_control.config.models import SonyTvConfig
from home_cinema_control.devices.tv.base import BaseTvController
from home_cinema_control.devices.tv.models import TvInputTarget
from home_cinema_control.network.arp import find_mac_by_ip
from home_cinema_control.playback.startup.models import DeviceCommandResult

SONY_REQUEST_TIMEOUT_SECONDS = 10.0
SONY_INPUT_CONFIRM_TIMEOUT_SECONDS = 3.0
SONY_INPUT_CONFIRM_INTERVAL_SECONDS = 0.25
SONY_WAKE_TIMEOUT_SECONDS = 20.0
SONY_WAKE_RETRY_INTERVAL_SECONDS = 1.0

# Not hardcodeable app ids like LG/Samsung use — Sony's setActiveApp needs the full
# per-TV discovered launch uri (see sony_app_uris). These are only a matching
# heuristic to pre-select the right entry when the user runs "detect installed apps".
JELLYFIN_ANDROID_TV_PACKAGE = "org.jellyfin.androidtv"
EMBY_ANDROID_TV_PACKAGE = "tv.emby.embyatv"


class SonyTvController(BaseTvController):
    def __init__(self, config: dict):
        super().__init__(config)
        self._tv = SonyTvConfig.model_validate(config.get("tv") or {})

    def test_connection(self) -> DeviceCommandResult:
        return self._execute_tv_operation(
            "testing Sony TV connection",
            lambda: self._call("system", "getPowerStatus"),
        )

    def retrieve_hdmi_inputs(self) -> DeviceCommandResult:
        return self._execute_tv_operation(
            "refreshing Sony TV inputs",
            self._refresh_inputs,
        )

    def switch_to_input(self, target: TvInputTarget) -> DeviceCommandResult:
        if not target.input_id:
            return DeviceCommandResult.failed("TV input_id is not configured.")
        return self._execute_tv_operation(
            "switching Sony TV to HDMI input",
            lambda: self._switch_to_hdmi_input(target),
        )

    def launch_app(self, app_id: str | None) -> DeviceCommandResult:
        if app_id is None:
            logging.warning("No app_id provided for Sony launch_app; skipping.")
            return DeviceCommandResult.skipped("No app_id to launch.")
        return self._execute_tv_operation(
            "launching Sony TV app",
            lambda: self._call("appControl", "setActiveApp", [{"uri": app_id}]),
        )

    def media_server_app_id(self, provider_type: str) -> str | None:
        return self._tv.sony_app_uris.get(provider_type)

    def get_current_app_id(self) -> str | None:
        try:
            body = self._call("avContent", "getPlayingContentInfo")
            result = (body.get("result") or [{}])[0]
            uri = result.get("uri", "")

            if not uri:
                return self._fallback_app_id()

            if uri.startswith("extInput") or uri.startswith("tv:"):
                # On an HDMI/tuner input or a live TV channel, not an
                # app-launched uri — nothing to restore. Distinguished by the
                # uri prefix, not a "source" field: verified against Home
                # Assistant's braviatv coordinator.py, which does the same
                # (media_uri[:8] == "extInput", media_uri[:2] == "tv") and
                # never reads a "source" key from this response.
                return None

            return uri

        except ValueError as exc:
            logging.error("TV configuration error while reading Sony current app: %s", exc)
            return self._fallback_app_id()

        except (OSError, TimeoutError, requests.RequestException) as exc:
            logging.warning("TV network error while reading Sony current app: %s", exc)
            return self._fallback_app_id()

        except Exception:
            logging.exception("Unexpected TV error while reading Sony current app")
            return self._fallback_app_id()

    def _fallback_app_id(self) -> str | None:
        """Sony's getPlayingContentInfo can error ("Illegal State") while an app is
        active on some models, unlike LG's reliable single-call get_current_app().

        There is no orchestrator-level safety net to lean on here: startup/
        orchestrator.py calls get_current_app_id() exactly once and threads the
        result straight through to launch_app() at finish (restoration.py) — a
        None here means TV restore is silently skipped, not retried elsewhere. So
        the fallback has to live in this adapter: fall back to the configured
        media-server provider's app id, so the orchestrator always has something
        to restore to instead of leaving the TV on the OPPO input.
        """
        if not active_media_server_config(self.config).server_url:
            return None
        return self.media_server_app_id(active_media_server_type(self.config))

    def get_application_list(self) -> DeviceCommandResult:
        """Setup-time app discovery. Not part of BaseTvController: only Sony needs
        this, since only Sony can't hardcode a launch id per provider."""
        return self._execute_tv_operation(
            "listing Sony TV installed apps",
            self._refresh_available_apps,
        )

    def _execute_tv_operation(self, operation_name, operation) -> DeviceCommandResult:
        try:
            operation()
            return DeviceCommandResult.success()

        except ValueError as exc:
            logging.error("TV configuration error while %s: %s", operation_name, exc)
            return DeviceCommandResult.failed(f"TV configuration error: {exc}")

        except TimeoutError as exc:
            logging.warning("TV timeout while %s: %s", operation_name, exc)
            return DeviceCommandResult.failed(f"TV timeout: {exc}")

        except (OSError, requests.RequestException) as exc:
            logging.warning("TV network error while %s: %s", operation_name, exc)
            return DeviceCommandResult.failed(f"TV network error: {exc}")

        except Exception:
            logging.exception("Unexpected TV error while %s", operation_name)
            return DeviceCommandResult.failed(
                f"Unexpected TV error during {operation_name}."
            )

    def _call(self, service: str, method: str, params: list | None = None) -> dict:
        ip = self._tv.ip
        if not ip:
            raise ValueError("tv.ip is not configured")

        psk = (self.config.get("tv") or {}).get("sony_psk", "")
        if not psk:
            raise ValueError("tv.sony_psk is not configured")

        response = requests.post(
            f"http://{ip}/sony/{service}",
            json={"method": method, "id": 1, "params": params or [], "version": "1.0"},
            headers={"X-Auth-PSK": psk},
            timeout=SONY_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()

        if "error" in body:
            raise OSError(f"Sony API error calling {service}.{method}: {body['error']}")

        return body

    def _call_or_wake(self, service: str, method: str, params: list | None = None) -> dict:
        try:
            return self._call(service, method, params)

        except ValueError:
            raise

        except (OSError, TimeoutError, requests.RequestException):
            logging.info("Sony TV is not reachable. Attempting Wake-on-LAN.")
            self._wake_tv()
            return self._wait_until_reachable(service, method, params)

    def _wait_until_reachable(self, service: str, method: str, params: list | None) -> dict:
        deadline = time.monotonic() + SONY_WAKE_TIMEOUT_SECONDS
        last_error: Exception | None = None

        while time.monotonic() < deadline:
            try:
                return self._call(service, method, params)

            except (OSError, TimeoutError, requests.RequestException) as exc:
                last_error = exc
                time.sleep(SONY_WAKE_RETRY_INTERVAL_SECONDS)

        raise TimeoutError(f"Sony TV did not become reachable after Wake-on-LAN: {last_error}")

    def _refresh_inputs(self) -> None:
        self._refresh_mac_from_arp()
        body = self._call("avContent", "getCurrentExternalInputsStatus")
        inputs = (body.get("result") or [[]])[0]

        sources = [
            {
                "index": index,
                "id": item["uri"],
                "nombre": item.get("title") or item["uri"],
                # No confirmed field name for physical connection state: Home
                # Assistant's braviatv (title/uri only, no connectivity check)
                # doesn't rely on one either, so default to available rather
                # than assume disconnected on an unverified key.
                "connected": bool(item.get("connectivity", True)),
            }
            for index, item in enumerate(inputs)
            if item.get("uri", "").startswith("extInput:hdmi")
        ]
        self.config.setdefault("tv", {})["available_hdmi_inputs"] = sources

    def _switch_to_hdmi_input(self, target: TvInputTarget) -> None:
        logging.info("Changing Sony TV input to %s", target.input_id)
        self._call_or_wake("avContent", "setPlayContent", [{"uri": target.input_id}])
        self._confirm_hdmi_input(target.input_id)

    def _confirm_hdmi_input(self, target_input_id: str) -> None:
        deadline = time.monotonic() + SONY_INPUT_CONFIRM_TIMEOUT_SECONDS
        observed_uri = None

        while time.monotonic() < deadline:
            try:
                body = self._call("avContent", "getPlayingContentInfo")
                result = (body.get("result") or [{}])[0]
                observed_uri = result.get("uri")

                if observed_uri == target_input_id:
                    logging.info(
                        "Sony HDMI input confirmed | target_input_id=%s", target_input_id
                    )
                    return

            except (OSError, TimeoutError, requests.RequestException) as exc:
                logging.warning(
                    "Unable to confirm Sony HDMI input after switch | "
                    "target_input_id=%s | error=%s",
                    target_input_id,
                    exc,
                )
                return

            time.sleep(SONY_INPUT_CONFIRM_INTERVAL_SECONDS)

        logging.warning(
            "Sony HDMI input not confirmed | target_input_id=%s | observed_uri=%s",
            target_input_id,
            observed_uri,
        )

    def _refresh_available_apps(self) -> None:
        body = self._call("appControl", "getApplicationList")
        apps = (body.get("result") or [[]])[0]

        self.config.setdefault("tv", {})["sony_available_apps"] = [
            {"title": app.get("title", ""), "uri": app.get("uri", "")}
            for app in apps
            if app.get("uri")
        ]

    def _wake_tv(self) -> None:
        mac = self._get_mac_for_wake()

        if not mac:
            raise ValueError("TV_MAC is not available and could not be detected automatically")

        try:
            logging.info("Sending Wake-on-LAN packet to Sony TV: %s", mac)
            wake(mac)

        except (OSError, ValueError) as exc:
            raise OSError(f"Unable to send Wake-on-LAN packet to Sony TV: {exc}") from exc

    def _get_mac_for_wake(self) -> str | None:
        return (self.config.get("tv") or {}).get("mac") or self._refresh_mac_from_arp()

    def _refresh_mac_from_arp(self) -> str | None:
        tv = self.config.get("tv") or {}
        tv_ip = tv.get("ip", "")

        if not tv_ip:
            return None

        detected_mac = find_mac_by_ip(tv_ip)

        if not detected_mac:
            return None

        stored_mac = tv.get("mac", "")

        if stored_mac != detected_mac:
            if stored_mac:
                logging.info(
                    "Sony TV MAC updated from ARP: old=%s | new=%s", stored_mac, detected_mac
                )
            else:
                logging.info("Sony TV MAC learned from ARP: %s", detected_mac)

            self.config.setdefault("tv", {})["mac"] = detected_mac

        return detected_mac
