# Referencia avanzada de HCC

[Inicio](../README.md) · [Instalación](../INSTALL.md) · [English](advanced-reference.en.md)

Esta página permite consultar opciones sin ejecutar cambios sobre Docker. Para gestionar un NAS, usar `docker run` o crear una copia manual, consulta [operaciones Docker avanzadas](operaciones-docker-avanzadas.md).

## Consulta rápida

| Elemento | Valor del Compose oficial | Para qué sirve |
|---|---|---|
| Imagen | `tousled/home-cinema-control:latest` | Descarga la última versión estable publicada, sin variables. |
| `HCC_VERSION` | No se utiliza en el ejemplo oficial | Opcional en un Compose personalizado, para fijar una versión. |
| Montaje de configuración | `home-cinema-control-config:/config` | Conserva los ajustes entre actualizaciones. Debe respetarse el montaje de cada instalación. |
| `HCC_CONFIG_FILE` | `/config/config.json` | Ruta de la configuración general dentro del contenedor. |
| `HCC_SECRETS_FILE_PATH` | `/config/secrets.json` | Ruta de credenciales y secretos dentro del contenedor. |
| `network_mode` | `host` | Permite las conexiones directas con los dispositivos de red. |

Los valores de esta tabla describen **el ejemplo de instalación oficial**, no los ajustes que necesariamente tienen todas las instalaciones existentes.


### Etiquetas de imagen

- `latest`: última versión estable publicada. Es la opción recomendada para la mayoría de las instalaciones.
- `1.4.6`: versión estable fijada manualmente. Solo se actualiza cuando cambias el tag.
- `rc` o una candidata exacta anunciada: para pruebas, solo cuando esté publicada. Consulta las releases antes de
  elegirla; no implica que 1.5.0 ya esté disponible.

### `HCC_VERSION`

El [`compose.yaml` oficial](../compose.yaml) usa `image: tousled/home-cinema-control:latest` sin interpolación de variables. Así puede copiarse o importarse directamente en gestores gráficos que no resuelven expresiones de Compose. No necesitas crear `HCC_VERSION` para instalar HCC.

Para fijar una versión estable publicada, cambia únicamente el tag `latest` de `image:` por el tag deseado, sin alterar el volumen de configuración. Si ya tienes una instalación funcionando, edita su Compose actual en vez de crear otro stack.

**Opción avanzada:** si utilizas Docker Compose con soporte para interpolación, puedes modificar tu propio archivo para usar `image: tousled/home-cinema-control:${HCC_VERSION:-latest}`. En ese caso, `HCC_VERSION` se puede fijar en el entorno o en un archivo `.env` junto a `compose.yaml`; si falta, se utiliza `latest`. Comprueba la imagen resuelta con `docker compose config --images` antes de desplegar. **Definir `HCC_VERSION` por sí sola no cambia la imagen del Compose oficial**, que utiliza un tag fijo. No compartas ni subas archivos `.env` con información privada. En un gestor que no admita interpolación, usa siempre el tag explícito.

Las instalaciones anteriores que ya utilizan `HCC_VERSION` pueden conservarla; no hay que cambiar el método de actualización si funciona.

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
