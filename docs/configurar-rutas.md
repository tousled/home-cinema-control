# Configura tus carpetas multimedia en HCC

[Inicio](../README.md) · [Instalación](../INSTALL.md) · [Primeros pasos](primeros-pasos.md) · [English](configure-media-paths.en.md)

**No tienes que escribir las rutas a mano.** HCC detecta las bibliotecas de Emby/Jellyfin y tiene un navegador para elegir las carpetas desde el OPPO/Chinoppo. Normalmente basta con seleccionar, explorar y probar.

Antes de empezar, las películas deben aparecer en Emby/Jellyfin y el OPPO debe poder abrir la carpeta compartida desde su propio menú. ¿Aún no tienes preparado el NAS, PC o Raspberry Pi? Sigue primero la [guía de AVPasión](https://foro.avpasion.com/t/xnoppo-lo-mejor-de-emby-en-tu-oppo-203-205-y-chinoppo-clones-m9702-m9201-m9203-m9205.2779/page-21#post-73867) y vuelve aquí.

## Configura una biblioteca

### 1. Elige tu biblioteca

Abre **Media Paths** en HCC. Se muestran las carpetas de las bibliotecas de tu servidor multimedia. Si acabas de añadir una biblioteca, pulsa **Actualizar bibliotecas**.

Selecciona, por ejemplo, **Películas**. HCC ya conoce la **ruta del servidor**, así que no tienes que escribirla ni modificarla.

<p align="center">
  <img src="../assets/screenshots/install/04-media-paths-overview.png" alt="Bibliotecas detectadas y rutas en Media Paths" width="860"/>
</p>

Por defecto puedes usar todas las bibliotecas. Si solo quieres que algunas reproduzcan a través del OPPO, elígelas en el apartado de selección y guarda los cambios.

<p align="center">
  <img src="../assets/screenshots/install/05-media-paths-library-filter.png" alt="Selección de bibliotecas que HCC debe controlar" width="860"/>
</p>

### 2. Abre el navegador del OPPO

En la sección **Acceso OPPO**, utiliza el protocolo con el que ya accedes a tus películas desde el reproductor: **NFS** o **Usar SMB/CIFS**.

Pulsa el botón **Explorar OPPO**, junto al campo de ruta del reproductor. **Entra en las carpetas que aparecen en el navegador hasta llegar a la carpeta compartida correspondiente a la biblioteca.** A medida que navegas, HCC rellena la ruta del OPPO por ti.

No copies aquí la ruta que aparece en Emby/Jellyfin: puede ser diferente aunque ambas apunten a las mismas películas.

Si utilizas SMB y el recurso pide usuario y contraseña, introdúcelos en **Acceso OPPO** y pulsa **Guardar** en el apartado de acceso antes de probar.

<p align="center">
  <img src="../assets/screenshots/install/07-media-paths-smb-credentials.png" alt="Acceso SMB con usuario y contraseña, solo cuando es necesario" width="860"/>
</p>

### 3. Pulsa «Probar ruta»

Con la carpeta elegida, pulsa **Probar ruta**.

**Si todo funciona, HCC muestra «Ruta verificada» en verde y guarda el mapeo.** Ya puedes utilizar esa biblioteca para reproducir en el OPPO. No necesitas guardar una ruta manual adicional.

<p align="center">
  <img src="../assets/screenshots/install/06-media-paths-nfs-mapping.png" alt="Ejemplo de una ruta NFS correctamente verificada" width="860"/>
</p>

Repite estos tres pasos para las demás bibliotecas que quieras utilizar. Si tienes una biblioteca con varias carpetas, puedes configurar las rutas que necesites.

## ¿Qué pasa si no aparece «Ruta verificada»?

Abre el apartado **Qué significa cada estado** de Media Paths:

| Estado | Qué hacer |
|---|---|
| **Verificada** (verde) | Todo listo: la ruta se ha probado correctamente. |
| **No verificada** | Falta probar la ruta o la prueba no se ha completado correctamente. Pulsa **Probar ruta**. |
| **Revisar** | Has cambiado una ruta antes verificada. Vuelve a probarla. |
| **Sin ruta** | Aún no has elegido la carpeta del OPPO. |
| **No interceptada** | Esa biblioteca no está activada para que HCC controle su reproducción. |
| **Error** | La última prueba ha fallado. Lee el motivo y la sugerencia que muestra HCC. |

<p align="center">
  <img src="../assets/screenshots/install/08-media-paths-states.png" alt="Estados de rutas verificadas, pendientes y con error" width="860"/>
</p>

**Si el navegador no abre las carpetas**, comprueba primero que el OPPO esté encendido y que pueda entrar en ellas desde su propio menú. En los **OPPO UDP-203/205**, verifica **SETUP → Network Setup → IP Control → On**; en clones comprueba la opción equivalente según el firmware. Comprueba también el protocolo elegido y, si usas SMB, sus credenciales. No repitas muchas veces una prueba SMB fallida: algunos reproductores necesitan reiniciarse tras varios intentos.

**Si el navegador no puede ayudarte**, puedes introducir la ruta del OPPO mediante el **modo avanzado/manual**. En ese caso:

1. Comprueba en el explorador de red del OPPO cuál es la carpeta compartida real.
2. Pulsa **Editar ruta del servidor** para abrir el modo avanzado y escribe o ajusta la ruta del OPPO para esa biblioteca.
3. Pulsa **Probar ruta** y no la des por terminada hasta obtener **Ruta verificada**.

<p align="center">
  <img src="../assets/screenshots/install/09-media-paths-manual.png" alt="Modo avanzado para introducir una ruta cuando no funciona el navegador" width="860"/>
</p>

Si el OPPO ve por SMB `Video/Peliculas` y Emby ve `/volume1/Video/Peliculas`, es normal que los nombres sean distintos: **el navegador evita que tengas que adivinarlos**.

Si el problema continúa, abre **Diagnóstico** y revisa el último fallo y su recomendación. En [Solucionar problemas](solucionar-problemas.md) encontrarás ayuda para NFS, SMB y los fallos de conexión; también explica cómo descargar los logs y [contactar con soporte](solucionar-problemas.md#contacto-y-soporte).
