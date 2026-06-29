import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager, suppress

from bscpylgtv import WebOsClient
from bscpylgtv.storage_sqlitedict import StorageSqliteDict
from wakeonlan import wake

from home_cinema_control.devices.tv.base import BaseTvController
from home_cinema_control.devices.tv.models import TvInputTarget
from home_cinema_control.network.arp import find_mac_by_ip
from home_cinema_control.playback.startup.models import DeviceCommandResult

EMBY_APP_ID = "com.emby.app"
JELLYFIN_APP_ID = "org.jellyfin.webos"

_MEDIA_SERVER_APP_IDS = {
    "emby": EMBY_APP_ID,
    "jellyfin": JELLYFIN_APP_ID,
}

LG_CONNECT_TIMEOUT_SECONDS = 20.0
LG_FAST_CONNECT_TIMEOUT_SECONDS = 2.0
LG_WAKE_TIMEOUT_SECONDS = 20.0
LG_WAKE_RETRY_INTERVAL_SECONDS = 1.0
LG_INPUT_CONFIRM_TIMEOUT_SECONDS = 3.0
LG_INPUT_CONFIRM_INTERVAL_SECONDS = 0.25
LG_KEY_FILE_PATH = "/config/.aiopylgtv.sqlite"

_TvOperation = Callable[[], Awaitable[None]]


def _map_webos_inputs_to_legacy_sources(inputs: list[dict]) -> list[dict]:
    sources = []

    for index, webos_input in enumerate(inputs):
        input_id = webos_input.get("id")

        if not input_id:
            logging.warning("Skipping LG input without id: %s", webos_input)
            continue

        sources.append({
            "index": index,
            "id": input_id,
            "appId": webos_input.get("appId", ""),
            "nombre": webos_input.get("label") or input_id,
            "connected": bool(webos_input.get("connected", False)),
        })

    return sources


