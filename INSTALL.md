# Instalación de Home Cinema Control

[English](INSTALL.en.md) · [README](README.md)

Esta guía cubre la instalación de HCC como contenedor Docker y la configuración inicial desde la interfaz web.

## Requisitos

- Docker en Linux, NAS o un host compatible.
- Red host disponible para el contenedor.
- Emby o Jellyfin accesible desde el host.
- Reproductor OPPO/Chinoppo compatible con la API de control.
- Bibliotecas multimedia visibles para el servidor y el reproductor.
- Recursos NFS o SMB/CIFS preparados cuando sean necesarios.
- TV y receptor AV opcionales.

## Inicio rápido

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

Abre `http://<tu-host>:8090`. La red host permite que HCC comunique directamente con el servidor multimedia, el reproductor, los dispositivos opcionales y las herramientas de descubrimiento local.

## Docker Compose

```yaml
services:
  home-cinema-control:
    image: ghcr.io/tousled/home-cinema-control:latest
    container_name: home-cinema-control
    network_mode: host
    cap_add:
      - NET_RAW
    restart: unless-stopped
    environment:
      TZ: Europe/Madrid
      PYTHONUNBUFFERED: "1"
      HCC_CONFIG_FILE: /config/config.json
      HCC_SECRETS_FILE_PATH: /config/secrets.json
    volumes:
      - home-cinema-control-config:/config

volumes:
  home-cinema-control-config:
    name: home-cinema-control-config
```

Inicia el servicio con `docker compose pull && docker compose up -d`.

## Configuración inicial

1. Abre la interfaz web.
2. Configura el proveedor de biblioteca: Emby o Jellyfin.
3. Comprueba la conexión y selecciona las bibliotecas que HCC debe interceptar.
4. Define el mapeo entre la ruta del servidor y la ruta visible para el reproductor.
5. Elige NFS o SMB/CIFS según el recurso compartido que hayas preparado.
6. Configura TV y receptor AV solo si forman parte de la sala.
7. Ejecuta las pruebas de diagnóstico antes de iniciar una reproducción real.

Las credenciales y datos sensibles deben permanecer en la configuración protegida del despliegue. No los publiques en Issues, diagnósticos ni capturas.

## Actualización y rollback

Para actualizar a la última estable ejecuta `docker compose pull && docker compose up -d`.

Para fijar una versión, sustituye `latest` por un tag concreto, por ejemplo `1.4.1`. Los prereleases usan tags como `1.4.1-rc.3` y `rc`.

La configuración persistente vive en el volumen `home-cinema-control-config`, separado de la imagen. Conserva una copia del volumen antes de cambios importantes.

## Ayuda

Consulta [SUPPORT.md](SUPPORT.md) y abre un issue con información redactada si necesitas ayuda.
