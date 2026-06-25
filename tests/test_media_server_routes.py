import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests
from fastapi.testclient import TestClient

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

    api_runtime = WebApiRuntime(
        runtime=runtime,
        config_service=config_service,
        config_file=Path("/tmp/config.json"),
        log_file=Path("/tmp/emby_xnoppo_client_logging.log"),
        frontend_dist_dir=Path("/tmp/frontend/dist"),
    )
    return TestClient(create_api_app(api_runtime)), runtime, config_service


class MediaServerCheckRouteTest(unittest.TestCase):
    def _mock_setup_service(self, mock_setup_service, *, status_code=204):
        setup_service = MagicMock()
        setup_service.check_connection.return_value = MagicMock(status_code=status_code)
        mock_setup_service.return_value = setup_service
        return setup_service

    @patch("home_cinema_control.web.media_server_routes.media_server_setup_service")
    def test_saves_config_and_restarts_listener_on_success(self, mock_setup_service):
        self._mock_setup_service(mock_setup_service)
        client, runtime, config_service = _make_client(config={
            "media_server": {
                "type": "emby",
                "server_url": "http://emby.local",
                "access_token": "secret-token",
                "user_id": "emby-user",
            },
            "playback": {"hcc_controlled_device": "living-room-tv"},
        })

        resp = client.post("/api/v1/media-server/check", json={
            "media_server": {"type": "emby", "server_url": "http://emby.local"},
            "playback": {"hcc_controlled_device": "living-room-tv"},
        })

        self.assertEqual(200, resp.status_code)
        config_service.save_config.assert_called_once()
        runtime.restart_playback_listener.assert_called_once()
        runtime.restart_process.assert_not_called()

    @patch("home_cinema_control.web.media_server_routes.media_server_setup_service")
    def test_restarts_listener_even_when_runtime_is_already_connected(self, mock_setup_service):
        # The old "only start if Not_Connected" guard was the bug: it left a
        # stale listener thread/connection running after a switch. Always
        # restarting is what's actually safe now that restart_playback_listener
        # stops the old one first.
        self._mock_setup_service(mock_setup_service)
        client, runtime, config_service = _make_client(config={
            "media_server": {
                "type": "emby",
                "server_url": "http://emby.local",
                "access_token": "secret-token",
                "user_id": "emby-user",
            },
        })

        resp = client.post("/api/v1/media-server/check", json={
            "media_server": {"type": "emby", "server_url": "http://emby.local"},
        })

        self.assertEqual(200, resp.status_code)
        config_service.save_config.assert_called_once()
        runtime.restart_playback_listener.assert_called_once()
        runtime.restart_process.assert_not_called()

    @patch("home_cinema_control.web.media_server_routes.media_server_setup_service")
    def test_switch_requires_confirmation_when_active_playback_on_current_provider(
            self, mock_setup_service
    ):
        setup_service = self._mock_setup_service(mock_setup_service)
        client, runtime, config_service = _make_client(config={
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {"server_url": "http://emby.local", "access_token": "emby-token"},
                    "jellyfin": {
                        "server_url": "http://jellyfin.local",
                        "access_token": "jf-token",
                    },
                },
            },
        })
        runtime.has_active_playback.return_value = True

        resp = client.post("/api/v1/media-server/check", json={
            "media_server": {"type": "jellyfin", "server_url": "http://jellyfin.local"},
        })

        self.assertEqual(200, resp.status_code)
        self.assertTrue(resp.json()["switch_requires_confirmation"])
        self.assertEqual("emby", resp.json()["active_session_provider"])
        setup_service.check_connection.assert_called_once()
        config_service.save_config.assert_not_called()
        runtime.restart_playback_listener.assert_not_called()

    @patch("home_cinema_control.web.media_server_routes.media_server_setup_service")
    def test_check_with_minimal_body_preserves_other_sections_and_dispatches_target_type(
            self, mock_setup_service
    ):
        # Regression: the frontend only ever sends the media_server wire
        # shape here (type/server_url), never a complete config. Trusting
        # that submitted body as the whole config would wipe every other
        # section on save, and never resolving media_servers.active would
        # always dispatch to whatever the *current* (not target) provider is.
        self._mock_setup_service(mock_setup_service)
        client, runtime, config_service = _make_client(config={
            "media_servers": {
                "active": "emby",
                "providers": {"emby": {"server_url": "http://emby.local"}},
            },
            "oppo": {"ip": "192.168.1.50"},
        })

        resp = client.post("/api/v1/media-server/check", json={
            "media_server": {"type": "jellyfin", "server_url": "http://jf.local"},
        })

        self.assertEqual(200, resp.status_code)
        dispatch_config = mock_setup_service.call_args.args[1]
        self.assertEqual("jellyfin", dispatch_config["media_servers"]["active"])
        saved = config_service.save_config.call_args.args[0]
        self.assertEqual("192.168.1.50", saved["oppo"]["ip"])
        self.assertEqual(
            "http://emby.local", saved["media_servers"]["providers"]["emby"]["server_url"]
        )
        self.assertEqual(
            "http://jf.local", saved["media_servers"]["providers"]["jellyfin"]["server_url"]
        )

    @patch("home_cinema_control.web.media_server_routes.media_server_setup_service")
    def test_check_returns_503_when_server_unreachable(self, mock_setup_service):
        # Regression: against a stopped/unreachable server, requests has no
        # default timeout, so this used to hang the request indefinitely
        # instead of failing. network/http.py now bounds it; this confirms
        # the resulting exception surfaces as a clean 503, not a 500 or a
        # hang.
        setup_service = MagicMock()
        setup_service.check_connection.side_effect = requests.exceptions.ConnectTimeout()
        mock_setup_service.return_value = setup_service
        client, runtime, config_service = _make_client(config={
            "media_server": {"type": "emby", "server_url": "http://emby.local"},
        })

        resp = client.post("/api/v1/media-server/check", json={
            "media_server": {"type": "emby", "server_url": "http://emby.local"},
        })

        self.assertEqual(503, resp.status_code)
        config_service.save_config.assert_not_called()
        runtime.restart_playback_listener.assert_not_called()
        runtime.set_last_diagnostic.assert_called_once()
        diagnostic = runtime.set_last_diagnostic.call_args.args[0]
        self.assertEqual("media_server", diagnostic.component)

    @patch("home_cinema_control.web.media_server_routes.media_server_setup_service")
    def test_switch_proceeds_when_confirmed_despite_active_playback(self, mock_setup_service):
        self._mock_setup_service(mock_setup_service)
        client, runtime, config_service = _make_client(config={
            "media_server": {"type": "emby", "server_url": "http://emby.local"},
        })
        runtime.has_active_playback.return_value = True

        resp = client.post("/api/v1/media-server/check", json={
            "media_server": {"type": "jellyfin", "server_url": "http://jellyfin.local"},
            "confirm_provider_switch": True,
        })

        self.assertEqual(200, resp.status_code)
        config_service.save_config.assert_called_once()
        runtime.restart_playback_listener.assert_called_once()


