import subprocess
import unittest
from unittest.mock import patch

from home_cinema_control.network.devices import _parse_arp_scan_output, discover_local_devices

ARP_SCAN_OUTPUT = (
    "Interface: eth0, datalink type: EN10MB (Ethernet)\n"
    "Starting arp-scan 1.9.8 with 256 hosts (https://www.nta-monitor.com/tools/arp-scan/)\n"
    "192.168.1.1\taa:bb:cc:dd:ee:01\tCisco Systems, Inc\n"
    "192.168.1.10\taa:bb:cc:dd:ee:02\t(Unknown)\n"
    "192.168.1.20\taa:bb:cc:dd:ee:03\tApple, Inc.\n"
    "\n"
    "3 packets received by filter, 0 packets dropped by kernel\n"
)


class ParseArpScanOutputTest(unittest.TestCase):
    def test_parse_valid_output(self):
        devices = _parse_arp_scan_output(ARP_SCAN_OUTPUT)
        self.assertEqual(len(devices), 3)
        self.assertEqual(devices[0].ip, "192.168.1.1")
        self.assertEqual(devices[0].mac, "aa:bb:cc:dd:ee:01")
        self.assertEqual(devices[0].vendor, "Cisco Systems, Inc")

    def test_skips_header_and_footer_lines(self):
        devices = _parse_arp_scan_output(ARP_SCAN_OUTPUT)
        for d in devices:
            self.assertNotIn("Interface", d.ip)
            self.assertNotIn("Starting", d.ip)
            self.assertNotIn("packets", d.ip)

    def test_unknown_vendor_becomes_none(self):
        devices = _parse_arp_scan_output(ARP_SCAN_OUTPUT)
        unknown = next(d for d in devices if d.ip == "192.168.1.10")
        self.assertIsNone(unknown.vendor)

    def test_empty_output_returns_empty_list(self):
        self.assertEqual(_parse_arp_scan_output(""), [])


class DiscoverLocalDevicesTest(unittest.TestCase):
    def test_returns_empty_when_no_arp_table(self):
        with patch("home_cinema_control.network.devices.ARP_TABLE_PATH") as mock_path:
            mock_path.exists.return_value = False
            result = discover_local_devices()
        self.assertEqual(result, [])

    def test_returns_empty_when_arp_scan_not_found(self):
        with patch("home_cinema_control.network.devices.ARP_TABLE_PATH") as mock_path, \
             patch("subprocess.run", side_effect=FileNotFoundError):
            mock_path.exists.return_value = True
            result = discover_local_devices()
        self.assertEqual(result, [])

    def test_returns_sorted_by_ip(self):
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout=ARP_SCAN_OUTPUT)
        with patch("home_cinema_control.network.devices.ARP_TABLE_PATH") as mock_path, \
             patch("subprocess.run", return_value=completed):
            mock_path.exists.return_value = True
            result = discover_local_devices()
        ips = [d.ip for d in result]
        self.assertEqual(ips, sorted(ips, key=lambda ip: tuple(int(p) for p in ip.split("."))))
