# Home Cinema Control

<p align="center">
  <img src="https://raw.githubusercontent.com/tousled/home-cinema-control/main/assets/brand/hcc-logo.png" alt="Home Cinema Control" width="720">
</p>

Home Cinema Control (HCC) turns playback in Emby or Jellyfin into a complete home-cinema flow for OPPO and Chinoppo
players:
verified media paths, NFS/SMB mounts, optional TV/AV input control, diagnostics, logs, and Docker-first updates.

## What it does

- Watches Emby or Jellyfin playback sessions.
- Resolves the media-server path to the path visible from the OPPO or Chinoppo player.
- Mounts NFS or SMB/CIFS shares per library mapping.
- Starts playback on OPPO UDP-203/205 and compatible Chinoppo players.
- Optionally switches TV and AV receiver inputs.
- Reports playback progress and state back to Emby when supported by the device flow.
- Exposes diagnostics, structured logs with copy/download support, version checks, update hooks, and rollback guidance.

## Quick start

```bash
docker volume create home-cinema-control-config

docker run -d \
  --name home-cinema-control \
  --network host \
  --cap-add NET_RAW \
  --restart unless-stopped \
  -e TZ=Europe/Madrid \
  -e PYTHONUNBUFFERED=1 \
  -e HCC_CONFIG_FILE=/config/config.json \
  -e HCC_SECRETS_FILE_PATH=/config/secrets.json \
  -v home-cinema-control-config:/config \
  tousled/home-cinema-control:latest
```

Open:

```text
http://<host>:8090
```

Host networking is required because HCC talks directly to Emby, the player, optional room devices, and local network
discovery tools.

## Recommended Docker Compose install

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

```bash
docker compose pull
docker compose up -d
```

Docker Compose is the better option for long-running installs, version pinning, updates, and rollback.

## Image tags

- `latest`: latest stable release.
- `1.0.0`, `1.0.1`, ...: pinned stable releases.
- `rc`: latest release candidate.
- `1.0.0-rc.1`, ...: pinned release candidates.

Images are published for `linux/amd64` and `linux/arm64`.

## Requirements

- Docker host with host networking support.
- Emby or Jellyfin server reachable from the HCC host.
- OPPO UDP-203/205 or compatible Chinoppo player exposing the OPPO-compatible control API.
- NAS or shared media folders reachable by both Emby and the player.
- NFS or SMB/CIFS shares mapped per media library.
- Optional TV and AV receiver control.

## Documentation

- GitHub project: https://github.com/tousled/home-cinema-control
- Installation guide: https://github.com/tousled/home-cinema-control/blob/main/INSTALL.md
- English installation guide: https://github.com/tousled/home-cinema-control/blob/main/INSTALL.en.md
- Release policy: https://github.com/tousled/home-cinema-control/blob/main/RELEASE_POLICY.md
- Changelog: https://github.com/tousled/home-cinema-control/blob/main/CHANGELOG.md

## Registries

- Docker Hub: `tousled/home-cinema-control`
- GitHub Container Registry: `ghcr.io/tousled/home-cinema-control`

## License

Home Cinema Control is source-available, not open source. Personal non-commercial use is allowed under the repository
license. Commercial use, redistribution, hosted services, published derivative images or packages, and paid support
bundles require written permission from the maintainer.
