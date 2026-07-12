import socket
import threading
import time
import unittest
from contextlib import closing, suppress
from unittest.mock import patch

from home_cinema_control.devices.av.adapters.trinnov import TrinnovAvReceiver
from home_cinema_control.devices.av.adapters.trinnov_client import TrinnovTcpClient
from home_cinema_control.devices.av.adapters.trinnov_mapper import (
    fallback_profile_sources,
    normalize_profile_command,
)
from home_cinema_control.devices.av.factory import create_av_receiver_or_none
from home_cinema_control.playback.startup.models import DeviceCommandStatus


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class FakeTrinnovServer:
    def __init__(self, responder, *, reject_identity=False):
        self.responder = responder
        self.reject_identity = reject_identity
        self.commands = []
        self.port = _free_port()
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)

    def __enter__(self):
        self._thread.start()
        if not self._ready.wait(timeout=1.0):
            raise RuntimeError("fake Trinnov server did not start")
        return self

    def __exit__(self, exc_type, exc, tb):
        self._stop.set()
        with suppress(OSError):
            socket.create_connection(("127.0.0.1", self.port), timeout=0.05).close()
        self._thread.join(timeout=1.0)

    def _serve(self):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("127.0.0.1", self.port))
            server.listen()
            self._ready.set()
            server.settimeout(0.1)
            while not self._stop.is_set():
                try:
                    conn, _ = server.accept()
                except socket.timeout:
                    continue
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        with closing(conn):
            conn.settimeout(0.5)
            with suppress(OSError):
                conn.sendall(b"Welcome on Trinnov Optimizer (Version 4.0.0, ID 1)\n")
                identity = _recv_line(conn)
                if identity:
                    self.commands.append(identity)
                if self.reject_identity or identity != "id Home Cinema Control":
                    conn.sendall(b"ERROR: invalid id\n")
                    return
                conn.sendall(b"OK\n")

                command = _recv_line(conn)
                if not command:
                    return
                self.commands.append(command)
                response = self.responder(command)
                if response == "close":
                    return
                if response == "never":
                    time.sleep(0.4)
                    return
                conn.sendall(response)


def _recv_line(conn) -> str:
    data = b""
    while b"\n" not in data:
        try:
            chunk = conn.recv(1)
        except socket.timeout:
            return ""
        if not chunk:
            return ""
        data += chunk
    return data.decode("ascii", errors="replace").strip()


def _config(port: int, **av_overrides):
    av = {
        "enabled": True,
        "model": "TRINNOV",
        "ip": "127.0.0.1",
        "port": port,
        "connection_timeout_seconds": 0.2,
        "command_timeout_seconds": 0.2,
        "always_on": True,
    }
    av.update(av_overrides)
    return {"av": av}


class TrinnovMapperTest(unittest.TestCase):
    def test_normalizes_profile_commands(self):
        self.assertEqual("profile 2\n", normalize_profile_command("2"))
        self.assertEqual("profile 2\n", normalize_profile_command("profile 2"))
        self.assertEqual("profile 2\n", normalize_profile_command("profile 2\n"))

    def test_rejects_invalid_profile_commands(self):
        for value in ["", "profile -1", "HDMI1", "volume -20", "profile abc"]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_profile_command(value)

    def test_fallback_profile_sources_are_bounded(self):
        sources = fallback_profile_sources(3)
        self.assertEqual([0, 1, 2], [source.id for source in sources])
        self.assertEqual("profile 2\n", sources[2].param)


