# Instalar Home Cinema Control

[English](INSTALL.en.md) · [Inicio](README.md)

**Vamos a poner HCC en marcha.** Si ya tienes Emby o Jellyfin, un reproductor OPPO/Chinoppo y Docker en tu NAS u ordenador, puedes seguir estos pasos aunque no seas experto en Docker.

Primero instalas HCC. Después, sigue las capturas para conectar **Emby/Jellyfin, el OPPO/Chinoppo, las carpetas de películas y tu TV y/o receptor AV**.

## Antes de empezar

Solo necesitas:

- Un **NAS u ordenador con Docker funcionando**. Si ya utilizas **Portainer**, puedes hacerlo desde su interfaz web, sin terminal.
- **Emby o Jellyfin** y un **OPPO/Chinoppo** conectados a la misma red local que HCC.
- Una carpeta de películas a la que el reproductor pueda acceder desde su menú de red. La conectaremos más adelante.

¿Todavía no tienes preparado el NAS, PC, Raspberry Pi o reproductor? Empieza por la [guía de AVPasión sobre Xnoppo](https://foro.avpasion.com/t/xnoppo-lo-mejor-de-emby-en-tu-oppo-203-205-y-chinoppo-clones-m9702-m9201-m9203-m9205.2779/page-21#post-73867), con instrucciones para preparar el equipo y compartir las carpetas. Después vuelve aquí para instalar HCC.

Si te falta Docker, instálalo primero siguiendo la [documentación oficial de Docker](https://docs.docker.com/engine/install/) o la guía de tu equipo. HCC no instala Docker automáticamente.

## 1. Instala HCC

**Elige un método.** Si ya usas Portainer, empieza por ahí. Si sueles trabajar con un archivo Compose, elige Docker Compose. **No necesitas hacer los dos.**

### Opción A. Desde Portainer (sin terminal)

1. Abre **Portainer → Stacks → Add stack**.
2. Escribe un nombre, por ejemplo `home-cinema-control`, y abre el editor web del stack.
3. Copia el archivo de configuración de abajo y pégalo **completo** en el editor.
4. Pulsa **Deploy the stack**.

**Resultado:** Portainer debe mostrar el stack creado y el contenedor de HCC funcionando.

### Opción B. Con Docker Compose

1. Crea una carpeta para HCC (por ejemplo, `home-cinema-control`).
2. Dentro de esa carpeta, crea un archivo llamado `compose.yaml`.
3. Copia el contenido de abajo y guárdalo en ese archivo.
4. Abre un terminal **dentro de esa misma carpeta** y ejecuta:

   ```bash
   docker compose pull
   docker compose up -d
   ```

**Resultado:** Docker inicia HCC. Conserva esa carpeta: para actualizarlo usarás los mismos dos comandos desde allí.

### Archivo de configuración (para ambas opciones)

Copia desde `services:` hasta la última línea de `volumes:`. No hace falta cambiar ninguna variable para empezar.

```yaml
services:
  home-cinema-control:
    image: tousled/home-cinema-control:latest
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

**Origen de descarga:** el archivo utiliza Docker Hub, sin necesidad de iniciar sesión. Si estás actualizando una instalación antigua que utiliza GHCR y ves `denied` o `403 Forbidden`, sigue la [solución para cambiar de registro sin perder los ajustes](docs/solucionar-problemas.md#docker-no-puede-descargar-la-imagen-desde-ghcr).

**Muy importante:** conserva el volumen `home-cinema-control-config`: es donde HCC guarda los ajustes. No debes borrarlo al actualizar.

## 2. Abre HCC

Desde el navegador de un dispositivo de tu red, escribe:

```text
http://IP-DE-TU-NAS:8090
```

Sustituye `IP-DE-TU-NAS` por la dirección de red del ordenador o NAS donde has instalado HCC. Por ejemplo, si su dirección es `192.168.1.50`, entrarías en `http://192.168.1.50:8090`.

**Resultado:** verás la interfaz de HCC. Si no abre, comprueba en Portainer o Docker que el contenedor está funcionando y consulta [solución de problemas](docs/solucionar-problemas.md).

## 3. Sigue las pantallas con capturas

Ahora viene la parte visual: [**primeros pasos en HCC**](docs/primeros-pasos.md).

Te enseñará a conectar **Media Server, OPPO/Chinoppo, Media Paths y Sala (TV y/o receptor AV)**, cada uno con sus capturas. Si necesitas ayuda con las carpetas, tienes la [guía visual de Media Paths](docs/configurar-rutas.md).

Configurar la **TV o el receptor AV es habitual y está incluido en el recorrido principal**; puedes hacerlo aunque solo tengas TV. **Home Assistant sí queda para más adelante**: es completamente opcional.

## ¿Y después?

- **Actualizar HCC:** [Portainer](docs/actualizar-portainer.md) o [Docker Compose](docs/actualizar-compose.md). No tendrás que instalarlo de nuevo.
- **HCC aparece vacío:** [recuperar configuración](docs/recuperar-configuracion.md), sin borrar nada.
- **Instalaciones especiales:** [operaciones Docker avanzadas](docs/operaciones-docker-avanzadas.md).

- **Ayudar a mejorar HCC:** [preguntas breves, intereses y consentimiento](docs/participar.md). Es opcional; no
  necesitas cuenta ni email.
