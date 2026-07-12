import unittest

from home_cinema_control.media_servers.common.playback_event_publisher import (
    MediaServerPlaybackContext,
)
from home_cinema_control.media_servers.emby.item_mapper import (
    media_server_playback_source_from_item,
)
from home_cinema_control.playback.content_kind import MediaContentKind
from home_cinema_control.media_servers.emby.playback import EmbyPlaybackEventPublisher


class FakeResponse:
    status_code = 204
    text = ""


class RecordingEmbyClient:
    def __init__(
            self,
            *,
            sessions=None,
            mark_unplayed_error=None,
            restore_position_error=None,
            stop_session_error=None,
    ):
        self.calls = []
        self.sessions = sessions if sessions is not None else []
        self.mark_unplayed_error = mark_unplayed_error
        self.restore_position_error = restore_position_error
        self.stop_session_error = stop_session_error

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

    def stop_session_playback(self, session_id, payload):
        if self.stop_session_error is not None:
            raise self.stop_session_error
        self.calls.append(("stop_session", {"session_id": session_id, "payload": payload}))
        return FakeResponse()

    def get_sessions_by_user(self, user_id):
        return self.sessions


class MediaServerPlaybackSourceTest(unittest.TestCase):
    def test_maps_matched_media_source_with_parent_item_metadata(self):
        source = media_server_playback_source_from_item(
            {
                "Type": "Movie",
                "Name": "Aquaman",
                "ProductionYear": 2018,
                "MediaSources": [
                    {
                        "Id": "source-1",
                        "Path": "/movies/aquaman.mkv",
                        "Container": "mkv",
                        "RunTimeTicks": 72_000_000_000,
                    },
                ],
            },
            "source-1",
        )

        self.assertEqual("/movies/aquaman.mkv", source.path)
        self.assertEqual("mkv", source.container)
        self.assertEqual(7200, source.duration_seconds)
        self.assertEqual(2018, source.production_year)
        self.assertEqual("Aquaman", source.title)
        self.assertEqual(MediaContentKind.MOVIE, source.content_kind)

    def test_falls_back_to_full_item_when_media_source_not_found(self):
        source = media_server_playback_source_from_item(
            {
                "Type": "Episode",
                "Name": "Pilot",
                "Path": "/tv/show/episode1.mkv",
                "Container": "mkv",
                "MediaSources": [],
            },
            "missing-source",
        )

        self.assertEqual("/tv/show/episode1.mkv", source.path)
        self.assertEqual(MediaContentKind.EPISODE, source.content_kind)

    def test_defaults_duration_to_zero_when_runtime_ticks_is_invalid(self):
        source = media_server_playback_source_from_item(
            {
                "Type": "Movie",
                "Name": "Movie",
                "MediaSources": [
                    {"Id": "source-1", "Path": "p", "Container": "mkv", "RunTimeTicks": "not-a-number"},
                ],
            },
            "source-1",
        )

        self.assertEqual(0, source.duration_seconds)

    def test_maps_music_video_to_concert(self):
        source = media_server_playback_source_from_item(
            {"Type": "MusicVideo", "Name": "Live at the Arena", "MediaSources": []},
            "source-1",
        )

        self.assertEqual(MediaContentKind.CONCERT, source.content_kind)

    def test_maps_live_tv_program_to_live_tv(self):
        source = media_server_playback_source_from_item(
            {"Type": "LiveTvProgram", "Name": "Evening News", "MediaSources": []},
            "source-1",
        )

        self.assertEqual(MediaContentKind.LIVE_TV, source.content_kind)

    def test_maps_unrecognized_type_to_other(self):
        source = media_server_playback_source_from_item(
            {"Type": "AudioBook", "Name": "Some Book", "MediaSources": []},
            "source-1",
        )

        self.assertEqual(MediaContentKind.OTHER, source.content_kind)

    def test_maps_missing_type_to_other(self):
        source = media_server_playback_source_from_item(
            {"Name": "Unknown", "MediaSources": []},
            "source-1",
        )

        self.assertEqual(MediaContentKind.OTHER, source.content_kind)


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
            ["stopped", "mark_unplayed", "set_position", "stop_session", "stop_session"],
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

        self.assertEqual(
            ["stopped", "stop_session", "stop_session"],
            [call[0] for call in client.calls],
        )

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
        self.assertEqual(
            ["stopped", "stop_session", "stop_session"],
            [call[0] for call in client.calls],
        )

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
        self.assertEqual(
            ["stopped", "mark_unplayed", "stop_session", "stop_session"],
            [call[0] for call in client.calls],
        )

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
        self.assertEqual(
            ["stopped", "stop_session", "stop_session"],
            [call[0] for call in client.calls],
        )

    def test_stopped_clears_stale_source_client_session(self):
        client = RecordingEmbyClient()
        publisher = EmbyPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
        )

        publisher.stopped(position_seconds=66, duration_seconds=120)

        self.assertEqual(
            {"session_id": "tv-session", "payload": {"Command": "Stop"}},
            client.calls[-1][1],
        )

    def test_stopped_clears_sessions_actively_playing_the_item_excludes_idle(self):
        client = RecordingEmbyClient(
            sessions=[
                _session_payload(
                    session_id="bridge-session",
                    device_id="home-cinema-control",
                    user_id="tv-user",
                    item_id="movie-1",
                ),
                _session_payload(
                    session_id="tv-session",
                    device_id="tv-device",
                    user_id="tv-user",
                    item_id="movie-1",
                ),
                _session_payload(
                    session_id="extra-tv-session",
                    device_id="tv-device",
                    user_id="tv-user",
                    item_id="movie-1",
                ),
                _session_payload(
                    session_id="idle-session",
                    device_id="mobile-device",
                    user_id="tv-user",
                    item_id=None,
                ),
                _session_payload(
                    session_id="other-item",
                    device_id="tablet-device",
                    user_id="tv-user",
                    item_id="movie-2",
                ),
                _session_payload(
                    session_id="other-user",
                    device_id="guest-device",
                    user_id="guest-user",
                    item_id="movie-1",
                ),
            ]
        )
        publisher = EmbyPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(source_client_session_id="tv-session"),
        )

        publisher.stopped(position_seconds=66, duration_seconds=120)

        stop_calls = [call for call in client.calls if call[0] == "stop_session"]
        self.assertEqual(
            [
                ("stop_session", {"session_id": "tv-session", "payload": {"Command": "Stop"}}),
                ("stop_session", {"session_id": "tv-session", "payload": {"Command": "Stop"}}),
                ("stop_session", {"session_id": "extra-tv-session", "payload": {"Command": "Stop"}}),
                ("stop_session", {"session_id": "extra-tv-session", "payload": {"Command": "Stop"}}),
            ],
            stop_calls,
        )

    def test_stopped_skips_source_client_cleanup_without_a_session_id(self):
        client = RecordingEmbyClient()
        publisher = EmbyPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(source_client_session_id=None),
        )

        publisher.stopped(position_seconds=66, duration_seconds=120)

        self.assertEqual(["stopped"], [call[0] for call in client.calls])

    def test_stopped_does_not_fail_when_source_client_cleanup_fails(self):
        client = RecordingEmbyClient(stop_session_error=TimeoutError("emby timeout"))
        publisher = EmbyPlaybackEventPublisher(
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
        session_id: str,
        device_id: str,
        user_id: str,
        item_id: str | None,
) -> dict:
    payload = {
        "Id": session_id,
        "DeviceId": device_id,
        "DeviceName": device_id,
        "UserId": user_id,
    }
    if item_id is not None:
        payload["NowPlayingItem"] = {"Id": item_id, "Name": "Movie"}
    return payload


if __name__ == "__main__":
    unittest.main()
