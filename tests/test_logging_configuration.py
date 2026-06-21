import logging
import logging.handlers
import tempfile
import unittest
from pathlib import Path

from home_cinema_control.runtime import configure_logging


class ConfigureLoggingTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.log_file = Path(self._tmp.name) / "test.log"

    def tearDown(self):
        root = logging.getLogger()
        for handler in list(root.handlers):
            handler.close()
            root.removeHandler(handler)
        self._tmp.cleanup()

    def _handler_levels(self):
        root = logging.getLogger()
        file_handler = next(
            h
            for h in root.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        )
        console_handler = next(
            h for h in root.handlers if type(h) is logging.StreamHandler
        )
        return file_handler.level, console_handler.level

    def test_console_inherits_file_level_by_default(self):
        configure_logging({"app": {"log_level": 1}}, self.log_file)

        file_level, console_level = self._handler_levels()
        self.assertEqual(logging.INFO, file_level)
        self.assertEqual(logging.INFO, console_level)

    def test_console_level_independent_of_file_level(self):
        configure_logging(
            {"app": {"log_level": 2, "console_log_level": 1}}, self.log_file
        )

        file_level, console_level = self._handler_levels()
        self.assertEqual(logging.DEBUG, file_level)
        self.assertEqual(logging.INFO, console_level)
        # Root must be the most verbose of the two so each handler can filter.
        self.assertEqual(logging.DEBUG, logging.getLogger().level)

    def test_quiet_console_with_verbose_file(self):
        configure_logging(
            {"app": {"log_level": 2, "console_log_level": 0}}, self.log_file
        )

        file_level, console_level = self._handler_levels()
        self.assertEqual(logging.DEBUG, file_level)
        self.assertEqual(logging.CRITICAL, console_level)


if __name__ == "__main__":
    unittest.main()
