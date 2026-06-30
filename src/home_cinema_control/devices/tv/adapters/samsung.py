import logging
import time
from contextlib import contextmanager, suppress

from samsungtvws import SamsungTVWS
from wakeonlan import wake

from home_cinema_control.devices.tv.adapters.smartthings_client import SmartThingsInputClient
from home_cinema_control.devices.tv.base import BaseTvController
from home_cinema_control.devices.tv.models import TvInputTarget
from home_cinema_control.network.arp import find_mac_by_ip
from home_cinema_control.playback.startup.models import DeviceCommandResult

SAMSUNG_TOKEN_FILE_PATH = "/config/.samsung_tv_token"
SAMSUNG_PORT_SSL = 8002
SAMSUNG_PORT_PLAIN = 8001
SAMSUNG_CONNECT_TIMEOUT_SECONDS = 10.0
SAMSUNG_FAST_CONNECT_TIMEOUT_SECONDS = 2.0
SAMSUNG_PORT_DETECT_TIMEOUT_SECONDS = 3.0
SAMSUNG_WAKE_TIMEOUT_SECONDS = 20.0
SAMSUNG_WAKE_RETRY_INTERVAL_SECONDS = 1.0

JELLYFIN_APP_ID = "AprZAARz4r.Jellyfin"
EMBY_APP_IDS = ("vYmY3ACVaa.emby", "3201606009872")

_MEDIA_SERVER_APP_IDS = {
    "emby": EMBY_APP_IDS[0],
    "jellyfin": JELLYFIN_APP_ID,
}

_STATIC_HDMI_INPUTS = [
    {"index": 0, "id": "HDMI1", "nombre": "HDMI 1"},
    {"index": 1, "id": "HDMI2", "nombre": "HDMI 2"},
    {"index": 2, "id": "HDMI3", "nombre": "HDMI 3"},
    {"index": 3, "id": "HDMI4", "nombre": "HDMI 4"},
]

def _format_input_name(src: str) -> str:
    if src.startswith("HDMI") and len(src) > 4:
        return f"HDMI {src[4:]}"
    if src == "digitalTv":
        return "Digital TV"
    return src


# Cached per IP within the process lifetime — the port doesn't change unless
# the TV firmware changes, so probing once per process is sufficient.
_port_cache: dict[str, int] = {}


