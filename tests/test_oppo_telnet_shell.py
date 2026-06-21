import unittest
from contextlib import contextmanager
from unittest.mock import patch

from home_cinema_control.devices.oppo import telnet_shell
from home_cinema_control.devices.oppo.telnet_shell import unmount_oppo_path


class _FakeSocket:
    def __init__(self, recv_chunks):
        self._chunks = list(recv_chunks)
        self.sent = []

    def settimeout(self, timeout):
        pass

    def recv(self, bufsize):
        if self._chunks:
            return self._chunks.pop(0)
        return b""

    def sendall(self, data):
        self.sent.append(data)


class _FakeTcpClient:
    def __init__(self, socket_obj):
        self._socket_obj = socket_obj

    @contextmanager
    def connect(self, *, host, port, timeout):
        yield self._socket_obj


class TelnetShellUnmountTest(unittest.TestCase):
    def test_aborts_without_sending_commands_when_no_login_prompt_appears(self):
        # This OPPO never sends a `login:` banner over telnet (confirmed live
        # against real hardware: the port answers OPPO's own #QPL/#QPW
        # protocol, not a jailbreak shell). Blindly sending root/umount into
        # that silence used to be reported as "success" with no evidence it
        # ever did anything.
        fake_socket = _FakeSocket([b""])

        with patch.object(telnet_shell, "_tcp", _FakeTcpClient(fake_socket)):
            result = unmount_oppo_path(
                host="192.168.1.50",
                mount_path="/mnt/cifs1",
                timeout=1,
            )

        self.assertFalse(result)
        self.assertEqual([], fake_socket.sent)

    def test_sends_unmount_commands_when_login_prompt_appears(self):
        fake_socket = _FakeSocket([b"login: ", b""])

        with patch.object(telnet_shell, "_tcp", _FakeTcpClient(fake_socket)):
            result = unmount_oppo_path(
                host="192.168.1.50",
                mount_path="/mnt/cifs1",
                timeout=1,
            )

        self.assertTrue(result)
        self.assertIn(b"root\n", fake_socket.sent)
        self.assertTrue(
            any(b"umount" in chunk for chunk in fake_socket.sent)
        )

    def test_rejects_unexpected_mount_path(self):
        with self.assertRaises(ValueError):
            unmount_oppo_path(host="192.168.1.50", mount_path="/etc", timeout=1)


if __name__ == "__main__":
    unittest.main()
