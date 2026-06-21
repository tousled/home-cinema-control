import unittest
from unittest.mock import patch

from home_cinema_control.devices.oppo.playback_adapters import (
    OppoStableMediaControlPlaybackAdapter,
    create_oppo_playback_adapter,
)
from home_cinema_control.playback.startup.models import (
    DeviceCommandStatus,
    OppoPlaybackStartResult,
)


class OppoPlaybackAdaptersTest(unittest.TestCase):
    def test_creates_stable_adapter_by_default(self):
        adapter = create_oppo_playback_adapter(_config())

        self.assertIsInstance(adapter, OppoStableMediaControlPlaybackAdapter)

    def test_creates_stable_adapter_even_for_legacy_verbose_config(self):
        adapter = create_oppo_playback_adapter(
            _config(observation_mode="oppo_verbose")
        )

        self.assertIsInstance(adapter, OppoStableMediaControlPlaybackAdapter)


class OppoAutoscriptCleanupTest(unittest.TestCase):
    def test_skips_cleanup_when_autoscript_disabled(self):
        adapter = OppoStableMediaControlPlaybackAdapter(_config())
        adapter._last_mounted_path = "/mnt/nfs1"

        with patch(
            "home_cinema_control.devices.oppo.playback_adapters.unmount_oppo_path"
        ) as mock_unmount:
            result = adapter.cleanup_after_playback_finish()

        self.assertEqual(DeviceCommandStatus.SKIPPED, result.status)
        mock_unmount.assert_not_called()

    def test_skips_cleanup_when_autoscript_enabled_but_nothing_was_mounted(self):
        adapter = OppoStableMediaControlPlaybackAdapter(_config(autoscript=True))

        with patch(
            "home_cinema_control.devices.oppo.playback_adapters.unmount_oppo_path"
        ) as mock_unmount:
            result = adapter.cleanup_after_playback_finish()

        self.assertEqual(DeviceCommandStatus.SKIPPED, result.status)
        mock_unmount.assert_not_called()

    def test_unmounts_recorded_share_when_autoscript_enabled(self):
        adapter = OppoStableMediaControlPlaybackAdapter(_config(autoscript=True))
        adapter._last_mounted_path = "/mnt/cifs1"

        with patch(
            "home_cinema_control.devices.oppo.playback_adapters.unmount_oppo_path",
            return_value=True,
        ) as mock_unmount:
            result = adapter.cleanup_after_playback_finish()

        self.assertEqual(DeviceCommandStatus.SUCCESS, result.status)
        mock_unmount.assert_called_once_with(
            host="192.168.1.50", port=23, mount_path="/mnt/cifs1", timeout=3
        )

    def test_skips_cleanup_for_nfs_mount_even_when_autoscript_enabled(self):
        # Autoscript-unmount was only ever designed/validated for CIFS/SMB
        # (see the legacy Xnoppo project this was ported from); NFS mounts
        # are left in place rather than attempting an unverified telnet path.
        adapter = OppoStableMediaControlPlaybackAdapter(_config(autoscript=True))
        adapter._last_mounted_path = "/mnt/nfs1"

        with patch(
                "home_cinema_control.devices.oppo.playback_adapters.unmount_oppo_path"
        ) as mock_unmount:
            result = adapter.cleanup_after_playback_finish()

        self.assertEqual(DeviceCommandStatus.SKIPPED, result.status)
        mock_unmount.assert_not_called()

    def test_reports_failure_when_unmount_returns_false(self):
        adapter = OppoStableMediaControlPlaybackAdapter(_config(autoscript=True))
        adapter._last_mounted_path = "/mnt/cifs1"

        with patch(
            "home_cinema_control.devices.oppo.playback_adapters.unmount_oppo_path",
            return_value=False,
        ):
            result = adapter.cleanup_after_playback_finish()

        self.assertEqual(DeviceCommandStatus.FAILED, result.status)

    def test_reports_failure_when_unmount_raises(self):
        adapter = OppoStableMediaControlPlaybackAdapter(_config(autoscript=True))
        adapter._last_mounted_path = "/mnt/cifs1"

        with patch(
            "home_cinema_control.devices.oppo.playback_adapters.unmount_oppo_path",
            side_effect=ValueError("Refusing to unmount unexpected OPPO path"),
        ):
            result = adapter.cleanup_after_playback_finish()

        self.assertEqual(DeviceCommandStatus.FAILED, result.status)

    def test_start_playback_records_mounted_path_for_later_cleanup(self):
        adapter = OppoStableMediaControlPlaybackAdapter(_config(autoscript=True))
        adapter._playback.start_playback = lambda request, on_waiting=None: (
            OppoPlaybackStartResult(
                media_mounted=True,
                playback_command_accepted=True,
                playback_started_on_device=True,
                mounted_path="/mnt/nfs1",
            )
        )

        adapter.start_playback(request=None)

        self.assertEqual("/mnt/nfs1", adapter._last_mounted_path)


def _config(*, observation_mode="auto", autoscript=False):
    return {
        "oppo": {
            "ip": "192.168.1.50",
            "observation_mode": observation_mode,
            "connection_timeout_seconds": 3,
            "nfs_mount_timeout_seconds": 30,
            "autoscript": autoscript,
        }
    }


if __name__ == "__main__":
    unittest.main()
