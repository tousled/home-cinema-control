# First steps in HCC

[Home](../README.en.md) · [Installation](../INSTALL.en.md) · [Español](primeros-pasos.md)

**HCC is now running.** Connect your media server, OPPO/Chinoppo, movie folders, and **TV and/or AV receiver**. These are the usual setup screens. **Home Assistant is optional** and can be configured later.

## Set up HCC in five steps

1. **[Media Server](#2-connect-emby-or-jellyfin):** choose Emby or Jellyfin, enter your server details and authorise the connection.
2. **[Media Player](#3-connect-your-oppochinoppo):** find your OPPO/Chinoppo and press **Test OPPO**.
3. **[Media Paths](configure-media-paths.en.md):** connect at least one library using the illustrated guide.
4. **[Room: TV and AV receiver](#5-tv-and-av-receiver-optional):** set up and test your TV, receiver, or both. If you only have a TV, configure just the TV.
5. Play a movie from your chosen Emby/Jellyfin device.

**Expected result:** the OPPO plays your movie. If it doesn't, open [troubleshooting](troubleshoot.en.md).

## Screenshots, step by step

### 1. New setup or migration

If HCC finds older settings, you may import them. Otherwise choose **Configure from scratch**. If HCC was already installed and unexpectedly shows an empty setup, **stop** and use [configuration recovery](recover-configuration.en.md).

<p align="center">
  <img src="../assets/screenshots/install/01-migration.png" alt="HCC migration screen" width="860"/>
</p>

### 2. Connect Emby or Jellyfin

Open **Media Server**, choose your provider, fill in the server address and authorise the connection. Then choose which Emby/Jellyfin client HCC will monitor.

<p align="center">
  <img src="../assets/screenshots/install/02-media-server.png" alt="HCC Media Server setup" width="860"/>
</p>

<p align="center">
  <img src="../assets/screenshots/install/02-media-server-pending.png" alt="Media Server with Jellyfin selected but pending authorization" width="860"/>
</p>

If you see a **pending** status, finish authorisation before continuing. HCC needs access to your existing Emby/Jellyfin libraries.

### 3. Connect your OPPO/Chinoppo

Open **Media Player**. Enter the player's IP address; if **Scan network** is available, use it to find the player. Press **Test OPPO**.

<p align="center">
  <img src="../assets/screenshots/install/03-media-player.png" alt="HCC Media Player setup" width="860"/>
</p>

<p align="center">
  <img src="../assets/screenshots/install/03-media-player-ip-discovery.png" alt="OPPO IP discovery filtered by device name" width="860"/>
</p>

If the test fails, first check that the player is powered on and on the same local network. Other checks are in [troubleshooting](troubleshoot.en.md).

### 4. Connect your movie folders

Follow the [Media Paths guide](configure-media-paths.en.md), including screenshots. The OPPO must already be able to browse the shared NAS folder over SMB or NFS. Once HCC confirms a path is verified, return here.

### 5. TV and AV receiver (optional)

You can skip **Room** and play movies without automated TV or receiver control. If you want HCC to change HDMI inputs automatically, enable and test the devices in **Room**.

<p align="center">
  <img src="../assets/screenshots/install/05-room.png" alt="HCC Room setup" width="860"/>
</p>

<p align="center">
  <img src="../assets/screenshots/install/05-room-ip-discovery.png" alt="IP discovery in the Home Cinema Control Room setup screen" width="860"/>
</p>

For LG TVs, accept the pairing prompt on the TV if one appears. For Sony TVs, IP control/PSK may need enabling in TV settings. See [troubleshooting](troubleshoot.en.md) if a receiver switches back to TV Audio.

### 6. Play your first movie

Open Emby/Jellyfin on the client selected in **Media Server** and play a movie in a library you've verified. Check that the OPPO starts playback. Pause, resume and stop to confirm everything responds.

If something fails, open **Diagnostics** and follow [troubleshooting](troubleshoot.en.md).

**HCC is ready.** Want lighting automations too? [Home Assistant setup is optional](home-assistant.en.md).
