# Home Cinema Control

Home Cinema Control coordinates Emby or Jellyfin playback with compatible OPPO/Chinoppo players, NAS paths, optional TV/AV control, diagnostics, and Docker-first deployment.

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

Open `http://<host>:8090`. Host networking is required for direct communication with the media server, player, optional room devices, and network discovery.

## Tags

- `latest`: latest stable release.
- `<version>`: a pinned stable or prerelease version.
- `rc`: the latest release candidate.

Images are published for `linux/amd64` and `linux/arm64`.

Documentation and releases: https://github.com/tousled/home-cinema-control

Home Cinema Control is proprietary software distributed by Llorente Software Solutions, S.L. under the Bytehund brand.
