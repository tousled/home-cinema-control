import unittest
from types import SimpleNamespace

from home_cinema_control.home_automation.home_assistant_consumer import (
    HomeAssistantWebhookConsumer,
)
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


class FakeHttp:
    def post(self, url, **kwargs):
        self.url = url
        self.kwargs = kwargs
        return SimpleNamespace(raise_for_status=lambda: None)


if __name__ == "__main__":
    unittest.main()
