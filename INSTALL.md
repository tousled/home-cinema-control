# Instalación y configuración de Home Cinema Control

[English](INSTALL.en.md) · [README](README.md)

Esta guía cubre el despliegue de HCC y la configuración desde la interfaz web. Está pensada para evitar los problemas
que más suelen aparecer en instalaciones con Emby/Jellyfin, NAS, OPPO/Chinoppo, TV y receptor AV: rutas mal mapeadas,
IPs escritas a mano, montajes que fallan sin explicación, CEC/ARC cambiando entradas y logs difíciles de interpretar.

Para capturas específicas de Synology, QNAP, Windows, Unraid o preparación del reproductor OPPO/Chinoppo, usa como
referencia externa el tutorial de la comunidad de AVPasion sobre Xnoppo:

https://foro.avpasion.com/t/xnoppo-lo-mejor-de-emby-en-tu-oppo-203-205-y-chinoppo-clones-m9702-m9201-m9203-m9205.2779/page-21#post-73867

Usa ese hilo para permisos de NAS, recursos compartidos y configuración del reproductor. Usa esta guía para HCC.

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

## 2. Arranque rápido con Docker

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

## 3. Instalación recomendada con Docker Compose

Para una instalación permanente, crea `compose.yaml`. Es más cómodo para actualizar, fijar una versión concreta o hacer
rollback:

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

Arranca:

```bash
docker compose pull
docker compose up -d
```

Abre `http://<tu-host>:8090`.

`network_mode: host` es necesario: HCC habla directamente con Emby/Jellyfin, el OPPO/Chinoppo, TV, AVR y herramientas
de descubrimiento como `arp-scan`.

### 3.1 Instalar con Portainer u otra interfaz web

En Portainer: **Stacks → Add stack** y pega el `compose.yaml` de arriba.

Para fijar una versión concreta (incluidas las release candidates), añade `HCC_VERSION` como variable de entorno del
stack, por ejemplo `HCC_VERSION=1.1.0-rc.2`. Es lo único que decide qué imagen se descarga — sin ella, Portainer usa
`latest` (la última estable). Para actualizar, cambia ese valor y vuelve a desplegar tirando de la imagen ("re-pull"),
no reconstruyendo desde el Dockerfile.

Otras interfaces (Synology Container Manager, Unraid...) deberían funcionar igual si permiten definir variables de
entorno para el stack — la lógica es la misma.

## 4. Migración o instalación limpia

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

No conviene adivinar estas rutas. NAS, NFS y SMB no siempre exponen los mismos nombres. Por eso HCC parte de las
bibliotecas del proveedor activo, te pide la ruta equivalente vista por el reproductor y la prueba antes de una sesión
real. La pantalla muestra una insignia de Emby/Jellyfin para que tengas claro qué servidor estás mapeando.

<p align="center">
  <img src="assets/screenshots/install/04-media-paths-overview.png" alt="Vista general del asistente de rutas de Home Cinema Control" width="860"/>
</p>

### 6.1 Crea primero las bibliotecas en Emby

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

### 6.2 Elige qué bibliotecas debe interceptar HCC

No todo lo que existe en Emby tiene que pasar por el OPPO. Puedes dejar fuera música, documentales, pruebas o cualquier
biblioteca que quieras reproducir normalmente desde el cliente Emby.

La pantalla muestra las bibliotecas detectadas y permite activar solo las que quieras que HCC controle. Las demás
seguirán reproduciéndose por el flujo normal de Emby.

<p align="center">
  <img src="assets/screenshots/install/05-media-paths-library-filter.png" alt="Selección de bibliotecas interceptadas en Home Cinema Control" width="860"/>
</p>

### 6.3 Prepara NFS o SMB/CIFS en el NAS

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

### 6.4 Encuentra la ruta como la ve el OPPO

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

### 6.5 Crea y prueba el mapeo en HCC

En **Media Paths**, trabaja biblioteca por biblioteca:

