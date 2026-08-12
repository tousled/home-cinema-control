import unittest
from unittest.mock import AsyncMock, patch

from home_cinema_control.devices.tv.adapters.lg import (
    LgTvController,
    _new_lg_webos_pairing_manifest,
)


class LgWebosPairingManifestTest(unittest.TestCase):
    def test_manifest_does_not_use_legacy_lg_test_signature(self):
        manifest = _new_lg_webos_pairing_manifest()

        self.assertNotIn("signatures", manifest)
        self.assertNotIn("signature", str(manifest).lower())
        self.assertNotEqual("com.lge.test", manifest["signed"]["appId"])
        self.assertEqual("com.homecinemacontrol.app", manifest["signed"]["appId"])

    def test_manifest_returns_independent_copies(self):
        first = _new_lg_webos_pairing_manifest()
        second = _new_lg_webos_pairing_manifest()

        first["permissions"].append("MUTATED")

        self.assertNotIn("MUTATED", second["permissions"])


class LgWebosConnectionManifestTest(unittest.IsolatedAsyncioTestCase):
    async def test_connect_installs_hcc_manifest_before_pairing(self):
        controller = LgTvController({"tv": {"ip": "192.0.2.10"}})
        fake_storage = object()
        fake_client = AsyncMock()
        fake_client.connect = AsyncMock(return_value=True)

        with (
            patch(
                "home_cinema_control.devices.tv.adapters.lg.StorageSqliteDict.create",
                new=AsyncMock(return_value=fake_storage),
            ) as storage_create,
            patch(
                "home_cinema_control.devices.tv.adapters.lg.WebOsClient.create",
                new=AsyncMock(return_value=fake_client),
            ) as client_create,
        ):
            client = await controller._connect(timeout=1.0)

        self.assertIs(client, fake_client)
        storage_create.assert_awaited_once_with(
            "/config/.aiopylgtv.sqlite",
            table="lg_pairing_keys",
        )
        client_create.assert_awaited_once_with(
            "192.0.2.10",
            storage=fake_storage,
            timeout_connect=1.0,
            states=[],
        )
        self.assertEqual(
            "com.homecinemacontrol.app",
            fake_client.manifest["signed"]["appId"],
        )
        self.assertNotIn("signatures", fake_client.manifest)
        fake_client.connect.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
