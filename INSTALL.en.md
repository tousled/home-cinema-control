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
    image: ghcr.io/tousled/home-cinema-control:latest
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

## After installation

- **Update HCC:** [Portainer](docs/update-portainer.en.md) or [Docker Compose](docs/update-compose.en.md). You don't need to install it again.
- **HCC looks unconfigured:** [configuration recovery](docs/recover-configuration.en.md), without deleting anything.
- **Special deployments:** [advanced Docker operations](docs/advanced-docker-operations.en.md).