class SamsungTvController(BaseTvController):
    def __init__(
        self,
        config: dict,
        smartthings_client: SmartThingsInputClient | None = None,
    ) -> None:
        super().__init__(config)
        self._smartthings_client = smartthings_client

    def test_connection(self) -> DeviceCommandResult:
        try:
            with self._connected_client():
                self._refresh_mac_from_arp()
            return DeviceCommandResult.success()
        except ValueError as exc:
            logging.error("Samsung TV configuration error while testing connection: %s", exc)
            return DeviceCommandResult.failed(f"TV configuration error: {exc}")
        except Exception as exc:
            logging.warning("Samsung TV error while testing connection: %s", exc)
            return DeviceCommandResult.failed(f"TV connection error: {exc}")

    def retrieve_hdmi_inputs(self) -> DeviceCommandResult:
        client = self._smartthings_client
        if client:
            try:
                sources = client.get_supported_inputs()
                inputs = [
                    {"index": i, "id": src, "nombre": _format_input_name(src)}
                    for i, src in enumerate(sources)
                ]
                self.config.setdefault("tv", {})["available_hdmi_inputs"] = inputs
                logging.info("Samsung TV: retrieved %d inputs from SmartThings", len(inputs))
                return DeviceCommandResult.success(detail="smartthings")
            except Exception as exc:
                logging.warning("Samsung TV: SmartThings input discovery failed: %s", exc)
                return DeviceCommandResult.failed(
                    f"SmartThings input discovery failed: {exc}. "
                    "Check your SmartThings token and device ID in TV settings."
                )
        self.config.setdefault("tv", {})["available_hdmi_inputs"] = list(_STATIC_HDMI_INPUTS)
        return DeviceCommandResult.success(detail="static")

    def switch_to_input(self, target: TvInputTarget) -> DeviceCommandResult:
        if not target.input_id:
            return DeviceCommandResult.failed("TV input_id is not configured.")
        client = self._smartthings_client
        if client:
            return self._switch_via_smartthings(target.input_id, client)
        return self._switch_via_websocket(target.input_id)

    def _switch_via_smartthings(
        self, input_id: str, client: SmartThingsInputClient
    ) -> DeviceCommandResult:
        try:
            logging.info("Switching Samsung TV input to %s via SmartThings", input_id)
            client.set_input(input_id)
            return DeviceCommandResult.success()
        except ValueError as exc:
            logging.error("Samsung TV configuration error while switching input: %s", exc)
            return DeviceCommandResult.failed(f"TV configuration error: {exc}")
        except Exception as exc:
            logging.warning("Samsung TV error switching input via SmartThings: %s", exc)
            return DeviceCommandResult.failed(f"TV error switching input: {exc}")

    def _switch_via_websocket(self, input_id: str) -> DeviceCommandResult:
        logging.warning(
            "SmartThings not configured; attempting WebSocket key fallback for input %s"
            " (may not work on all Samsung TV models — configure SmartThings for reliability)",
            input_id,
        )
        try:
            with self._connected_client(wake_if_unreachable=True) as tv:
                key = f"KEY_{input_id}"
                logging.info("Sending WebSocket key to Samsung TV: %s", key)
                tv.send_key(key)
            return DeviceCommandResult.success()
        except ValueError as exc:
            logging.error("Samsung TV configuration error while switching input: %s", exc)
            return DeviceCommandResult.failed(f"TV configuration error: {exc}")
        except Exception as exc:
            logging.warning("Samsung TV error switching input via WebSocket: %s", exc)
            return DeviceCommandResult.failed(f"TV error switching input: {exc}")

    def launch_app(self, app_id: str | None) -> DeviceCommandResult:
        if app_id is None:
            logging.warning("No app_id provided for Samsung launch_app; skipping.")
            return DeviceCommandResult.skipped("No app_id to launch.")
        try:
            ip = self._get_ip()
        except ValueError as exc:
            logging.error("Samsung TV configuration error while launching app: %s", exc)
            return DeviceCommandResult.failed(f"TV configuration error: {exc}")
        rest = SamsungTVWS(host=ip, port=SAMSUNG_PORT_PLAIN, timeout=SAMSUNG_CONNECT_TIMEOUT_SECONDS)
        try:
            logging.info("Launching Samsung TV app: %s", app_id)
            rest.rest_app_run(app_id)
            return DeviceCommandResult.success()
        except Exception:
            if app_id == EMBY_APP_IDS[0]:
                try:
                    rest.rest_app_run(EMBY_APP_IDS[1])
                    return DeviceCommandResult.success()
                except Exception:
                    pass
            logging.exception("Samsung TV launch_app failed for app_id=%s", app_id)
            return DeviceCommandResult.failed(f"Could not launch app {app_id}.")

    def get_current_app_id(self) -> str | None:
        try:
            ip = self._get_ip()
        except ValueError as exc:
            logging.warning("Samsung TV get_current_app_id skipped: %s", exc)
            return None
        rest = SamsungTVWS(host=ip, port=SAMSUNG_PORT_PLAIN, timeout=SAMSUNG_CONNECT_TIMEOUT_SECONDS)
        for app_id in (JELLYFIN_APP_ID, *EMBY_APP_IDS):
            try:
                status = rest.rest_app_status(app_id)
                result = status.get("result") or {}
                if result.get("visible"):
                    logging.info("Samsung TV current app: %s", app_id)
                    return app_id
            except Exception:
                continue
        # Nothing visible — fall back to the configured media server so the
        # orchestrator has something to restore to after playback.
        provider_type = (self.config.get("media_servers") or {}).get("active")
        fallback = self.media_server_app_id(str(provider_type)) if provider_type else None
        if fallback:
            logging.info(
                "Samsung TV: no visible app detected; falling back to configured provider %s → %s",
                provider_type,
                fallback,
            )
        else:
            logging.warning(
                "Samsung TV: no visible app and no configured provider fallback; get_current_app_id returns None"
            )
        return fallback

    def media_server_app_id(self, provider_type: str) -> str | None:
        return _MEDIA_SERVER_APP_IDS.get(provider_type)

    @contextmanager
    def _connected_client(self, *, wake_if_unreachable: bool = False):
        ip = self._get_ip()
        port = self._detect_port(ip)
        client = None
        try:
            if wake_if_unreachable:
                client = self._connect_or_wake(ip, port)
            else:
                client = SamsungTVWS(
                    host=ip,
                    port=port,
                    token_file=SAMSUNG_TOKEN_FILE_PATH,
                    timeout=SAMSUNG_CONNECT_TIMEOUT_SECONDS,
                )
                client.open()
            yield client
        finally:
            if client is not None:
                with suppress(Exception):
                    client.close()

    def _connect_or_wake(self, ip: str, port: int) -> SamsungTVWS:
        try:
            client = SamsungTVWS(
                host=ip,
                port=port,
                token_file=SAMSUNG_TOKEN_FILE_PATH,
                timeout=SAMSUNG_FAST_CONNECT_TIMEOUT_SECONDS,
            )
            client.open()
            return client
        except ValueError:
            raise
        except (OSError, TimeoutError):
            logging.info("Samsung TV not reachable. Attempting Wake-on-LAN.")
            self._wake_tv()
            return self._wait_until_reachable(ip, port)

    def _wait_until_reachable(self, ip: str, port: int) -> SamsungTVWS:
        deadline = time.monotonic() + SAMSUNG_WAKE_TIMEOUT_SECONDS
        last_error = None
        while time.monotonic() < deadline:
            try:
                client = SamsungTVWS(
                    host=ip,
                    port=port,
                    token_file=SAMSUNG_TOKEN_FILE_PATH,
                    timeout=SAMSUNG_FAST_CONNECT_TIMEOUT_SECONDS,
                )
                client.open()
                return client
            except (OSError, TimeoutError) as exc:
                last_error = exc
                time.sleep(SAMSUNG_WAKE_RETRY_INTERVAL_SECONDS)
        raise TimeoutError(
            f"Samsung TV did not become reachable after Wake-on-LAN: {last_error}"
        )

    def _detect_port(self, ip: str) -> int:
        if ip in _port_cache:
            logging.debug("Samsung TV port from cache: %d for %s", _port_cache[ip], ip)
            return _port_cache[ip]
        for port in (SAMSUNG_PORT_SSL, SAMSUNG_PORT_PLAIN):
            try:
                client = SamsungTVWS(
                    host=ip,
                    port=port,
                    token_file=SAMSUNG_TOKEN_FILE_PATH,
                    timeout=SAMSUNG_PORT_DETECT_TIMEOUT_SECONDS,
                )
                client.open()
                client.close()
                _port_cache[ip] = port
                logging.info(
                    "Samsung TV port detected: %d for %s (%s)",
                    port,
                    ip,
                    "SSL/token" if port == SAMSUNG_PORT_SSL else "plain/no-token",
                )
                return port
            except Exception:
                continue
        _port_cache[ip] = SAMSUNG_PORT_SSL
        logging.warning(
            "Samsung TV port detection failed for %s; defaulting to %d",
            ip,
            SAMSUNG_PORT_SSL,
        )
        return SAMSUNG_PORT_SSL

    def _get_ip(self) -> str:
        ip = (self.config.get("tv") or {}).get("ip", "")
        if not ip:
            raise ValueError("tv.ip is not configured")
        return ip

    def _wake_tv(self) -> None:
        mac = self._get_mac_for_wake()
        if not mac:
            raise ValueError("TV MAC is not available and could not be detected automatically")
        try:
            logging.info("Sending Wake-on-LAN packet to Samsung TV: %s", mac)
            wake(mac)
        except (OSError, ValueError) as exc:
            raise OSError(f"Unable to send Wake-on-LAN packet to Samsung TV: {exc}") from exc

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
                    "Samsung TV MAC updated from ARP: old=%s | new=%s",
                    stored_mac,
                    detected_mac,
                )
            else:
                logging.info("Samsung TV MAC learned from ARP: %s", detected_mac)
            self.config.setdefault("tv", {})["mac"] = detected_mac
        return detected_mac