class MediaServerTokenRouteTest(unittest.TestCase):
    """Regression for the real bug found testing against real Emby/Jellyfin
    servers: the frontend only ever sends {config: {media_server: {type,
    server_url}}, credentials: {...}} here, never a complete config.
    """

    @patch("home_cinema_control.web.media_server_routes.media_server_setup_service")
    def test_token_request_preserves_other_sections_and_dispatches_target_type(
            self, mock_setup_service
    ):
        setup_service = MagicMock()
        setup_service.configure_token.side_effect = lambda config, credentials: config
        mock_setup_service.return_value = setup_service

        client, runtime, config_service = _make_client(config={
            "media_servers": {
                "active": "jellyfin",
                "providers": {
                    "emby": {"server_url": "http://emby.local"},
                    "jellyfin": {"server_url": "http://jf.local"},
                },
            },
            "oppo": {"ip": "192.168.1.50"},
        })

        resp = client.post("/api/v1/media-server/token", json={
            "config": {"media_server": {"type": "jellyfin", "server_url": "http://jf.local"}},
            "credentials": {"user_name": "pedro", "password": "secret"},
        })

        self.assertEqual(200, resp.status_code)
        dispatch_config = mock_setup_service.call_args.args[1]
        self.assertEqual("jellyfin", dispatch_config["media_servers"]["active"])
        saved = config_service.save_config.call_args.args[0]
        self.assertEqual("192.168.1.50", saved["oppo"]["ip"])
        self.assertEqual(
            "http://emby.local", saved["media_servers"]["providers"]["emby"]["server_url"]
        )

    @patch("home_cinema_control.web.media_server_routes.media_server_setup_service")
    def test_token_request_returns_503_when_server_unreachable(self, mock_setup_service):
        setup_service = MagicMock()
        setup_service.configure_token.side_effect = requests.exceptions.ConnectionError()
        mock_setup_service.return_value = setup_service

        client, runtime, config_service = _make_client(config={
            "media_servers": {
                "active": "jellyfin",
                "providers": {"jellyfin": {"server_url": "http://jf.local"}},
            },
        })

        resp = client.post("/api/v1/media-server/token", json={
            "config": {"media_server": {"type": "jellyfin", "server_url": "http://jf.local"}},
            "credentials": {"user_name": "pedro", "password": "secret"},
        })

        self.assertEqual(503, resp.status_code)
        config_service.save_config.assert_not_called()
        runtime.restart_playback_listener.assert_not_called()
        runtime.set_last_diagnostic.assert_called_once()
        self.assertEqual(
            "media_server", runtime.set_last_diagnostic.call_args.args[0].component
        )

    @patch("home_cinema_control.web.media_server_routes.media_server_setup_service")
    def test_token_request_requires_confirmation_before_active_playback_switch(
            self, mock_setup_service
    ):
        setup_service = MagicMock()
        setup_service.configure_token.side_effect = lambda config, credentials: config
        mock_setup_service.return_value = setup_service

        client, runtime, config_service = _make_client(config={
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {"server_url": "http://emby", "access_token": "emby-token"},
                    "jellyfin": {"server_url": "http://jf.local"},
                },
            },
        })
        runtime.has_active_playback.return_value = True

        resp = client.post("/api/v1/media-server/token", json={
            "config": {"media_server": {"type": "jellyfin", "server_url": "http://jf.local"}},
            "credentials": {"user_name": "pedro", "password": "secret"},
        })

        self.assertEqual(200, resp.status_code)
        self.assertTrue(resp.json()["switch_requires_confirmation"])
        self.assertEqual("emby", resp.json()["active_session_provider"])
        setup_service.configure_token.assert_not_called()
        config_service.save_config.assert_not_called()
        runtime.restart_playback_listener.assert_not_called()


