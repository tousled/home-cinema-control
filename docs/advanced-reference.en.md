# Advanced HCC reference

[Home](../README.en.md) · [Installation](../INSTALL.en.md) · [Español](referencia-avanzada.md)

Use this page to look up options without changing Docker. For NAS managers, `docker run` or a manual backup, see [advanced Docker operations](advanced-docker-operations.en.md).

## Quick lookup

| Item | Official Compose example | Purpose |
|---|---|---|
| Image | `tousled/home-cinema-control:${HCC_VERSION:-latest}` | Pulls the selected version; uses `latest` if the variable is unset. |
| `HCC_VERSION` | Unset | Optional. Pins a version for testing or rollback. |
| Configuration mount | `home-cinema-control-config:/config` | Preserves settings across updates. Keep the actual mount used by your installation. |
| `HCC_CONFIG_FILE` | `/config/config.json` | General settings file inside the container. |
| `HCC_SECRETS_FILE_PATH` | `/config/secrets.json` | Credentials and secrets file inside the container. |
| `network_mode` | `host` | Allows direct communication with devices on the local network. |

These values describe **the official installation example**, not necessarily every existing deployment.


### Image tags

- `latest`: the latest stable release. This is the recommended option for most installations.
- `1.4.5`: a manually pinned stable release. It only updates when you change the tag.
- `rc` or an announced exact candidate tag: for testing, only when published. Check the releases before selecting it;
  this does not mean 1.5.0 is available yet.

### `HCC_VERSION`

The `compose.yaml` uses `${HCC_VERSION:-latest}`. This means Compose uses `latest` when it finds no value in the `.env`
file or environment. You do not need to create this variable for a normal HCC installation or update.

You can use `HCC_VERSION` to pin a known version or temporarily return to an earlier version during recovery. If it
exists, the `.env` file must be next to `compose.yaml`. Do not share it or commit it to a repository.

### Where the configuration lives

The container receives configuration at `/config`:

- `config.json`: HCC's general configuration.
- `secrets.json`: protected credentials and secrets.
- `home-cinema-control-config`: the named volume used by the official Compose file.

The Docker image can be replaced without losing these files as long as the same volume or host mount remains connected.
Deleting the volume is not an update: it deletes the data.

### HCC's update button

HCC does not run Docker commands by itself. Without a webhook, **Update** shows a manual command for you to run in your
manager. With a webhook, HCC notifies the configured manager, and that manager downloads the image and restarts the
container. In both cases, the persistent volume must be preserved.

### Player profiles and paths in 1.5.0

Public configuration uses `media_players.active` for the selected player and `media_players.providers` for OPPO and Kodi
profiles. Kodi's username, address, port, and advanced settings are public; its password is stored only in
`secrets.json`, under `media_players.providers.kodi.password`. The interface reports whether a password is saved without
returning it. Omitting a password preserves the previous one.

Paths belong to the media server and player: `media_servers.providers.<server>.playback.path_mappings_by_player`. HCC
still reads earlier formats and assigns older paths without a player to OPPO. Do not edit or duplicate these settings to
switch devices: use **Media Player** and **Media Paths**.

Kodi's HTTP port is usually `8080`; use the one displayed in Kodi's control settings. HCC's web interface uses `8090`.
These are different services.

See [configuration recovery](recover-configuration.en.md#if-a-save-is-interrupted) for interrupted saves. Keep one HCC
process writing to each configuration volume.