1. Pulsa **Recargar bibliotecas** para traer las bibliotecas actuales de Emby.
2. Selecciona la biblioteca que quieres interceptar.
3. Revisa la **ruta del servidor** que HCC ha leído desde Emby.
4. Elige `nfs` o `cifs` para esa biblioteca.
5. Escribe o selecciona la **ruta OPPO** tal como la ve el reproductor.
6. Si usas SMB con usuario, rellena credenciales en la sección SMB.
7. Pulsa **Probar ruta**.
8. Guarda cuando la ruta quede verificada.

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

### 6.6 Cuándo usar modo manual

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

### 6.7 Lo que HCC hace mejor aquí

- detecta bibliotecas y rutas físicas desde Emby;
- permite elegir qué bibliotecas interceptar;
- permite configurar NFS o SMB/CIFS por mapeo;
- puede probar si el OPPO/Chinoppo monta la ruta;
- marca rutas como verificadas, pendientes, revisables o con error;
- permite crear una ruta manual si Emby no devuelve las carpetas esperadas o si tu estructura necesita ajustes.

Conceptos clave:

| Campo             | Qué significa                                                        |
|-------------------|----------------------------------------------------------------------|
| Ruta del servidor | Ruta física que Emby reporta para la biblioteca.                     |
| Ruta OPPO         | Ruta NFS o SMB/CIFS que el reproductor ve desde su navegador de red. |
| Protocolo         | `nfs` o `cifs`, elegido por cada ruta.                               |
| Verificada        | HCC ha probado que el reproductor puede montar esa ruta.             |

HCC no cambia silenciosamente de SMB a NFS ni de NFS a SMB. Si una ruta está configurada como SMB, se prueba y reproduce
como SMB. Esto evita errores invisibles cuando una biblioteca funciona con un protocolo y otra necesita otro.

### 6.8 Por qué este paso mejora toda la reproducción

Cuando las rutas están verificadas, HCC puede tratar la sesión como un flujo controlado y no como una cadena de
intentos:

- monta directamente el recurso correcto en el OPPO/Chinoppo;
- evita reintentos con protocolos que no has elegido;
- clasifica el error si el montaje falla;
- observa el estado del reproductor con SVM3 cuando está disponible;
- usa polling acotado como respaldo, no como única estrategia permanente;
- reporta progreso a Emby con una cadencia controlada;
- limpia la sesión al parar o terminar para no dejar el reproductor en un estado raro.

La diferencia no siempre se ve en pantalla, pero sí importa: menos ruido hacia el reproductor, menos comportamientos
aleatorios y más información cuando algo falla.

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
- En LG WebOS, HCC puede detectar entradas HDMI y restaurar la app del servidor multimedia.
- En Samsung Tizen (2016+), HCC necesita SmartThings para cambiar de entrada HDMI — ver sección siguiente.
- En AVR compatibles, HCC puede encender, apagar, cambiar entrada y aplicar esperas para mitigar problemas HDMI.

### 8.1 Samsung TV: configuración de SmartThings

HCC controla la Samsung TV por WebSocket para la conexión, el emparejamiento y el Wake-on-LAN. Sin embargo, para
cambiar de entrada HDMI necesita SmartThings: los códigos de mando (`KEY_HDMI1`…) no funcionan de forma fiable en
la mayoría de modelos Tizen para saltar directamente a un input concreto.

