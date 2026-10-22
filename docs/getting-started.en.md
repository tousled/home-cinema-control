# First steps in HCC

[Home](../README.en.md) · [Installation](../INSTALL.en.md) · [Español](primeros-pasos.md)

**HCC is now running.** Follow the usual screens: **Media Server**, **Media Player**, **Media Paths**, and **Room** (TV and/or AV receiver). HCC can find devices and test connections, so you don't need to enter everything by hand. Home Assistant can wait.

## Set up HCC in five steps

1. **[Media Server](#2-connect-emby-or-jellyfin):** choose Emby or Jellyfin, enter your server details and authorise the connection.
2. **[Media Player](#3-connect-your-oppochinoppo):** find your OPPO/Chinoppo and press **Test OPPO**.
3. **[Media Paths](configure-media-paths.en.md):** choose a library, click **Browse OPPO** to find its folder, then **Test path**. You're done when **Path verified** appears in green.
4. **[Room: TV and AV receiver](#5-tv-and-av-receiver-optional):** set up and test your TV, receiver, or both. If you only have a TV, configure just the TV.
5. Play a movie from your chosen Emby/Jellyfin device.

**Expected result:** the OPPO plays your movie. If it doesn't, open [troubleshooting](troubleshoot.en.md).

## Screenshots, step by step

### 1. New setup or migration

If HCC finds older settings, you may import them. Otherwise choose **Configure from scratch**. If HCC previously worked and now shows an empty setup, **stop** and use [configuration recovery](recover-configuration.en.md). For unexpected errors, check [Diagnostics](troubleshoot.en.md#check-hcc-diagnostics).

<p align="center">
  <img src="../assets/screenshots/install/01-migration.png" alt="HCC migration screen" width="860"/>
</p>

### 2. Connect Emby or Jellyfin

Open **Media Server**, choose **Emby** or **Jellyfin**, enter the server address and authorise the connection. Then choose the Emby/Jellyfin client HCC should monitor. You don't need to re-create your existing media libraries.

<p align="center">
  <img src="../assets/screenshots/install/02-media-server.png" alt="HCC Media Server setup" width="860"/>
</p>

<p align="center">
  <img src="../assets/screenshots/install/02-media-server-pending.png" alt="Media Server with Jellyfin selected but pending authorization" width="860"/>
</p>

If you see **pending**, finish authorisation before continuing. You should then be able to refresh and see your devices and libraries. If they're missing, check [Diagnostics](troubleshoot.en.md#check-hcc-diagnostics) for the error.

### 3. Connect your OPPO/Chinoppo

**First, check that network control is enabled.** On an **OPPO UDP-203/205**, press **SETUP** on the remote and select **Network Setup → IP Control → On** (enabled by default). This allows HCC to control the player over the network. See the [official OPPO UDP-203 manual](https://www.oppodigital.com/blu-ray-udp-203/blu-ray-udp-203-Support.aspx). On **Chinoppo/clones**, look for the equivalent IP/network control setting; the exact wording or menu location may differ by firmware and has not been verified for every model.

Open **Media Player**. If **Scan network** appears, **click it**: HCC searches for devices on your local network. Click the **IP** field and start typing to see suggestions filtered by **IP address, name or vendor**, when that information is available. Select your OPPO/Chinoppo.

<p align="center">
  <img src="../assets/screenshots/install/03-media-player.png" alt="HCC Media Player setup" width="860"/>
</p>

<p align="center">
  <img src="../assets/screenshots/install/03-media-player-ip-discovery.png" alt="OPPO IP discovery filtered by device name" width="860"/>
</p>

Once the IP is selected, click **Test connection** and save. If **Scan network** isn't available, enter the IP manually. Discovery needs HCC and the devices on the local network with host scanning available; keep **`network_mode: host`** in Compose. Names only appear when your network or router provides them. If the test fails, open [Diagnostics](troubleshoot.en.md#check-hcc-diagnostics).

### 4. Connect your movie folders

Follow the [Media Paths guide](configure-media-paths.en.md). Use **Browse OPPO** to choose the folder, click **Test path** and look for **Path verified** in green. If it fails, HCC provides a reason; also check [Diagnostics](troubleshoot.en.md#check-hcc-diagnostics).

### 5. TV and AV receiver (optional)

Open **Room** to set up your **TV, AV receiver or both**. Enable each device you have, choose its model and configure its IP address. If **Scan network** is available, click it and use the suggestions as you type, just as in Media Player. Click **Test connection** before selecting TV inputs or features. You can set up just your TV if you have no AV receiver.

<p align="center">
  <img src="../assets/screenshots/install/05-room.png" alt="HCC Room setup" width="860"/>
</p>

<p align="center">
  <img src="../assets/screenshots/install/05-room-ip-discovery.png" alt="IP discovery in the Home Cinema Control Room setup screen" width="860"/>
</p>

If suggestions don't appear, enter the IP manually. HCC and your devices must be able to communicate on the local network (keep **`network_mode: host`**). Names depend on what your router or network supplies.

On LG TVs, accept the pairing prompt if one appears. On Sony TVs, IP control/PSK may need enabling in the TV settings. For failed tests, check [Diagnostics](troubleshoot.en.md#check-hcc-diagnostics). If your receiver switches back to TV Audio, see [troubleshooting](troubleshoot.en.md#the-avr-changes-input-by-itself).

### 6. Play your first movie

Open Emby/Jellyfin on the client selected in **Media Server** and play a movie in a library you've verified. Check that the OPPO starts playback. Pause, resume and stop to confirm everything responds.

If something fails, open **Diagnostics** and follow [troubleshooting](troubleshoot.en.md).

**HCC is ready.** Want lighting automations too? [Home Assistant setup is optional](home-assistant.en.md).