class MediaServerSectionRouteTest(unittest.TestCase):
    def test_patch_media_server_section_without_provider_change_just_merges_fields(self):
        client, runtime, config_service = _make_client(config={
            "media_server": {"type": "emby", "server_url": "http://old", "display_name": "Pedro"},
        })

        resp = client.patch("/api/v1/config/media-server", json={
            "media_server": {"type": "emby", "server_url": "http://new"},
        })

        self.assertEqual(200, resp.status_code)
        saved = config_service.save_config.call_args.args[0]
        self.assertEqual(
            "http://new", saved["media_servers"]["providers"]["emby"]["server_url"]
        )
        self.assertEqual("emby", saved["media_servers"]["active"])
        runtime.restart_playback_listener.assert_not_called()

    def test_patch_media_server_section_switch_to_unconfigured_provider_saves_draft_without_runtime_switch(self):
        client, runtime, config_service = _make_client(config={
            "media_server": {"type": "emby", "server_url": "http://old", "display_name": "Pedro"},
            "playback": {"hcc_controlled_device": "emby-device"},
        })

        resp = client.patch("/api/v1/config/media-server", json={
            "media_server": {"type": "jellyfin", "server_url": "http://jellyfin.local"},
        })

        self.assertEqual(200, resp.status_code)
        self.assertEqual("jellyfin", resp.json()["media_server_pending_provider"])
        saved = config_service.save_config.call_args.args[0]
        self.assertEqual("emby", saved["media_servers"]["active"])
        self.assertEqual(
            "http://jellyfin.local",
            saved["media_servers"]["providers"]["jellyfin"]["server_url"],
        )
        # Emby's data is still sitting in the legacy media_server field (this
        # install never migrated) and is untouched by switching away from it
        # — the transitional fallback in get_media_server_provider means
        # switching back to "emby" later still resolves it correctly.
        self.assertEqual("Pedro", saved["media_server"]["display_name"])
        runtime.restart_playback_listener.assert_not_called()

    @patch("home_cinema_control.web.media_server_routes.media_server_setup_service")
    def test_patch_media_server_section_switch_to_configured_provider_checks_connection(
            self, mock_setup_service
    ):
        setup_service = MagicMock()
        setup_service.check_connection.return_value = MagicMock(status_code=204)
        mock_setup_service.return_value = setup_service

        client, runtime, config_service = _make_client(config={
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {"server_url": "http://emby"},
                    "jellyfin": {
                        "server_url": "http://jellyfin.local",
                        "access_token": "jf-token",
                        "user_id": "jf-user",
                    },
                },
            },
        })

        resp = client.patch("/api/v1/config/media-server", json={
            "media_server": {"type": "jellyfin"},
        })

        self.assertEqual(200, resp.status_code)
        saved = config_service.save_config.call_args.args[0]
        self.assertEqual("jellyfin", saved["media_servers"]["active"])
        runtime.restart_playback_listener.assert_called_once()
        # Regression: switching to an already-configured provider runs the
        # same check_connection validity check as "Probar conexión" — it
        # should mark the section verified too, instead of leaving readiness
        # stuck on "configured" (yellow) until a separate manual test.
        self.assertEqual("ok", saved["setup_verification"]["media_server"]["status"])

    @patch("home_cinema_control.web.media_server_routes.media_server_setup_service")
    def test_patch_media_server_section_switch_clears_only_target_token_on_401(
            self, mock_setup_service
    ):
        setup_service = MagicMock()
        setup_service.check_connection.return_value = MagicMock(status_code=401)
        mock_setup_service.return_value = setup_service

        client, runtime, config_service = _make_client(config={
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {
                        "server_url": "http://emby",
                        "access_token": "emby-token",
                        "user_id": "emby-user",
                    },
                    "jellyfin": {
                        "server_url": "http://jellyfin.local",
                        "display_name": "Pedro",
                        "access_token": "stale-token",
                        "user_id": "jf-user",
                    },
                },
            },
        })

        resp = client.patch("/api/v1/config/media-server", json={
            "media_server": {"type": "jellyfin"},
        })

        self.assertEqual(200, resp.status_code)
        self.assertTrue(resp.json()["media_server_session_expired"])
        self.assertEqual("jellyfin", resp.json()["media_server_pending_provider"])
        saved = config_service.save_config.call_args.args[0]
        jellyfin = saved["media_servers"]["providers"]["jellyfin"]
        self.assertEqual("", jellyfin["access_token"])
        self.assertEqual("jf-user", jellyfin["user_id"])
        self.assertEqual("http://jellyfin.local", jellyfin["server_url"])
        self.assertEqual("emby", saved["media_servers"]["active"])
        # Emby's own stored token is untouched by Jellyfin's auth failure.
        self.assertEqual("emby-token", saved["media_servers"]["providers"]["emby"]["access_token"])
        runtime.restart_playback_listener.assert_not_called()

    @patch("home_cinema_control.web.media_server_routes.media_server_setup_service")
    def test_patch_media_server_section_switch_connection_failure_changes_nothing(
            self, mock_setup_service
    ):
        setup_service = MagicMock()
        setup_service.check_connection.return_value = MagicMock(status_code=500)
        mock_setup_service.return_value = setup_service

        client, runtime, config_service = _make_client(config={
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {"server_url": "http://emby", "access_token": "emby-token"},
                    "jellyfin": {
                        "server_url": "http://jellyfin.local",
                        "access_token": "jf-token",
                    },
                },
            },
        })

        resp = client.patch("/api/v1/config/media-server", json={
            "media_server": {"type": "jellyfin"},
        })

        self.assertEqual(400, resp.status_code)
        config_service.save_config.assert_not_called()
        runtime.restart_playback_listener.assert_not_called()
        runtime.set_last_diagnostic.assert_called_once()
        self.assertEqual(
            "media_server", runtime.set_last_diagnostic.call_args.args[0].component
        )

    @patch("home_cinema_control.web.media_server_routes.media_server_setup_service")
    def test_patch_media_server_section_switch_unreachable_returns_503_changes_nothing(
            self, mock_setup_service
    ):
        # Regression: stopping the target server used to hang this request
        # forever (no HTTP timeout) while the UI sat in an ambiguous
        # "switching" state. Now bounded by network/http.py's default
        # timeout, and the resulting exception maps to a clean 503 instead
        # of an unhandled 500.
        setup_service = MagicMock()
        setup_service.check_connection.side_effect = requests.exceptions.ConnectionError()
        mock_setup_service.return_value = setup_service

        client, runtime, config_service = _make_client(config={
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {"server_url": "http://emby", "access_token": "emby-token"},
                    "jellyfin": {
                        "server_url": "http://jellyfin.local",
                        "access_token": "jf-token",
                    },
                },
            },
        })

        resp = client.patch("/api/v1/config/media-server", json={
            "media_server": {"type": "jellyfin"},
        })

        self.assertEqual(503, resp.status_code)
        config_service.save_config.assert_not_called()
        runtime.restart_playback_listener.assert_not_called()
        runtime.set_last_diagnostic.assert_called_once()
        self.assertEqual(
            "media_server", runtime.set_last_diagnostic.call_args.args[0].component
        )

    @patch("home_cinema_control.web.media_server_routes.media_server_setup_service")
    def test_patch_media_server_section_checks_connection_before_active_playback_confirmation(
            self, mock_setup_service
    ):
        setup_service = MagicMock()
        setup_service.check_connection.return_value = MagicMock(status_code=204)
        mock_setup_service.return_value = setup_service

        client, runtime, config_service = _make_client(config={
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {"server_url": "http://old", "access_token": "emby-token"},
                    "jellyfin": {
                        "server_url": "http://jellyfin.local",
                        "access_token": "jf-token",
                    },
                },
            },
        })
        runtime.has_active_playback.return_value = True

        resp = client.patch("/api/v1/config/media-server", json={
            "media_server": {"type": "jellyfin"},
        })

        self.assertEqual(200, resp.status_code)
        self.assertTrue(resp.json()["switch_requires_confirmation"])
        self.assertEqual("emby", resp.json()["active_session_provider"])
        setup_service.check_connection.assert_called_once()
        config_service.save_config.assert_not_called()
        runtime.restart_playback_listener.assert_not_called()


