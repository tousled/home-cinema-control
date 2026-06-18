# Instalación y configuración de Home Cinema Control

[English](INSTALL.en.md) · [README](README.md)

Esta guía cubre el despliegue de HCC y la configuración desde la interfaz web. Está pensada para evitar los problemas
que más suelen aparecer en instalaciones con Emby, NAS, OPPO/Chinoppo, TV y receptor AV: rutas mal mapeadas, IPs
escritas a mano, montajes que fallan sin explicación, CEC/ARC cambiando entradas y logs difíciles de interpretar.

Para capturas específicas de Synology, QNAP, Windows, Unraid o preparación del reproductor OPPO/Chinoppo, usa como
referencia externa el tutorial de la comunidad de AVPasion sobre Xnoppo:

https://foro.avpasion.com/t/xnoppo-lo-mejor-de-emby-en-tu-oppo-203-205-y-chinoppo-clones-m9702-m9201-m9203-m9205.2779/page-21#post-73867

Usa ese hilo para permisos de NAS, recursos compartidos y configuración del reproductor. Usa esta guía para HCC.

## 1. Antes de empezar

Necesitas:

| Requisito                | Notas                                                     |
|--------------------------|-----------------------------------------------------------|
| Docker                   | Linux recomendado. HCC usa red host.                      |
| Emby Server              | Accesible desde el host donde corre HCC.                  |
| OPPO/Chinoppo            | Debe exponer la API MediaControl de OPPO en la red local. |
| NAS o carpeta compartida | Debe ser visible desde Emby y desde el reproductor.       |
| NFS o SMB/CIFS           | Se elige por cada mapeo de ruta en HCC.                   |
| TV y receptor AV         | Opcionales. HCC puede funcionar sin ellos.                |

Recomendaciones antes de instalar:

