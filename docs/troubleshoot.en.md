# Troubleshoot HCC

[Home](../README.en.md) · [Installation](../INSTALL.en.md) · [Español](solucionar-problemas.md)

Find the symptom you're experiencing. **You only need the section that matches your problem.**

If HCC appears to have lost its settings after an update, start with [configuration recovery](recover-configuration.en.md).

## Check HCC diagnostics

Open **Diagnostics** in HCC to check connections, see the latest error and find the installed version.

<p align="center">
  <img src="../assets/screenshots/install/06-status.png" alt="HCC diagnostics screen" width="860"/>
</p>

If you need support, use **Send diagnostics**. HCC prepares a summary without paths, IP addresses or credentials. You can review it before sharing; nothing is sent automatically.

## Read logs only when needed

Open **Logs** and filter recent errors or warnings. Copy relevant lines for support after checking for private information.

<p align="center">
  <img src="../assets/screenshots/install/07-logs.png" alt="HCC logs screen with filters" width="860"/>
</p>

[Optional telemetry](https://github.com/tousled/home-cinema-control/blob/main/docs/telemetry.md) is separate from diagnostics you choose to share.

## Frequent Issues

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

- Check the OPPO/Chinoppo IP address.
- Check `network_mode: host`.
- Check firewall rules.
- Wake the player and test again.

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
