# Home Cinema Control

Home Cinema Control (HCC) coordina una sesión de cine en casa entre Emby o Jellyfin, un reproductor OPPO/Chinoppo y los dispositivos de la sala.

Cuando el usuario pulsa Play, HCC ayuda a resolver la ruta correcta, preparar el acceso NFS o SMB del reproductor, iniciar la reproducción, cambiar las entradas configuradas y devolver el estado de reproducción al servidor multimedia.

## Qué incluye

- Integración con Emby y Jellyfin.
- Reproducción de archivos, ISOs y carpetas Blu-ray/UHD en reproductores OPPO/Chinoppo compatibles.
- Mapeos de rutas por biblioteca con NFS o SMB/CIFS.
- Control opcional de TV y receptor AV.
- Diagnóstico, logs y estado de actualización desde la interfaz web.
- Imágenes Docker para `linux/amd64` y `linux/arm64`.

Las integraciones de dispositivos dependen del modelo, firmware y validación disponible. Consulta la documentación antes de asumir compatibilidad con una sala concreta.

## Instalación

La instalación recomendada usa Docker con red host y configuración persistente:

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

Abre `http://<tu-host>:8090` y sigue el asistente de configuración. La guía completa está en [INSTALL.md](INSTALL.md) y [INSTALL.en.md](INSTALL.en.md).

## Versiones e historia

- [Releases](https://github.com/tousled/home-cinema-control/releases)
- [RELEASE_HISTORY.md](RELEASE_HISTORY.md)
- [CHANGELOG.md](CHANGELOG.md)
- [Notas históricas de release](docs/releases/)

HCC tiene una evolución documentada desde `0.1.0`, con múltiples versiones estables, release candidates, correcciones e integraciones. Este repositorio conserva esa historia como documentación pública de producto.

## Soporte

Usa [Issues](https://github.com/tousled/home-cinema-control/issues) para errores reproducibles, preguntas y propuestas. Incluye versión, plataforma, modelo de reproductor y un diagnóstico redactado; nunca adjuntes contraseñas, tokens, claves o archivos de configuración privados.

Consulta [SUPPORT.md](SUPPORT.md) y [SECURITY.md](SECURITY.md) antes de abrir un ticket.

## Licencia

HCC se distribuye bajo la **Home Cinema Control Proprietary Software License 2.0**. No es software open source y esta licencia no concede acceso al código fuente.

Home Cinema Control  \
Copyright © 2026 Llorente Software Solutions, S.L.  \
Developed/distributed under the Bytehund brand.

Consulta [LICENSE](LICENSE) para los términos completos.
