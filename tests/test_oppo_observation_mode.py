import unittest

from home_cinema_control.devices.oppo.observation_mode import (
    OppoObservationMode,
    resolve_oppo_observation_mode,
)


class OppoObservationModeTest(unittest.TestCase):
    def test_defaults_to_auto(self):
        self.assertEqual(
            OppoObservationMode.AUTO,
            resolve_oppo_observation_mode({}),
        )

    def test_legacy_stable_mode_resolves_to_auto_observation(self):
        self.assertEqual(
            OppoObservationMode.AUTO,
            resolve_oppo_observation_mode({"oppo": {"observation_mode": "stable"}}),
        )

    def test_legacy_verbose_mode_resolves_to_auto_observation(self):
        self.assertEqual(
            OppoObservationMode.AUTO,
            resolve_oppo_observation_mode(
                {"oppo": {"observation_mode": "oppo_verbose"}}
            ),
        )

    def test_polling_mode_disables_svm3_observation(self):
        self.assertEqual(
            OppoObservationMode.POLLING,
            resolve_oppo_observation_mode({"oppo": {"observation_mode": "polling"}}),
        )

    def test_unknown_mode_falls_back_to_auto(self):
        self.assertEqual(
            OppoObservationMode.AUTO,
            resolve_oppo_observation_mode(
                {"oppo": {"observation_mode": "unsupported"}}
            ),
        )


if __name__ == "__main__":
    unittest.main()
