# Installing Home Cinema Control

[Español](INSTALL.md) · [README](README.en.md)

This guide covers installing HCC as a Docker container and completing the initial setup in the web interface.

## Requirements

- Docker on Linux, a NAS, or a compatible host.
- Host networking available to the container.
- Emby or Jellyfin reachable from the host.
- An OPPO/Chinoppo player compatible with the control API.
- Media libraries visible to both the server and the player.
- NFS or SMB/CIFS shares prepared when required.
- TV and AV receiver are optional.

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
  ghcr.io/tousled/home-cinema-control:latest
```

Open `http://<your-host>:8090`. Host networking lets HCC communicate directly with the media server, player, optional room devices, and local discovery tools.

## Docker Compose

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

Start the service with `docker compose pull && docker compose up -d`.

## Initial setup

1. Open the web interface.
2. Configure the library provider: Emby or Jellyfin.
3. Test the connection and select the libraries HCC should intercept.
4. Define the mapping from the server path to the path visible to the player.
5. Select NFS or SMB/CIFS according to the share you prepared.
6. Configure TV and AV only when they are part of the room.
7. Run the diagnostic checks before starting real playback.

Keep credentials and sensitive data in the deployment's protected configuration. Do not publish them in Issues, diagnostics, or screenshots.

## Updates and rollback

To update to the latest stable image, run `docker compose pull && docker compose up -d`.

To pin a version, replace `latest` with a specific tag such as `1.4.1`. Prereleases use tags such as `1.4.1-rc.3` and `rc`.

Persistent configuration lives in the `home-cinema-control-config` volume, separate from the image. Back up the volume before important changes.

## Help

See [SUPPORT.md](SUPPORT.md) and open an issue with redacted information if you need help.
