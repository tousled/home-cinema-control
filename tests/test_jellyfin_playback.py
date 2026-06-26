import unittest

from home_cinema_control.media_servers.common.playback_event_publisher import (
    MediaServerPlaybackContext,
)
from home_cinema_control.media_servers.jellyfin.playback import (
    JellyfinPlaybackEventPublisher,
)


class FakeResponse:
    status_code = 204
    text = ""


class RecordingJellyfinClient:
    def __init__(
        self,
        *,
        sessions=None,
        mark_unplayed_error=None,
        restore_position_error=None,
        stop_session_error=None,
        session_lookup_error=None,
    ):
        self.calls = []
        self.sessions = sessions if sessions is not None else []
        self.mark_unplayed_error = mark_unplayed_error
        self.restore_position_error = restore_position_error
        self.stop_session_error = stop_session_error
        self.session_lookup_error = session_lookup_error

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
        self.calls.append(
            (
                "set_position",
                {"user_id": user_id, "item_id": item_id, "payload": payload},
            )
        )
        return FakeResponse()

    def stop_session_playback(self, session_id, payload):
        if self.stop_session_error is not None:
            raise self.stop_session_error
        self.calls.append(("stop_session", {"session_id": session_id, "payload": payload}))
        return FakeResponse()

    def send_general_command(self, session_id, command):
        if self.stop_session_error is not None:
            raise self.stop_session_error
        self.calls.append(("general_command", {"session_id": session_id, "command": command}))
        return FakeResponse()

    def get_sessions_by_user(self, user_id):
        if self.session_lookup_error is not None:
            raise self.session_lookup_error
        return self.sessions