Los dos campos son obligatorios para que el cambio de HDMI funcione. Para seguir el proceso con capturas de
pantalla paso a paso, consulta
la [guía de configuración de la API SmartThings](https://tavicu.github.io/homebridge-samsung-tizen/configuration/smartthings-api.html)
(escrita para Homebridge, pero las pantallas de SmartThings son idénticas). La referencia oficial del token está en
[developer.smartthings.com](https://developer.smartthings.com/docs/getting-started/authorization-and-permissions).

#### Cómo obtener el SmartThings Token

1. Abre [account.smartthings.com/tokens](https://account.smartthings.com/tokens) e inicia sesión con tu cuenta Samsung.
2. Pulsa **Generate new token**.
3. Dale un nombre descriptivo, por ejemplo `Home Cinema Control`.
4. En **Authorized Scopes**, activa como mínimo **Devices**.
5. Pulsa **Generate token** y copia el valor inmediatamente — no se vuelve a mostrar.
6. Pega el token en el campo **SmartThings Token** de la configuración Samsung en HCC.

> **Caducidad del token:** Los tokens de SmartThings caducan a las 24 horas de su creación. Cuando el cambio
> de HDMI deje de funcionar, vuelve a [account.smartthings.com/tokens](https://account.smartthings.com/tokens),
> genera uno nuevo y pégalo en el campo **SmartThings Token** de la configuración Samsung en HCC.

#### Cómo obtener el SmartThings Device ID

1. Abre [account.smartthings.com](https://account.smartthings.com) e inicia sesión.
2. En el panel principal, localiza la TV y haz clic en ella.
3. El identificador aparece a la izquierda del modal, en formato `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`.
4. Copia ese valor y pégalo en el campo **SmartThings Device ID** de la configuración Samsung en HCC.

Si la TV no aparece en el panel, ábrela desde la app Samsung SmartThings en tu móvil y completa el registro del
dispositivo antes de volver a este paso.

Nota sobre CEC/ARC:

Si el receptor AV cambia a la entrada correcta pero vuelve solo a TV Audio, ARC o CEC probablemente está interviniendo.
En ese caso, desactiva CEC/ARC en el receptor o revisa la configuración HDMI. HCC puede reintentar cambios de entrada,
pero si el AVR o la TV fuerzan otra fuente por CEC, la automatización será inestable.

## 9. Diagnóstico: saber qué falla

La pantalla **Diagnóstico** resume estado, recursos, último fallo, versión y acciones de soporte.

<p align="center">
  <img src="assets/screenshots/install/06-status.png" alt="Pantalla de diagnóstico de Home Cinema Control" width="860"/>
</p>

Úsala para:

- comprobar si HCC está conectado;
- copiar un resumen de soporte;
- ver el último fallo;
- comprobar actualizaciones;
- activar o desactivar telemetría anónima y enviar interés de roadmap;
- reiniciar el servicio si tu despliegue lo permite.

El bloque de versión muestra la versión instalada con el mismo formato que las etiquetas Docker (`1.1.1-rc.1`, por
ejemplo). Si configuras un webhook de actualización, HCC guarda la versión actual antes de pedir el redeploy; si esa
información no existe en una instalación antigua, intenta derivar una versión de rollback desde las releases/tags de
GitHub en vez de mostrar el fallback interno de build.

El objetivo es que un fallo no sea simplemente “no reproduce”, sino una pista concreta: servidor no accesible, ruta sin
verificar, montaje OPPO fallido, TV/AV desactivado, error de recuperación, etc.

La telemetría es opcional y viene desactivada. Si la activas, HCC envía datos anónimos mínimos para entender adopción y
priorizar desarrollo: instalación activa, versión, idioma, proveedor Emby/Jellyfin, uso de OPPO, TV/AV, NFS/SMB y
eventos de reproducción iniciada/finalizada/fallida. Si el backend de telemetría no está disponible, HCC guarda
temporalmente esos eventos anónimos en `/config/telemetry_queue.json` y los reintenta después. No envía rutas, IPs,
tokens, URLs, nombres de servidor, bibliotecas, títulos, logs, scripts ni comandos personalizados. Más detalle:
[`docs/telemetry.md`](docs/telemetry.md).

## 10. Logs entendibles

La pantalla **Logs** muestra líneas estructuradas con severidad y permite filtrar.

<p align="center">
  <img src="assets/screenshots/install/07-logs.png" alt="Logs estructurados y filtrables de Home Cinema Control" width="860"/>
</p>

La consola muestra por defecto las últimas 100 líneas visibles. Puedes cambiar el rango a más líneas o al log completo,
filtrar por severidad y copiar al portapapeles exactamente las líneas mostradas, algo útil cuando compartes información
desde el móvil. La descarga sigue generando el log completo.

Esto sustituye el patrón de revisar logs crudos sin contexto. Los errores y avisos quedan marcados visualmente para que
sea más fácil compartir información útil en soporte.

## 11. Primera reproducción de validación

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

## 12. Configuración del NAS y del reproductor

HCC no cambia permisos del NAS ni configura el reproductor por ti. Antes de probar rutas:

- el NAS debe compartir la carpeta por NFS o SMB/CIFS;
- el OPPO/Chinoppo debe poder ver ese recurso desde su navegador de red;
- si usas SMB, revisa usuario, contraseña y compatibilidad SMB de tu NAS;
- si usas NFS, revisa permisos de export y acceso desde la IP del reproductor.

Para capturas de Synology, QNAP, Windows, Unraid y M9702/M920x, usa el hilo de AVPasion enlazado al principio.

## 13. Actualización

Si instalaste con Docker Compose:

```bash
docker compose pull
docker compose up -d
```

Si instalaste con `docker run`:

```bash
docker pull ghcr.io/tousled/home-cinema-control:latest
docker stop home-cinema-control
docker rm home-cinema-control

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

Si instalaste con Portainer u otra interfaz web: cambia la variable de entorno `HCC_VERSION` del stack a la versión
que quieras y vuelve a desplegar tirando de la imagen ("re-pull"), no reconstruyendo desde el Dockerfile — ver
[3.1](#31-instalar-con-portainer-u-otra-interfaz-web).

Si configuras un webhook de redespliegue, la pantalla Diagnóstico puede lanzar la actualización desde la web. Si no, HCC
muestra el comando para ejecutarlo manualmente.

## 14. Problemas frecuentes

### Jellyfin: no aparecen dispositivos ni bibliotecas al pulsar "Actualizar"

- La cuenta de Jellyfin con la que autorizas HCC debe permisos de **administrador**. Jellyfin protege la lista de
  dispositivos (`/Devices`) y la de carpetas de biblioteca (`/Library/VirtualFolders`) para cuentas con privilegios
  elevados — una cuenta normal recibe un error 403 al cargarlas, aunque el login en sí (autorizar, reproducir,
  reportar progreso) funcione con normalidad.
- En Jellyfin 12.0 RC1 y versiones posteriores, HCC usa la autorización moderna de Jellyfin. Si ves `401` en
  `/Devices`, `/Library/VirtualFolders` o `/Sessions/Capabilities/Full`, junto con `403 Forbidden` en el WebSocket,
  actualiza HCC a una versión que incluya esta corrección y vuelve a autorizar Jellyfin desde la pantalla
  **Media Server** si el token guardado quedó invalidado durante la actualización.
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
- Prueba el pre-montaje SMB si tu combinación NAS/reproductor necesita preparar la sesión.
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

### La TV Samsung no cambia de entrada HDMI

- Comprueba que los campos **SmartThings Token** y **SmartThings Device ID** estén rellenos en la pantalla
  Sala. Sin ellos, HCC no puede cambiar de entrada HDMI en Samsung —
  ver [sección 8.1](#81-samsung-tv-configuración-de-smartthings).
- El token debe tener al menos el permiso **Devices** en SmartThings. Si lo generaste con todos los permisos
  desmarcados, revócalo y genera uno nuevo con ese permiso activo.
- Los tokens de SmartThings caducan a las 24 horas. Si el cambio de HDMI dejó de funcionar después de haber
  funcionado correctamente, lo más probable es que el token haya caducado — genera uno nuevo en
  [account.smartthings.com/tokens](https://account.smartthings.com/tokens) y actualiza el campo **SmartThings Token** en
  HCC.
- Verifica que la TV esté registrada en SmartThings: debe aparecer como dispositivo en
  [account.smartthings.com](https://account.smartthings.com) y en la app SmartThings del móvil.
- Si la TV acaba de encenderse o se despertó por Wake-on-LAN, espera unos segundos antes de que SmartThings la
  detecte disponible y vuelve a intentarlo.

### La TV Samsung pide confirmar el acceso en cada conexión

HCC guarda el token de emparejamiento WebSocket en `/config/.samsung_tv_token`. Si el contenedor no tiene
permisos de escritura sobre el volumen `/config`, el fichero no puede crearse y la TV mostrará el diálogo
de emparejamiento en cada operación. Comprueba que el volumen esté montado con permisos de escritura y reinicia
el contenedor.

### El AVR cambia solo de entrada

- Revisa CEC/ARC.
- Desactiva CEC/ARC en el AVR si fuerza TV Audio.
- Aumenta el delay de cambio HDMI si el receptor necesita más tiempo al salir de standby.
