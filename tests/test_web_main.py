import unittest
from pathlib import Path
from unittest.mock import patch

from home_cinema_control.web.main import main


class MainEntrypointTest(unittest.TestCase):
    """Checkpoint 5's last step: the media_server -> media_servers migration
    is wired in at startup here, not inside load_effective_config. See
    .agents/specs/2026-06-23-media-server-multi-provider-config-design.md.
    """

    @patch("home_cinema_control.web.main.serve_web_app")
    @patch("home_cinema_control.web.main.prepare_runtime_for_web")
    @patch("home_cinema_control.web.main.build_web_runtime_composition")
    @patch("home_cinema_control.web.main.migrate_media_server_to_media_servers_on_disk")
    @patch("home_cinema_control.web.main.ensure_config_exists")
    def test_runs_migration_against_the_real_config_file_at_startup(
        self,
        mock_ensure_config_exists,
        mock_migrate,
        mock_build_composition,
        mock_prepare_runtime,
        mock_serve_web_app,
    ):
        mock_ensure_config_exists.return_value = Path("/data/config.json")

        main()

        mock_migrate.assert_called_once_with(Path("/data/config.json"))


class MainEntrypointPlaybackMigrationTest(unittest.TestCase):
    """Phase 7's last step of the scoped-paths-libraries-device spec: a
    second, separate migration runs right after the auth one, same call site.
    See .agents/specs/2026-06-23-media-server-scoped-paths-libraries-device.md.
    """

    @patch("home_cinema_control.web.main.serve_web_app")
    @patch("home_cinema_control.web.main.prepare_runtime_for_web")
    @patch("home_cinema_control.web.main.build_web_runtime_composition")
    @patch("home_cinema_control.web.main.migrate_playback_to_media_servers_on_disk")
    @patch("home_cinema_control.web.main.migrate_media_server_to_media_servers_on_disk")
    @patch("home_cinema_control.web.main.ensure_config_exists")
    def test_runs_playback_migration_against_the_real_config_file_at_startup(
            self,
            mock_ensure_config_exists,
            mock_migrate_media_server,
            mock_migrate_playback,
            mock_build_composition,
            mock_prepare_runtime,
            mock_serve_web_app,
    ):
        mock_ensure_config_exists.return_value = Path("/data/config.json")

        main()

        mock_migrate_playback.assert_called_once_with(Path("/data/config.json"))


if __name__ == "__main__":
    unittest.main()
