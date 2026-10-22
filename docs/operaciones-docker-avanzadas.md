# Operaciones Docker avanzadas

[Inicio](../README.md) · [Instalación](../INSTALL.md) · [English](advanced-docker-operations.en.md)

Guías para operaciones especiales. Para actualizar un stack habitual, usa [Portainer](actualizar-portainer.md) o [Compose](actualizar-compose.md). Las opciones y conceptos se explican en la [referencia](referencia-avanzada.md).

**Antes de continuar:** utiliza siempre el volumen o carpeta que ya tiene tu instalación. No crees otro proyecto para actualizar HCC, ni borres volúmenes. Si no reconoces el montaje de `/config`, detente y consulta [recuperar configuración](recuperar-configuracion.md).

## Instalar mediante `docker run` (avanzado)

Esta opción es **solo para una instalación nueva** y para quien ya conoce Docker. Si HCC ya funciona y quieres actualizarlo, no ejecutes este comando: primero localiza tu contenedor y su montaje de `/config`.

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

Abre:

```text
http://<tu-host>:8090
```

`--network host` es importante porque HCC habla directamente con Emby, el OPPO/Chinoppo, TV, AVR y herramientas de
descubrimiento como `arp-scan`.

## Actualizar desde un gestor del NAS

Synology Container Manager, Unraid u otro gestor solo debe usarse para este procedimiento si permite editar o volver a
desplegar el mismo proyecto Compose/Stack.

1. Abre el proyecto o aplicación existente de HCC, no la pantalla para crear una aplicación nueva.
2. Comprueba que conserva el mismo archivo Compose, el mismo servicio y el mismo volumen o montaje en `/config`.
3. Cambia una imagen `:1.3.0` por `:latest` o elimina la variable que la fija.
4. Usa **Update**, **Redeploy**, **Recreate** o el nombre equivalente del gestor, activando la descarga de la imagen si
   ofrece esa opción.
5. Confirma que el proyecto sigue usando el mismo volumen y comprueba HCC y su versión.

Los nombres de los botones cambian según el gestor. Si no puedes confirmar que conserva `/config`, no continúes: usa la
documentación de ese gestor o pide ayuda antes de eliminar nada.

## Si instalaste con `docker run`

Este es un procedimiento avanzado. Primero comprueba que el contenedor usa el volumen correcto:

```bash
docker inspect home-cinema-control --format '{{range .Mounts}}{{println .Name .Source "->" .Destination}}{{end}}'
```

Debe aparecer `home-cinema-control-config` apuntando a `/config`, o la misma carpeta del host que usaste al instalar.
Descarga la nueva imagen y recrea solo el contenedor con exactamente el mismo montaje. No borres el volumen. Si no conservas el comando original, **detente**: anota la configuración obtenida con `docker inspect` y busca el despliegue existente. No cambies a Compose ni vuelvas a instalar HCC como supuesto método de actualización, porque podrías iniciar otro proyecto con datos distintos. Consulta [recuperar configuración](recuperar-configuracion.md).

## Crear una copia manual de un volumen Docker

HCC no exporta la configuración desde la interfaz. Si tu NAS o gestor no ofrece snapshots o copias de volúmenes, una
persona con acceso al terminal puede crear una copia del volumen oficial sin modificarlo:

Para usar el ejemplo oficial, el volumen debe llamarse `home-cinema-control-config`. Si tu instalación usa otra ruta o un volumen diferente, no copies el comando sin adaptarlo.

```bash
docker volume inspect home-cinema-control-config
```

Antes de hacer la copia, comprueba también que el contenedor de HCC usa **ese mismo volumen** en `/config` con `docker inspect home-cinema-control --format '{{range .Mounts}}{{println .Name .Destination}}{{end}}'`. Si `docker volume inspect` devuelve un error, **no ejecutes el comando de copia**: primero identifica el volumen correcto. Docker puede crear volúmenes vacíos al usar algunos comandos. Los archivos de copia contienen credenciales: protégelos y no los compartas.

```bash
mkdir -p hcc-backups
docker run --rm \
  --mount source=home-cinema-control-config,target=/config,readonly \
  --volume "$PWD/hcc-backups:/backup" \
  alpine:3.20 \
  tar -czf /backup/hcc-config-backup.tar.gz -C /config .
```

El archivo `hcc-backups/hcc-config-backup.tar.gz` debe aparecer en la carpeta actual. Guarda esa copia fuera del host
Docker. Este procedimiento es opcional y está pensado para Linux/macOS; en Windows o en un NAS usa la herramienta de
copias del propio sistema.

**Resultado esperado:** el archivo `hcc-backups/hcc-config-backup.tar.gz` contiene `config.json` y, si tu instalación usa secretos, `secrets.json`. Confirma su contenido con `tar -tzf hcc-backups/hcc-config-backup.tar.gz`, sin extraerlo ni compartirlo. Guárdalo fuera del host Docker. Para restaurar, sigue el procedimiento de copias de tu NAS o pide ayuda antes de sobrescribir el volumen actual.