class JellyfinPlaybackEventPublisherTest(unittest.TestCase):
    def test_started_uses_resume_position_and_play_session_id(self):
        client = RecordingJellyfinClient()
        publisher = JellyfinPlaybackEventPublisher(
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
        self.assertEqual("movie-1", payload["ItemId"])
        self.assertEqual("source-1", payload["MediaSourceId"])
        self.assertEqual(["Video"], payload["QueueableMediaTypes"])

    def test_progress_uses_time_update_and_reports_every_configured_interval(self):
        client = RecordingJellyfinClient()
        publisher = JellyfinPlaybackEventPublisher(
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
        self.assertEqual(1_000_000_000, client.calls[0][1]["RunTimeTicks"])
        self.assertEqual(200_000_000, client.calls[1][1]["PositionTicks"])

    def test_progress_reports_immediately_when_position_moves_backwards(self):
        client = RecordingJellyfinClient()
        publisher = JellyfinPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
            progress_interval_seconds=10,
        )

        publisher.progress(position_seconds=600, duration_seconds=1000)
        publisher.progress(position_seconds=590, duration_seconds=1000)

        self.assertEqual(["progress", "progress"], [call[0] for call in client.calls])
        self.assertEqual(5_900_000_000, client.calls[1][1]["PositionTicks"])

    def test_report_event_updates_active_tracks(self):
        client = RecordingJellyfinClient()
        publisher = JellyfinPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
        )

        publisher.report_event(
            "AudioTrackChange",
            position_ticks=123,
            audio_track_id=4,
            subtitle_track_id=7,
        )

        payload = client.calls[0][1]
        self.assertEqual("AudioTrackChange", payload["EventName"])
        self.assertEqual(4, payload["AudioStreamIndex"])
        self.assertEqual(7, payload["SubtitleStreamIndex"])

    def test_stopped_reports_final_position_without_event_name(self):
        client = RecordingJellyfinClient()
        publisher = JellyfinPlaybackEventPublisher(
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
        client = RecordingJellyfinClient()
        publisher = JellyfinPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
        )

        publisher.stopped(position_seconds=66, duration_seconds=100, played=False)

        self.assertEqual(
            [
                "stopped",
                "mark_unplayed",
                "set_position",
                "stop_session",
                "stop_session",
            ],
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
        client = RecordingJellyfinClient()
        publisher = JellyfinPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
        )

        publisher.stopped(position_seconds=0, duration_seconds=100, played=False)

        self.assertEqual(
            ["stopped", "stop_session", "stop_session"],
            [call[0] for call in client.calls],
        )

    def test_stopped_does_not_fail_when_mark_unplayed_fails(self):
        client = RecordingJellyfinClient(mark_unplayed_error=TimeoutError("timeout"))
        publisher = JellyfinPlaybackEventPublisher(
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
        self.assertEqual(
            ["stopped", "stop_session", "stop_session"],
            [call[0] for call in client.calls],
        )

    def test_stopped_is_idempotent(self):
        client = RecordingJellyfinClient()
        publisher = JellyfinPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
        )

        first_response = publisher.stopped(position_seconds=66, duration_seconds=120)
        second_response = publisher.stopped(position_seconds=67, duration_seconds=120)

        self.assertIsInstance(first_response, FakeResponse)
        self.assertIsNone(second_response)
        self.assertEqual(
            ["stopped", "stop_session", "stop_session"],
            [call[0] for call in client.calls],
        )

    def test_stopped_clears_stale_source_client_session_with_double_stop(self):
        client = RecordingJellyfinClient()
        publisher = JellyfinPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
        )

        publisher.stopped(position_seconds=66, duration_seconds=120)

        self.assertEqual(
            [
                ("stop_session", {"session_id": "tv-session", "payload": {"Command": "Stop"}}),
                ("stop_session", {"session_id": "tv-session", "payload": {"Command": "Stop"}}),
            ],
            client.calls[-2:],
        )

    def test_stopped_clears_sessions_actively_playing_the_item_excludes_idle(self):
        client = RecordingJellyfinClient(
            sessions=[
                _session_payload(
                    session_id="bridge-session",
                    device_id="home-cinema-control",
                    user_id="tv-user",
                    item_id="movie-1",
                ),
                _session_payload(
                    session_id="web-session",
                    device_id="web-device",
                    device_name="Chrome",
                    client_name="Jellyfin Web",
                    user_id="tv-user",
                    item_id="movie-1",
                ),
                _session_payload(
                    session_id="phone-session",
                    device_id="phone-device",
                    device_name="OPPO Find X9 Pro",
                    client_name="Jellyfin Android",
                    user_id="tv-user",
                    item_id="movie-1",
                ),
                _session_payload(
                    session_id="mobile-frozen-session",
                    device_id="mobile-device",
                    device_name="Pixel",
                    client_name="Jellyfin Android",
                    user_id="tv-user",
                    item_id=None,
                ),
                _session_payload(
                    session_id="tablet-session",
                    device_id="tablet-device",
                    device_name="iPad",
                    client_name="Jellyfin iOS",
                    user_id="tv-user",
                    item_id="movie-2",
                ),
                _session_payload(
                    session_id="guest-session",
                    device_id="guest-device",
                    user_id="guest-user",
                    item_id="movie-1",
                ),
            ]
        )
        publisher = JellyfinPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(source_client_session_id="web-session"),
        )

        publisher.stopped(position_seconds=66, duration_seconds=120)

        stop_calls = [c for c in client.calls if c[0] == "stop_session"]
        # mobile-frozen-session has item_id=None (already idle) — must NOT receive Playstate Stop
        self.assertEqual(
            [
                ("stop_session", {"session_id": "web-session", "payload": {"Command": "Stop"}}),
                ("stop_session", {"session_id": "web-session", "payload": {"Command": "Stop"}}),
                ("stop_session", {"session_id": "phone-session", "payload": {"Command": "Stop"}}),
                ("stop_session", {"session_id": "phone-session", "payload": {"Command": "Stop"}}),
            ],
            stop_calls,
        )

    def test_stopped_sends_back_to_all_non_bridge_sessions(self):
        client = RecordingJellyfinClient(
            sessions=[
                _session_payload(
                    session_id="bridge-session",
                    device_id="home-cinema-control",
                    user_id="tv-user",
                    item_id="movie-1",
                ),
                _session_payload(
                    session_id="web-session",
                    device_id="web-device",
                    device_name="Chrome",
                    client_name="Jellyfin Web",
                    user_id="tv-user",
                    item_id="movie-1",
                ),
                _session_payload(
                    session_id="mobile-idle-session",
                    device_id="mobile-device",
                    device_name="OPPO Find X9 Pro",
                    client_name="Jellyfin Android",
                    user_id="tv-user",
                    item_id=None,
                ),
            ]
        )
        publisher = JellyfinPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(source_client_session_id="web-session"),
        )

        publisher.stopped(position_seconds=66, duration_seconds=120)

        back_calls = [c for c in client.calls if c[0] == "general_command"]
        navigated_ids = [c[1]["session_id"] for c in back_calls]
        # Idle sessions get Back even though they don't get Playstate Stop — this
        # is what closes the remote-player screen after the user presses Stop.
        self.assertIn("mobile-idle-session", navigated_ids)
        # The source also gets Back so the queue page navigates away.
        self.assertIn("web-session", navigated_ids)
        # Bridge (HCC itself) must never receive Back.
        self.assertNotIn("bridge-session", navigated_ids)
        self.assertTrue(all(c[1]["command"] == "Back" for c in back_calls))

    def test_stopped_skips_source_client_cleanup_without_a_session_id(self):
        client = RecordingJellyfinClient()
        publisher = JellyfinPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(source_client_session_id=None),
        )

        publisher.stopped(position_seconds=66, duration_seconds=120)

        self.assertEqual(["stopped"], [call[0] for call in client.calls])

    def test_stopped_does_not_fail_when_source_client_cleanup_fails(self):
        client = RecordingJellyfinClient(stop_session_error=TimeoutError("timeout"))
        publisher = JellyfinPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
        )

        response = publisher.stopped(position_seconds=66, duration_seconds=120)

        self.assertIsInstance(response, FakeResponse)
        self.assertEqual(["stopped"], [call[0] for call in client.calls])


def _context(start_position_ticks=0, source_client_session_id="tv-session"):
    return MediaServerPlaybackContext(
        media_library_item_id="movie-1",
        media_source_file_id="source-1",
        selected_audio_track_id=1,
        selected_subtitle_track_id=-1,
        media_server_user_id="tv-user",
        source_client_session_id=source_client_session_id,
        media_server_playback_id="play-session",
        start_position_ticks=start_position_ticks,
    )


def _session_payload(
    *,
    session_id,
    device_id,
    user_id,
    item_id,
    device_name="",
    client_name="",
):
    payload = {
        "Id": session_id,
        "DeviceId": device_id,
        "DeviceName": device_name,
        "Client": client_name,
        "UserId": user_id,
        "PlayState": {},
    }
    if item_id is not None:
        payload["NowPlayingItem"] = {"Id": item_id, "Name": "Movie"}
    return payload


if __name__ == "__main__":
    unittest.main()
