import unittest

from home_cinema_control.playback.startup.factory import create_playback_startup_wiring


def _config(*, tv_enabled, av_enabled, tv_model="", av_model=""):
    return {
        "oppo": {"ip": "192.168.1.100"},
        "tv": {"enabled": tv_enabled, "model": tv_model},
        "av": {"enabled": av_enabled, "model": av_model},
    }


class TestPlaybackStartupWiringDisabled(unittest.TestCase):
    def test_both_disabled_does_not_raise(self):
        wiring = create_playback_startup_wiring(_config(tv_enabled=False, av_enabled=False))
        self.assertIsNotNone(wiring.startup_orchestrator)

    def test_both_disabled_adapters_are_none(self):
        wiring = create_playback_startup_wiring(_config(tv_enabled=False, av_enabled=False))
        self.assertIsNone(wiring.startup_orchestrator._television)
        self.assertIsNone(wiring.startup_orchestrator._av_receiver)

    def test_tv_disabled_av_disabled_empty_models_do_not_raise(self):
        wiring = create_playback_startup_wiring(
            _config(tv_enabled=False, av_enabled=False, tv_model="", av_model="")
        )
        self.assertIsNone(wiring.startup_orchestrator._television)
        self.assertIsNone(wiring.startup_orchestrator._av_receiver)

    def test_tv_disabled_av_enabled_known_model_does_not_raise(self):
        wiring = create_playback_startup_wiring(
            _config(tv_enabled=False, av_enabled=True, av_model="SCRIPTS")
        )
        self.assertIsNone(wiring.startup_orchestrator._television)
        self.assertIsNotNone(wiring.startup_orchestrator._av_receiver)

    def test_tv_enabled_unknown_model_raises(self):
        with self.assertRaises(ValueError):
            create_playback_startup_wiring(
                _config(tv_enabled=True, av_enabled=False, tv_model="UNKNOWN")
            )

    def test_av_enabled_unknown_model_raises(self):
        with self.assertRaises(ValueError):
            create_playback_startup_wiring(
                _config(tv_enabled=False, av_enabled=True, av_model="UNKNOWN")
            )
