# Update HCC with Docker Compose

[Home](../README.en.md) · [Installation](../INSTALL.en.md) · [Español](actualizar-compose.md)

If you installed HCC with Docker Compose and use `latest`, **you only need to download the updated image and restart the service**. You don't need a new Compose file or different settings.

## Update

1. Open a terminal on the server running HCC.
2. Go to the **same folder that contains your original Compose file** (`compose.yaml` or `docker-compose.yml`).
3. Run these two commands:

   ```bash
   docker compose pull
   docker compose up -d
   ```

4. Open HCC and check the installed version under **Diagnostics**.

If the new version appears and your settings are still there, **you're done**.

Do not delete HCC's volume or run `docker compose down -v`. The volume stores your settings.

## If the version hasn't changed

Check these items in order:

1. **Correct folder.** Run the commands from the folder containing the original Compose file. If you don't remember it, try:

   ```bash
   docker inspect home-cinema-control --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}'
   ```

   If it shows no path, locate the original Compose file. Don't create a replacement.

2. **Pinned image.** If the file uses `:1.3.0` (or another numbered release), Docker will keep using that version. Change **only the image tag** to `:latest`, then run the two update commands again. If it already uses `latest`, leave it unchanged.

3. **Version variable.** If the image uses `HCC_VERSION`, check whether the environment or `.env` pins an older version. To see the actual image Compose will use, run:

   ```bash
   docker compose config --images
   ```

   This lists configured images. Don't share the full output of `docker compose config`, as it can contain secrets.

`latest` means **latest stable release**, not a release candidate (RC).

## If HCC opens without your settings

**Don't run the setup wizard again or delete the volume.** HCC may be using another `/config` mount. Follow the [configuration recovery guide](recover-configuration.en.md).

If HCC won't start, run `docker compose logs --tail=100 home-cinema-control` from the original project folder and read [troubleshooting](troubleshoot.en.md).
