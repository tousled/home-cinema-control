# Install Home Cinema Control

[Español](INSTALL.md) · [Home](README.en.md)

**Get HCC running in a few steps.** If you already have Emby or Jellyfin, an OPPO/Chinoppo player and Docker on your NAS or computer, you can follow this guide without being a Docker expert.

First, install HCC. Then use the screenshots to connect **Emby/Jellyfin, your OPPO/Chinoppo, movie folders, and TV and/or AV receiver**.

## Before you start

You need:

- A **NAS or computer with Docker running**. If you already use **Portainer**, you can install from its web interface without a terminal.
- **Emby or Jellyfin** and an **OPPO/Chinoppo** on the same local network as HCC.
- A movie folder your player can browse over the network. You'll connect it later.

Need to prepare your NAS, PC, Raspberry Pi or player first? Follow the [AVPasión Xnoppo setup guide](https://foro.avpasion.com/t/xnoppo-lo-mejor-de-emby-en-tu-oppo-203-205-y-chinoppo-clones-m9702-m9201-m9203-m9205.2779/page-21#post-73867) for hardware and network shares, then return here to install HCC.

If Docker is missing, install it first using [Docker's official instructions](https://docs.docker.com/engine/install/) or your device's guide. HCC cannot install Docker for you.

## 1. Install HCC

**Choose one method.** If you already use Portainer, start there. If you work with Compose files, choose Docker Compose. **You don't need both.**

### Option A. Portainer (no terminal)

1. Open **Portainer → Stacks → Add stack**.
2. Enter a name, for example `home-cinema-control`, and open the stack web editor.
3. Copy the configuration below and paste it **in full** into the editor.
4. Click **Deploy the stack**.

**Expected result:** Portainer shows the new stack and the running HCC container.

### Option B. Docker Compose

1. Create a folder for HCC (for example, `home-cinema-control`).
2. Inside that folder, create a file named `compose.yaml`.
3. Copy the configuration below into that file and save it.
4. Open a terminal **inside that same folder** and run:

   ```bash
   docker compose pull
   docker compose up -d
   ```

**Expected result:** Docker starts HCC. Keep this folder: future updates use the same two commands from there.

### Configuration file (both methods)

Copy everything from `services:` through the final `volumes:` entry. You don't need to set a version variable.

```yaml
services:
  home-cinema-control:
    image: tousled/home-cinema-control:latest
    container_name: home-cinema-control
    network_mode: host
    cap_add:
      - NET_RAW
    restart: unless-stopped
    environment:
      TZ: Europe/Madrid
      PYTHONUNBUFFERED: "1"
      HCC_CONFIG_FILE: /config/config.json
      HCC_SECRETS_FILE_PATH: /config/secrets.json
    volumes:
      - home-cinema-control-config:/config

volumes:
  home-cinema-control-config:
    name: home-cinema-control-config
```

**Image source:** this example uses Docker Hub and needs no sign-in. If an existing installation still uses GHCR and gets `denied` or `403 Forbidden`, see [how to switch safely](docs/troubleshoot.en.md#ghcr-pull-fails-denied-or-403-forbidden).

**Important:** keep the `home-cinema-control-config` volume. HCC stores your settings there. Don't delete it when updating.

## 2. Open HCC

In a browser on your local network, enter:

```text
http://YOUR-NAS-IP:8090
```

Replace `YOUR-NAS-IP` with the local IP address of the NAS or computer running HCC. For example, if its address is `192.168.1.50`, open `http://192.168.1.50:8090`.

**Expected result:** you see HCC's web interface. If it doesn't load, check in Portainer or Docker that the container is running, and see [troubleshooting](docs/troubleshoot.en.md).

## 3. Follow the illustrated setup

Next, open [**your first steps in HCC**](docs/getting-started.en.md).

The screenshots walk you through **Media Server, OPPO/Chinoppo, Media Paths and Room (TV and/or AV receiver)**. If you need help with your folders, use the [illustrated Media Paths guide](docs/configure-media-paths.en.md).

**TV and AV receiver setup is part of the normal walkthrough**, including setups with just a TV. **Home Assistant can wait**: it is entirely optional.

## If the OPPO or a media path is not ready

HCC **doesn't hand a movie over to the OPPO** unless it can confirm the player responds and the media path is configured and verified. On Emby/Jellyfin clients supporting remote notifications, you'll see the problem first and the recommended action in a separate message.

| Situation | Error message | Suggested action |
|---|---|---|
| OPPO off or unreachable | “OPPO isn't responding.” | “Make sure it's powered on and connected to the network.” |
| Unverified path (Emby) | “Path not verified. Playback continues in Emby.” | “Verify the path in HCC Media Paths.” |
| Missing path (Jellyfin) | “Path not configured. Playback continues in Jellyfin.” | “Configure the path in HCC Media Paths.” |

**Emby or Jellyfin is taken from your configured media server**. When the OPPO is unreachable, HCC leaves TV and receiver inputs unchanged. For a missing or unverified media path, HCC doesn't hand over to the OPPO, and native playback may continue in Emby/Jellyfin. If the source app was already playing when HCC detected the unavailable OPPO, you may need to stop it manually. Notification visibility depends on the client.

Check **Media Player → Test connection** or **Media Paths → Test path**. For screenshots, see [First steps](docs/getting-started.en.md#6-play-your-first-movie).

## After installation

- **Update HCC:** [Portainer](docs/update-portainer.en.md) or [Docker Compose](docs/update-compose.en.md). You don't need to install it again. The Portainer guide also explains webhook errors and the wait when GitHub limits version lookups.
- **HCC looks unconfigured:** [configuration recovery](docs/recover-configuration.en.md), without deleting anything.
- **Special deployments:** [advanced Docker operations](docs/advanced-docker-operations.en.md).

- **Help improve HCC:** [short questions, interests, and consent](docs/participate.en.md). Taking part is optional; no
  account or email is required.
