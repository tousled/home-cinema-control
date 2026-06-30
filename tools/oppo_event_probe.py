#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from home_cinema_control.config.manager import load_effective_config  # noqa: E402
from home_cinema_control.devices.oppo.constants import OPPO_TELNET_PORT  # noqa: E402
from home_cinema_control.devices.oppo.verbose_events import OppoVerboseEventListener  # noqa: E402


def now() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Listen for OPPO TCP verbose status events on port 23."
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Config file used when --host is not provided.",
    )
    parser.add_argument("--host", default="", help="OPPO/Chinoppo IP address.")
    parser.add_argument("--port", type=int, default=OPPO_TELNET_PORT)
    parser.add_argument("--connect-timeout", type=float, default=3.0)
    parser.add_argument("--read-timeout", type=float, default=0.5)
    parser.add_argument(
        "--mode",
        type=int,
        default=2,
        choices=[0, 1, 2, 3],
        help="OPPO verbose mode sent through SVM. Use 2 for status changes, 3 for detailed timecode updates.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=60.0,
        help="Seconds to listen. Use 0 for no time limit.",
    )
    parser.add_argument(
        "--initial-command",
        action="append",
        default=[],
        help="Command sent after SVM. Repeatable.",
    )
    parser.add_argument(
        "--query-initial-qpl",
        action="store_true",
        help="Send QPL after SVM. Disabled by default because some OPPO variants close verbose sessions after mixed command traffic.",
    )
    parser.add_argument(
        "--keepalive-command",
        default="",
        help="Optional command sent periodically to keep the TCP connection open.",
    )
    parser.add_argument(
        "--keepalive-interval",
        type=float,
        default=10.0,
        help="Seconds between keepalive commands.",
    )
    parser.add_argument(
        "--no-restore",
        action="store_true",
        help="Do not send SVM 0 when the probe exits. Use only for manual debugging.",
    )
    parser.add_argument(
        "--reconnect-delay",
        type=float,
        default=1.0,
        help="Seconds to wait before reconnecting when the OPPO closes the connection. Set to 0 to disable reconnect.",
    )

    args = parser.parse_args()
    host = args.host.strip()

    if not host:
        config = load_effective_config(args.config)
        host = str(config.get("oppo", {}).get("ip", "")).strip()

    if not host:
        print("OPPO host is not configured. Pass --host or configure oppo.ip.", file=sys.stderr)
        return 2

    duration = None if args.duration <= 0 else args.duration
    reconnect_delay = args.reconnect_delay
    listener = OppoVerboseEventListener(
        host=host,
        port=args.port,
        connect_timeout_seconds=args.connect_timeout,
        read_timeout_seconds=args.read_timeout,
    )

    print(
        f"{now()} Listening OPPO verbose events host={host} port={args.port} "
        f"mode={args.mode} duration={duration or 'unbounded'}s "
        f"initial_commands={_initial_commands(args)} "
        f"keepalive={args.keepalive_command or 'off'} "
        f"reconnect_delay={reconnect_delay}s "
        f"restore_svm0={not args.no_restore}. Press Ctrl+C to stop.",
        flush=True,
    )

    deadline = None if duration is None else time.monotonic() + duration

    try:
        while True:
            remaining = (
                None
                if deadline is None
                else max(0.0, deadline - time.monotonic())
            )
            if deadline is not None and remaining <= 0:
                break

            for event in listener.listen(
                verbose_mode=args.mode,
                duration_seconds=remaining,
                initial_commands=_initial_commands(args),
                keepalive_command=args.keepalive_command or None,
                keepalive_interval_seconds=args.keepalive_interval,
                restore_verbose_mode=not args.no_restore,
            ):
                print(
                    f"{now()} code={event.code or '-'} payload={event.payload!r} raw={event.raw!r}",
                    flush=True,
                )

            if deadline is not None and time.monotonic() >= deadline:
                break

            if reconnect_delay <= 0:
                break

            print(f"{now()} [connection closed — reconnecting in {reconnect_delay}s]", flush=True)
            time.sleep(reconnect_delay)
    except KeyboardInterrupt:
        print(f"\n{now()} Stopped.", flush=True)
        return 0

    print(f"{now()} Finished.", flush=True)
    return 0


def _initial_commands(args) -> list[str]:
    commands = list(args.initial_command)

    if args.query_initial_qpl:
        commands.insert(0, "QPL")

    return commands


if __name__ == "__main__":
    raise SystemExit(main())
