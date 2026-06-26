import unittest
from types import SimpleNamespace

from home_cinema_control.playback.active_context import ActivePlaybackRuntimeContext


class ActivePlaybackRuntimeContextTest(unittest.TestCase):
    def test_exposes_runtime_handles_while_active(self):
        context = ActivePlaybackRuntimeContext()
        publisher = object()
        oppo_playback = object()

        context.activate(
            SimpleNamespace(
                playback_event_publisher=publisher,
                startup_wiring=SimpleNamespace(media_player=oppo_playback),
            )
        )

        self.assertIs(publisher, context.publisher)
        self.assertIs(oppo_playback, context.oppo_playback)

    def test_clears_runtime_handles(self):
        context = ActivePlaybackRuntimeContext()
        context.activate(
            SimpleNamespace(
                playback_event_publisher=object(),
                startup_wiring=SimpleNamespace(media_player=object()),
            )
        )

        context.clear()

        self.assertIsNone(context.publisher)
        self.assertIsNone(context.oppo_playback)


if __name__ == "__main__":
    unittest.main()
