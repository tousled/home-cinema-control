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

    def _handlers(self):
        root = logging.getLogger()
        file_handler = next(
            h
            for h in root.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        )
        console_handler = next(
            h for h in root.handlers if type(h) is logging.StreamHandler
        )
        return file_handler, console_handler

    def test_one_level_drives_both_file_and_console(self):
        configure_logging({"app": {"log_level": 1}}, self.log_file)

        file_handler, console_handler = self._handlers()
        # A single level is applied to both sinks via the root logger.
        self.assertEqual(logging.INFO, logging.getLogger().level)
        self.assertEqual(self.log_file, Path(file_handler.baseFilename))
        self.assertIsInstance(console_handler, logging.StreamHandler)

    def test_debug_level(self):
        configure_logging({"app": {"log_level": 2}}, self.log_file)
        self.assertEqual(logging.DEBUG, logging.getLogger().level)

    def test_off_level_is_critical(self):
        configure_logging({"app": {"log_level": 0}}, self.log_file)
        self.assertEqual(logging.CRITICAL, logging.getLogger().level)


if __name__ == "__main__":
    unittest.main()
