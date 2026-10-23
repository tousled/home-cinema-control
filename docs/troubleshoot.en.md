# Troubleshoot HCC

[Home](../README.en.md) · [Installation](../INSTALL.en.md) · [Español](solucionar-problemas.md)

Find the symptom you're experiencing. **You only need the section that matches your problem.**

If HCC appears to have lost its settings after an update, start with [configuration recovery](recover-configuration.en.md).

## Check HCC diagnostics

Open **Diagnostics** in HCC to check connections, see the latest error and find the installed version.

<p align="center">
  <img src="../assets/screenshots/install/06-status.png" alt="HCC diagnostics screen" width="860"/>
</p>

For help, click **Send diagnostics**. HCC prepares a status summary and up to **200 recent log lines** by default. It redacts credentials, IPs, MACs and paths known from your configuration, plus IPv4 addresses found in the text. **Review the report** before sharing. **Copy & open GitHub** copies it and opens an issue, but **you must paste it**; nothing is submitted automatically.

## Read logs only when needed

Open **Logs** and filter recent errors or warnings. HCC avoids logging credentials in OPPO requests, but **the original log may include IP addresses and folder names**. For an extra-redacted support report, use **Send diagnostics**. You can also copy the visible lines or download `hcc.log`.

<p align="center">
  <img src="../assets/screenshots/install/07-logs.png" alt="HCC logs screen with filters" width="860"/>
</p>

[Optional telemetry](https://github.com/tousled/home-cinema-control/blob/main/docs/telemetry.md) is separate from diagnostics you choose to share.

## Contact and support

If you think you've found an **HCC bug**, [open an issue in the public repository](https://github.com/tousled/home-cinema-control/issues/new). This makes it easier to reproduce the issue and share a fix.

For **installation help**, email [llorente.software.solutions@gmail.com](mailto:llorente.software.solutions@gmail.com). Programming knowledge isn't required.

### How to share a failed test log

1. Repeat the failing action once, such as **Test connection** or **Test path**. Note what you expected and what error appeared.
2. Open **Diagnostics** and check the latest failure. Click **Send diagnostics** for a report with known private values redacted. Review it, then click **Copy & open GitHub**. The report is copied, **but you must paste it yourself** into the issue. It is not posted automatically.
3. Open **Logs**. Click **Refresh** if needed and filter for **Error** or **Warning**. Click **Copy lines** to share the relevant visible entries. To save the full file, click **Download**; this saves `hcc.log`.
4. In the issue or email, include your **HCC version** (under Diagnostics), media server and device, **steps to reproduce**, the displayed error, and the relevant log entries from the test.

**Privacy:** HCC avoids writing credentials in player requests and **Send diagnostics** applies additional redaction. Still, check for device addresses, folder names or other personal details before posting publicly. **Download** saves the complete `hcc.log`, not just the lines filtered on screen. For public issues, prefer the redacted Diagnostics report or the relevant log lines.

## Frequent Issues

### GHCR pull fails (`denied` or `403 Forbidden`)

If Docker cannot pull `ghcr.io/tousled/home-cinema-control` when installing or updating HCC, use Docker Hub without reinstalling HCC. In **your existing Compose file**, replace only:

```yaml
image: ghcr.io/tousled/home-cinema-control:latest
```

with:

```yaml
image: tousled/home-cinema-control:latest
```

**Keep everything else, including the `/config` volume.** If you pin a release, retain its version tag when the same release is available on Docker Hub. If using `HCC_VERSION`, keep that variable too. Finish using the [Docker Compose guide](update-compose.en.md) or [Portainer guide](update-portainer.en.md) for your existing installation. Do not delete the volume or create a new stack.

### Jellyfin: devices and libraries don't show up when you click "Reload"

- The Jellyfin account you authorize HCC with must be an **administrator**. Jellyfin restricts the device list
  (`/Devices`) and the library/virtual-folder list (`/Library/VirtualFolders`) to elevated accounts — a regular
  account gets a 403 error loading them, even though login itself (authorizing, playing, reporting progress) works
  normally.
- If Jellyfin returns `401` or `403` while reloading devices or libraries, update HCC and re-authorize Jellyfin from
  **Media Server**.
- If you only have one Jellyfin user, it's almost certainly already the administrator and there's nothing to change.
  If HCC uses a secondary account, grant it administrator rights from the Jellyfin dashboard.

### HCC cannot reach the player

- Check the OPPO/Chinoppo IP address and make sure the player is powered on.
- On **OPPO UDP-203/205**, open **SETUP → Network Setup → IP Control → On**. On a Chinoppo/clone, look for the equivalent IP/network-control option; wording and location may vary by firmware.
- Check `network_mode: host`.
- Check firewall rules.
- Wake the player and test again.

### Chinoppo times out while mounting a folder or starting playback

Different timeouts have different causes:

- **`Timeout in Mount Request`:** the player did not complete an NFS/SMB mount. **This may affect folder browsing, Test path and playback**, which share the same mount service. In one reported case, the Chinoppo's network API was not ready after power-up; opening its NFS browser once allowed the mount to complete. Check that **IP Control** is enabled, let the player finish starting, and retry once.
- **`Timeout in Play Request`:** the player did not answer the play command in time. **This does not prove the media path is wrong.**
- **Playback startup timeout:** HCC did not confirm active playback after starting the handoff. This is not necessarily a path-mapping problem; inspect the player state and the latest diagnostic.

If it happens again, open **Diagnostics** and share the report and test log as explained in [Contact and support](#contact-and-support). HCC prepares the control API before mounting and retries one timed-out NFS mount; if the retry fails, investigate the specific cause instead of increasing timeouts blindly.

### NFS mount fails

- Verify that the NFS export exists.
- Confirm the player can browse it manually.
- Physically restart the player if its browser works but the mount remains stuck.

### SMB returns `id_error`

- Check share name, username, password, and permissions.
- If your NAS/player combination needs SMB session preparation, check that the credentials are saved in HCC and test
  the path again.
- If `id_error` repeats, avoid pressing "Test path" many times in a row: some OPPO/Chinoppo players degrade their
  control API after too many failed SMB mounts. Physically restart the player before testing again.
- If that library is already verified through NFS and SMB keeps failing, use NFS for that mapping.
- Do not expect fallback to NFS: fix SMB or explicitly change that mapping to NFS.

### SMB times out on long folder names or names with special characters

Some OPPO/Chinoppo players time out mounting an SMB folder whose name is very long or includes
parentheses, brackets, or a `+` sign (common in release-style names for movies and TV episodes, e.g.
`The Veil red de mentiras (2024) S01 [PACK][DSNP WEB-DL 1080p AVC ES DD+ 5.1][HDO]`). The same content,
in the same NAS folder, mounts and plays fine over NFS, and over SMB too once the folder/file name is
shortened or simplified. If one specific library keeps timing out over SMB while your other SMB
libraries work fine, suspect the name length/characters first, before checking the network or the NAS:

- Switch that specific mapping to NFS if your NAS exposes it (the fastest way to keep watching that
  content).
- Or rename the folder/file to something shorter without parentheses/brackets if you want to keep
  using SMB.

### The AVR changes input by itself

- Review CEC/ARC.
- Disable CEC/ARC on the AVR if it forces TV Audio.
- Increase HDMI switch delay if the receiver needs more time after standby.
