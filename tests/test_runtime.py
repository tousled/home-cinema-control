import json
import logging
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from home_cinema_control.runtime import (
    HomeCinemaControlRuntime,
    JsonLinesFormatter,
    build_runtime_paths,
    configure_logging,
)
from home_cinema_control.playback.diagnostics import PlaybackDiagnostic


from home_cinema_control.playback.intent import PlaybackIntent
from home_cinema_control.playback.state import BridgePlaybackState


class FakePlaybackState(BridgePlaybackState):
    def __init__(self):
        super().__init__()
        self.playstate = "Free"


class FakeEmbySession:
    def __init__(self):
        self.config = None


class FakeWebSocket:
    def __init__(self):
        self.config = None
        self.config_file = None
        self.language = None
        self.emby_session = FakeEmbySession()
        self.playback_state = FakePlaybackState()
        self.started = False
        self.played_data = None
        self.stopped = False
        self.updated_configs = []

    def run(self):
        self.started = True

    def update_config(self, config):
        self.updated_configs.append(config)
        self.config = config
        self.emby_session.config = config

    def stop(self):
        self.stopped = True

    def _play(self, data):
        self.played_data = data


class RuntimeTest(unittest.TestCase):
    def tearDown(self):
        logging.basicConfig(handlers=[], force=True)

    def test_build_runtime_paths(self):
        paths = build_runtime_paths("/app", "/config/config.json")

        self.assertEqual(Path("/app"), paths.base_dir)
        self.assertEqual(Path("/config/config.json"), paths.config_file)
        self.assertEqual(Path("/app/emby_xnoppo_client_logging.log"), paths.log_file)

    def test_reports_not_connected_without_playback_listener(self):
        with self._runtime(configured=False) as runtime:
            state = runtime.get_state()

        self.assertEqual("0.5.1", state["Version"])
        self.assertEqual("Not_Connected", state["Playstate"])
        self.assertIsNone(state["ActiveSession"])

    def test_does_not_start_playback_listener_when_config_is_incomplete(self):
        with self._runtime(configured=False) as runtime:
            started = runtime.start_playback_listener_if_configured()

        self.assertFalse(started)
        self.assertIsNone(runtime.emby_websocket)

    def test_starts_playback_listener_when_config_is_complete(self):
        with self._runtime(configured=True) as runtime:
            started = runtime.start_playback_listener_if_configured()
            runtime.websocket_thread.join(timeout=1)

        self.assertTrue(started)
        self.assertIsInstance(runtime.emby_websocket, FakeWebSocket)
        self.assertTrue(runtime.emby_websocket.started)
        self.assertEqual(
            "http://emby.local",
            runtime.emby_websocket.config["media_server"]["server_url"],
        )
        self.assertIn("msg-startup-received", runtime.emby_websocket.language)

    def test_save_config_updates_active_websocket_config(self):
        with self._runtime(configured=True) as runtime:
            runtime.start_playback_listener_if_configured()
            runtime.websocket_thread.join(timeout=1)

            config = runtime.load_config()
            config["media_server"]["server_url"] = "http://updated.local"
            runtime.save_config(config)

        self.assertEqual(
            "http://updated.local",
            runtime.emby_websocket.config["media_server"]["server_url"],
        )
        self.assertEqual(
            "http://updated.local",
            runtime.emby_websocket.emby_session.config["media_server"]["server_url"],
        )
        self.assertEqual([config], runtime.emby_websocket.updated_configs)

    def test_start_movie_delegates_to_active_websocket(self):
        with self._runtime(configured=True) as runtime:
            runtime.start_playback_listener_if_configured()
            runtime.websocket_thread.join(timeout=1)

            runtime.start_movie({"ItemIds": ["1"]})

        self.assertEqual({"ItemIds": ["1"]}, runtime.emby_websocket.played_data)

    def test_get_state_reports_active_session_as_typed_status(self):
        with self._runtime(configured=True) as runtime:
            runtime.start_playback_listener_if_configured()
            runtime.websocket_thread.join(timeout=1)
            playback_state = runtime.emby_websocket.playback_state
            playback_state.start_loading(_intent())

            state = runtime.get_state()

        self.assertEqual("media-1", state["ActiveSession"]["media_item_id"])
        self.assertEqual("source-1", state["ActiveSession"]["media_source_id"])
        self.assertEqual(2, state["ActiveSession"]["selected_audio_track_id"])

    def test_set_last_diagnostic_records_latest_and_history(self):
        with self._runtime(configured=True) as runtime:
            runtime.start_playback_listener_if_configured()
            runtime.websocket_thread.join(timeout=1)

            runtime.set_last_diagnostic(PlaybackDiagnostic(
                code="OPPO_UNAVAILABLE",
                severity="error",
                component="oppo",
                reason="OPPO unavailable",
                suggestion="Check IP",
                timestamp=123,
            ))

            state = runtime.get_state()

        self.assertEqual("OPPO_UNAVAILABLE", state["LastDiagnostic"]["code"])
        self.assertEqual("OPPO_UNAVAILABLE", state["DiagnosticHistory"][0]["code"])

    def test_clear_last_diagnostic_preserves_history(self):
        with self._runtime(configured=True) as runtime:
            runtime.start_playback_listener_if_configured()
            runtime.websocket_thread.join(timeout=1)
            runtime.set_last_diagnostic(PlaybackDiagnostic(
                code="PATH_TEST_FAILED",
                severity="error",
                component="path",
                reason="Bad path",
                suggestion="Fix path",
                timestamp=456,
            ))

            runtime.clear_last_diagnostic()
            state = runtime.get_state()

        self.assertIsNone(state["LastDiagnostic"])
        self.assertEqual("PATH_TEST_FAILED", state["DiagnosticHistory"][0]["code"])

    def test_support_summary_is_sanitized_runtime_context(self):
        with self._runtime(configured=True) as runtime:
            runtime.start_playback_listener_if_configured()
            runtime.websocket_thread.join(timeout=1)
            runtime.set_last_diagnostic(PlaybackDiagnostic(
                code="TEST",
                severity="info",
                component="system",
                reason="Reason",
                suggestion="Suggestion",
                timestamp=789,
            ))

            summary = runtime.get_support_summary()

        self.assertEqual("0.5.1", summary["version"])
        self.assertEqual("TEST", summary["last_diagnostic"]["code"])
        self.assertIn("resources", summary)

    def test_configure_logging_reports_when_application_logs_are_disabled(self):
        output = StringIO()

        with redirect_stdout(output):
            configure_logging(
                {"app": {"log_level": 0}},
                Path("unused.log"),
            )

        self.assertIn("app.log_level=0", output.getvalue())
        self.assertIn("normal application logs are disabled", output.getvalue())

    def _runtime(self, *, configured):
        return RuntimeFixture(configured=configured)


