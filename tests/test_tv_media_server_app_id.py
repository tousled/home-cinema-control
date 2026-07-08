import unittest
from unittest.mock import patch

from home_cinema_control.devices.tv.adapters.lg import (
    EMBY_APP_ID,
    LG_CURRENT_APP_CONNECT_TIMEOUT_SECONDS,
    JELLYFIN_APP_ID,
    LgTvController,
)
from home_cinema_control.devices.tv.adapters.scripts import ScriptsTvController
from home_cinema_control.devices.tv.setup_control import restore_tv_media_server_app


class LgMediaServerAppIdTest(unittest.TestCase):
    def test_resolves_emby_app_id(self):
        controller = LgTvController({"tv": {}})
        self.assertEqual(EMBY_APP_ID, controller.media_server_app_id("emby"))

    def test_resolves_jellyfin_app_id(self):
        controller = LgTvController({"tv": {}})
        self.assertEqual(JELLYFIN_APP_ID, controller.media_server_app_id("jellyfin"))

    def test_unknown_provider_returns_none(self):
        controller = LgTvController({"tv": {}})
        self.assertIsNone(controller.media_server_app_id("plex"))

    def test_current_app_lookup_uses_short_startup_timeout(self):
        self.assertEqual(3.0, LG_CURRENT_APP_CONNECT_TIMEOUT_SECONDS)


class ScriptsMediaServerAppIdTest(unittest.TestCase):
    def test_scripts_controller_ignores_provider_type(self):
        controller = ScriptsTvController({"tv": {}})
        self.assertIsNone(controller.media_server_app_id("emby"))
        self.assertIsNone(controller.media_server_app_id("jellyfin"))


class RestoreTvMediaServerAppTest(unittest.TestCase):
    def test_launches_app_id_for_selected_provider(self):
        controller = FakeTvController()
        with patch(
            "home_cinema_control.devices.tv.setup_control.create_tv_controller",
            return_value=controller,
        ):
            result = restore_tv_media_server_app(
                {
                    "tv": {"model": "LG"},
                    "media_servers": {
                        "active": "jellyfin",
                        "providers": {"jellyfin": {"server_url": "http://jf"}},
                    },
                }
            )

        self.assertEqual("OK", result)
        self.assertEqual([JELLYFIN_APP_ID], controller.launched_app_ids)

    def test_missing_media_server_section_resolves_to_no_app_id(self):
        controller = FakeTvController()
        with patch(
            "home_cinema_control.devices.tv.setup_control.create_tv_controller",
            return_value=controller,
        ):
            result = restore_tv_media_server_app({"tv": {"model": "LG"}})

        self.assertEqual("OK", result)
        self.assertEqual([None], controller.launched_app_ids)

    def test_provider_configured_without_server_url_resolves_to_no_app_id(self):
        # An active provider entry with no server_url isn't "configured" —
        # nothing to restore to.
        controller = FakeTvController()
        with patch(
                "home_cinema_control.devices.tv.setup_control.create_tv_controller",
                return_value=controller,
        ):
            result = restore_tv_media_server_app(
                {
                    "tv": {"model": "LG"},
                    "media_servers": {
                        "active": "jellyfin",
                        "providers": {"jellyfin": {}},
                    },
                }
            )

        self.assertEqual("OK", result)
        self.assertEqual([None], controller.launched_app_ids)

    def test_launches_app_id_for_migrated_active_provider(self):
        controller = FakeTvController()
        with patch(
                "home_cinema_control.devices.tv.setup_control.create_tv_controller",
                return_value=controller,
        ):
            result = restore_tv_media_server_app(
                {
                    "tv": {"model": "LG"},
                    "media_servers": {
                        "active": "jellyfin",
                        "providers": {"jellyfin": {"server_url": "http://jf"}},
                    },
                }
            )

        self.assertEqual("OK", result)
        self.assertEqual([JELLYFIN_APP_ID], controller.launched_app_ids)


class FakeTvController:
    def __init__(self):
        self.launched_app_ids = []

    def media_server_app_id(self, provider_type):
        return {"emby": EMBY_APP_ID, "jellyfin": JELLYFIN_APP_ID}.get(provider_type)

    def launch_app(self, app_id):
        self.launched_app_ids.append(app_id)
        return _Result(successful=True)


class _Result:
    def __init__(self, *, successful):
        self.successful = successful


if __name__ == "__main__":
    unittest.main()
