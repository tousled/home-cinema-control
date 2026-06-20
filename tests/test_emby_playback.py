import unittest

from home_cinema_control.media_servers.common.playback_event_publisher import (
    MediaServerPlaybackContext,
)
from home_cinema_control.media_servers.emby.playback import EmbyPlaybackEventPublisher


class FakeResponse:
    status_code = 204
    text = ""


class RecordingEmbyClient:
    def __init__(self, *, mark_unplayed_error=None, restore_position_error=None):
        self.calls = []
        self.mark_unplayed_error = mark_unplayed_error
        self.restore_position_error = restore_position_error

    def notify_playback_started(self, payload):
        self.calls.append(("started", payload))
        return FakeResponse()

    def report_playback_progress(self, payload):
        self.calls.append(("progress", payload))
        return FakeResponse()

    def notify_playback_stopped(self, payload):
        self.calls.append(("stopped", payload))
        return FakeResponse()

    def mark_item_unplayed(self, user_id, item_id):
        if self.mark_unplayed_error is not None:
            raise self.mark_unplayed_error
        self.calls.append(("mark_unplayed", {"user_id": user_id, "item_id": item_id}))
        return FakeResponse()

    def set_item_playback_position(self, user_id, item_id, payload):
        if self.restore_position_error is not None:
            raise self.restore_position_error
        self.calls.append((
            "set_position",
            {"user_id": user_id, "item_id": item_id, "payload": payload},
        ))
        return FakeResponse()


class EmbyPlaybackEventPublisherTest(unittest.TestCase):
    def test_started_uses_resume_position_and_play_session_id(self):
        client = RecordingEmbyClient()
        publisher = EmbyPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(start_position_ticks=420_000_000),
        )

        publisher.started()

        self.assertEqual("started", client.calls[0][0])
        payload = client.calls[0][1]
        self.assertEqual(420_000_000, payload["PositionTicks"])
        self.assertEqual("play-session", payload["PlaySessionId"])
        self.assertEqual("bridge-session", payload["SessionId"])
        self.assertEqual(["Video"], payload["QueueableMediaTypes"])

    def test_progress_uses_time_update_and_reports_every_configured_interval(self):
        client = RecordingEmbyClient()
        publisher = EmbyPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
            progress_interval_seconds=10,
        )

        publisher.progress(position_seconds=10, duration_seconds=100)
        publisher.progress(position_seconds=15, duration_seconds=100)
        publisher.progress(position_seconds=20, duration_seconds=100)

        self.assertEqual(["progress", "progress"], [call[0] for call in client.calls])
        self.assertEqual("TimeUpdate", client.calls[0][1]["EventName"])
        self.assertEqual(100_000_000, client.calls[0][1]["PositionTicks"])
        self.assertEqual(200_000_000, client.calls[1][1]["PositionTicks"])

    def test_progress_reports_immediately_when_position_moves_backwards(self):
        client = RecordingEmbyClient()
        publisher = EmbyPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
            progress_interval_seconds=10,
        )

        publisher.progress(position_seconds=600, duration_seconds=1000)
        publisher.progress(position_seconds=590, duration_seconds=1000)

        self.assertEqual(["progress", "progress"], [call[0] for call in client.calls])
        self.assertEqual(5_900_000_000, client.calls[1][1]["PositionTicks"])

    def test_stopped_reports_final_position_without_event_name(self):
        client = RecordingEmbyClient()
        publisher = EmbyPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
        )

        publisher.stopped(position_seconds=66, duration_seconds=100)

        self.assertEqual("stopped", client.calls[0][0])
        payload = client.calls[0][1]
        self.assertEqual(660_000_000, payload["PositionTicks"])
        self.assertEqual(1_000_000_000, payload["RunTimeTicks"])
        self.assertNotIn("EventName", payload)

    def test_stopped_marks_item_unplayed_and_restores_resume_when_stop_was_not_natural_end(self):
        client = RecordingEmbyClient()
        publisher = EmbyPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
        )

        publisher.stopped(position_seconds=66, duration_seconds=100, played=False)

        self.assertEqual(
            ["stopped", "mark_unplayed", "set_position"],
            [call[0] for call in client.calls],
        )
        self.assertEqual(
            {"user_id": "tv-user", "item_id": "movie-1"},
            client.calls[1][1],
        )
        self.assertEqual(
            {
                "user_id": "tv-user",
                "item_id": "movie-1",
                "payload": {
                    "ItemId": "movie-1",
                    "PlaybackPositionTicks": 660_000_000,
                    "Played": False,
                },
            },
            client.calls[2][1],
        )

    def test_stopped_does_not_mark_item_unplayed_without_resume_position(self):
        client = RecordingEmbyClient()
        publisher = EmbyPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
        )

        publisher.stopped(position_seconds=0, duration_seconds=100, played=False)

        self.assertEqual(["stopped"], [call[0] for call in client.calls])

    def test_stopped_does_not_fail_when_mark_unplayed_fails(self):
        client = RecordingEmbyClient(mark_unplayed_error=TimeoutError("emby timeout"))
        publisher = EmbyPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
        )

        response = publisher.stopped(
            position_seconds=66,
            duration_seconds=100,
            played=False,
        )

        self.assertIsInstance(response, FakeResponse)
        self.assertEqual(["stopped"], [call[0] for call in client.calls])

    def test_stopped_does_not_fail_when_restore_resume_position_fails(self):
        client = RecordingEmbyClient(restore_position_error=TimeoutError("emby timeout"))
        publisher = EmbyPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
        )

        response = publisher.stopped(
            position_seconds=66,
            duration_seconds=100,
            played=False,
        )

        self.assertIsInstance(response, FakeResponse)
        self.assertEqual(["stopped", "mark_unplayed"], [call[0] for call in client.calls])

    def test_progress_adapts_domain_seconds_to_emby_ticks(self):
        client = RecordingEmbyClient()
        publisher = EmbyPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
        )

        publisher.progress(position_seconds=12, duration_seconds=120)

        payload = client.calls[0][1]
        self.assertEqual(120_000_000, payload["PositionTicks"])
        self.assertEqual(1_200_000_000, payload["RunTimeTicks"])

    def test_stopped_adapts_domain_seconds_to_emby_ticks(self):
        client = RecordingEmbyClient()
        publisher = EmbyPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
        )

        publisher.stopped(position_seconds=66, duration_seconds=120)

        self.assertEqual("stopped", client.calls[0][0])
        payload = client.calls[0][1]
        self.assertEqual(660_000_000, payload["PositionTicks"])
        self.assertEqual(1_200_000_000, payload["RunTimeTicks"])

    def test_stopped_is_idempotent(self):
        client = RecordingEmbyClient()
        publisher = EmbyPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
        )

        first_response = publisher.stopped(position_seconds=66, duration_seconds=120)
        second_response = publisher.stopped(position_seconds=67, duration_seconds=120)

        self.assertIsInstance(first_response, FakeResponse)
        self.assertIsNone(second_response)
        self.assertEqual(["stopped"], [call[0] for call in client.calls])


def _context(start_position_ticks=0):
    return MediaServerPlaybackContext(
        media_library_item_id="movie-1",
        media_source_file_id="source-1",
        selected_audio_track_id=1,
        selected_subtitle_track_id=-1,
        media_server_user_id="tv-user",
        source_client_session_id="tv-session",
        media_server_playback_id="play-session",
        start_position_ticks=start_position_ticks,
    )


if __name__ == "__main__":
    unittest.main()
