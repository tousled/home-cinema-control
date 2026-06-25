import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from fastapi.testclient import TestClient

from home_cinema_control.config.models import OppoConfig
from home_cinema_control.web.api_app import create_api_app
from home_cinema_control.web.api_runtime import WebApiRuntime


def _make_client(*, config=None, sanitized=None):
    config = config or {}
    sanitized = sanitized or config

    runtime = MagicMock()
    runtime.has_active_playback.return_value = False
    config_service = MagicMock()
    config_service.load_config.return_value = config
    config_service.sanitize.side_effect = lambda x: x
    config_service.prepare_submitted_config.side_effect = lambda x: x
    config_service.oppo.side_effect = lambda current_config=None: OppoConfig.model_validate(
        (current_config or config).get("oppo") or {}
    )

    api_runtime = WebApiRuntime(
        runtime=runtime,
        config_service=config_service,
        config_file=Path("/tmp/config.json"),
        log_file=Path("/tmp/emby_xnoppo_client_logging.log"),
        frontend_dist_dir=Path("/tmp/frontend/dist"),
    )
    return TestClient(create_api_app(api_runtime)), runtime, config_service


class OppoAdvancedDefaultsRouteTest(unittest.TestCase):
    def test_returns_pydantic_model_defaults(self):
        client, _, _ = _make_client()

        resp = client.get("/api/v1/oppo/advanced-defaults")

        self.assertEqual(200, resp.status_code)
        self.assertEqual(
            {
                "connection_timeout_seconds": 10.0,
                "playback_start_timeout_seconds": 30.0,
                "nfs_mount_timeout_seconds": 30.0,
                "autoscript": False,
            },
            resp.json(),
        )


class OppoKeyRouteTest(unittest.TestCase):
    def test_pon_uses_typed_bluray_disc_mode_for_second_eject(self):
        client, _, _ = _make_client(
            config={"oppo": {"ip": "192.168.1.10", "bluray_disc_mode": True}}
        )
        oppo_client = MagicMock()

        with (
            patch(
                "home_cinema_control.web.oppo_routes.send_remote_login_notification"
            ) as send_remote_login_notification,
            patch("home_cinema_control.web.oppo_routes.check_oppo_control_api", return_value=0),
            patch(
                "home_cinema_control.web.oppo_routes.OppoControlApiClient.from_config",
                return_value=oppo_client,
            ),
            patch("home_cinema_control.web.oppo_routes.time.sleep"),
        ):
            resp = client.get("/api/v1/oppo/key/PON")

        self.assertEqual(200, resp.status_code)
        send_remote_login_notification.assert_called_once_with("192.168.1.10")
        oppo_client.send_remote_key.assert_has_calls([call("EJT"), call("EJT")])


if __name__ == "__main__":
    unittest.main()
