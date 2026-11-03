# Update HCC with Portainer

[Home](../README.en.md) · [Installation](../INSTALL.en.md) · [Español](actualizar-portainer.md)

If you installed HCC as a **Portainer stack**, you normally only need to update that existing stack. You don't need a new stack or different settings.

## Update

1. In Portainer, open **Stacks** and select your existing HCC stack.
2. Click **Update the stack**. If **Re-pull image** is available, enable it to download the updated image.
3. When it finishes, open HCC and check the version under **Diagnostics**.

If the new version appears and your settings remain, **you're done**.

**Don't delete the stack or HCC's volume.** The `/config` storage contains your settings.

If GHCR returns `denied` or `403 Forbidden` during a download, see [how to switch this stack to Docker Hub](troubleshoot.en.md#ghcr-pull-fails-denied-or-403-forbidden).

## Update from HCC with a webhook

If you configured an update webhook, HCC confirms completion only after it responds with the expected installed version. HTTP errors appear on screen; a connection interrupted during restart keeps the version check running without resending the webhook.

If the version cannot be confirmed, check that the webhook targets the correct stack, its image uses the desired version or `latest`, and Portainer pulls the image. HCC logs record delivery attempts and results without exposing the webhook URL.

If GitHub limits version lookups, HCC shows a message and waits 15 minutes before another request, including manual checks. You can still update the stack directly in Portainer.

## If the version hasn't changed

Open the editor for the **same stack** and check the `image:` line.

- If it ends with `:latest`, leave it unchanged. Try **Update the stack** with **Re-pull image** enabled.
- If it ends with `:1.3.0` or another fixed version, change **only the tag** to `:latest` and update the stack.
- If the image uses `HCC_VERSION`, check **Environment variables** for an older pinned version. Remove it or set it to `latest`.

`latest` means the **latest stable release**, not an RC.

## If your configuration disappears

**Don't set up HCC again or delete the stack.** Use [configuration recovery](recover-configuration.en.md) to check whether the container still uses the original volume or host folder at `/config`.

If HCC won't start, view the container logs in Portainer and consult [troubleshooting](troubleshoot.en.md).
