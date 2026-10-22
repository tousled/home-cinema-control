# Advanced Docker operations

[Home](../README.en.md) · [Installation](../INSTALL.en.md) · [Español](operaciones-docker-avanzadas.md)

Guides for less common Docker operations. For regular stack updates, use [Portainer](update-portainer.en.md) or [Compose](update-compose.en.md). See the [reference](advanced-reference.en.md) for terms and configuration options.

**Before proceeding:** preserve the actual volume or host folder used by your existing installation. Do not create another project merely to update HCC, and do not delete volumes. If you cannot identify the `/config` mount, stop and read [configuration recovery](recover-configuration.en.md).

## Install using `docker run` (advanced)

This option is **only for a new installation** and assumes you are familiar with Docker. If HCC is already running and you want to update it, do not run this command: identify your existing container and `/config` mount first.

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

Open `http://<your-host>:8090`.

Host networking is required so HCC can reach Emby, the player, TV, AVR, and network discovery tools directly.

## Update from a NAS manager

Use Synology Container Manager, Unraid, or another manager only if it lets you edit or redeploy the same Compose/Stack
project.

1. Open HCC's existing project or application, not the screen for creating a new application.
2. Check that it keeps the same Compose file, service, and volume or host mount at `/config`.
3. Change an image tagged `:1.3.0` to `:latest`, or remove the variable that pins it.
4. Use **Update**, **Redeploy**, **Recreate**, or the equivalent action, and enable image pulling if offered.
5. Confirm that the project still uses the same volume and check HCC and its version.

Button names vary by manager. If you cannot confirm that `/config` will be preserved, stop and use that manager's
documentation or ask for help before removing anything.

## If you installed with `docker run`

This is an advanced procedure. First check that the container uses the right volume:

```bash
docker inspect home-cinema-control --format '{{range .Mounts}}{{println .Name .Source "->" .Destination}}{{end}}'
```

It should show `home-cinema-control-config` pointing to `/config`, or the same host folder used during installation.
Pull the new image and recreate only the container with exactly the same mount. Do not delete the volume. If you no longer have the original command, **stop**: inspect the existing container and recover its deployment details. Do not switch to Compose or reinstall HCC as an update shortcut; that can start a different project with different data. See [configuration recovery](recover-configuration.en.md).

## Back up a named Docker volume manually

HCC does not export configuration from its interface. If your NAS or manager has no volume snapshots or backups, someone
with terminal access can create a copy of the official volume without changing it:

To use the example, the named volume must be `home-cinema-control-config`. If your installation uses a different volume or a bind mount, do not copy this command without adapting it.

```bash
docker volume inspect home-cinema-control-config
```

Before backing up, also confirm that the HCC container mounts **that same volume** at `/config` using `docker inspect home-cinema-control --format '{{range .Mounts}}{{println .Name .Destination}}{{end}}'`. If `docker volume inspect` fails, **do not run the backup command**. Identify the correct volume first. Some Docker commands automatically create an empty volume. Backups contain credentials: protect the archives and do not share them.

```bash
mkdir -p hcc-backups
docker run --rm \
  --mount source=home-cinema-control-config,target=/config,readonly \
  --volume "$PWD/hcc-backups:/backup" \
  alpine:3.20 \
  tar -czf /backup/hcc-config-backup.tar.gz -C /config .
```

The file `hcc-backups/hcc-config-backup.tar.gz` should appear in the current folder. Store that copy outside the Docker
host. This procedure is optional and intended for Linux/macOS; on Windows or a NAS, use the system's own backup tool.

**Expected result:** `hcc-backups/hcc-config-backup.tar.gz` includes `config.json` and, if your installation uses secrets, `secrets.json`. Check with `tar -tzf hcc-backups/hcc-config-backup.tar.gz` without extracting or sharing the archive. Store a copy outside the Docker host. For restoration, use the backup procedure for your NAS or seek help before overwriting your current volume.
