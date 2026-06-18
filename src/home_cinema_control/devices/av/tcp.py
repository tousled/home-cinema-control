import time

from home_cinema_control.network.tcp import LoggingTcpClient


class TcpCommandSender:
    _tcp = LoggingTcpClient(name="av-receiver")

    def send_command(self, command):
        host = self.config["av"]["ip"]
        port = int(self.config["av"]["port"])
        timeout = float(self.config["av"]["connection_timeout_seconds"])

        if isinstance(command, str):
            command = command.encode("ascii")

        self._tcp.send_only(host=host, port=port, payload=command, timeout=timeout)
        time.sleep(0.1)

        return "OK"

    def query_command(self, command, *, timeout=None, expected_prefix=None):
        host = self.config["av"]["ip"]
        port = int(self.config["av"]["port"])
        query_timeout = float(timeout or self.config["av"]["command_timeout_seconds"])

        if isinstance(command, str):
            command = command.encode("ascii")

        return self._tcp.request(
            host=host,
            port=port,
            payload=command,
            timeout=query_timeout,
            complete=lambda response: (
                not expected_prefix
                or _has_response_with_prefix(response, expected_prefix)
            ),
        )


def _has_response_with_prefix(response, expected_prefix):
    for line in response.replace("\r", "\n").splitlines():
        if line.strip().startswith(expected_prefix):
            return True

    return False
