# Recover your HCC configuration

[Home](../README.en.md) · [Installation](../INSTALL.en.md) · [Español](recuperar-configuracion.md)

If HCC shows the setup wizard after an update, **your settings may still be intact**. The container might be using a different volume.

**Don't complete the setup wizard or delete any volumes.**

## 1. Check which storage HCC uses

**In Portainer:**

1. Open **Containers** and select your HCC container.
2. Find **Volumes** or **Mounts**.
3. Look for the entry ending in `/config`. It must point to the **same Docker volume or NAS folder used before**. Also check your original project under **Stacks**; don't create another one.

**With Docker Compose:**

Run this command on your Docker host:

```bash
docker inspect home-cinema-control --format '{{range .Mounts}}{{println .Name .Source "->" .Destination}}{{end}}'
```

Find the entry ending in `/config`. If your container has a different name, use that name in the command.

## 2. If the volume or folder changed

Open the **original** stack or Compose file and reconnect the storage you used before. Don't create a new stack, rename the project or delete the volume you found.

If you don't remember the original volume, look under **Volumes** in Portainer or run `docker volume ls` in a terminal. **Don't try random volumes**; identify where your files were stored first.

## 3. If the original volume was deleted

Only a **NAS/server backup or snapshot** can recover your previous settings. Before setting up HCC from scratch, check that no other volume or folder still contains the configuration.

The important files inside `/config` are `config.json` and `secrets.json`.

To avoid this issue later, keep the same `/config` mount during updates and back it up. For manual backups, see [advanced Docker operations](advanced-docker-operations.en.md).

## If a save is interrupted

HCC 1.5.0 stores settings in `config.json` and passwords in `secrets.json`, and recovers both files as one update after
an interrupted save. You do not need to edit them to recover the operation.

1. Keep the entire volume or directory previously mounted at `/config`, including hidden files. If
   `HCC_SECRETS_FILE_PATH` points to another directory, also keep that entire directory and its hidden files.
2. Restart the same container with the same `HCC_CONFIG_FILE` and `HCC_SECRETS_FILE_PATH` settings.
3. Reopen HCC and check the setting you were saving. An interrupted operation may have completed during restart.

Do not delete `.hcc-next.json` or `.hcc-transaction.json` recovery files while recovery is pending. HCC removes them
after completing or discarding the operation. They may contain secrets: do not publish them or copy only one file from a
pending update. For a backup, preserve both complete directories while HCC is stopped if the paths differ.

If the log reports a changed secrets path, restore the previous path before restarting. Do not run two HCC containers
writing to the same volume. If recovery fails, preserve a complete copy and
contact [support](troubleshoot.en.md#contact-and-support) without sharing passwords.

## When switching players

OPPO and Kodi keep independent settings and media paths. Selecting OPPO does not delete Kodi's password or folders, and
vice versa. Check the active player and media server before assuming data is missing.

Migration retains earlier paths for OPPO. Configure Kodi's own paths separately. Do not manually copy passwords into
`config.json`: secrets belong in `secrets.json`.
