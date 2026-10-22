# Actualizar HCC con Portainer

[Inicio](../README.md) · [Instalación](../INSTALL.md) · [English](update-portainer.en.md)

Si instalaste HCC desde un **stack de Portainer**, normalmente solo tienes que actualizar ese mismo stack. No necesitas crear uno nuevo ni modificar su configuración.

## Actualizar

1. En Portainer, entra en **Stacks** y abre el stack donde ya tienes HCC.
2. Pulsa **Update the stack**. Si aparece la opción **Re-pull image**, actívala para descargar la imagen nueva.
3. Cuando termine, abre HCC y mira la versión en **Diagnóstico**.

Si aparece la nueva versión y tus ajustes siguen ahí, **has terminado**.

**No elimines el stack ni el volumen de HCC.** El almacenamiento de `/config` contiene tu configuración.

## Si la versión no ha cambiado

Abre el editor del **mismo stack** y revisa la línea `image:`.

- Si termina en `:latest`, no cambies nada. Repite **Update the stack** con **Re-pull image** activado.
- Si termina en `:1.3.0` u otro número fijo, cambia **solo el tag** a `:latest` y actualiza el stack.
- Si utiliza `HCC_VERSION`, comprueba en **Environment variables** que no tenga fijada una versión anterior. Puedes quitar esa variable o poner `latest`.

`latest` es la **última versión estable**; no instala una RC.

## Si desaparece tu configuración

**No vuelvas a configurar HCC ni elimines el stack.** Comprueba con la [guía de recuperación](recuperar-configuracion.md) si el contenedor sigue usando el volumen o carpeta original de `/config`.

Si el servicio no arranca, abre los logs del contenedor desde Portainer y consulta [solución de problemas](solucionar-problemas.md).
