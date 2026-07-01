import json
import unittest

from home_cinema_control.web.support_report import (
    DEFAULT_LOG_LINES,
    MAX_LOG_LINES,
    MIN_LOG_LINES,
    build_diagnostic_report,
    clamp_log_lines,
    collect_redaction_targets,
    redact_text,
)


def _log_line(message, level="INFO"):
    return json.dumps({
        "timestamp": "01/01/2026 12:00:00 PM",
        "level": level,
        "logger": "home_cinema_control",
        "message": message,
    })


class ClampLogLinesTest(unittest.TestCase):
    def test_default_when_none(self):
        self.assertEqual(clamp_log_lines(None), DEFAULT_LOG_LINES)

    def test_clamps_below_minimum(self):
        self.assertEqual(clamp_log_lines(1), MIN_LOG_LINES)

    def test_clamps_above_maximum(self):
        self.assertEqual(clamp_log_lines(5000), MAX_LOG_LINES)

    def test_passes_through_in_range(self):
        self.assertEqual(clamp_log_lines(50), 50)


class CollectRedactionTargetsTest(unittest.TestCase):
    def test_collects_device_ips_credentials_urls_and_paths(self):
        config = {
            "oppo": {"ip": "192.168.1.10"},
            "av": {"ip": "192.168.1.20"},
            "tv": {"ip": "192.168.1.30", "mac": "AA:BB:CC:DD:EE:FF", "sony_psk": "s3cr3tpsk"},
            "smb": {"username": "guest", "password": "hunter2"},
            "app": {"update_webhook_url": "https://hooks.example.com/abc"},
            "media_servers": {
                "providers": {
                    "emby": {
                        "server_url": "http://192.168.1.50:8096",
                        "access_token": "tok_1234567890",
                        "user_id": "user_1234567890",
                        "playback": {
                            "path_mappings": [
                                {"source_path": "/mnt/nas/Pelis de Pedro", "player_path": "/mnt/nfs1"}
                            ]
                        },
                    }
                }
            },
        }

        targets = collect_redaction_targets(config)

        self.assertEqual(targets["192.168.1.10"], "IP")
        self.assertEqual(targets["192.168.1.20"], "IP")
        self.assertEqual(targets["192.168.1.30"], "IP")
        self.assertEqual(targets["AA:BB:CC:DD:EE:FF"], "MAC")
        self.assertEqual(targets["s3cr3tpsk"], "CREDENTIAL")
        self.assertEqual(targets["guest"], "CREDENTIAL")
        self.assertEqual(targets["hunter2"], "CREDENTIAL")
        self.assertEqual(targets["https://hooks.example.com/abc"], "URL")
        self.assertEqual(targets["http://192.168.1.50:8096"], "URL")
        self.assertEqual(targets["tok_1234567890"], "CREDENTIAL")
        self.assertEqual(targets["user_1234567890"], "CREDENTIAL")
        self.assertEqual(targets["/mnt/nas/Pelis de Pedro"], "PATH")
        self.assertEqual(targets["/mnt/nfs1"], "PATH")

    def test_skips_short_or_empty_values(self):
        config = {"smb": {"username": "ab"}, "tv": {"ip": ""}}

        targets = collect_redaction_targets(config)

        self.assertEqual(targets, {})


class RedactTextTest(unittest.TestCase):
    def test_literal_match_is_redacted(self):
        targets = {"hunter2": "CREDENTIAL"}

        redacted, count = redact_text("smb login failed with password hunter2", targets)

        self.assertNotIn("hunter2", redacted)
        self.assertEqual(count, 1)

    def test_longer_value_redacted_before_embedded_ip_fragments_it(self):
        targets = {
            "http://192.168.1.50:8096": "URL",
            "192.168.1.50": "IP",
        }

        redacted, _count = redact_text("connecting to http://192.168.1.50:8096/emby", targets)

        self.assertNotIn("192.168.1.50", redacted)
        self.assertIn("[REDACTED:URL]", redacted)
        self.assertNotIn("[REDACTED:IP]", redacted)

    def test_ipv4_safety_net_catches_ip_not_in_config(self):
        redacted, count = redact_text("device seen at 10.0.0.55 during discovery", {})

        self.assertNotIn("10.0.0.55", redacted)
        self.assertEqual(count, 1)


class BuildDiagnosticReportTest(unittest.TestCase):
    def test_redacts_summary_and_log_and_sums_counts(self):
        config = {"oppo": {"ip": "192.168.1.10"}}
        sanitized_summary = {
            "last_diagnostic": {
                "code": "OPPO_MOUNT_FAILED",
                "details": {"detail": "could not reach 192.168.1.10"},
            }
        }
        raw_log_text = "\n".join([
            _log_line("startup ok"),
            _log_line("mount failed for 192.168.1.10", level="ERROR"),
        ])

        result = build_diagnostic_report(
            config=config,
            sanitized_summary=sanitized_summary,
            raw_log_text=raw_log_text,
            max_lines=200,
        )

        self.assertNotIn("192.168.1.10", result.report)
        self.assertEqual(result.log_lines_included, 2)
        self.assertGreaterEqual(result.redaction_count, 2)

    def test_respects_max_lines(self):
        raw_log_text = "\n".join(_log_line(f"line {i}") for i in range(50))

        result = build_diagnostic_report(
            config={},
            sanitized_summary={},
            raw_log_text=raw_log_text,
            max_lines=10,
        )

        self.assertEqual(result.log_lines_included, 10)
        self.assertIn(": line 49", result.report)
        self.assertNotIn(": line 39", result.report)


if __name__ == "__main__":
    unittest.main()
