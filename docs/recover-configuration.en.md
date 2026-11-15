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
