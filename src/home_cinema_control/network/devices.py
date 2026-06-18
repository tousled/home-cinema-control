import ipaddress
import logging
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from home_cinema_control.network.arp import ARP_TABLE_PATH

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiscoveredDevice:
    ip: str
    mac: str
    vendor: str | None
    name: str | None = None


def discover_local_devices() -> list[DiscoveredDevice]:
    if not ARP_TABLE_PATH.exists():
        return []
    cmd = ["arp-scan", "--localnet"]
    iface = _detect_default_interface()
    if iface:
        cmd.extend(["--interface", iface])
        logger.debug("arp-scan using interface: %s", iface)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("arp-scan failed: %s", exc)
        return []
    if result.returncode != 0 or result.stderr:
        logger.warning(
            "arp-scan exited %s | stderr: %s",
            result.returncode,
            result.stderr.strip()[:500],
        )
    logger.debug("arp-scan stdout: %s chars | %s lines", len(result.stdout), result.stdout.count("\n"))
    seen: set[str] = set()
    unique = []
    for d in _parse_arp_scan_output(result.stdout):
        if d.ip not in seen:
            seen.add(d.ip)
            unique.append(d)
    devices = sorted(unique, key=lambda d: ipaddress.ip_address(d.ip))
    return _enrich_with_hostnames(devices)


def _lookup_hostname(ip: str) -> str | None:
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        # Take only the first label (strip .local / .lan / .home etc.)
        name = hostname.split(".")[0].strip()
        return name if name and name != ip else None
    except (socket.herror, socket.gaierror, OSError):
        return None


def _enrich_with_hostnames(devices: list[DiscoveredDevice]) -> list[DiscoveredDevice]:
    if not devices:
        return devices
    names: dict[str, str | None] = {}
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {pool.submit(_lookup_hostname, d.ip): d.ip for d in devices}
        for future in as_completed(futures, timeout=5):
            ip = futures[future]
            try:
                names[ip] = future.result()
            except Exception:
                names[ip] = None
    return [
        DiscoveredDevice(ip=d.ip, mac=d.mac, vendor=d.vendor, name=names.get(d.ip))
        for d in devices
    ]


def _detect_default_interface() -> str | None:
    # Read the kernel routing table directly — no external tools needed.
    # /proc/net/route columns: Iface Destination Gateway Flags RefCnt Use Metric Mask ...
    # Default route has Destination == "00000000".
    try:
        best_iface = None
        best_metric = float("inf")
        with open("/proc/net/route") as f:
            next(f)  # skip header line
            for line in f:
                fields = line.strip().split()
                if len(fields) >= 8 and fields[1] == "00000000":
                    metric = int(fields[6])
                    if metric < best_metric:
                        best_metric = metric
                        best_iface = fields[0]
        return best_iface
    except Exception:
        return None


def _parse_arp_scan_output(output: str) -> list[DiscoveredDevice]:
    devices = []
    for line in output.splitlines():
        cols = line.split("\t")
        if len(cols) < 2:
            continue
        ip = cols[0].strip()
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            continue
        mac = cols[1].strip()
        vendor_raw = cols[2].strip() if len(cols) >= 3 else ""
        vendor = vendor_raw if vendor_raw and vendor_raw != "(Unknown)" else None
        devices.append(DiscoveredDevice(ip=ip, mac=mac, vendor=vendor))
    return devices