- Reserva IP fija para Emby, NAS, OPPO/Chinoppo, TV y receptor AV.
- Crea primero las bibliotecas en Emby. HCC no inventa bibliotecas: lee las que ya existen en tu servidor. La guía
  oficial de Emby explica el flujo en
  [Library Setup](https://emby.media/support/articles/Library-Setup.html) y su
  [Quick Start](https://emby.media/support/articles/Quick-Start.html).
- Comparte las carpetas del NAS por NFS o SMB/CIFS y comprueba que el reproductor puede verlas desde su propio
  explorador de red.
- Decide qué bibliotecas debe interceptar HCC.
- Si usas receptor AV, revisa HDMI CEC/ARC. En algunos Denon/Marantz y configuraciones similares, CEC/ARC puede volver a
  seleccionar la entrada de TV después de que HCC haya cambiado a la entrada del reproductor. Si ves ese comportamiento,
  desactiva CEC/ARC en el AVR o ajusta la configuración HDMI del receptor.

## 2. Docker Compose

Crea `compose.yaml`:

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

Abre:

```text
http://<tu-host>:8090
```

`network_mode: host` es importante porque HCC habla directamente con Emby, el OPPO/Chinoppo, TV, AVR y herramientas de
descubrimiento como `arp-scan`.

## 3. Migración o instalación limpia

Si HCC encuentra una configuración anterior compatible, mostrará una pantalla de migración. Puedes importar la
configuración o empezar desde cero.

<p align="center">
  <img src="assets/screenshots/install/01-migration.png" alt="Pantalla de migración de configuración anterior" width="860"/>
</p>

La migración existe para conservar lo reutilizable, pero HCC guarda ahora la configuración por secciones y separa los
secretos en `/config/secrets.json`.

## 4. Media Server: conecta Emby

En **Media Server** se configura la URL de Emby, el usuario y el dispositivo de Emby que HCC debe monitorizar.

<p align="center">
  <img src="assets/screenshots/install/02-media-server.png" alt="Pantalla Media Server de Home Cinema Control" width="860"/>
</p>

Qué resuelve esta pantalla:

- evita editar tokens a mano;
- guarda credenciales sensibles en `secrets.json`;
- permite recargar dispositivos de Emby;
- detecta bibliotecas para usarlas después en el asistente de rutas;
- mantiene el guardado limitado a la sección de Media Server.

El dispositivo monitorizado es importante: HCC solo intercepta sesiones que lleguen desde ese cliente/dispositivo de
Emby.

## 5. Media Player: localiza el OPPO/Chinoppo

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

## 6. Rutas de medios: la parte importante

Esta es la parte más importante de la configuración porque aquí se resuelve el problema real: Emby sabe dónde está la
película en el servidor, pero el OPPO/Chinoppo necesita llegar a la misma película como recurso de red del NAS.

Piensa en HCC como un traductor de rutas:

```text
Emby ve:          /volume1/Video/Peliculas/Dune (2021).mkv
OPPO ve por NFS:  volume1/Video/Peliculas/Dune (2021).mkv
OPPO ve por SMB:  Video/Peliculas/Dune (2021).mkv
HCC guarda:       esta biblioteca usa esta ruta OPPO y este protocolo
```

No conviene adivinar estas rutas. NAS, NFS y SMB no siempre exponen los mismos nombres. Por eso HCC parte de las
bibliotecas de Emby, te pide la ruta equivalente vista por el reproductor y la prueba antes de una sesión real.

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

## 7. Sala: TV y receptor AV son opcionales

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
- En AVR compatibles, HCC puede encender, apagar, cambiar entrada y aplicar esperas para mitigar problemas HDMI.

Nota sobre CEC/ARC:

Si el receptor AV cambia a la entrada correcta pero vuelve solo a TV Audio, ARC o CEC probablemente está interviniendo.
En ese caso, desactiva CEC/ARC en el receptor o revisa la configuración HDMI. HCC puede reintentar cambios de entrada,
pero si el AVR o la TV fuerzan otra fuente por CEC, la automatización será inestable.

## 8. Diagnóstico: saber qué falla

La pantalla **Diagnóstico** resume estado, recursos, último fallo, versión y acciones de soporte.

<p align="center">
  <img src="assets/screenshots/install/06-status.png" alt="Pantalla de diagnóstico de Home Cinema Control" width="860"/>
</p>

Úsala para:

- comprobar si HCC está conectado;
- copiar un resumen de soporte;
- ver el último fallo;
- comprobar actualizaciones;
- reiniciar el servicio si tu despliegue lo permite.

El objetivo es que un fallo no sea simplemente “no reproduce”, sino una pista concreta: servidor no accesible, ruta sin
verificar, montaje OPPO fallido, TV/AV desactivado, error de recuperación, etc.

## 9. Logs entendibles

La pantalla **Logs** muestra líneas estructuradas con severidad y permite filtrar.

<p align="center">
  <img src="assets/screenshots/install/07-logs.png" alt="Logs estructurados y filtrables de Home Cinema Control" width="860"/>
</p>

Esto sustituye el patrón de revisar logs crudos sin contexto. Los errores y avisos quedan marcados visualmente para que
sea más fácil compartir información útil en soporte.

## 10. Primera reproducción de validación

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

## 11. Configuración del NAS y del reproductor

HCC no cambia permisos del NAS ni configura el reproductor por ti. Antes de probar rutas:

- el NAS debe compartir la carpeta por NFS o SMB/CIFS;
- el OPPO/Chinoppo debe poder ver ese recurso desde su navegador de red;
- si usas SMB, revisa usuario, contraseña y compatibilidad SMB de tu NAS;
- si usas NFS, revisa permisos de export y acceso desde la IP del reproductor.

Para capturas de Synology, QNAP, Windows, Unraid y M9702/M920x, usa el hilo de AVPasion enlazado al principio.

## 12. Actualización

```bash
docker compose pull
docker compose up -d
```

Si configuras un webhook de redespliegue, la pantalla Diagnóstico puede lanzar la actualización desde la web. Si no, HCC
muestra el comando para ejecutarlo manualmente.

## 13. Problemas frecuentes

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

### El AVR cambia solo de entrada

- Revisa CEC/ARC.
- Desactiva CEC/ARC en el AVR si fuerza TV Audio.
- Aumenta el delay de cambio HDMI si el receptor necesita más tiempo al salir de standby.
