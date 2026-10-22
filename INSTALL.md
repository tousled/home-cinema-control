# Instalación y configuración de Home Cinema Control

[English](INSTALL.en.md) · [README](README.md)

Esta guía cubre el despliegue de HCC y la configuración desde la interfaz web. Está pensada para evitar los problemas
que más suelen aparecer en instalaciones con Emby/Jellyfin, NAS, OPPO/Chinoppo, TV y receptor AV: rutas mal mapeadas,
IPs escritas a mano, montajes que fallan sin explicación, CEC/ARC cambiando entradas y logs difíciles de interpretar.

Para capturas específicas de Synology, QNAP, Windows, Unraid o preparación del reproductor OPPO/Chinoppo, usa como
referencia externa el tutorial de la comunidad de AVPasion sobre Xnoppo:

https://foro.avpasion.com/t/xnoppo-lo-mejor-de-emby-en-tu-oppo-203-205-y-chinoppo-clones-m9702-m9201-m9203-m9205.2779/page-21#post-73867

Usa ese hilo para permisos de NAS, recursos compartidos y configuración del reproductor. Usa esta guía para HCC.

## ¿Qué quieres hacer?

No necesitas leer toda la guía. Empieza por la opción que describe tu caso:

- **Instalar HCC por primera vez:** ve a [Instalar HCC](#2-instalar-hcc). Para la mayoría de las instalaciones, usa
  [Docker Compose](#3-instalación-con-docker-compose).
- **Actualizar HCC:** ve directamente a [Actualizar HCC](#13-actualizar-hcc). No borres el volumen y ejecuta Compose
  desde la carpeta que contiene `compose.yaml`.
- **Usar Portainer, Synology o Unraid:**
  sigue [Instalar con Portainer u otra interfaz web](#31-instalar-con-portainer-u-otra-interfaz-web).
- **HCC ha perdido la configuración o aparece como una instalación nueva:** revisa
  [Migración o instalación limpia](#4-migración-o-instalación-limpia). Si el volumen se borró, HCC no puede reconstruir
  automáticamente los datos que había dentro.
- **La instalación funciona pero no reproduce:** empieza por [Diagnóstico](#10-diagnóstico-saber-qué-falla) y después
  consulta [Problemas frecuentes](#14-problemas-frecuentes).
- **Consultar opciones avanzadas:** ve a la [Referencia avanzada](#15-referencia-avanzada) cuando necesites fijar una
  versión, hacer rollback o entender el almacenamiento.

Si no sabes qué opción elegir, usa Docker Compose. Guarda su carpeta y no borres nunca el volumen
`home-cinema-control-config`: ahí viven la configuración, las credenciales y las rutas de HCC.

## Índice

1. [Antes de empezar](#1-antes-de-empezar)
2. [Instalar HCC](#2-instalar-hcc)
3. [Instalación con Docker Compose](#3-instalación-con-docker-compose)
4. [Migración o instalación limpia](#4-migración-o-instalación-limpia)
5. [Conectar Emby o Jellyfin](#5-media-server-conecta-emby-o-jellyfin)
6. [Conectar el OPPO/Chinoppo](#6-media-player-localiza-el-oppochinoppo)
7. [Configurar las rutas de medios](#7-rutas-de-medios-la-parte-importante)
8. [Configurar la sala](#8-sala-tv-y-receptor-av-son-opcionales)
9. [Conectar Home Assistant](#9-conecta-hcc-con-home-assistant)
10. [Comprobar el estado](#10-diagnóstico-saber-qué-falla)
11. [Leer los logs](#11-logs-entendibles)
12. [Validar la primera reproducción](#12-primera-reproducción-de-validación)
13. [Actualizar HCC](#13-actualizar-hcc)
14. [Problemas frecuentes](#14-problemas-frecuentes)
15. [Referencia avanzada](#15-referencia-avanzada)

> **Importante:** la configuración de HCC está en el volumen Docker
> `home-cinema-control-config`. No lo borres al actualizar ni al eliminar el contenedor. Borrar el contenedor es
> seguro; borrar el volumen elimina la configuración y los secretos.

## 1. Antes de empezar

Necesitas:

| Requisito                | Notas                                                                |
|--------------------------|----------------------------------------------------------------------|
| Docker                   | Linux recomendado. HCC usa red host.                                 |
| Emby o Jellyfin          | Uno de los dos, accesible desde el host donde corre HCC.             |
| OPPO/Chinoppo            | Debe exponer la API MediaControl de OPPO en la red local.            |
| NAS o carpeta compartida | Debe ser visible desde tu servidor de medios y desde el reproductor. |
| NFS o SMB/CIFS           | Se elige por cada mapeo de ruta en HCC.                              |
| TV y receptor AV         | Opcionales. HCC puede funcionar sin ellos.                           |

Recomendaciones antes de instalar:

- Reserva IP fija para tu servidor de medios, NAS, OPPO/Chinoppo, TV y receptor AV.
- Crea primero las bibliotecas en Emby o Jellyfin. HCC no inventa bibliotecas: lee las que ya existen en tu servidor.
  Para Emby, ver [Library Setup](https://emby.media/support/articles/Library-Setup.html) y
  [Quick Start](https://emby.media/support/articles/Quick-Start.html). Para Jellyfin, ver
  [Adding Media Libraries](https://jellyfin.org/docs/general/server/libraries/).
- Comparte las carpetas del NAS por NFS o SMB/CIFS y comprueba que el reproductor puede verlas desde su propio
  explorador de red.
- Decide qué bibliotecas debe interceptar HCC.
- Si usas receptor AV, revisa HDMI CEC/ARC. En algunos Denon/Marantz y configuraciones similares, CEC/ARC puede volver a
  seleccionar la entrada de TV después de que HCC haya cambiado a la entrada del reproductor. Si ves ese comportamiento,
  desactiva CEC/ARC en el AVR o ajusta la configuración HDMI del receptor.

## 2. Instalar HCC

Para la mayoría de las personas, la opción más sencilla es [Docker Compose](#3-instalación-con-docker-compose): deja
todos los datos en un volumen con nombre y facilita las actualizaciones. Si utilizas Portainer, sigue la misma opción
desde **Stacks**.

La opción `docker run` de abajo es para quien ya está acostumbrado a usar comandos Docker. No mezcles los dos métodos:
elige uno y conserva sus instrucciones para actualizarlo después.

## 2.1 Arranque rápido con Docker

Puedes arrancar HCC directamente con `docker run`:

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

## 3. Instalación con Docker Compose

Esta es la opción recomendada. Docker Compose necesita encontrar el archivo `compose.yaml`, así que guarda el archivo en
una carpeta propia y ejecuta siempre los comandos desde esa misma carpeta.

1. Crea una carpeta para HCC, por ejemplo `home-cinema-control`.
2. Crea dentro un archivo llamado exactamente `compose.yaml` y pega este contenido:

```yaml
services:
  home-cinema-control:
    image: ghcr.io/tousled/home-cinema-control:${HCC_VERSION:-latest}
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
      HCC_TELEMETRY_ENDPOINT_URL: ${HCC_TELEMETRY_ENDPOINT_URL:-}
      HCC_TELEMETRY_INGEST_KEY: ${HCC_TELEMETRY_INGEST_KEY:-}
    volumes:
      - home-cinema-control-config:/config

volumes:
  home-cinema-control-config:
    name: home-cinema-control-config
```

No tienes que crear `HCC_VERSION`: Compose utiliza `latest` si no has definido esa variable en el entorno ni en un archivo `.env`.
Las variables de telemetría también pueden quedarse vacías.

3. Abre un terminal en esa carpeta. Comprueba que estás en el lugar correcto: debes ver `compose.yaml` al listar los
   archivos.

Si la carpeta está en otra ubicación, entra en ella antes de ejecutar los comandos. Por ejemplo:

```bash
cd /ruta/a/home-cinema-control
ls compose.yaml
```

El segundo comando debe mostrar `compose.yaml`. Si dice que el archivo no existe, no continúes: estás en otra carpeta.

4. Arranca HCC:

```bash
docker compose pull
docker compose up -d
```

Abre `http://<tu-host>:8090`.

Para actualizar más adelante, vuelve a esta carpeta y sigue [Actualizar HCC](#13-actualizar-hcc). No ejecutes
`docker compose` desde otra carpeta: Docker podría no encontrar este servicio.

`network_mode: host` es necesario: HCC habla directamente con Emby/Jellyfin, el OPPO/Chinoppo, TV, AVR y herramientas
de descubrimiento como `arp-scan`.

### 3.1 Instalar con Portainer u otra interfaz web

En Portainer: **Stacks → Add stack**, ponle un nombre como `home-cinema-control` y pega el `compose.yaml` de arriba en
el editor. No añadas variables de entorno: el archivo ya usa `latest`, que es la última versión estable. Al actualizar,
abre este mismo stack y pulsa **Update the stack**; si aparece la opción **Re-pull image**, actívala.

Para fijar una versión concreta (incluidas las release candidates), añade `HCC_VERSION` como variable de entorno del
stack, por ejemplo `HCC_VERSION=1.4.2-rc.1`. El ejemplo de Compose utiliza `${HCC_VERSION:-latest}` para seleccionar la etiqueta de la imagen. Esta variable se sustituye al desplegar el stack; si usas un Compose diferente que tiene `:latest` fijo, `HCC_VERSION` no surtirá efecto. Sin definirla, Portainer usa
`latest` (la última estable). Para actualizar, cambia ese valor y vuelve a desplegar tirando de la imagen ("re-pull"),
no reconstruyendo desde el Dockerfile.

Otras interfaces (Synology Container Manager, Unraid...) deberían funcionar igual si permiten definir variables de
entorno para el stack — la lógica es la misma.

En Synology Container Manager, Unraid u otra interfaz web, busca la opción equivalente a **Stack** o **Compose** y
mantén este mismo archivo. No crees un contenedor nuevo cada vez: debe seguir usando el volumen
`home-cinema-control-config`.

## 4. Migración o instalación limpia

Si HCC aparece vacío después de una actualización y no querías empezar de cero, **no completes todavía la
configuración**.
Vuelve al stack o a la carpeta original y comprueba que sigues usando el volumen
`home-cinema-control-config`. Si ese volumen todavía existe, la configuración debería reaparecer al arrancar el
contenedor correcto. Si el volumen se borró, solo podrás recuperar la configuración desde una copia de seguridad de
Docker o del host.

Si HCC encuentra una configuración anterior compatible, mostrará una pantalla de migración. Puedes importar la
configuración o empezar desde cero.

<p align="center">
  <img src="assets/screenshots/install/01-migration.png" alt="Pantalla de migración de configuración anterior" width="860"/>
</p>

La migración existe para conservar lo reutilizable, pero HCC guarda ahora la configuración por secciones y separa los
secretos en `/config/secrets.json`.

Si en cambio es una instalación completamente nueva (sin configuración previa de HCC) y vienes del proyecto
predecesor XNOPPO/Chinoppo, HCC te ofrecerá un segundo aviso distinto: importar tu antiguo `config.json` de XNOPPO en
lugar de configurarlo todo desde cero. Selecciona el fichero, HCC migra OPPO/TV/AV/rutas igual que en la migración
normal, mueve la URL de tu Emby al nuevo formato y, si el servidor está accesible en ese momento, inicia sesión con
el usuario/contraseña del fichero antiguo para obtener un token — si no puede, el proveedor queda añadido pero sin
autenticar, y el indicador de Media Server en el menú lateral te avisará en naranja para que termines de conectarlo
desde su pantalla. Si no tienes un `config.json` de XNOPPO o prefieres no importarlo, elige "Configurar desde cero" y
sigue el asistente normal.

<!-- TODO: captura de pantalla del modal de importación XNOPPO en instalación nueva -->

## 5. Media Server: conecta Emby o Jellyfin

En **Media Server** eliges el tipo de servidor (Emby o Jellyfin) y configuras su URL, el usuario y el dispositivo que
HCC debe monitorizar. Las capturas de esta guía muestran Emby, pero el flujo es el mismo con Jellyfin.

<p align="center">
  <img src="assets/screenshots/install/02-media-server.png" alt="Pantalla Media Server de Home Cinema Control" width="860"/>
</p>

En la cabecera de esta pantalla verás el logo del proveedor seleccionado, por ejemplo Emby o Jellyfin. Ese logo sirve
para reconocer de un vistazo qué integración estás configurando: aparece atenuado mientras falta autorizar el servidor
o completar la conexión, y se muestra con más presencia cuando el proveedor queda autorizado. La URL, el usuario y los
detalles de preparación siguen estando en los paneles de configuración para no duplicar información en la cabecera.

<p align="center">
  <img src="assets/screenshots/install/02-media-server-pending.png" alt="Media Server con Jellyfin seleccionado pero pendiente de autorización" width="860"/>
</p>

Qué resuelve esta pantalla:

- evita editar tokens a mano;
- guarda credenciales sensibles en `secrets.json`;
- permite recargar dispositivos del servidor multimedia;
- detecta bibliotecas para usarlas después en el asistente de rutas;
- mantiene el guardado limitado a la sección de Media Server.

El dispositivo monitorizado es importante: HCC solo intercepta sesiones que lleguen desde ese cliente/dispositivo.

### 5.1 Configuración recomendada de Emby para ISO Blu-ray y DVD

Esta configuración es **opcional** y HCC funciona sin ella. Si tienes Blu-ray o DVD en formato ISO, te recomendamos
instalar **IsoMounter** desde el catálogo de plugins de Emby, reiniciar Emby y actualizar la biblioteca o los elementos
ISO existentes.

El plugin permite que Emby analice el contenido del disco y devuelva sus pistas de audio y subtítulos. Así, la pantalla
de Emby puede mostrar un selector con las diferentes pistas disponibles antes o durante la reproducción. HCC también
consulta esa información cuando está disponible y conserva un fallback compatible si el plugin no está instalado.

El idioma solo aparecerá si Emby lo devuelve en los metadatos de la pista. Si Emby no identifica el idioma, se mostrará
la información técnica disponible —por ejemplo, `DTS-HD MA 5.1` para audio o `PGSSUB` para subtítulos—, pero no se
podrá mostrar de forma fiable el idioma como: `ES`, `CAT`, `GA` o `JA`. La reproducción y el cambio de pistas seguirán
funcionando.

Si usas Jellyfin, la cuenta con la que autorizas HCC debe tener permisos de **administrador** para que la recarga de
dispositivos
y bibliotecas funcione — ver [Problemas frecuentes](#14-problemas-frecuentes).

## 6. Media Player: localiza el OPPO/Chinoppo

En **Media Player** se configura la IP del reproductor y se prueba la API MediaControl.

<p align="center">
  <img src="assets/screenshots/install/03-media-player.png" alt="Pantalla Media Player de Home Cinema Control" width="860"/>
</p>

Cuando `arp-scan` está disponible dentro del contenedor, aparece el botón **Escanear red**. Al pulsarlo, HCC muestra
dispositivos detectados como sugerencias bajo el campo de IP para no tener que escribir direcciones a ciegas.

<p align="center">
  <img src="assets/screenshots/install/03-media-player-ip-discovery.png" alt="Descubrimiento de IP del OPPO filtrando por nombre" width="860"/>
</p>

El buscador filtra por IP, nombre o fabricante cuando esa información está disponible. Para buscar por nombres como
`oppo`, `lg` o `denon`, conviene configurar nombres de dispositivo, reservas DHCP o DNS local en el router. Si tu red no
devuelve nombres, puedes buscar o escribir la IP directamente.

Usa **Probar OPPO** antes de continuar. Si falla, revisa:

- IP del reproductor;
- que esté encendido o accesible en red;
- firewall;
- red host de Docker;
- que el reproductor exponga la API compatible con OPPO MediaControl.

## 7. Rutas de medios: la parte importante

Esta es la parte más importante de la configuración porque aquí se resuelve el problema real: Emby o Jellyfin saben
dónde está la película en el servidor, pero el OPPO/Chinoppo necesita llegar a la misma película como recurso de red
del NAS.

Piensa en HCC como un traductor de rutas:

```text
Emby ve:          /volume1/Video/Peliculas/Dune (2021).mkv
OPPO ve por NFS:  volume1/Video/Peliculas/Dune (2021).mkv
OPPO ve por SMB:  Video/Peliculas/Dune (2021).mkv
HCC guarda:       esta biblioteca usa esta ruta OPPO y este protocolo
```

Si Emby tiene configurado **Shared network folder**, puede informar durante la reproducción una ruta de red alternativa
en lugar de la ruta de biblioteca. HCC la traduce automáticamente a la ruta canónica de Emby antes de aplicar el
mapeo hacia el OPPO. No hace falta crear un segundo mapeo para esa ruta alternativa. Jellyfin no expone actualmente
ese campo equivalente en su API; sus `Locations` siguen siendo la ruta canónica que debes mapear.

No conviene adivinar estas rutas. NAS, NFS y SMB no siempre exponen los mismos nombres. Por eso HCC parte de las
bibliotecas del proveedor activo, te pide la ruta equivalente vista por el reproductor y la prueba antes de una sesión
real. La pantalla muestra una insignia de Emby/Jellyfin para que tengas claro qué servidor estás mapeando.

<p align="center">
  <img src="assets/screenshots/install/04-media-paths-overview.png" alt="Vista general del asistente de rutas de Home Cinema Control" width="860"/>
</p>

### 7.1 Crea primero las bibliotecas en Emby

Antes de entrar en HCC, Emby debe tener sus bibliotecas creadas y escaneadas: Películas, Series, Conciertos o las que
vayas a usar. En Emby, una biblioteca agrupa una o varias carpetas físicas. HCC detecta esas bibliotecas y sus rutas,
pero no crea la biblioteca por ti.

Ruta típica en Emby:

```text
Dashboard de Emby -> Library -> Add Media Library
```

La documentación oficial de Emby cubre este paso en
[Library Setup](https://emby.media/support/articles/Library-Setup.html). Su guía rápida también recuerda que conviene
separar el contenido en carpetas por tipo, como Movies, TV Shows o Music:
[Quick Start](https://emby.media/support/articles/Quick-Start.html).

Cuando termines, entra en HCC y usa **Recargar bibliotecas** en Media Paths. Si no aparece una biblioteca, primero
corrige Emby; no empieces a escribir rutas manuales a ciegas.

### 7.2 Elige qué bibliotecas debe interceptar HCC

No todo lo que existe en Emby tiene que pasar por el OPPO. Puedes dejar fuera música, documentales, pruebas o cualquier
biblioteca que quieras reproducir normalmente desde el cliente Emby.

La pantalla muestra las bibliotecas detectadas y permite activar solo las que quieras que HCC controle. Las demás
seguirán reproduciéndose por el flujo normal de Emby.

<p align="center">
  <img src="assets/screenshots/install/05-media-paths-library-filter.png" alt="Selección de bibliotecas interceptadas en Home Cinema Control" width="860"/>
</p>

### 7.3 Prepara NFS o SMB/CIFS en el NAS

HCC no configura permisos del NAS. Necesitas que el OPPO/Chinoppo pueda navegar el recurso desde su propio menú de red.

Para NFS:

- activa NFS en el NAS;
- exporta la carpeta de medios;
- permite acceso desde la IP del reproductor;
- revisa permisos de lectura;
- comprueba desde el OPPO que el recurso aparece y que puedes entrar hasta la carpeta de la biblioteca.

Para SMB/CIFS:

- activa SMB en el NAS;
- comparte la carpeta de medios;
- crea o elige un usuario con permiso de lectura;
- guarda usuario y contraseña en HCC si el recurso no es invitado;
- comprueba desde el OPPO que puedes navegar hasta la carpeta.

Cuando uses SMB/CIFS, HCC muestra las credenciales en la misma pantalla de rutas para que no tengas que saltar entre
pantallas ni editar ficheros.

<p align="center">
  <img src="assets/screenshots/install/07-media-paths-smb-credentials.png" alt="Credenciales SMB en el asistente de rutas de Home Cinema Control" width="860"/>
</p>

Si necesitas capturas concretas de Synology, QNAP, Windows, Unraid o M9702/M920x, usa el hilo de AVPasion enlazado al
principio de esta guía. HCC documenta su parte; la configuración exacta del NAS depende de tu plataforma.

### 7.4 Encuentra la ruta como la ve el OPPO

Este paso evita la mayoría de errores. No copies solo la ruta de Emby. Entra en el explorador de red del OPPO/Chinoppo y
observa cómo aparece la carpeta.

Ejemplos habituales:

| Emby puede ver             | OPPO puede ver                 |
|----------------------------|--------------------------------|
| `/volume1/Video/Peliculas` | NFS: `volume1/Video/Peliculas` |
| `/volume1/Video/Peliculas` | SMB: `Video/Peliculas`         |
| `/mnt/media/Movies`        | SMB: `NAS/Movies`              |
| `D:\Movies` en Windows     | SMB: `Servidor/Movies`         |

Si dudas entre NFS y SMB, empieza por el protocolo que ya funcione manualmente desde el reproductor. Después podrás
crear otro mapeo con otro protocolo si una biblioteca concreta lo necesita.

### 7.5 Crea y prueba el mapeo en HCC

En **Media Paths**, trabaja biblioteca por biblioteca:

1. Pulsa **Recargar bibliotecas** para traer las bibliotecas actuales de Emby.
2. Selecciona la biblioteca que quieres interceptar.
3. Revisa la **ruta del servidor** que HCC ha leído desde Emby.
4. Elige `nfs` o `cifs` para esa biblioteca.
5. Escribe o selecciona la **ruta OPPO** tal como la ve el reproductor.
6. Si usas SMB con usuario, rellena credenciales en la sección SMB.
7. Pulsa **Probar ruta**.
8. Guarda cuando la ruta quede verificada.

HCC une las rutas como rutas, no como texto literal: la **Ruta OPPO** puede terminar en `/` o no, y las rutas de
Emby con formato Windows como `Z:\` se normalizan automáticamente. Por ejemplo, `//192.168.1.149/Z` más
`HD-Olimpo/Película` produce `//192.168.1.149/Z/HD-Olimpo/Película`.

<p align="center">
  <img src="assets/screenshots/install/06-media-paths-nfs-mapping.png" alt="Mapeo NFS verificado entre Emby y OPPO" width="860"/>
</p>

Qué significa cada estado:

| Estado     | Qué debes hacer                                                                  |
|------------|----------------------------------------------------------------------------------|
| Verificada | Esa ruta ha montado correctamente desde el reproductor.                          |
| Pendiente  | Has cambiado algo y falta probar de nuevo.                                       |
| Revisable  | El mapeo existía, pero cambió alguna pieza relacionada. Repite la prueba.        |
| Error      | HCC no pudo montar la ruta. Mira la sugerencia y los logs filtrados por errores. |

<p align="center">
  <img src="assets/screenshots/install/08-media-paths-states.png" alt="Leyenda de estados de rutas verificadas, pendientes y con error" width="860"/>
</p>

### 7.6 Cuándo usar modo manual

El modo manual existe para casos reales, no para volver al método antiguo:

- Emby no devuelve la carpeta esperada;
- una biblioteca mezcla varias carpetas físicas;
- el NAS expone nombres distintos por NFS y SMB;
- quieres crear una ruta de pruebas antes de tocar la principal;
- vienes de una configuración anterior y quieres revisar cada mapeo.

La mejora importante es que el modo manual ya no es “escribe algo y cruza los dedos”: puedes probar el montaje, ver el
diagnóstico y guardar solo cuando entiendes qué ruta funciona.

<p align="center">
  <img src="assets/screenshots/install/09-media-paths-manual.png" alt="Modo manual de rutas de Home Cinema Control" width="860"/>
</p>

### 7.7 Conceptos clave del mapeo

| Campo             | Qué significa                                                        |
|-------------------|----------------------------------------------------------------------|
| Ruta del servidor | Ruta física que Emby reporta para la biblioteca.                     |
| Ruta OPPO         | Ruta NFS o SMB/CIFS que el reproductor ve desde su navegador de red. |
| Protocolo         | `nfs` o `cifs`, elegido por cada ruta.                               |
| Verificada        | HCC ha probado que el reproductor puede montar esa ruta.             |

HCC no cambia silenciosamente de SMB a NFS ni de NFS a SMB. Si una ruta está configurada como SMB, se prueba y reproduce
como SMB. Esto evita errores invisibles cuando una biblioteca funciona con un protocolo y otra necesita otro.

HCC comprueba las rutas por carpetas completas: `/media/Movies` coincide con `/media/Movies/Alien.mkv`, pero no con
`/media/Movies-Old/Alien.mkv`. Si tienes rutas anidadas, como `/media/Movies` y `/media/Movies/4K`, utiliza la más
específica. Esa ruta concreta debe estar verificada; HCC no prueba otra más amplia ni envía una ruta no verificada al
OPPO. Si la reproducción se bloquea, la pantalla de estado indica qué ruta falta o necesita probarse y guardarse.

Si un elemento tiene varias versiones, HCC usa la versión que el usuario ha seleccionado en Emby o Jellyfin. El servidor
identifica esa versión con `MediaSourceId`; HCC busca la ruta correspondiente en `MediaSources` y aplica el mapeo a esa
ruta, en lugar de asumir siempre la ruta de la versión principal. Si el servidor no devuelve una coincidencia exacta,
HCC conserva la ruta principal como fallback compatible.

### 7.8 Por qué es importante este paso

Emby o Jellyfin y el OPPO pueden referirse al mismo contenido con rutas distintas. La ruta que conoce el servidor
multimedia no siempre es la que el reproductor puede abrir desde su red.

Una ruta verificada le dice a HCC exactamente:

- qué carpeta debe montar el OPPO;
- con qué protocolo debe acceder a ella;
- qué bibliotecas deben pasar por el reproductor;
- qué configuración ha funcionado antes de iniciar una reproducción real.

Por eso conviene probar y verificar cada mapeo. Si una ruta falla, el problema queda acotado al NAS, al protocolo o a
los permisos, en lugar de aparecer más tarde como un fallo ambiguo al intentar reproducir.

## 8. Sala: TV y receptor AV son opcionales

La pantalla **Sala** controla qué debe hacer HCC al iniciar y terminar una reproducción: cambiar entrada de TV, encender
o cambiar entrada del AVR, restaurar audio de TV, etc.

<p align="center">
  <img src="assets/screenshots/install/05-room.png" alt="Configuración de sala con TV y receptor AV" width="860"/>
</p>

El mismo escaneo de red sirve para localizar TV y receptor AV cuando los configuras desde **Sala**.

<p align="center">
  <img src="assets/screenshots/install/05-room-ip-discovery.png" alt="Descubrimiento de IP en la pantalla Sala de Home Cinema Control" width="860"/>
</p>

Puntos importantes:

- TV y AV se configuran por separado.
- Si TV está desactivada, no entra en el flujo de reproducción.
- Si AV está desactivado, no entra en el flujo de reproducción.
- En LG WebOS, HCC puede detectar entradas HDMI y restaurar la app del servidor multimedia. El primer uso muestra el
  diálogo normal de emparejamiento en la TV; tras actualizar HCC o la TV puede que tengas que aceptarlo de nuevo.
- En Sony BRAVIA (2013 o posterior), HCC hace lo mismo vía la API REST oficial de Sony, autenticada con una
  clave PSK — ver más abajo cómo activarla.
- En AVR compatibles, HCC puede encender, apagar, cambiar entrada y aplicar esperas para mitigar problemas HDMI.
- En Trinnov Altitude, HCC usa números de fuente/perfil en lugar de nombres de entrada HDMI. El protocolo requiere que
  HCC y el procesador estén en la misma subred. Introduce la IP y usa **Detectar MAC** para que HCC intente rellenar
  la MAC desde el escaneo de red; las acciones de encendido/apagado quedan bloqueadas hasta tener esa MAC.
- Para configurar Trinnov: selecciona **TRINNOV**, introduce la IP, detecta o escribe la MAC, pulsa **Detectar entradas
  HDMI** y elige el source/profile donde está conectado el OPPO.
- La detección de entradas HDMI, "Cambiar a OPPO", "Detectar apps" y "Abrir Emby/Jellyfin" quedan bloqueados hasta
  que "Probar conexión" confirma que la TV responde — no tiene sentido detectar nada contra una TV inalcanzable.
  "Abrir Emby/Jellyfin" además requiere haber detectado esa app en la TV; si no aparece entre las detectadas, HCC te
  lo indica para que la elijas manualmente si aparece con otro nombre.
- Cambiar el modelo de TV limpia los campos del formulario (IP, MAC, entradas detectadas…), salvo que vuelvas al
  modelo que ya tienes guardado, en cuyo caso se restaura su configuración.

### Sony BRAVIA: activar el Pre-Shared Key (PSK)

Antes de configurar la TV Sony en HCC, hay que activar el control por IP directamente en el televisor — a diferencia
de LG, aquí no hay un diálogo de emparejamiento en pantalla, se configura una vez desde los ajustes:

1. En el mando, ve a **Ajustes → Red y Internet → Configuración de red doméstica → Control IP**.
2. Activa **Autenticación** y elige **Pre-Shared Key**.
3. Escribe una clave (cualquier cadena de texto) y guárdala — es la misma clave que introducirás en HCC.

> La ruta exacta del menú varía algo según el año del modelo; el camino general **Red → Configuración de red
> doméstica → Control IP → Pre-Shared Key** se mantiene desde los modelos de 2014 en adelante.

En la pantalla **Sala** de HCC, introduce la IP de la TV y la misma clave PSK, y pulsa "Probar conexión". Después,
usa "Detectar apps" para que HCC liste las apps instaladas en esa TV y puedas elegir la de tu servidor multimedia.
Este paso hace falta una sola vez por TV.

*(Capturas de pantalla de los ajustes de Sony pendientes de añadir — requieren una TV Sony real.)*

Nota sobre CEC/ARC:

Si el receptor AV cambia a la entrada correcta pero vuelve solo a TV Audio, ARC o CEC probablemente está interviniendo.
En ese caso, desactiva CEC/ARC en el receptor o revisa la configuración HDMI. HCC puede reintentar cambios de entrada,
pero si el AVR o la TV fuerzan otra fuente por CEC, la automatización será inestable.

## 9. Conecta HCC con Home Assistant

Con esta integración, HCC avisa a Home Assistant cuando detecta una reproducción, empieza, se pausa, continúa o termina.
Después,
Home Assistant decide qué hacer: encender luces, activar una escena, enviar un aviso o simplemente guardar el evento en
el
registro. HCC no crea automatizaciones por su cuenta; tú eliges la reacción en Home Assistant.

<p align="center">
  <img src="assets/screenshots/install/10-home-assistant.png" alt="Pantalla de configuración de Home Assistant en HCC" width="860"/>
</p>

### 9.1 Crea la automatización en Home Assistant

En Home Assistant crea una automatización con un disparador **Webhook**. Puedes copiar este ejemplo completo. De momento
solo escribe cada cambio en el registro de Home Assistant, para que puedas comprobar que la conexión funciona antes de
añadir luces, escenas o notificaciones.

```yaml
alias: HCC - eventos de reproducción
triggers:
  - trigger: webhook
    webhook_id: reemplaza-esto-por-un-id-largo-y-aleatorio
    allowed_methods:
      - POST
    local_only: true
conditions:
  - condition: template
    value_template: >-
      {{ trigger.json.event | default('') in ['detected', 'started', 'paused', 'resumed', 'stopped'] }}
actions:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ trigger.json.event == 'detected' }}"
        sequence:
          - action: logbook.log
            data:
              name: HCC
              message: "Reproducción detectada: {{ trigger.json.title | default('') }}"
      - conditions:
          - condition: template
            value_template: "{{ trigger.json.event == 'started' }}"
        sequence:
          - action: logbook.log
            data:
              name: HCC
              message: "Reproducción iniciada: {{ trigger.json.title | default('') }}"
      - conditions:
          - condition: template
            value_template: "{{ trigger.json.event == 'paused' }}"
        sequence:
          - action: logbook.log
            data:
              name: HCC
              message: "Reproducción pausada: {{ trigger.json.title | default('') }}"
      - conditions:
          - condition: template
            value_template: "{{ trigger.json.event == 'resumed' }}"
        sequence:
          - action: logbook.log
            data:
              name: HCC
              message: "Reproducción reanudada: {{ trigger.json.title | default('') }}"
      - conditions:
          - condition: template
            value_template: "{{ trigger.json.event == 'stopped' }}"
        sequence:
          - action: logbook.log
            data:
              name: HCC
              message: "Reproducción detenida: {{ trigger.json.title | default('') }}"
mode: queued
```

El texto `reemplaza-esto-por-un-id-largo-y-aleatorio` es un ejemplo. Sustitúyelo por un identificador nuevo y guárdalo:
será el código que permitirá a HCC enviar eventos a esta automatización. Trátalo como una contraseña: no lo publiques ni
lo compartas.

Deja `local_only: true` si HCC y Home Assistant están en tu red local. Así Home Assistant no acepta este webhook desde
Internet. El método `POST` es el que utiliza HCC para enviar los datos.

Para aprender más sobre automatizaciones, consulta la
[documentación oficial de Home Assistant](https://www.home-assistant.io/docs/automation/). Para las opciones del
disparador,
consulta la [documentación oficial del Webhook](https://www.home-assistant.io/docs/automation/trigger/#webhook-trigger).

### 9.2 Configura HCC

En la pantalla **Home Assistant** de HCC:

1. Activa **Enviar eventos de HCC a Home Assistant**.
2. Escribe la dirección de Home Assistant, por ejemplo `http://homeassistant.local:8123`. Escribe solo la dirección
   base;
   no añadas `/api/webhook`.
3. Escribe el mismo código en **ID del webhook** que has puesto en la automatización.
4. Pulsa **Guardar**.
5. Pulsa **Reiniciar HCC** en el enlace que aparece debajo del botón para aplicar la configuración.

El ajuste de timeout de **Ajustes avanzados** normalmente no tienes que cambiarlo. Solo úsalo si Home Assistant tarda
más
de lo normal en responder.

### 9.3 Comprueba que funciona

HCC envía estos cinco eventos:

- `detected`: HCC ha detectado una reproducción válida en el dispositivo monitorizado y ha aceptado el handoff.
- `started`: la reproducción ha comenzado.
- `paused`: la reproducción está pausada.
- `resumed`: la reproducción continúa.
- `stopped`: la reproducción ha terminado o se ha detenido.

El contenido de un evento se parece a esto:

```json
{
  "event": "started",
  "event_id": "57438c115b84467dafcf843368d9bef6",
  "session_id": "33feec42b11b48799f749bf6534e371c",
  "media_type": "movie",
  "title": "Interstellar",
  "source": "emby",
  "player": "oppo"
}
```

`event` indica qué ha ocurrido. `event_id` identifica ese envío y `session_id` agrupa los eventos de la misma
reproducción.
El título, el servidor y el reproductor aparecen cuando HCC dispone de esos datos.

Para probarlo, inicia una reproducción desde el dispositivo que HCC monitoriza y revisa el **Registro** de Home
Assistant.
La pantalla de HCC también muestra la última entrega real. Antes de enviar el primer evento aparecerá como pendiente; no
se envía una petición de prueba automática.

Si Home Assistant no responde, HCC registra el error y la reproducción continúa. Si cambias la dirección o el ID del
webhook, el estado vuelve a pendiente hasta que HCC consiga enviar un evento con la nueva configuración.

Si HCC no puede cargar esta pantalla, muestra un error con la opción **Reintentar** en lugar de rellenar el formulario
con
valores que podrían no ser los tuyos.

## 10. Diagnóstico: saber qué falla

La pantalla **Diagnóstico** resume estado, recursos, último fallo, versión y acciones de soporte.

<p align="center">
  <img src="assets/screenshots/install/06-status.png" alt="Pantalla de diagnóstico de Home Cinema Control" width="860"/>
</p>

Úsala para:

- comprobar si HCC está conectado;
- copiar un resumen de soporte;
- enviar un diagnóstico: genera un informe redactado automáticamente (sin IPs, credenciales ni rutas), te deja
  revisarlo y editarlo, y luego lo copia al portapapeles y abre un nuevo issue en GitHub para que lo pegues y lo
  envíes tú mismo — nada se envía en segundo plano ni sin que lo veas antes;
- ver el último fallo;
- comprobar actualizaciones;
- activar o desactivar telemetría anónima y enviar interés de roadmap;
- reiniciar el servicio si tu despliegue lo permite.

El bloque de versión muestra la versión instalada con el mismo formato que las etiquetas Docker (`1.1.1-rc.1`, por
ejemplo). Si configuras un webhook de actualización, HCC guarda la versión actual antes de pedir el redeploy y muestra
la información disponible para volver atrás si fuese necesario.

El objetivo es que un fallo no sea simplemente “no reproduce”, sino una pista concreta: servidor no accesible, ruta sin
verificar, montaje OPPO fallido, TV/AV desactivado, error de recuperación, etc.

La telemetría es opcional y viene desactivada. Si la activas, HCC envía datos anónimos mínimos para entender adopción y
priorizar desarrollo: instalación activa, versión, idioma, proveedor Emby/Jellyfin, uso de OPPO, TV/AV, NFS/SMB y
eventos de intento, reproducción iniciada, finalizada, rechazada antes del handoff y fallida. Los eventos llevan
identificadores aleatorios y anónimos de evento/intento, además del proveedor, componente y código diagnóstico
normalizados, para poder analizar fallos repetidos por instalación. Si el backend de telemetría no está disponible, HCC
guarda temporalmente esos eventos
anónimos en `/config/telemetry_queue.json` y los reintenta después. No envía rutas, IPs, tokens, URLs, nombres de
servidor, bibliotecas, títulos, IDs del servidor multimedia, logs, scripts ni comandos personalizados. Más detalle:
la [documentación pública de telemetría](https://github.com/tousled/home-cinema-control/blob/main/docs/telemetry.md).

## 11. Logs entendibles

La pantalla **Logs** muestra líneas estructuradas con severidad y permite filtrar.

<p align="center">
  <img src="assets/screenshots/install/07-logs.png" alt="Logs estructurados y filtrables de Home Cinema Control" width="860"/>
</p>

La consola muestra por defecto las últimas 100 líneas visibles. Puedes cambiar el rango a más líneas o al log completo,
filtrar por severidad y copiar al portapapeles exactamente las líneas mostradas, algo útil cuando compartes información
desde el móvil. La descarga sigue generando el log completo.

Esto sustituye el patrón de revisar logs crudos sin contexto. Los errores y avisos quedan marcados visualmente para que
sea más fácil compartir información útil en soporte.

## 12. Primera reproducción de validación

Cuando las pantallas anteriores estén guardadas y verificadas, haz una primera prueba con una película de una biblioteca
interceptada. No pruebes solo que el OPPO empieza a reproducir; prueba el ciclo completo.

Checklist recomendado:

| Prueba                                  | Qué confirma                                                         |
|-----------------------------------------|----------------------------------------------------------------------|
| Play desde el cliente Emby monitorizado | HCC intercepta solo el dispositivo correcto.                         |
| Montaje NFS/SMB elegido                 | La biblioteca usa el protocolo configurado, sin fallback silencioso. |
| Pausa y reanudación                     | Emby y OPPO no se quedan con estados distintos.                      |
| Seek desde Emby                         | El reproductor responde a comandos interactivos básicos.             |
| Cambio de audio/subtítulos              | La selección de pistas no queda acoplada a índices incorrectos.      |
| Stop y final natural                    | Emby conserva visto/reanudar y HCC limpia la sesión.                 |
| Vuelta a la app o entrada esperada      | TV/AV terminan en el estado previsto si los configuraste.            |
| Diagnóstico tras fallo provocado        | El último fallo explica componente, razón y siguiente acción.        |

La validación real de hardware sigue siendo importante: OPPO original, clones Chinoppo, firmware, NAS, TV y AVR pueden
comportarse de forma distinta. Si algo falla, copia el resumen de soporte desde **Diagnóstico** y revisa los logs
filtrando por avisos o errores.

## 13. Actualizar HCC

**Qué conseguirás:** actualizar la imagen de HCC y conservar la configuración, las credenciales y las rutas.

La imagen y la configuración son cosas distintas. La actualización sustituye la imagen y vuelve a crear el contenedor;
el volumen o montaje que apunta a `/config` debe permanecer exactamente igual.

> **No borres el volumen.** No ejecutes `docker compose down -v`, `docker volume rm` ni elimines el volumen desde
> Portainer o Docker Desktop durante una actualización. Borrar el contenedor puede ser parte de algunos métodos, pero
> borrar el volumen elimina la configuración.

Antes de empezar:

1. Abre HCC y anota la versión que aparece en **Diagnóstico**.
2. Decide qué método usas: **Docker Compose**, **Portainer** o un gestor de contenedores del NAS.
3. Comprueba que existe una copia del volumen o del directorio que contiene `/config`. HCC no tiene un botón para
   exportar y restaurar la configuración; usa las copias de seguridad o snapshots de tu NAS/host.
4. Si no puedes identificar el volumen o la carpeta de configuración, detente aquí. No crees un contenedor nuevo.

### 13.1 Actualizar con Docker Compose

Usa este procedimiento si HCC se inició desde un archivo `compose.yaml`.

1. **Localiza la instalación existente.** Si el contenedor está funcionando, ejecuta:

   ```bash
   docker inspect home-cinema-control --format '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}'
   ```

   El resultado debe ser la carpeta donde está el Compose de HCC. Si no aparece ninguna carpeta, busca `compose.yaml`
   en el gestor de archivos del host o del NAS. No crees otro archivo para probar.

2. **Entra en esa carpeta y comprueba el archivo.** Sustituye la ruta por la que has encontrado:

   ```bash
   cd /ruta/a/home-cinema-control
   ls compose.yaml
   ```

   El segundo comando debe mostrar `compose.yaml`. Si indica que no existe, estás en otra carpeta y no debes continuar.

3. **Comprueba la configuración persistente.** El archivo debe conservar este volumen:

   ```yaml
   services:
     home-cinema-control:
       volumes:
         - home-cinema-control-config:/config

   volumes:
     home-cinema-control-config:
       name: home-cinema-control-config
   ```

   Si tu instalación usa una carpeta del host en vez de un volumen con nombre, conserva esa misma carpeta. No la
   sustituyas por una nueva.

4. **Comprueba la versión.** La opción recomendada es dejar esta imagen:

   ```yaml
   image: ghcr.io/tousled/home-cinema-control:${HCC_VERSION:-latest}
   ```

   No tienes que crear `HCC_VERSION`. Si `HCC_VERSION` no está definida en el entorno ni en `.env`, Compose utiliza `latest`. Si ves una imagen
   fija como `ghcr.io/tousled/home-cinema-control:1.3.0`, cámbiala por la línea anterior. Si existe un `.env` con
   `HCC_VERSION=1.3.0`, elimina esa línea o cambia su valor a `latest`.

5. **Descarga y arranca la nueva imagen desde esa misma carpeta:**

   ```bash
   docker compose pull
   docker compose up -d
   ```

   `docker pull` por sí solo solo descarga una imagen: no actualiza el contenedor que ya está funcionando.

6. **Comprueba el resultado.** Ejecuta:

   ```bash
   docker compose ps
   ```

   El servicio debe aparecer como iniciado. Abre HCC, comprueba que sigue mostrando tu configuración y revisa la nueva
   versión en **Diagnóstico**.

Si algo falla, no borres el volumen ni ejecutes `down -v`. Revisa los últimos mensajes con
`docker compose logs --tail=100 home-cinema-control` y vuelve a la versión anterior solo si conoces el tag que
funcionaba.

### 13.2 Actualizar con Portainer

Usa este procedimiento si HCC aparece dentro de **Stacks** en Portainer.

1. Abre Portainer y entra en **Stacks**.
2. Busca el stack existente de HCC, normalmente llamado `home-cinema-control`. Abre ese stack; no pulses **Add stack**.
3. Revisa el editor del stack. Debe conservar el servicio `home-cinema-control` y el volumen
   `home-cinema-control-config:/config`. Si Portainer muestra que el volumen se va a eliminar, cancela la operación.
4. Revisa la imagen. Usa `ghcr.io/tousled/home-cinema-control:${HCC_VERSION:-latest}` o
   `ghcr.io/tousled/home-cinema-control:latest`. Si aparece `:1.3.0`, sustitúyelo por una de esas opciones.
5. Si aparece una variable `HCC_VERSION` con `1.3.0`, elimínala o cambia su valor a `latest`. No necesitas añadir
   ninguna variable para una actualización normal.
6. Si tu NAS permite crear un snapshot o una copia del volumen, hazlo antes de actualizar. Portainer no convierte la
   actualización en una copia de seguridad automática.
7. Pulsa **Update the stack**. Activa **Re-pull image** si Portainer muestra esa opción. No elijas una opción que borre
   el volumen ni crees un stack con otro nombre.
8. Espera a que el stack termine y abre HCC. La configuración debe ser la misma y **Diagnóstico** debe mostrar la nueva
   versión.

Si HCC no vuelve a responder, revisa los logs del contenedor desde Portainer. Mantén el stack y el volumen existentes;
no lo elimines para intentar empezar de nuevo.

### 13.3 Actualizar desde un gestor del NAS

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

### 13.4 Si instalaste con `docker run`

Este es un procedimiento avanzado. Primero comprueba que el contenedor usa el volumen correcto:

```bash
docker inspect home-cinema-control --format '{{range .Mounts}}{{println .Name .Source "->" .Destination}}{{end}}'
```

Debe aparecer `home-cinema-control-config` apuntando a `/config`, o la misma carpeta del host que usaste al instalar.
Descarga la nueva imagen y recrea solo el contenedor con exactamente el mismo montaje. No borres el volumen. Si no
conservas el comando original, no improvises otro: vuelve a instalar mediante Compose usando la guía anterior.

### 13.5 Si la actualización ha fallado

- Si HCC conserva la configuración, abre **Diagnóstico** y revisa la versión y el último fallo.
- Si HCC aparece como nuevo, no completes el asistente: vuelve al stack o al Compose original y revisa `/config`.
- Si el volumen todavía existe, arranca el contenedor correcto con ese volumen.
- Si el volumen se borró, solo una copia de seguridad o snapshot del host/NAS puede recuperar la configuración.
- Si necesitas volver atrás y conoces la versión anterior, usa el tag anterior en el Compose. `HCC_VERSION` está pensado
  para ese caso avanzado; no es necesario para actualizar a `latest`.

## 14. Problemas frecuentes

### Jellyfin: no aparecen dispositivos ni bibliotecas al pulsar "Actualizar"

- La cuenta de Jellyfin con la que autorizas HCC debe tener permisos de **administrador**. Jellyfin protege la lista de
  dispositivos (`/Devices`) y la de carpetas de biblioteca (`/Library/VirtualFolders`) para cuentas con privilegios
  elevados — una cuenta normal recibe un error 403 al cargarlas, aunque el login en sí (autorizar, reproducir,
  reportar progreso) funcione con normalidad.
- Si Jellyfin muestra errores `401` o `403` al recargar dispositivos o bibliotecas, actualiza HCC y vuelve a autorizar
  Jellyfin desde la pantalla **Media Server**.
- Si solo tienes un usuario en tu Jellyfin, normalmente ya es el administrador y no tienes que hacer nada. Si usas un
  usuario secundario para HCC, dale permisos de administrador desde el panel de Jellyfin.

### HCC no llega al reproductor

- Comprueba la IP del OPPO/Chinoppo.
- Comprueba `network_mode: host`.
- Comprueba firewall.
- Despierta el reproductor y repite la prueba.

### El montaje NFS falla

- Verifica que el export NFS existe.
- Comprueba que el reproductor lo ve manualmente.
- Reinicia físicamente el reproductor si el navegador de red funciona pero el montaje sigue bloqueado.

### SMB devuelve `id_error`

- Revisa nombre de recurso, usuario, contraseña y permisos.
- Si tu combinación NAS/reproductor necesita preparar la sesión SMB, comprueba que las credenciales estén guardadas en
  HCC y vuelve a probar la ruta.
- Si se repite `id_error`, evita pulsar "Probar ruta" muchas veces seguidas: algunos OPPO/Chinoppo degradan su API de
  control tras demasiados montajes SMB fallidos. Reinicia físicamente el reproductor antes de volver a probar.
- Si esa biblioteca ya está verificada por NFS y SMB sigue fallando, usa NFS para ese mapeo.
- No esperes fallback a NFS: corrige SMB o cambia explícitamente esa ruta a NFS.

### SMB da timeout con carpetas de nombre largo o con caracteres especiales

Algunos reproductores OPPO/Chinoppo dan timeout al montar por SMB una carpeta cuyo nombre es muy largo o
incluye paréntesis, corchetes o el símbolo `+` (típico en nombres de release de series y películas, por
ejemplo `The Veil red de mentiras (2024) S01 [PACK][DSNP WEB-DL 1080p AVC ES DD+ 5.1][HDO]`). El mismo
contenido, en la misma carpeta NAS, monta y reproduce sin problema por NFS, y por SMB si se acorta o
simplifica el nombre de la carpeta/fichero. Si una biblioteca concreta te da timeouts SMB recurrentes y el
resto de bibliotecas SMB funcionan bien, sospecha primero de la longitud/caracteres del nombre antes de
revisar red o NAS:

- Cambia esa ruta concreta a NFS si el NAS lo expone (la forma más rápida de seguir viendo ese contenido).
- O renombra la carpeta/fichero a algo más corto y sin paréntesis/corchetes si quieres seguir usando SMB.

### El AVR cambia solo de entrada

- Revisa CEC/ARC.
- Desactiva CEC/ARC en el AVR si fuerza TV Audio.
- Aumenta el delay de cambio HDMI si el receptor necesita más tiempo al salir de standby.

## 15. Referencia avanzada

### Etiquetas de imagen

- `latest`: última versión estable publicada. Es la opción recomendada para la mayoría de las instalaciones.
- `1.4.2` o similar: versión estable fijada manualmente. Solo se actualiza cuando cambias el tag.
- `1.4.2-rc.1` o similar: versión candidata. No la uses en una instalación normal salvo que quieras probarla.

### `HCC_VERSION`

El `compose.yaml` usa `${HCC_VERSION:-latest}`. Esto significa que Compose utiliza `latest` si no encuentra un valor en
el archivo `.env` o en el entorno. No tienes que crear esa variable para instalar o actualizar HCC normalmente.

Puedes usar `HCC_VERSION` para fijar una versión conocida o volver temporalmente a una versión anterior durante una
recuperación. El archivo `.env`, si existe, debe estar junto a `compose.yaml`. No lo compartas ni lo subas a un
repositorio.

### Copia manual de un volumen con nombre

HCC no exporta la configuración desde la interfaz. Si tu NAS o gestor no ofrece snapshots o copias de volúmenes, una
persona con acceso al terminal puede crear una copia del volumen oficial sin modificarlo:

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

### Dónde está la configuración

El contenedor recibe la configuración en `/config`:

- `config.json`: configuración general de HCC.
- `secrets.json`: credenciales y secretos protegidos.
- `home-cinema-control-config`: volumen con nombre usado por el Compose oficial.

La imagen Docker se puede sustituir sin perder estos archivos si el mismo volumen o montaje sigue conectado. Borrar el
volumen no es una actualización: es borrar los datos.

### Botón de actualización de HCC

HCC no ejecuta comandos Docker por su cuenta. Sin un webhook configurado, **Actualizar** muestra el comando manual para
que lo ejecutes en tu gestor. Con un webhook, HCC avisa al gestor configurado y ese gestor descarga la imagen y reinicia
el contenedor. En ambos casos, el volumen persistente debe conservarse.
