import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from home_cinema_control.notifications.models import (
    UpdateAvailableEvent,
    UpdateNotification,
)
from home_cinema_control.notifications.monitor import UpdateMonitor
from home_cinema_control.notifications.service import UpdateNotificationService
from home_cinema_control.notifications.state import NotificationStateStore
from home_cinema_control.playback.events import PlaybackEvent, PlaybackEventType
from home_cinema_control.playback.startup.models import DeviceCommandResult


def _notification(version="1.4.1"):
    return UpdateNotification(
        current_version="1.4.0",
        latest_version=version,
        release_url=f"https://example.test/{version}",
        title=f"HCC {version} disponible",
        message=f"HCC {version} disponible",
    )


class NotificationStateStoreTest(unittest.TestCase):
    def test_state_survives_a_new_store_instance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notifications.sqlite"
            NotificationStateStore(path).mark_notified("home_assistant", "1.4.1")

            restored = NotificationStateStore(path)
            self.assertEqual("1.4.1", restored.last_notified_version("home_assistant"))


class UpdateNotificationServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = NotificationStateStore(Path(self.temp_dir.name) / "state.sqlite")
        self.ha = FakeHomeAssistant()
        self.tv = FakeTv()
        self.config = {"tv": {"model": "LG", "enabled": True}}
        self.service = UpdateNotificationService(
            state_store=self.store,
            home_assistant_consumer=self.ha,
            television_factory=lambda _config: self.tv,
            config_provider=lambda: self.config,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_home_assistant_is_not_repeated_for_same_release(self):
        event = UpdateAvailableEvent(notification=_notification())

        self.service.consume(event)
        self.service.consume(event)

        self.assertEqual(1, len(self.ha.notifications))
        self.assertEqual("1.4.1", self.store.last_notified_version("home_assistant"))

    def test_home_assistant_and_tv_state_are_independent(self):
        event = UpdateAvailableEvent(notification=_notification())
        self.tv.result = DeviceCommandResult.failed("off")

        self.service.consume(event)
        self.service.consume(_started_event())

        self.assertEqual("1.4.1", self.store.last_notified_version("home_assistant"))
        self.assertIsNone(self.store.last_notified_version("lg_tv"))

        self.tv.result = DeviceCommandResult.success()
        self.service.consume(_started_event())

        self.assertEqual("1.4.1", self.store.last_notified_version("lg_tv"))
        self.assertEqual(
            ["HCC 1.4.1 disponible", "HCC 1.4.1 disponible"],
            self.tv.messages,
        )

    def test_unsupported_tv_is_not_recorded_as_delivered(self):
        self.tv.result = DeviceCommandResult.skipped("unsupported")

        self.service.consume(UpdateAvailableEvent(notification=_notification()))
        self.service.consume(_started_event())

        self.assertIsNone(self.store.last_notified_version("lg_tv"))


class UpdateMonitorTest(unittest.TestCase):
    def test_no_update_is_not_published(self):
        published = []
        monitor = UpdateMonitor(
            load_config=lambda: {"app": {}},
            publish=published.append,
            check_version=lambda *_args: SimpleNamespace(new_version=False),
        )

        monitor._check_once({"app": {}})

        self.assertEqual([], published)

    def test_new_version_is_published_without_blocking_the_caller(self):
        published = []
        checked = threading.Event()

        def check_version(_config, _current_version):
            checked.set()
            return SimpleNamespace(
                current_version="1.4.0",
                latest_version="1.4.1",
                release_url="https://example.test/1.4.1",
                new_version=True,
            )

        monitor = UpdateMonitor(
            load_config=lambda: {"app": {"version_check_interval_hours": 24}},
            publish=published.append,
            current_version="1.4.0",
            check_version=check_version,
        )
        monitor.start()
        self.assertTrue(checked.wait(timeout=1))
        monitor.stop()

        self.assertEqual(1, len(published))
        self.assertIsInstance(published[0], UpdateAvailableEvent)
        self.assertEqual("1.4.1", published[0].notification.latest_version)

    def test_check_failure_is_swallowed(self):
        monitor = UpdateMonitor(
            load_config=lambda: {"app": {}},
            publish=lambda _event: self.fail("must not publish"),
            check_version=lambda *_args: (_ for _ in ()).throw(RuntimeError("offline")),
        )

        monitor._check_once({"app": {}})


def _started_event():
    return PlaybackEvent(
        event_id="event-1",
        session_id="session-1",
        event_type=PlaybackEventType.STARTED,
    )


class FakeHomeAssistant:
    def __init__(self):
        self.notifications = []

    def send(self, payload):
        self.notifications.append(payload)


class FakeTv:
    def __init__(self):
        self.messages = []
        self.result = DeviceCommandResult.success()

    def show_notification(self, message):
        self.messages.append(message)
        return self.result


if __name__ == "__main__":
    unittest.main()
