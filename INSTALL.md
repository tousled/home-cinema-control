# Instalar Home Cinema Control

[English](INSTALL.en.md) · [Inicio](README.md)

Instala HCC y después conecta tu servidor multimedia, el reproductor y las carpetas de películas desde el navegador. La
TV, el receptor AV y Home Assistant son opcionales.

> Esta guía prepara la futura 1.5.0. La última estable publicada es 1.4.6 y es la que instala `latest` hasta que se
> publique otra estable. Kodi requiere la 1.5.0 descrita en esta documentación. Para probar antes una candidata, utiliza
> únicamente una etiqueta anunciada en
> las [releases del proyecto](https://github.com/tousled/home-cinema-control/releases); no hay que adivinar una etiqueta.

## Antes de empezar

Comprueba que tienes:

- Docker funcionando en un NAS o equipo de 64 bits, con Linux y red de host. Las imágenes son para `linux/amd64` y
  `linux/arm64`; no se publican para ARM de 32 bits.
- Emby o Jellyfin funcionando y películas visibles en su biblioteca.
- Un OPPO/Chinoppo con control por red compatible o Kodi, conectado a la misma red local. El reproductor debe poder
  abrir las películas por NFS o SMB, los dos tipos de carpeta compartida admitidos.

Si utilizas Docker Desktop, necesitas contenedores Linux y activar **Settings → Resources → Network → Enable host
networking** (disponible desde Docker Desktop 4.34). Ese modo tiene limitaciones para el descubrimiento de red: si no
aparecen sugerencias, introduce las direcciones manualmente. Los resultados pueden pertenecer a la red virtual de
Docker: una dirección sugerida no verifica la identidad de tu TV o receptor. Consulta
la [documentación de Docker sobre red de host](https://docs.docker.com/engine/network/drivers/host/). Un NAS o servidor
Linux es el recorrido recomendado.

Si todavía no tienes Docker, sigue la [instalación oficial](https://docs.docker.com/engine/install/) o las instrucciones
del fabricante de tu NAS. HCC no instala Docker. No necesitas preparar Home Assistant para ver tu primera película.

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

El ejemplo descarga la imagen desde Docker Hub. Si una instalación anterior usa GHCR y falla con `denied` o
`403 Forbidden`,
consulta [cómo cambiar de registro conservando los ajustes](docs/solucionar-problemas.md#error-de-descarga-desde-ghcr-denied-o-403-forbidden).

El volumen `home-cinema-control-config` es el espacio donde Docker conserva tus ajustes y contraseñas. Mantén el mismo
volumen al actualizar; no lo borres. HCC guarda los ajustes en `config.json` y los secretos en `secrets.json`. Si un
guardado se interrumpe, conserva también los archivos ocultos del volumen y reinicia con el mismo
montaje: [recuperación de un guardado interrumpido](docs/recuperar-configuracion.md#si-se-interrumpe-un-guardado).

## 2. Abre HCC

En un navegador de tu red, abre `http://IP-DE-TU-NAS:8090`. Sustituye `IP-DE-TU-NAS` por la dirección del NAS u
ordenador que ejecuta Docker. Por ejemplo, si su dirección es `192.168.1.50`, abre `http://192.168.1.50:8090`. Las
direcciones de esta guía son ejemplos; utiliza las de tus equipos.

Resultado: aparece HCC. Si no abre, comprueba que el contenedor está en ejecución en Portainer o Docker y
consulta [solución de problemas](docs/solucionar-problemas.md).

## 3. Configura y reproduce tu primera película

Sigue los [primeros pasos dentro de HCC](docs/primeros-pasos.md) para conectar Emby/Jellyfin, configurar el
reproductor y las rutas, y reproducir tu primera película. La TV y el receptor AV son opcionales.

Puedes preparar las secciones y guardar rutas manuales aunque los equipos estén apagados. Si queda una comprobación
relevante, HCC explica la limitación al continuar. Guardar no verifica conexiones ni habilita una ruta para reproducir.
Las pruebas y las operaciones reales conservan sus requisitos.

Para NFS/SMB, consulta la [guía de carpetas](docs/configurar-rutas.md).
Antes de elegir entradas HDMI, revisa los [esquemas de cableado](docs/primeros-pasos.md#5-tv-y-receptor-av-opcional).
En **Sala**, el asistente separa dirección, conexión y entradas de TV/AV: guardar una dirección o HDMI no
significa que se haya comprobado su funcionamiento. Si un paso queda pendiente o una acción está deshabilitada,
consulta [Sala: problemas frecuentes](docs/solucionar-problemas.md#sala-tvav-problemas-frecuentes-en-150-rc2).

## Después de la instalación

Usa la guía de [Portainer](docs/actualizar-portainer.md) o [Docker Compose](docs/actualizar-compose.md) para actualizar
sin reinstalar. Si HCC aparece vacío, consulta [recuperar configuración](docs/recuperar-configuracion.md) antes de
volver a configurar nada.

[Home Assistant](docs/home-assistant.md) y [Participar](docs/participar.md) son opcionales.
Para copias manuales o instalaciones especiales,
consulta [operaciones Docker avanzadas](docs/operaciones-docker-avanzadas.md).
