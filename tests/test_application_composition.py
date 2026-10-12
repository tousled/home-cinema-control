import tempfile
import unittest
from pathlib import Path

from home_cinema_control.composition import build_application_composition
from home_cinema_control.playback.events import PlaybackDomainEvent
from home_cinema_control.telemetry.consumer import TelemetryConsumer
from home_cinema_control.telemetry.events import TelemetryEvent


class ApplicationCompositionTest(unittest.TestCase):
    def test_telemetry_consumer_is_wired_to_the_shared_application_bus(self):
        with tempfile.TemporaryDirectory() as directory:
            base_dir = Path(directory)
            config_file = base_dir / "config.json"
            config_file.write_text("{}", encoding="utf-8")

            composition = build_application_composition(
                base_dir=base_dir,
                config_file=config_file,
                version="1.4.0",
            )

            telemetry_subscriptions = [
                subscription
                for subscription in composition.event_bus._subscriptions
                if subscription.event_type is TelemetryEvent
            ]
            playback_telemetry_subscriptions = [
                subscription
                for subscription in composition.event_bus._subscriptions
                if subscription.event_type is PlaybackDomainEvent
            ]

            self.assertIs(composition.runtime.application_event_bus, composition.event_bus)
            self.assertEqual(1, len(telemetry_subscriptions))
            self.assertEqual(1, len(playback_telemetry_subscriptions))
            self.assertIsInstance(
                telemetry_subscriptions[0].consumer,
                TelemetryConsumer,
            )

            composition.event_bus.shutdown(drain=True)


if __name__ == "__main__":
    unittest.main()
