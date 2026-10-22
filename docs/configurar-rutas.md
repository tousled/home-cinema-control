# Conecta tus carpetas multimedia a HCC

[Inicio](../README.md) · [Instalación](../INSTALL.md) · [Primeros pasos](primeros-pasos.md) · [English](configure-media-paths.en.md)

**Si ya puedes acceder a tus películas desde el OPPO/Chinoppo**, puedes seguir estos pasos directamente. HCC conecta la carpeta que ve Emby/Jellyfin con la que ve el reproductor.

Si todavía no tienes preparado el **NAS, PC, Raspberry Pi o las carpetas compartidas**, empieza por la [guía de AVPasión sobre Xnoppo](https://foro.avpasion.com/t/xnoppo-lo-mejor-de-emby-en-tu-oppo-203-205-y-chinoppo-clones-m9702-m9201-m9203-m9205.2779/page-21#post-73867) y vuelve aquí cuando puedas abrir la carpeta desde el reproductor.

## Lo habitual

1. Abre **Media Paths** en HCC. Aparecerán las bibliotecas que ya tienes en Emby o Jellyfin.
2. Elige una biblioteca, por ejemplo **Películas**, y la carpeta de red a la que puede entrar el OPPO.
3. Elige **SMB** o **NFS**: utiliza el sistema que ya funciona cuando navegas desde el OPPO.
4. Pulsa **Probar ruta** y guarda la configuración cuando HCC confirme que funciona.

Repite estos pasos con las demás bibliotecas que quieras reproducir con el OPPO. **Ruta verificada** significa que HCC ya ha comprobado que esa carpeta funciona.

Si falla la prueba, consulta las explicaciones y capturas de abajo. No necesitas leerlas si todo funciona.

## Capturas y ayuda

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
  <img src="../assets/screenshots/install/04-media-paths-overview.png" alt="Vista general del asistente de rutas de Home Cinema Control" width="860"/>
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
  <img src="../assets/screenshots/install/05-media-paths-library-filter.png" alt="Selección de bibliotecas interceptadas en Home Cinema Control" width="860"/>
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
  <img src="../assets/screenshots/install/07-media-paths-smb-credentials.png" alt="Credenciales SMB en el asistente de rutas de Home Cinema Control" width="860"/>
</p>

Para preparar las carpetas compartidas del NAS, PC o Raspberry Pi, consulta la [guía de AVPasión](https://foro.avpasion.com/t/xnoppo-lo-mejor-de-emby-en-tu-oppo-203-205-y-chinoppo-clones-m9702-m9201-m9203-m9205.2779/page-21#post-73867). Aquí seguimos con la configuración dentro de HCC.

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
  <img src="../assets/screenshots/install/06-media-paths-nfs-mapping.png" alt="Mapeo NFS verificado entre Emby y OPPO" width="860"/>
</p>

Qué significa cada estado:

| Estado     | Qué debes hacer                                                                  |
|------------|----------------------------------------------------------------------------------|
| Verificada | Esa ruta ha montado correctamente desde el reproductor.                          |
| Pendiente  | Has cambiado algo y falta probar de nuevo.                                       |
| Revisable  | El mapeo existía, pero cambió alguna pieza relacionada. Repite la prueba.        |
| Error      | HCC no pudo montar la ruta. Mira la sugerencia y los logs filtrados por errores. |

<p align="center">
  <img src="../assets/screenshots/install/08-media-paths-states.png" alt="Leyenda de estados de rutas verificadas, pendientes y con error" width="860"/>
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
  <img src="../assets/screenshots/install/09-media-paths-manual.png" alt="Modo manual de rutas de Home Cinema Control" width="860"/>
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