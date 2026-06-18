import unittest

from home_cinema_control.config.models import HccConfig


class TestConfigDisabledDevice(unittest.TestCase):
    def test_disabled_av_with_empty_model_is_valid(self):
        config = HccConfig(**{"av": {"enabled": False, "model": ""}})
        self.assertFalse(config.av.enabled)
        self.assertEqual("", config.av.model)

    def test_disabled_tv_with_empty_model_is_valid(self):
        config = HccConfig(**{"tv": {"enabled": False, "model": ""}})
        self.assertFalse(config.tv.enabled)
        self.assertEqual("", config.tv.model)

    def test_disabled_av_preserves_ip_on_round_trip(self):
        original = HccConfig(**{"av": {"enabled": True, "model": "DENON", "ip": "192.168.1.20"}})
        data = original.model_dump()
        data["av"]["enabled"] = False
        reloaded = HccConfig(**data)
        self.assertFalse(reloaded.av.enabled)
        self.assertEqual("DENON", reloaded.av.model)
        self.assertEqual("192.168.1.20", reloaded.av.ip)

    def test_disabled_tv_preserves_details_on_round_trip(self):
        original = HccConfig(**{"tv": {"enabled": True, "model": "LG", "ip": "192.168.1.10"}})
        data = original.model_dump()
        data["tv"]["enabled"] = False
        reloaded = HccConfig(**data)
        self.assertFalse(reloaded.tv.enabled)
        self.assertEqual("LG", reloaded.tv.model)
        self.assertEqual("192.168.1.10", reloaded.tv.ip)

    def test_missing_enabled_key_defaults_to_false_for_tv(self):
        config = HccConfig(**{"tv": {"model": "LG"}})
        self.assertFalse(config.tv.enabled)

    def test_missing_enabled_key_defaults_to_false_for_av(self):
        config = HccConfig(**{"av": {"model": "DENON"}})
        self.assertFalse(config.av.enabled)

    def test_enabled_av_round_trips_correctly(self):
        original = HccConfig(**{"av": {"enabled": True, "model": "YAMAHA", "ip": "10.0.0.5"}})
        reloaded = HccConfig(**original.model_dump())
        self.assertTrue(reloaded.av.enabled)
        self.assertEqual("YAMAHA", reloaded.av.model)

    def test_enabled_tv_round_trips_correctly(self):
        original = HccConfig(**{"tv": {"enabled": True, "model": "LG", "ip": "10.0.0.6"}})
        reloaded = HccConfig(**original.model_dump())
        self.assertTrue(reloaded.tv.enabled)
        self.assertEqual("LG", reloaded.tv.model)