class JsonLinesFormatterTest(unittest.TestCase):
    def test_formats_record_as_single_json_line(self):
        record = logging.LogRecord(
            name="home_cinema_control.test",
            level=logging.WARNING,
            pathname=__file__,
            lineno=1,
            msg="OPPO mount failed",
            args=(),
            exc_info=None,
        )

        line = JsonLinesFormatter().format(record)
        parsed = json.loads(line)

        self.assertEqual("WARNING", parsed["level"])
        self.assertEqual("home_cinema_control.test", parsed["logger"])
        self.assertEqual("OPPO mount failed", parsed["message"])
        self.assertIn("timestamp", parsed)

    def test_folds_traceback_into_message_field(self):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="home_cinema_control.test",
                level=logging.ERROR,
                pathname=__file__,
                lineno=1,
                msg="Unhandled error",
                args=(),
                exc_info=sys.exc_info(),
            )

        line = JsonLinesFormatter().format(record)
        parsed = json.loads(line)

        self.assertIn("Unhandled error", parsed["message"])
        self.assertIn("ValueError: boom", parsed["message"])
        self.assertIn("\n", parsed["message"])


class RuntimeFixture:
    def __init__(self, *, configured):
        self.configured = configured
        self.temp_dir = None
        self.runtime = None

    def __enter__(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        base_dir = Path(self.temp_dir.name)
        config_file = base_dir / "config.json"
        secrets_file = base_dir / "secrets.json"
        config = {
            "media_server": {
                "type": "emby",
                "server_url": "http://emby.local" if self.configured else "",
                "display_name": "Emby",
                "access_token_configured": self.configured,
            },
            "tv": {"enabled": False},
            "av": {"enabled": False},
            "servers": [],
            "language": "es-ES",
            "DebugLevel": 0,
        }
        config_file.write_text(json.dumps(config), "utf-8")
        secrets_file.write_text(
            json.dumps(
                {
                    "media_server": {
                        "access_token": "token" if self.configured else "",
                        "user_id": "user-id" if self.configured else "",
                    }
                }
            ),
            "utf-8",
        )

        self.runtime = HomeCinemaControlRuntime(
            paths=build_runtime_paths(base_dir, config_file),
            version="0.5.1",
            websocket_factory=FakeWebSocket,
            exit_process=lambda _code: None,
        )
        return self.runtime

    def __exit__(self, exc_type, exc, traceback):
        self.temp_dir.cleanup()


def _intent() -> PlaybackIntent:
    return PlaybackIntent(
        media_item_id="media-1",
        media_source_id="source-1",
        source_user_id="user-1",
        source_client_session_id="session-1",
        source_device_id="device-1",
        source_device_name="Living Room TV",
        start_position_seconds=12,
        selected_audio_track_id=2,
        selected_subtitle_track_id=-1,
    )


if __name__ == "__main__":
    unittest.main()
