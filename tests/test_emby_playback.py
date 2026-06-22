import unittest

from home_cinema_control.media_servers.emby.playback import (
    MediaContentKind,
    MediaServerPlaybackContext,
    MediaServerPlaybackEventPublisher,
    MediaServerPlaybackSource,
)


class FakeResponse:
    status_code = 204
    text = ""


class RecordingEmbyClient:
    def __init__(
            self,
            *,
            mark_unplayed_error=None,
            restore_position_error=None,
            stop_session_error=None,
    ):
        self.calls = []
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


class MediaServerPlaybackSourceTest(unittest.TestCase):
    def test_maps_matched_media_source_with_parent_item_metadata(self):
        source = MediaServerPlaybackSource.from_emby_item(
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
        source = MediaServerPlaybackSource.from_emby_item(
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
        source = MediaServerPlaybackSource.from_emby_item(
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
        source = MediaServerPlaybackSource.from_emby_item(
            {"Type": "MusicVideo", "Name": "Live at the Arena", "MediaSources": []},
            "source-1",
        )

        self.assertEqual(MediaContentKind.CONCERT, source.content_kind)

    def test_maps_live_tv_program_to_live_tv(self):
        source = MediaServerPlaybackSource.from_emby_item(
            {"Type": "LiveTvProgram", "Name": "Evening News", "MediaSources": []},
            "source-1",
        )

        self.assertEqual(MediaContentKind.LIVE_TV, source.content_kind)

    def test_maps_unrecognized_type_to_other(self):
        source = MediaServerPlaybackSource.from_emby_item(
            {"Type": "AudioBook", "Name": "Some Book", "MediaSources": []},
            "source-1",
        )

        self.assertEqual(MediaContentKind.OTHER, source.content_kind)

    def test_maps_missing_type_to_other(self):
        source = MediaServerPlaybackSource.from_emby_item(
            {"Name": "Unknown", "MediaSources": []},
            "source-1",
        )

        self.assertEqual(MediaContentKind.OTHER, source.content_kind)


class MediaServerPlaybackContextTest(unittest.TestCase):
    def test_builds_context_from_playback_event(self):
        context = MediaServerPlaybackContext.from_event(
            {
                "ItemIds": ["movie-1"],
                "MediaSourceId": "source-1",
                "AudioStreamIndex": 4,
                "SubtitleStreamIndex": 7,
                "ControllingUserId": "tv-user",
                "SessionID": "tv-session",
                "PlaySessionId": "play-session",
                "StartPositionTicks": 420_000_000,
            },
            load_user_item=_unused_load_user_item,
        )

        self.assertEqual("movie-1", context.media_library_item_id)
        self.assertEqual("source-1", context.media_source_file_id)
        self.assertEqual(4, context.selected_audio_track_id)
        self.assertEqual(7, context.selected_subtitle_track_id)
        self.assertEqual("tv-user", context.media_server_user_id)
        self.assertEqual("tv-session", context.source_client_session_id)
        self.assertEqual(
            "play-session", context.media_server_playback_id
        )
        self.assertEqual(420_000_000, context.start_position_ticks)

    def test_loads_user_data_position_when_event_has_no_start_position(self):
        context = MediaServerPlaybackContext.from_event(
            {
                "ItemIds": ["movie-1"],
                "ControllingUserId": "tv-user",
            },
            load_user_item=lambda user_id, item_id: {
                "UserData": {"PlaybackPositionTicks": 120_000_000}
            },
        )

        self.assertEqual(120_000_000, context.start_position_ticks)

    def test_generates_playback_id_when_event_has_no_play_session_id(self):
        context = MediaServerPlaybackContext.from_event(
            {"ItemIds": ["movie-1"], "StartPositionTicks": 0},
            load_user_item=_unused_load_user_item,
        )

        self.assertNotEqual("", context.media_server_playback_id)
        self.assertEqual(36, len(context.media_server_playback_id))

    def test_uses_play_session_id_from_event_when_present(self):
        context = MediaServerPlaybackContext.from_event(
            {
                "ItemIds": ["movie-1"],
                "StartPositionTicks": 0,
                "PlaySessionId": "server-provided-session",
            },
            load_user_item=_unused_load_user_item,
        )

        self.assertEqual("server-provided-session", context.media_server_playback_id)


class MediaServerPlaybackEventPublisherTest(unittest.TestCase):
    def test_started_uses_resume_position_and_play_session_id(self):
        client = RecordingEmbyClient()
        publisher = MediaServerPlaybackEventPublisher(
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
        publisher = MediaServerPlaybackEventPublisher(
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
        publisher = MediaServerPlaybackEventPublisher(
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
        publisher = MediaServerPlaybackEventPublisher(
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
        publisher = MediaServerPlaybackEventPublisher(
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
        publisher = MediaServerPlaybackEventPublisher(
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
        publisher = MediaServerPlaybackEventPublisher(
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
        publisher = MediaServerPlaybackEventPublisher(
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
        publisher = MediaServerPlaybackEventPublisher(
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
        publisher = MediaServerPlaybackEventPublisher(
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
        publisher = MediaServerPlaybackEventPublisher(
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
        publisher = MediaServerPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(),
        )

        publisher.stopped(position_seconds=66, duration_seconds=120)

        self.assertEqual(
            {"session_id": "tv-session", "payload": {"Command": "Stop"}},
            client.calls[-1][1],
        )

    def test_stopped_skips_source_client_cleanup_without_a_session_id(self):
        client = RecordingEmbyClient()
        publisher = MediaServerPlaybackEventPublisher(
            client,
            bridge_session_id="bridge-session",
            context=_context(source_client_session_id=None),
        )

        publisher.stopped(position_seconds=66, duration_seconds=120)

        self.assertEqual(["stopped"], [call[0] for call in client.calls])

    def test_stopped_does_not_fail_when_source_client_cleanup_fails(self):
        client = RecordingEmbyClient(stop_session_error=TimeoutError("emby timeout"))
        publisher = MediaServerPlaybackEventPublisher(
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


def _unused_load_user_item(user_id, item_id):
    raise AssertionError("load_user_item should not be called")


if __name__ == "__main__":
    unittest.main()
