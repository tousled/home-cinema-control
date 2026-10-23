# Actualizar HCC con Docker Compose

[Inicio](../README.md) · [Instalación](../INSTALL.md) · [English](update-compose.en.md)

Si ya tienes HCC instalado con Docker Compose y utilizas `latest`, **solo tienes que descargar la nueva imagen y reiniciar el servicio**. No necesitas crear un archivo nuevo ni cambiar la configuración.

## Actualizar

1. Abre un terminal en el servidor donde está instalado HCC.
2. Entra en la **misma carpeta donde guardaste el archivo Compose** al instalarlo (`compose.yaml` o `docker-compose.yml`).
3. Ejecuta estos dos comandos, uno detrás de otro:

   ```bash
   docker compose pull
   docker compose up -d
   ```

4. Abre HCC y consulta **Diagnóstico** para ver la versión instalada.

Si aparece la nueva versión y tu configuración sigue ahí, **has terminado**.

No borres el volumen de HCC ni ejecutes `docker compose down -v`: allí se guardan los ajustes.

Si `docker compose pull` termina con `denied` o `403 Forbidden` al descargar desde GHCR, consulta [cómo cambiar a Docker Hub conservando tu configuración](solucionar-problemas.md#error-de-descarga-desde-ghcr-denied-o-403-forbidden).

## Si la versión no ha cambiado

Comprueba lo siguiente, por este orden:

1. **Carpeta correcta.** Los comandos deben ejecutarse donde está el Compose de tu instalación. Si no recuerdas la ruta, puedes consultarla con:

   ```bash
   docker inspect home-cinema-control --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}'
   ```

   Si no devuelve ninguna ruta, busca el archivo Compose original. No crees otro.

2. **Versión fijada.** Si el archivo contiene una imagen terminada en `:1.3.0` (u otra versión concreta), Docker seguirá usando esa versión. Cambia **solo el tag** a `:latest` y repite los dos comandos. Si ya usa `latest`, no tienes que modificar nada.

3. **Variable de versión.** Si la imagen utiliza `HCC_VERSION`, comprueba que no esté fijada a una versión anterior en las variables del entorno o en `.env`. Puedes comprobar qué imagen utilizará Compose con:

   ```bash
   docker compose config --images
   ```

   Este comando muestra las imágenes configuradas. No compartas la salida completa de `docker compose config`: puede contener credenciales.

`latest` significa **última versión estable**, no versión de prueba (RC).

## Si HCC se abre sin tu configuración

**No completes otra vez el asistente ni borres el volumen.** Es posible que hayas arrancado HCC con otro montaje de `/config`. Sigue la [guía para recuperar tu configuración](recuperar-configuracion.md).

Si HCC no arranca, revisa `docker compose logs --tail=100 home-cinema-control` desde la carpeta original y consulta [solución de problemas](solucionar-problemas.md).
