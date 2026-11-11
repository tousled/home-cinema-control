# Install Home Cinema Control

[Español](INSTALL.md) · [Home](README.en.md)

Install HCC, then connect your media server, player, and movie folders in your browser. TV, AV receiver, and Home
Assistant setup is optional.

> This guide prepares the future 1.5.0. The latest published stable release is 1.4.5, which `latest` installs until
> another stable release is published. Kodi requires the 1.5.0 described here. To test a candidate beforehand, use only a
> tag announced in the [project releases](https://github.com/tousled/home-cinema-control/releases); do not guess a tag.

## Before you start

Check that you have:

- Docker running on a 64-bit NAS or computer, with Linux and host networking. Images target `linux/amd64` and
  `linux/arm64`; 32-bit ARM images are not published.
- A working Emby or Jellyfin server with movies visible in its library.
- An OPPO/Chinoppo with compatible network control or Kodi on the same local network. Your player must be able to open
  movies through NFS or SMB, the two supported types of shared folder.

For Docker Desktop, use Linux containers and enable **Settings → Resources → Network → Enable host networking**
(available from Docker Desktop 4.34). This mode has network discovery limitations: enter addresses manually if
suggestions are missing.
See [Docker's host networking documentation](https://docs.docker.com/engine/network/drivers/host/). A NAS or Linux
server is the recommended route.

If Docker is not installed, follow the [official installation instructions](https://docs.docker.com/engine/install/) or
your NAS manufacturer's guide. HCC does not install Docker. You do not need Home Assistant for your first movie.

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

The example downloads the image from Docker Hub. If an older installation uses GHCR and reports `denied` or
`403 Forbidden`,
see [how to change registries while preserving settings](docs/troubleshoot.en.md#ghcr-pull-fails-denied-or-403-forbidden).

The `home-cinema-control-config` volume is where Docker keeps your settings and passwords. Keep the same volume during
updates; do not delete it. HCC stores settings in `config.json` and secrets in `secrets.json`. After an interrupted
save, also keep hidden files in the volume and restart with the same
mount: [recovering an interrupted save](docs/recover-configuration.en.md#if-a-save-is-interrupted).

## 2. Open HCC

In a browser on your network, open `http://YOUR-NAS-IP:8090`. Replace `YOUR-NAS-IP` with the address of the NAS or
computer running Docker. For example, if its address is `192.168.1.50`, open `http://192.168.1.50:8090`. Addresses in
this guide are examples; use those of your own devices.

Expected result: HCC opens. If it does not, check that the container is running in Portainer or Docker and
see [troubleshooting](docs/troubleshoot.en.md).

## 3. Set up HCC and play your first movie

Follow [first steps in HCC](docs/getting-started.en.md). The complete walkthrough explains how to:

1. Authorise Emby or Jellyfin and choose the device HCC monitors.
2. Prepare and connect OPPO/Chinoppo or Kodi.
3. Choose player folders, test the paths, and save the result.
4. Set up your TV and/or AV receiver if you want HCC to coordinate inputs.
5. Start your first movie from Emby/Jellyfin and check progress.

The walkthrough includes current OPPO, Kodi, Paths, and Room screenshots captured in an isolated instance with
demonstration data and simulated devices. The [folder guide](docs/configure-media-paths.en.md) expands on NFS/SMB
options. Before choosing HDMI inputs, check
the [wiring layouts](docs/getting-started.en.md#5-tv-and-av-receiver-optional).

## After installation

Use the [Portainer](docs/update-portainer.en.md) or [Docker Compose](docs/update-compose.en.md) guide to update without
reinstalling. If HCC appears empty, check [configuration recovery](docs/recover-configuration.en.md) before setting
anything up again.

[Home Assistant](docs/home-assistant.en.md) and [Take part](docs/participate.en.md) are optional. For manual backups or
special installations, see [advanced Docker operations](docs/advanced-docker-operations.en.md).
