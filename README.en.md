# Home Cinema Control

Home Cinema Control (HCC) coordinates a home-cinema session between Emby or Jellyfin, an OPPO/Chinoppo player, and the devices in the room.

When a user presses Play, HCC helps resolve the correct path, prepare the player's NFS or SMB access, start playback, switch configured inputs, and report playback state back to the media server.

## What it includes

- Emby and Jellyfin integration.
- Playback of files, ISOs, and Blu-ray/UHD folders on compatible OPPO/Chinoppo players.
- Per-library NFS or SMB/CIFS path mappings.
- Optional TV and AV receiver control.
- Diagnostics, logs, and update status in the web interface.
- Docker images for `linux/amd64` and `linux/arm64`.

Device integrations depend on the model, firmware, and available validation. Read the documentation before assuming compatibility with a specific room.

## Installation

The recommended installation uses Docker with host networking and persistent configuration:

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

Open `http://<your-host>:8090` and follow the setup screens. The full guide is available in [INSTALL.en.md](INSTALL.en.md) and [INSTALL.md](INSTALL.md).

## Versions and history

- [Releases](https://github.com/tousled/home-cinema-control/releases)
- [RELEASE_HISTORY.md](RELEASE_HISTORY.md)
- [CHANGELOG.md](CHANGELOG.md)
- [Historical release notes](docs/releases/)

HCC has documented evolution since `0.1.0`, including stable versions, release candidates, fixes, and integrations. This repository preserves that history as public product documentation.

## Support

Use [Issues](https://github.com/tousled/home-cinema-control/issues) for reproducible bugs, questions, and proposals. Include the version, platform, player model, and a redacted diagnostic summary; never attach passwords, tokens, keys, or private configuration files.

See [SUPPORT.md](SUPPORT.md) and [SECURITY.md](SECURITY.md) before opening an issue.

## License

HCC is distributed under the **Home Cinema Control Proprietary Software License 2.0**. It is not open-source software, and this license does not grant access to the source code.

Home Cinema Control  \
Copyright © 2026 Llorente Software Solutions, S.L.  \
Developed/distributed under the Bytehund brand.

See [LICENSE](LICENSE) for the complete terms.