class NowPlayingImageRouteTest(unittest.TestCase):
    def _make_client_with_active_session(self, *, media_item_id="item-123"):
        config = {
            "media_servers": {
                "active": "emby",
                "providers": {
                    "emby": {
                        "server_url": "http://emby.local",
                        "access_token": "secret-token",
                    }
                },
            }
        }
        client, runtime, config_service = _make_client(config=config)
        runtime.get_state.return_value = {
            "ActiveSession": {"media_item_id": media_item_id}
        }
        return client, runtime, config_service

    @patch("home_cinema_control.web.media_server_routes._requests")
    def test_backdrop_proxies_image_from_media_server(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"image-bytes"
        mock_resp.headers = {"content-type": "image/jpeg"}
        mock_requests.get.return_value = mock_resp
        client, _, _ = self._make_client_with_active_session()

        resp = client.get("/api/v1/now-playing/backdrop")

        self.assertEqual(200, resp.status_code)
        self.assertEqual(b"image-bytes", resp.content)
        url = mock_requests.get.call_args.args[0]
        self.assertIn("item-123", url)
        self.assertIn("Backdrop", url)

    @patch("home_cinema_control.web.media_server_routes._requests")
    def test_poster_proxies_image_from_media_server(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"poster-bytes"
        mock_resp.headers = {"content-type": "image/jpeg"}
        mock_requests.get.return_value = mock_resp
        client, _, _ = self._make_client_with_active_session()

        resp = client.get("/api/v1/now-playing/poster")

        self.assertEqual(200, resp.status_code)
        url = mock_requests.get.call_args.args[0]
        self.assertIn("Primary", url)

    def test_backdrop_returns_404_when_nothing_playing(self):
        client, runtime, _ = _make_client()
        runtime.get_state.return_value = {}

        resp = client.get("/api/v1/now-playing/backdrop")

        self.assertEqual(404, resp.status_code)

    def test_poster_returns_404_when_nothing_playing(self):
        client, runtime, _ = _make_client()
        runtime.get_state.return_value = {}

        resp = client.get("/api/v1/now-playing/poster")

        self.assertEqual(404, resp.status_code)

    @patch("home_cinema_control.web.media_server_routes._requests")
    def test_backdrop_returns_502_when_media_server_unreachable(self, mock_requests):
        mock_requests.get.side_effect = requests.exceptions.ConnectionError()
        client, _, _ = self._make_client_with_active_session()

        resp = client.get("/api/v1/now-playing/backdrop")

        self.assertEqual(502, resp.status_code)

    @patch("home_cinema_control.web.media_server_routes._requests")
    def test_backdrop_includes_api_key_when_token_configured(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b""
        mock_resp.headers = {}
        mock_requests.get.return_value = mock_resp
        client, _, _ = self._make_client_with_active_session()

        client.get("/api/v1/now-playing/backdrop")

        params = mock_requests.get.call_args.kwargs.get("params", {})
        self.assertEqual("secret-token", params.get("api_key"))


class LibraryPathsRouteTest(unittest.TestCase):
    @patch("home_cinema_control.media_servers.emby.web_config.fetch_library_paths")
    def test_returns_library_paths_on_success(self, mock_fetch):
        mock_fetch.return_value = ["/volume1/Video/Movies", "/volume1/Video/Series"]
        client, _, _ = _make_client()

        resp = client.get("/api/v1/media-server/library-paths")

        self.assertEqual(200, resp.status_code)
        self.assertEqual(["/volume1/Video/Movies", "/volume1/Video/Series"], resp.json())
        # The setup-service boundary receives the raw config dict (with secrets and
        # arbitrary keys), not a pruned Pydantic model. Guards the candidate-1 regression.
        mock_fetch.assert_called_once()
        self.assertIsInstance(mock_fetch.call_args.args[0], dict)

    @patch("home_cinema_control.media_servers.emby.web_config.fetch_library_paths")
    def test_returns_502_when_emby_unreachable(self, mock_fetch):
        mock_fetch.side_effect = Exception("Connection refused")
        client, runtime, _ = _make_client()

        resp = client.get("/api/v1/media-server/library-paths")

        self.assertEqual(502, resp.status_code)
        runtime.set_last_diagnostic.assert_called_once()


if __name__ == "__main__":
    unittest.main()
