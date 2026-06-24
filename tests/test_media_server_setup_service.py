import types
import unittest

from home_cinema_control.media_servers.common.setup import ModuleMediaServerSetupService


class _FakeModuleReturningNewDict:
    """A provider setup module whose load_* functions return a brand-new
    dict instead of mutating the one they were given - exactly what
    emby/jellyfin's web_config.py does since the scoped-paths-libraries-device
    spec (config = upsert_provider_playback(...).model_dump()).
    """

    @staticmethod
    def load_devices(config):
        return {**config, "devices": ["new-device"]}

    @staticmethod
    def load_libraries(config):
        return {**config, "libraries_loaded": True}

    @staticmethod
    def load_selectable_folders(config):
        return {**config, "folders_loaded": True}


class ModuleMediaServerSetupServiceTest(unittest.TestCase):
    """Regression test for a real bug: the wrapper used to call
    self._module.load_*(updated) and discard the return value, returning the
    pre-call `updated` unchanged. That was invisible while every provider
    module mutated its config dict in place, and broke silently once
    load_libraries/load_selectable_folders started doing
    config = upsert_provider_playback(...).model_dump() (a reassignment, not
    a mutation) - reported by Pedro as "Bibliotecas interceptadas" showing
    empty in MediaPathsView.vue after Jellyfin library detection.
    """

    def setUp(self):
        self.service = ModuleMediaServerSetupService(
            types.SimpleNamespace(**{
                name: getattr(_FakeModuleReturningNewDict, name)
                for name in ("load_devices", "load_libraries", "load_selectable_folders")
            })
        )

    def test_load_devices_returns_the_modules_actual_return_value(self):
        result = self.service.load_devices({"media_servers": {"active": "emby", "providers": {}}})
        self.assertEqual(["new-device"], result["devices"])

    def test_load_libraries_returns_the_modules_actual_return_value(self):
        result = self.service.load_libraries({"media_servers": {"active": "emby", "providers": {}}})
        self.assertTrue(result.get("libraries_loaded"))

    def test_load_selectable_folders_returns_the_modules_actual_return_value(self):
        result = self.service.load_selectable_folders({"media_servers": {"active": "emby", "providers": {}}})
        self.assertTrue(result.get("folders_loaded"))


if __name__ == "__main__":
    unittest.main()