class LgTvController(BaseTvController):
    def test_connection(self) -> DeviceCommandResult:
        return self._execute_tv_operation(
            "testing LG TV connection",
            self._test_connection,
        )

    def retrieve_hdmi_inputs(self) -> DeviceCommandResult:
        return self._execute_tv_operation(
            "refreshing LG TV inputs",
            self._refresh_inputs,
        )

    def switch_to_input(self, target: TvInputTarget) -> DeviceCommandResult:
        return self._execute_tv_operation(
            "switching LG TV to HDMI input",
            lambda: self._switch_to_hdmi_input(target),
        )

    def launch_app(self, app_id: str | None) -> DeviceCommandResult:
        if app_id is None:
            logging.warning("No app_id provided for LG launch_app; skipping.")
            return DeviceCommandResult.skipped("No app_id to launch.")
        return self._execute_tv_operation(
            "launching LG TV app",
            lambda: self._launch_app(app_id),
        )

    def media_server_app_id(self, provider_type: str) -> str | None:
        return _MEDIA_SERVER_APP_IDS.get(provider_type)

    def get_current_app_id(self) -> str | None:
        try:
            return asyncio.run(self._get_current_app())

        except ValueError as exc:
            logging.error(
                "TV configuration error while reading LG current app: %s", exc
            )
            return None

        except TimeoutError as exc:
            logging.warning("TV timeout while reading LG current app: %s", exc)
            return None

        except OSError as exc:
            logging.warning("TV network error while reading LG current app: %s", exc)
            return None

        except Exception:
            logging.exception("Unexpected TV error while reading LG current app")
            return None

    def _execute_tv_operation(
        self,
        operation_name: str,
        operation: _TvOperation,
    ) -> DeviceCommandResult:
        try:
            asyncio.run(operation())
            return DeviceCommandResult.success()

        except ValueError as exc:
            logging.error("TV configuration error while %s: %s", operation_name, exc)
            return DeviceCommandResult.failed(f"TV configuration error: {exc}")

        except TimeoutError as exc:
            logging.warning("TV timeout while %s: %s", operation_name, exc)
            return DeviceCommandResult.failed(f"TV timeout: {exc}")

        except OSError as exc:
            logging.warning("TV network error while %s: %s", operation_name, exc)
            return DeviceCommandResult.failed(f"TV network error: {exc}")

        except Exception:
            logging.exception("Unexpected TV error while %s", operation_name)
            return DeviceCommandResult.failed(
                f"Unexpected TV error during {operation_name}."
            )

    @asynccontextmanager
    async def _connected_client(self, *, wake_if_unreachable: bool = False):
        client = None

        try:
            if wake_if_unreachable:
                client = await self._connect_or_wake()
            else:
                client = await self._connect()

            yield client

        finally:
            await self._disconnect(client)

    async def _connect(self, *, timeout: float = LG_CONNECT_TIMEOUT_SECONDS) -> WebOsClient:
        tv_ip = (self.config.get("tv") or {}).get("ip", "")

        if not tv_ip:
            raise ValueError("tv.ip is not configured")

        storage = await StorageSqliteDict.create(LG_KEY_FILE_PATH, table="lg_pairing_keys")
        client = await WebOsClient.create(
            tv_ip,
            storage=storage,
            timeout_connect=timeout,
        )
        await asyncio.wait_for(client.connect(), timeout=timeout)

        return client

    async def _connect_or_wake(self) -> WebOsClient:
        try:
            return await self._connect(timeout=LG_FAST_CONNECT_TIMEOUT_SECONDS)

        except ValueError:
            raise

        except TimeoutError:
            logging.info("LG TV is not reachable due to timeout. Attempting Wake-on-LAN.")
            self._wake_tv()
            return await self._wait_until_reachable()

        except OSError:
            logging.info("LG TV is not reachable due to network error. Attempting Wake-on-LAN.")
            self._wake_tv()
            return await self._wait_until_reachable()

    async def _wait_until_reachable(self) -> WebOsClient:
        deadline = time.monotonic() + LG_WAKE_TIMEOUT_SECONDS
        last_error = None

        while time.monotonic() < deadline:
            try:
                return await self._connect(timeout=LG_FAST_CONNECT_TIMEOUT_SECONDS)

            except TimeoutError as exc:
                last_error = exc
                await asyncio.sleep(LG_WAKE_RETRY_INTERVAL_SECONDS)

            except OSError as exc:
                last_error = exc
                await asyncio.sleep(LG_WAKE_RETRY_INTERVAL_SECONDS)

        raise TimeoutError(f"LG TV did not become reachable after Wake-on-LAN: {last_error}")

    @staticmethod
    async def _disconnect(client: WebOsClient | None) -> None:
        if client is not None:
            with suppress(Exception):
                await client.disconnect()

    def _wake_tv(self) -> None:
        mac = self._get_mac_for_wake()

        if not mac:
            raise ValueError("TV_MAC is not available and could not be detected automatically")

        try:
            logging.info("Sending Wake-on-LAN packet to LG TV: %s", mac)
            wake(mac)

        except (OSError, ValueError) as exc:
            raise OSError(f"Unable to send Wake-on-LAN packet to LG TV: {exc}") from exc

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
                    "LG TV MAC updated from ARP: old=%s | new=%s",
                    stored_mac,
                    detected_mac,
                )
            else:
                logging.info("LG TV MAC learned from ARP: %s", detected_mac)

            self.config.setdefault("tv", {})["mac"] = detected_mac

        return detected_mac

    async def _test_connection(self) -> None:
        async with self._connected_client():
            self._refresh_mac_from_arp()

    async def _refresh_inputs(self) -> None:
        async with self._connected_client() as client:
            self._refresh_mac_from_arp()

            inputs = await client.get_inputs()
            self.config.setdefault("tv", {})["available_hdmi_inputs"] = _map_webos_inputs_to_legacy_sources(inputs)

    async def _switch_to_hdmi_input(self, target: TvInputTarget) -> None:
        if not target.input_id:
            raise ValueError("TV input_id is not configured in TvInputTarget.")

        async with self._connected_client(wake_if_unreachable=True) as client:
            logging.info("Changing LG TV input to %s", target.input_id)
            await client.set_input(target.input_id)
            await self._confirm_hdmi_input(
                client,
                target.input_id,
                target.confirmation_app_id,
            )

    async def _confirm_hdmi_input(
        self,
        client: WebOsClient,
        target_input_id: str,
        expected_reported_input: str | None,
    ) -> None:
        if not expected_reported_input:
            logging.info(
                "LG HDMI input confirmation unavailable | target_input_id=%s | expected_reported_input is not configured",
                target_input_id,
            )
            return

        start_time = time.monotonic()
        deadline = start_time + LG_INPUT_CONFIRM_TIMEOUT_SECONDS
        observed_input = None

        try:
            while True:
                remaining_time = deadline - time.monotonic()

                if remaining_time <= 0:
                    break

                observed_input = await asyncio.wait_for(
                    client.get_input(),
                    timeout=remaining_time,
                )
                elapsed = time.monotonic() - start_time

                if observed_input == expected_reported_input:
                    logging.info(
                        "LG HDMI input confirmed | target_input_id=%s | expected_reported_input=%s | observed_input=%s | elapsed=%.2fs",
                        target_input_id,
                        expected_reported_input,
                        observed_input,
                        elapsed,
                    )
                    return

                sleep_time = min(
                    LG_INPUT_CONFIRM_INTERVAL_SECONDS,
                    deadline - time.monotonic(),
                )

                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

        except (TimeoutError, OSError) as exc:
            logging.warning(
                "Unable to confirm LG HDMI input after switch | target_input_id=%s | expected_reported_input=%s | error=%s",
                target_input_id,
                expected_reported_input,
                exc,
            )
            return

        except Exception:
            logging.exception(
                "Unexpected error while confirming LG HDMI input | target_input_id=%s | expected_reported_input=%s",
                target_input_id,
                expected_reported_input,
            )
            return

        elapsed = time.monotonic() - start_time
        logging.warning(
            "LG HDMI input not confirmed | target_input_id=%s | expected_reported_input=%s | observed_input=%s | elapsed=%.2fs",
            target_input_id,
            expected_reported_input,
            observed_input,
            elapsed,
        )

    async def _launch_app(self, app_id: str) -> None:
        async with self._connected_client() as client:
            logging.info("Launching LG app: %s", app_id)
            await client.launch_app(app_id)

    async def _get_current_app(self) -> str | None:
        async with self._connected_client() as client:
            current_app = await client.get_current_app()
            logging.info("Current LG app: %s", current_app)
            return current_app
