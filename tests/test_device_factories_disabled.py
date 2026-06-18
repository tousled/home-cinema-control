import unittest

from home_cinema_control.devices.av.factory import create_av_receiver_or_none
from home_cinema_control.devices.tv.factory import create_tv_controller_or_none


class TestCreateTvControllerOrNone(unittest.TestCase):
    def test_returns_none_when_tv_disabled(self):
        config = {"tv": {"enabled": False, "model": "LG", "ip": "192.168.1.10"}}
        self.assertIsNone(create_tv_controller_or_none(config))

    def test_returns_none_when_enabled_key_absent(self):
        # Backwards compat: missing enabled key defaults to disabled (False)
        config = {"tv": {"model": "LG", "ip": "192.168.1.10"}}
        self.assertIsNone(create_tv_controller_or_none(config))

    def test_returns_none_when_tv_section_absent(self):
        self.assertIsNone(create_tv_controller_or_none({}))

    def test_raises_for_unsupported_model_when_enabled(self):
        config = {"tv": {"enabled": True, "model": "SAMSUNG"}}
        with self.assertRaises(ValueError):
            create_tv_controller_or_none(config)

    def test_raises_for_empty_model_when_enabled(self):
        config = {"tv": {"enabled": True, "model": ""}}
        with self.assertRaises(ValueError):
            create_tv_controller_or_none(config)

    def test_returns_controller_for_known_model_when_enabled(self):
        config = {"tv": {"enabled": True, "model": "SCRIPTS"}}
        controller = create_tv_controller_or_none(config)
        self.assertIsNotNone(controller)


class TestCreateAvReceiverOrNone(unittest.TestCase):
    def test_returns_none_when_av_disabled(self):
        config = {"av": {"enabled": False, "model": "DENON", "ip": "192.168.1.20"}}
        self.assertIsNone(create_av_receiver_or_none(config))

    def test_returns_none_when_enabled_key_absent(self):
        config = {"av": {"model": "DENON", "ip": "192.168.1.20"}}
        self.assertIsNone(create_av_receiver_or_none(config))

    def test_returns_none_when_av_section_absent(self):
        self.assertIsNone(create_av_receiver_or_none({}))

    def test_raises_for_unsupported_model_when_enabled(self):
        config = {"av": {"enabled": True, "model": "UNKNOWN_BRAND"}}
        with self.assertRaises(ValueError):
            create_av_receiver_or_none(config)

    def test_raises_for_empty_model_when_enabled(self):
        config = {"av": {"enabled": True, "model": ""}}
        with self.assertRaises(ValueError):
            create_av_receiver_or_none(config)

    def test_returns_receiver_for_known_model_when_enabled(self):
        config = {"av": {"enabled": True, "model": "SCRIPTS"}}
        receiver = create_av_receiver_or_none(config)
        self.assertIsNotNone(receiver)
