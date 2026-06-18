import unittest

from home_cinema_control.playback.intent import PlaybackIntent, PlaybackOrigin
from home_cinema_control.playback.thread_lifecycle import PlaybackThreadLifecycle


class PlaybackThreadLifecycleTest(unittest.TestCase):
    def test_start_runs_playback_and_reloads_config(self):
        calls = []
        lifecycle = PlaybackThreadLifecycle(
            start_playback=lambda *args, **kwargs: calls.append(
                ("start", args, kwargs)
            ),
            reload_config=lambda: calls.append(("reload", None)),
            stop_active_playback=lambda: calls.append("stop_active"),
        )
        intent = _intent(media_item_id="1")

        lifecycle._run_start(intent, PlaybackOrigin.OBSERVED_TV_CLIENT)

        self.assertEqual("start", calls[0][0])
        self.assertEqual(intent, calls[0][1][0])
        self.assertEqual(PlaybackOrigin.OBSERVED_TV_CLIENT, calls[0][2]["origin"])
        self.assertEqual(("reload", None), calls[1])

    def test_replace_stops_active_playback_then_starts_replacement(self):
        calls = []
        lifecycle = PlaybackThreadLifecycle(
            start_playback=lambda *args, **kwargs: calls.append(
                ("start", args, kwargs)
            ),
            reload_config=lambda: None,
            stop_active_playback=lambda: calls.append("stop_active"),
            thread_factory=ImmediateThread,
        )
        lifecycle._active_thread = FakeActiveThread(calls)
        intent = _intent(media_item_id="2")

        lifecycle._run_replace(intent, PlaybackOrigin.REMOTE_CONTROL_COMMAND)

        self.assertEqual("stop_active", calls[0])
        self.assertEqual("join_active", calls[1])
        self.assertEqual("start", calls[2][0])
        self.assertEqual(intent, calls[2][1][0])
        self.assertEqual(PlaybackOrigin.REMOTE_CONTROL_COMMAND, calls[2][2]["origin"])

    def test_replace_is_accepted_when_no_replacement_is_running(self):
        calls = []
        lifecycle = PlaybackThreadLifecycle(
            start_playback=lambda *args, **kwargs: calls.append(
                ("start", args, kwargs)
            ),
            reload_config=lambda: None,
            stop_active_playback=lambda: calls.append("stop_active"),
            thread_factory=ImmediateThread,
        )
        intent = _intent(media_item_id="2")

        replaced = lifecycle.replace(
            intent,
            origin=PlaybackOrigin.REMOTE_CONTROL_COMMAND,
        )

        self.assertTrue(replaced)
        self.assertEqual("start", calls[0][0])
        self.assertEqual(intent, calls[0][1][0])

    def test_replace_marks_active_finish_as_replacement_until_joined(self):
        calls = []
        lifecycle = PlaybackThreadLifecycle(
            start_playback=lambda *args, **kwargs: calls.append(
                ("start", lifecycle.replacement_requested, args, kwargs)
            ),
            reload_config=lambda: None,
            stop_active_playback=lambda: calls.append(
                ("stop_active", lifecycle.replacement_requested)
            ),
            thread_factory=ImmediateThread,
        )
        lifecycle._active_thread = FakeActiveThread(calls)

        lifecycle._run_replace(
            _intent(media_item_id="2"),
            PlaybackOrigin.REMOTE_CONTROL_COMMAND,
        )

        self.assertEqual(("stop_active", True), calls[0])
        self.assertEqual("join_active", calls[1])
        self.assertFalse(calls[2][1])

    def test_replace_does_not_start_next_item_when_active_finish_failed(self):
        calls = []
        lifecycle = PlaybackThreadLifecycle(
            start_playback=lambda *args, **kwargs: calls.append(
                ("start", args, kwargs)
            ),
            reload_config=lambda: None,
            stop_active_playback=lambda: calls.append("stop_active"),
            thread_factory=ImmediateThread,
        )
        lifecycle._active_thread = FakeActiveThread(calls)
        lifecycle._last_playback_result = FakePlaybackResult(successful=False)

        lifecycle._run_replace(
            _intent(media_item_id="2"),
            PlaybackOrigin.REMOTE_CONTROL_COMMAND,
        )

        self.assertEqual(["stop_active", "join_active"], calls)

    def test_replace_ignores_request_when_replacement_is_already_running(self):
        lifecycle = PlaybackThreadLifecycle(
            start_playback=lambda *args, **kwargs: None,
            reload_config=lambda: None,
            stop_active_playback=lambda: None,
            thread_factory=ImmediateThread,
        )
        lifecycle._replacement_thread = FakeAliveThread()

        replaced = lifecycle.replace(
            _intent(media_item_id="2"),
            origin=PlaybackOrigin.REMOTE_CONTROL_COMMAND,
        )

        self.assertFalse(replaced)


class ImmediateThread:
    def __init__(self, *, target, args):
        self._target = target
        self._args = args
        self._alive = False

    def start(self):
        self._alive = True
        try:
            self._target(*self._args)
        finally:
            self._alive = False

    def is_alive(self):
        return self._alive


class FakeActiveThread:
    def __init__(self, calls):
        self._calls = calls

    def is_alive(self):
        return True

    def join(self, timeout=None):
        self._calls.append("join_active")


class FakeAliveThread:
    def is_alive(self):
        return True


class FakePlaybackResult:
    def __init__(self, *, successful):
        self.successful = successful


def _intent(*, media_item_id: str) -> PlaybackIntent:
    return PlaybackIntent(
        media_item_id=media_item_id,
        media_source_id="",
        source_user_id="",
        source_client_session_id=None,
        source_device_id="",
        source_device_name="",
        start_position_seconds=0,
        selected_audio_track_id=1,
        selected_subtitle_track_id=-1,
    )


if __name__ == "__main__":
    unittest.main()
