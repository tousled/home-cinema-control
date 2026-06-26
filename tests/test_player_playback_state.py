import unittest

from home_cinema_control.playback.player_state import (
    PlayerPlaybackLifecyclePhase,
    PlayerPlaybackState,
    PlayerPlaybackStatus,
    lifecycle_phase_for_status,
)


class PlayerPlaybackStateTest(unittest.TestCase):
    def test_lifecycle_phase_for_active_status(self):
        self.assertEqual(
            PlayerPlaybackLifecyclePhase.ACTIVE,
            lifecycle_phase_for_status(PlayerPlaybackStatus.PLAY),
        )

    def test_lifecycle_phase_for_idle_status(self):
        self.assertEqual(
            PlayerPlaybackLifecyclePhase.IDLE,
            lifecycle_phase_for_status(PlayerPlaybackStatus.MEDIA_CENTER),
        )

    def test_lifecycle_phase_for_transition_status(self):
        self.assertEqual(
            PlayerPlaybackLifecyclePhase.TRANSITION,
            lifecycle_phase_for_status(PlayerPlaybackStatus.LOADING),
        )

    def test_lifecycle_phase_for_unknown_status(self):
        self.assertEqual(
            PlayerPlaybackLifecyclePhase.UNKNOWN,
            lifecycle_phase_for_status("NOT_A_PLAYER_STATE"),
        )

    def test_state_helpers(self):
        paused = PlayerPlaybackState(
            status=PlayerPlaybackStatus.PAUSE,
            lifecycle_phase=PlayerPlaybackLifecyclePhase.ACTIVE,
            raw_response="@OK PAUSE",
            ok=True,
        )
        idle = PlayerPlaybackState(
            status=PlayerPlaybackStatus.HOME_MENU,
            lifecycle_phase=PlayerPlaybackLifecyclePhase.IDLE,
            raw_response="@OK HOME MENU",
            ok=True,
        )

        self.assertTrue(paused.is_paused)
        self.assertFalse(paused.is_playing)
        self.assertFalse(paused.is_idle)
        self.assertTrue(idle.is_idle)


if __name__ == "__main__":
    unittest.main()
