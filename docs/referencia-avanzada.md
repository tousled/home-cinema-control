# Referencia avanzada de HCC

[Inicio](../README.md) · [Instalación](../INSTALL.md) · [English](advanced-reference.en.md)

Esta página permite consultar opciones sin ejecutar cambios sobre Docker. Para gestionar un NAS, usar `docker run` o crear una copia manual, consulta [operaciones Docker avanzadas](operaciones-docker-avanzadas.md).

## Consulta rápida

| Elemento | Valor del Compose oficial | Para qué sirve |
|---|---|---|
| Imagen | `tousled/home-cinema-control:${HCC_VERSION:-latest}` | Descarga la versión elegida; usa `latest` si no hay variable definida. |
| `HCC_VERSION` | Sin definir | Opcional. Fija una versión cuando necesitas mantenerla o volver atrás. |
| Montaje de configuración | `home-cinema-control-config:/config` | Conserva los ajustes entre actualizaciones. Debe respetarse el montaje de cada instalación. |
| `HCC_CONFIG_FILE` | `/config/config.json` | Ruta de la configuración general dentro del contenedor. |
| `HCC_SECRETS_FILE_PATH` | `/config/secrets.json` | Ruta de credenciales y secretos dentro del contenedor. |
| `network_mode` | `host` | Permite las conexiones directas con los dispositivos de red. |

Los valores de esta tabla describen **el ejemplo de instalación oficial**, no los ajustes que necesariamente tienen todas las instalaciones existentes.


### Etiquetas de imagen

- `latest`: última versión estable publicada. Es la opción recomendada para la mayoría de las instalaciones.
- `1.4.5`: versión estable fijada manualmente. Solo se actualiza cuando cambias el tag.
- `rc` o una candidata exacta anunciada: para pruebas, solo cuando esté publicada. Consulta las releases antes de
  elegirla; no implica que 1.5.0 ya esté disponible.

### `HCC_VERSION`

El `compose.yaml` usa `${HCC_VERSION:-latest}`. Esto significa que Compose utiliza `latest` si no encuentra un valor en
el archivo `.env` o en el entorno. No tienes que crear esa variable para instalar o actualizar HCC normalmente.

Puedes usar `HCC_VERSION` para fijar una versión conocida o volver temporalmente a una versión anterior durante una
recuperación. El archivo `.env`, si existe, debe estar junto a `compose.yaml`. No lo compartas ni lo subas a un
repositorio.

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

### Perfiles y rutas de reproductores en 1.5.0

La configuración pública utiliza `media_players.active` para el reproductor elegido y `media_players.providers` para los
perfiles de OPPO y Kodi. El usuario, dirección, puerto y ajustes avanzados de Kodi son públicos; su contraseña solo se
guarda en `secrets.json`, bajo `media_players.providers.kodi.password`. La interfaz indica si hay contraseña guardada
sin devolverla. Una contraseña omitida conserva la anterior.

Las rutas pertenecen al servidor multimedia y al reproductor:
`media_servers.providers.<servidor>.playback.path_mappings_by_player`. HCC conserva la lectura de formatos anteriores y
asigna las rutas antiguas sin reproductor a OPPO. No edites ni dupliques estos datos para alternar equipos: utiliza
**Media Player** y **Media Paths**.

El puerto HTTP de Kodi suele ser `8080`; utiliza el que muestre Kodi en sus ajustes de control. La interfaz web de HCC
utiliza `8090`. No son el mismo servicio.

Consulta [recuperación de configuración](recuperar-configuracion.md#si-se-interrumpe-un-guardado) para guardados
interrumpidos. Mantén un único proceso HCC escribiendo en cada volumen de configuración.
