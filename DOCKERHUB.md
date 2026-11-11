# Home Cinema Control

<p align="center">
  <img src="https://raw.githubusercontent.com/tousled/home-cinema-control/main/assets/brand/hcc-logo.png" alt="Home Cinema Control" width="720">
</p>

Choose a movie in Emby or Jellyfin. Home Cinema Control coordinates playback on your selected player, TV and AV receiver
inputs, and progress reporting. Optional Home Assistant events connect playback to your own lighting or scene
automations.

OPPO UDP-203/205 and compatible Chinoppo players use NFS or SMB shares. HCC 1.5.0 adds Kodi through HTTP control and
NFS/SMB video sources configured in Kodi. Each player retains its own settings and folder mappings.

> Prepared for the future 1.5.0, not published yet. The latest published stable release is 1.4.5. `latest` remains the
> published stable channel; it does not provide Kodi until a release containing it is published. For testing, use only a
> candidate tag announced in [project releases](https://github.com/tousled/home-cinema-control/releases).

## Install with Portainer or Docker Compose

You need a working Emby or Jellyfin server and a player that can open your movie folders over the local network. Images
target 64-bit Linux (`linux/amd64` and `linux/arm64`); 32-bit ARM images are not published.

Use a NAS or Linux Docker host with host networking. On Docker Desktop, Linux containers and **Enable host networking**
are required (Desktop 4.34 or later). Discovery may be limited; enter device IPs manually if needed.
See [Docker host networking](https://docs.docker.com/engine/network/drivers/host/).

1. In Portainer, open **Stacks → Add stack** and paste the complete example below, then click **Deploy the stack**.
   Alternatively, save it as `compose.yaml` in a dedicated folder on your Docker host.
2. For Compose, run the commands below from that same folder. Portainer users do not need to run them.
3. Open `http://YOUR-DOCKER-HOST-IP:8090` in a browser on your network.
4. Follow
   the [complete first-run setup](https://github.com/tousled/home-cinema-control/blob/main/docs/getting-started.en.md)
   to connect your server, player, and folders, then play a movie.

```yaml
services:
  home-cinema-control:
    image: tousled/home-cinema-control:${HCC_VERSION:-latest}
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

```bash
docker compose pull
docker compose up -d
```

Keep the `home-cinema-control-config` volume. It contains both `config.json` (settings) and `secrets.json`
(credentials). Replacing the image preserves them when the same volume stays mounted. Do not remove the volume or create
a different stack when updating an existing installation.

The installation example uses the official Compose settings with optional telemetry overrides omitted. `HCC_VERSION`
selects an image tag here; leave it unset to use `latest`. TV, receiver, Home Assistant, and voluntary telemetry can be
configured later.

## Update an existing installation

For Compose, return to your original Compose folder and run `docker compose pull` followed by `docker compose up -d`.
For Portainer, update the original stack and request a new image pull. Verify the installed version in HCC's
**Diagnostics** screen.

Use the
detailed [Compose update guide](https://github.com/tousled/home-cinema-control/blob/main/docs/update-compose.en.md)
or [Portainer update guide](https://github.com/tousled/home-cinema-control/blob/main/docs/update-portainer.en.md). Keep
the existing volume, mounts, and version variables. If HCC looks freshly installed after an update,
use [configuration recovery](https://github.com/tousled/home-cinema-control/blob/main/docs/recover-configuration.en.md)
before entering settings again.

## Images and tags

- `tousled/home-cinema-control:latest`: latest published stable release.
- `tousled/home-cinema-control:1.4.5`: published stable version pinned explicitly.
- `rc`: release-candidate channel, when available. Use only an announced, published candidate for testing; it is
  separate from `latest`.
- Exact candidate tags: use the spelling shown in the project's releases. This page does not announce a 1.5.0 image.

The alternative registry is `ghcr.io/tousled/home-cinema-control` with the corresponding published tag. If an older GHCR
deployment cannot pull with `denied` or `403 Forbidden`, change only the image registry to Docker Hub and retain its tag
and volume.
See [download troubleshooting](https://github.com/tousled/home-cinema-control/blob/main/docs/troubleshoot.en.md#ghcr-pull-fails-denied-or-403-forbidden).

## Kodi scope in 1.5.0

Enable HTTP remote control and authentication in Kodi, add NFS/SMB video sources there, then save and test Kodi in HCC.
Browse the sources from **Paths** and click **Test path**. This checks access without starting a movie.

Local Kodi folders are reserved for a later 1.5.x update, with no date announced. `plugin://` sources and other
protocols are unsupported. Kodi format support depends on its device; ISO, Blu-ray folders, and disc menus are not
verified as equivalent to OPPO. HCC does not provide Kodi power or disc-eject controls. There is no certified Kodi
platform/version matrix.

## Guides and help

- [Español: presentación e instalación](https://github.com/tousled/home-cinema-control/blob/main/INSTALL.md).
- [English installation](https://github.com/tousled/home-cinema-control/blob/main/INSTALL.en.md).
- [Player folders and NFS/SMB](https://github.com/tousled/home-cinema-control/blob/main/docs/configure-media-paths.en.md).
- [Troubleshooting and support](https://github.com/tousled/home-cinema-control/blob/main/docs/troubleshoot.en.md).
- [Home Assistant](https://github.com/tousled/home-cinema-control/blob/main/docs/home-assistant.en.md).
- [Optional participation](https://github.com/tousled/home-cinema-control/blob/main/docs/participate.en.md)
  and [telemetry](https://github.com/tousled/home-cinema-control/blob/main/docs/telemetry.en.md), off by default.
- [Changelog](https://github.com/tousled/home-cinema-control/blob/main/CHANGELOG.md).

Trinnov Altitude control has contract tests and awaits real-hardware validation. See
the [project README](https://github.com/tousled/home-cinema-control) for integrations and licensing.

## License

Home Cinema Control is proprietary software distributed by Llorente Software Solutions, S.L. under the Bytehund brand.
The Home Cinema Control Proprietary Software License 2.0 does not grant access to the source code.
