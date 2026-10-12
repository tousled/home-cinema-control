import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from home_cinema_control.home_automation.home_assistant_consumer import (
    HomeAssistantWebhookConsumer,
)
from home_cinema_control.home_automation.home_assistant_transport import (
    HomeAssistantWebhookClient,
    HomeAssistantWebhookError,
)
from home_cinema_control.home_automation.delivery_status import (
    HomeAssistantDeliveryStatus,
    home_assistant_configuration_fingerprint,
)
from home_cinema_control.home_automation.delivery_status_store import (
    HomeAssistantDeliveryStatusStore,
)
from home_cinema_control.notifications.models import UpdateNotification
from home_cinema_control.playback.events import PlaybackEvent, PlaybackEventType


class HomeAssistantWebhookConsumerTest(unittest.TestCase):
    def test_posts_neutral_event_payload(self):
        http = FakeHttp()
        consumer = HomeAssistantWebhookConsumer(
            base_url="http://ha.local:8123",
            webhook_id="secret/id",
            http_session=http,
        )

        consumer.consume(
            PlaybackEvent(
                event_id="event-1",
                session_id="session-1",
                event_type=PlaybackEventType.STARTED,
                media_type="movie",
                title="Example",
                source="emby",
                player="oppo",
            )
        )

        self.assertEqual("http://ha.local:8123/api/webhook/secret%2Fid", http.url)
        self.assertEqual("started", http.kwargs["json"]["event"])
        self.assertEqual("event-1", http.kwargs["json"]["event_id"])

    def test_posts_compact_update_payload(self):
        http = FakeHttp()
        consumer = HomeAssistantWebhookConsumer(
            base_url="http://ha.local:8123",
            webhook_id="secret/id",
            http_session=http,
        )

        consumer.send_update(
            UpdateNotification(
                current_version="1.4.0",
                latest_version="1.4.1",
                release_url="https://example.test/1.4.1",
                title="HCC 1.4.1 está disponible",
                message="HCC 1.4.1 disponible",
            )
        )

        self.assertEqual(
            {
                "event": "hcc_update_available",
                "current_version": "1.4.0",
                "latest_version": "1.4.1",
                "release_url": "https://example.test/1.4.1",
            },
            http.kwargs["json"],
        )

    def test_http_failure_does_not_expose_webhook_id(self):
        webhook_id = "secret-webhook-id"
        client = HomeAssistantWebhookClient(
            base_url="http://ha.local:8123",
            webhook_id=webhook_id,
            http_session=FailingHttp(status_code=500),
        )

        with self.assertRaises(HomeAssistantWebhookError) as raised:
            client.send({"event": "started"})

        self.assertNotIn(webhook_id, str(raised.exception))
        self.assertEqual(500, raised.exception.status_code)

    def test_playback_http_failure_is_logged_without_webhook_id(self):
        webhook_id = "secret-webhook-id"
        consumer = HomeAssistantWebhookConsumer(
            base_url="http://ha.local:8123",
            webhook_id=webhook_id,
            http_session=FailingHttp(status_code=500),
        )

        with self.assertLogs(
            "home_cinema_control.home_automation.home_assistant_consumer",
            level="WARNING",
        ) as logs:
            consumer.consume(
                PlaybackEvent(
                    event_id="event-1",
                    session_id="session-1",
                    event_type=PlaybackEventType.STARTED,
                )
            )

        self.assertNotIn(webhook_id, "\n".join(logs.output))

    def test_delivery_status_records_real_success_and_failure(self):
        status = HomeAssistantDeliveryStatus()
        client = HomeAssistantWebhookClient(
            base_url="http://ha.local:8123",
            webhook_id="secret-webhook-id",
            http_session=FakeHttp(),
            delivery_status=status,
        )

        client.send({"event": "started"})

        delivered = status.snapshot()
        self.assertEqual("delivered", delivered["status"])
        self.assertEqual("started", delivered["last_event"])
        self.assertIsNotNone(delivered["last_attempt_at"])
        self.assertIsNone(delivered["detail"])

        failing_client = HomeAssistantWebhookClient(
            base_url="http://ha.local:8123",
            webhook_id="secret-webhook-id",
            http_session=FailingHttp(status_code=503),
            delivery_status=status,
        )
        with self.assertRaises(HomeAssistantWebhookError):
            failing_client.send({"event": "paused"})

        failed = status.snapshot()
        self.assertEqual("failed", failed["status"])
        self.assertEqual("paused", failed["last_event"])
        self.assertEqual("status=503", failed["detail"])
        self.assertNotIn("secret-webhook-id", str(failed))

    def test_delivery_status_survives_restart_without_persisting_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "hcc_notifications.sqlite"
            status = HomeAssistantDeliveryStatus(
                store=HomeAssistantDeliveryStatusStore(store_path),
            )
            status.mark_delivered("started")

            restored = HomeAssistantDeliveryStatus(
                store=HomeAssistantDeliveryStatusStore(store_path),
            )

        self.assertEqual("delivered", restored.snapshot()["status"])
        self.assertEqual("started", restored.snapshot()["last_event"])
        self.assertNotIn("webhook", str(restored.snapshot()).lower())

    def test_delivery_status_becomes_pending_when_configuration_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "hcc_notifications.sqlite"
            first_fingerprint = home_assistant_configuration_fingerprint(
                "http://ha.local:8123",
                "first-secret",
            )
            second_fingerprint = home_assistant_configuration_fingerprint(
                "http://ha.local:8123",
                "second-secret",
            )
            first = HomeAssistantDeliveryStatus(
                store=HomeAssistantDeliveryStatusStore(store_path),
                configuration_fingerprint=first_fingerprint,
            )
            first.mark_delivered("started")

            changed = HomeAssistantDeliveryStatus(
                store=HomeAssistantDeliveryStatusStore(store_path),
                configuration_fingerprint=second_fingerprint,
            )

        self.assertEqual(
            {"status": "pending", "last_event": None, "last_attempt_at": None, "detail": None},
            changed.snapshot(),
        )

    def test_legacy_delivery_status_without_fingerprint_is_treated_as_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "hcc_notifications.sqlite"
            with sqlite3.connect(store_path) as connection:
                connection.execute(
                    """
                    CREATE TABLE home_assistant_delivery_status (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        status TEXT NOT NULL,
                        last_event TEXT,
                        last_attempt_at TEXT,
                        detail TEXT
                    )
                    """
                )
                connection.execute(
                    "INSERT INTO home_assistant_delivery_status VALUES (1, 'delivered', 'started', 'now', NULL)"
                )
                connection.commit()

            status = HomeAssistantDeliveryStatus(
                store=HomeAssistantDeliveryStatusStore(store_path),
                configuration_fingerprint="current-configuration",
            )

        self.assertEqual("pending", status.snapshot()["status"])



class FakeHttp:
    def post(self, url, **kwargs):
        self.url = url
        self.kwargs = kwargs
        return SimpleNamespace(raise_for_status=lambda: None)


class FailingHttp:
    def __init__(self, *, status_code):
        self.status_code = status_code

    def post(self, url, **kwargs):
        response = SimpleNamespace(status_code=self.status_code, url=url)

        def raise_for_status():
            error = RuntimeError(f"request failed for {url}")
            error.response = response
            raise error

        response.raise_for_status = raise_for_status
        return response


if __name__ == "__main__":
    unittest.main()
