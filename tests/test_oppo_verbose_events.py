import unittest

from home_cinema_control.devices.oppo.verbose_events import (
    _split_complete_lines,
    normalize_oppo_tcp_command,
    parse_verbose_event,
)


class OppoVerboseEventsTest(unittest.TestCase):
    def test_parse_verbose_event_splits_code_and_payload(self):
        event = parse_verbose_event("@UPL PLAY")

        self.assertEqual("@UPL PLAY", event.raw)
        self.assertEqual("UPL", event.code)
        self.assertEqual("PLAY", event.payload)

    def test_parse_verbose_event_accepts_ok_response(self):
        event = parse_verbose_event("@OK PAUSE")

        self.assertEqual("OK", event.code)
        self.assertEqual("PAUSE", event.payload)

    def test_normalize_oppo_tcp_command_adds_prefix_and_carriage_return(self):
        self.assertEqual(b"#SVM 2\r", normalize_oppo_tcp_command("SVM 2"))
        self.assertEqual(b"#QPL\r", normalize_oppo_tcp_command("#qpl"))

    def test_split_complete_lines_keeps_partial_tail(self):
        lines, pending = _split_complete_lines("@OK PLAY\r@UPL PA")

        self.assertEqual(["@OK PLAY"], lines)
        self.assertEqual("@UPL PA", pending)


if __name__ == "__main__":
    unittest.main()
