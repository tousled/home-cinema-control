import unittest
from types import SimpleNamespace
from unittest.mock import patch

from home_cinema_control.playback.oppo_lifecycle import OppoPlaybackLifecycleService
from home_cinema_control.playback.state import BridgePlaybackState


class OppoPlaybackLifecycleServiceTest(unittest.TestCase):
    def test_prepare_playback_start_restores_svm_before_qpl_logging(self):
        calls = []
        service = OppoPlaybackLifecycleService()

        with (
            patch(
                "home_cinema_control.playback.oppo_lifecycle.prepare_oppo_observation_mode",
                side_effect=lambda config: calls.append(("prepare", config)),
            ),
            patch(
                "home_cinema_control.playback.oppo_lifecycle.log_oppo_qpl_state",
                side_effect=lambda config, label: calls.append(("qpl", config, label)),
            ),
        ):
            service.prepare_playback_start({"oppo": {}})

        self.assertEqual(
            [("prepare", {"oppo": {}}), ("qpl", {"oppo": {}}, "playback_application_start")],
            calls,
        )

    def test_configure_observed_reporting_builds_media_server_dependencies(self):
        service = OppoPlaybackLifecycleService()
        playback_wiring = SimpleNamespace(playback_event_publisher="publisher")
        playback_session = object()
        playback_state = BridgePlaybackState()
        observed_sink = object()
        track_mapper = object()
        media_server_services = SimpleNamespace(
            create_observed_playback_consumer=lambda **kwargs: observed_sink,
            create_observed_track_mapper=lambda session, *, playback_state: track_mapper,
        )

        with patch(
            "home_cinema_control.playback.oppo_lifecycle.configure_oppo_observed_event_reporting",
            return_value=True,
        ) as configure:
            configured = service.configure_observed_event_reporting(
                playback_wiring=playback_wiring,
                media_server_services=media_server_services,
                playback_session=playback_session,
                playback_state=playback_state,
            )

        self.assertTrue(configured)
        configure.assert_called_once_with(
            playback_wiring=playback_wiring,
            observed_event_sink=observed_sink,
            track_mapper=track_mapper,
        )

    def test_finish_playback_delegates_power_down_policy(self):
        service = OppoPlaybackLifecycleService()
        config = {"oppo": {"always_on": False}}

        with patch(
            "home_cinema_control.playback.oppo_lifecycle.power_down_after_playback_if_configured"
        ) as power_down:
            service.finish_playback(config)

        power_down.assert_called_once_with(config)

    def test_stop_active_playback_delegates_replacement_policy(self):
        service = OppoPlaybackLifecycleService()
        state = BridgePlaybackState()
        config = {"oppo": {}}

        with patch(
            "home_cinema_control.playback.oppo_lifecycle.stop_active_player_playback_before_replacement"
        ) as stop:
            service.stop_active_playback_before_replacement(state, config)

        stop.assert_called_once_with(state, config)


if __name__ == "__main__":
    unittest.main()