class TrinnovClientContractTest(unittest.TestCase):
    def test_identifies_before_operational_command(self):
        with FakeTrinnovServer(lambda command: b"OK\n") as server:
            client = TrinnovTcpClient(
                host="127.0.0.1",
                port=server.port,
                connection_timeout_seconds=0.2,
                command_timeout_seconds=0.2,
            )

            response = client.send_command("profile 2\n")

        self.assertTrue(response.successful)
        self.assertEqual(["id Home Cinema Control", "profile 2"], server.commands)

    def test_treats_async_lines_before_ok_as_success(self):
        with FakeTrinnovServer(lambda command: b"VOLUME -20.000000\nOK\n") as server:
            result = TrinnovAvReceiver(_config(server.port)).switch_to_input("2")

        self.assertEqual(DeviceCommandStatus.SUCCESS, result.status)

    def test_treats_ok_before_async_lines_as_success(self):
        with FakeTrinnovServer(lambda command: b"OK\nMETA_PRESET_LOADED 2\n") as server:
            result = TrinnovAvReceiver(_config(server.port)).switch_to_input("2")

        self.assertEqual(DeviceCommandStatus.SUCCESS, result.status)

    def test_treats_error_as_failure_with_detail(self):
        with FakeTrinnovServer(lambda command: b"ERROR: invalid profile\n") as server:
            result = TrinnovAvReceiver(_config(server.port)).switch_to_input("99")

        self.assertEqual(DeviceCommandStatus.FAILED, result.status)
        self.assertIn("invalid profile", result.detail)

    def test_connection_close_before_terminal_is_failure(self):
        with FakeTrinnovServer(lambda command: "close") as server:
            result = TrinnovAvReceiver(_config(server.port)).switch_to_input("2")

        self.assertEqual(DeviceCommandStatus.FAILED, result.status)
        self.assertIn("closed the connection", result.detail)

    def test_timeout_before_terminal_is_failure(self):
        with FakeTrinnovServer(lambda command: "never") as server:
            result = TrinnovAvReceiver(_config(server.port)).switch_to_input("2")

        self.assertEqual(DeviceCommandStatus.FAILED, result.status)
        self.assertIn("timed out", result.detail)

    def test_identity_rejection_is_failure(self):
        with FakeTrinnovServer(lambda command: b"OK\n", reject_identity=True) as server:
            result = TrinnovAvReceiver(_config(server.port)).switch_to_input("2")

        self.assertEqual(DeviceCommandStatus.FAILED, result.status)
        self.assertIn("invalid id", result.detail)


class TrinnovAvReceiverTest(unittest.TestCase):
    def test_invalid_input_is_rejected_before_opening_socket(self):
        receiver = TrinnovAvReceiver(_config(1))

        with patch.object(receiver, "_client") as client:
            result = receiver.switch_to_input("volume -20")

        client.assert_not_called()
        self.assertEqual(DeviceCommandStatus.FAILED, result.status)

    def test_source_discovery_returns_profile_names(self):
        def responder(command):
            if command == "get_profile_name 0":
                return b"OPPO\nOK\n"
            if command == "get_profile_name 1":
                return b"TV Audio\nOK\n"
            return b"ERROR: missing profile\n"

        with FakeTrinnovServer(responder) as server:
            sources = TrinnovAvReceiver(_config(server.port)).list_hdmi_inputs()

        self.assertEqual(2, len(sources))
        self.assertEqual("Source/profile 0 - OPPO", sources[0].name)
        self.assertEqual("profile 1\n", sources[1].param)

    def test_source_discovery_falls_back_when_no_names_return(self):
        with FakeTrinnovServer(lambda command: b"ERROR: missing profile\n") as server:
            sources = TrinnovAvReceiver(_config(server.port)).list_hdmi_inputs()

        self.assertEqual(32, len(sources))
        self.assertEqual("Source/profile 0", sources[0].name)

    def test_restore_tv_audio_skips_when_not_configured(self):
        result = TrinnovAvReceiver(_config(1, tv_connected_input="")).restore_tv_audio()

        self.assertEqual(DeviceCommandStatus.SKIPPED, result.status)

    def test_power_off_skips_when_always_on(self):
        result = TrinnovAvReceiver(_config(1, always_on=True)).power_off()

        self.assertEqual(DeviceCommandStatus.SKIPPED, result.status)

    def test_power_off_sends_secured_command_when_allowed(self):
        with FakeTrinnovServer(lambda command: b"OK\n") as server:
            result = TrinnovAvReceiver(
                _config(server.port, always_on=False, trinnov_mac="aa:bb:cc:dd:ee:ff")
            ).power_off()

        self.assertEqual(DeviceCommandStatus.SUCCESS, result.status)
        self.assertIn("power_off_SECURED_FHZMCH48FE", server.commands)

    @patch("home_cinema_control.devices.av.adapters.trinnov.find_mac_by_ip", return_value=None)
    def test_power_on_without_mac_reports_wol_requirement(self, _):
        result = TrinnovAvReceiver(_config(_free_port(), trinnov_mac="")).power_on()

        self.assertEqual(DeviceCommandStatus.SKIPPED, result.status)
        self.assertIn("MAC address", result.detail)

    @patch("home_cinema_control.devices.av.adapters.trinnov.find_mac_by_ip", return_value=None)
    def test_power_off_without_mac_is_skipped(self, _):
        result = TrinnovAvReceiver(_config(1, always_on=False, trinnov_mac="")).power_off()

        self.assertEqual(DeviceCommandStatus.SKIPPED, result.status)
        self.assertIn("MAC address", result.detail)

    def test_factory_resolves_trinnov(self):
        receiver = create_av_receiver_or_none(_config(1))

        self.assertIsInstance(receiver, TrinnovAvReceiver)


if __name__ == "__main__":
    unittest.main()
