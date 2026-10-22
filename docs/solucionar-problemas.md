# Solucionar problemas de HCC

[Inicio](../README.md) · [Instalación](../INSTALL.md) · [English](troubleshoot.en.md)

Busca el síntoma que estás viendo. **Solo necesitas leer el apartado que coincida con tu problema.**

Si HCC aparece sin tus ajustes después de actualizar, empieza por [recuperar la configuración](recuperar-configuracion.md).

## Consulta el diagnóstico de HCC

Abre **Diagnóstico** en HCC. Ahí puedes comprobar conexiones, ver el último error y consultar la versión instalada.

<p align="center">
  <img src="../assets/screenshots/install/06-status.png" alt="Pantalla de diagnóstico de Home Cinema Control" width="860"/>
</p>

Si necesitas ayuda, pulsa **Enviar diagnóstico**. HCC prepara un informe con el estado del sistema y hasta **200 líneas recientes de logs** (por defecto); oculta las credenciales, IP, MAC y rutas conocidas de tu configuración, además de las direcciones IPv4 encontradas. **Puedes leerlo y corregirlo antes de compartirlo.** Al pulsar **Copiar y abrir GitHub**, HCC copia el informe y abre un issue: **tú debes pegarlo** y decidir si publicarlo; no se envía automáticamente.

## Consulta los logs solo si hace falta

Abre **Logs** y filtra errores o avisos recientes. HCC evita registrar credenciales en las peticiones al OPPO, pero **el log original puede mostrar IP y nombres de carpetas**. Para un informe de soporte con ocultación adicional, utiliza **Enviar diagnóstico**. También puedes copiar las líneas visibles o descargar `hcc.log`.

<p align="center">
  <img src="../assets/screenshots/install/07-logs.png" alt="Pantalla de logs con filtros de Home Cinema Control" width="860"/>
</p>

La [telemetría opcional](https://github.com/tousled/home-cinema-control/blob/main/docs/telemetry.md) es independiente de los diagnósticos que decides compartir.

## Contacto y soporte

¿Algo no funciona? Si sospechas que has encontrado un **fallo de HCC**, [abre un issue en el repositorio público](https://github.com/tousled/home-cinema-control/issues/new). Así podemos reproducirlo y compartir la solución con otros usuarios.

Para pedir **ayuda con tu instalación**, escribe a [llorente.software.solutions@gmail.com](mailto:llorente.software.solutions@gmail.com). No hace falta saber programar.

### Cómo enviar el log de una prueba fallida

1. Repite la acción que falla una vez, por ejemplo **Probar conexión** o **Probar ruta**. Apunta qué esperabas que ocurriese y qué mensaje apareció.
2. Abre **Diagnóstico** y revisa el último fallo. Pulsa **Enviar diagnóstico** para crear un informe con datos conocidos ocultos. Revísalo y pulsa **Copiar y abrir GitHub**: el informe queda copiado, **pero debes pegarlo tú** en el issue. No se publica automáticamente.
3. Abre **Logs**, pulsa **Actualizar** si necesitas cargar las últimas líneas y filtra **Error** o **Aviso**. Pulsa **Copiar líneas** para compartir las líneas visibles relevantes. Si necesitas el archivo completo, pulsa **Descargar**: obtendrás `hcc.log`.
4. En el issue o correo incluye la **versión de HCC** (en Diagnóstico), el dispositivo y servidor multimedia que utilizas, los **pasos para reproducir el error**, el mensaje que viste y las líneas del log correspondientes a esa prueba.

**Privacidad:** HCC evita escribir credenciales en las peticiones al reproductor y el informe de **Enviar diagnóstico** aplica un filtrado adicional. Aun así, antes de publicar un registro revisa si aparecen nombres de carpetas, direcciones u otros datos propios. **Descargar** guarda el `hcc.log` completo, no solo las líneas filtradas en pantalla. Para un issue público es preferible compartir el informe de Diagnóstico o las líneas necesarias.

## Problemas frecuentes

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

- Comprueba la IP del OPPO/Chinoppo y que el reproductor esté encendido.
- En **OPPO UDP-203/205**, abre **SETUP → Network Setup → IP Control → On**. En un Chinoppo/clon, busca la opción equivalente de control IP en los ajustes de red; el nombre y la ruta pueden variar según su firmware.
- Comprueba `network_mode: host`.
- Comprueba firewall.
- Despierta el reproductor y repite la prueba.

### El Chinoppo da timeout al montar la carpeta o al reproducir

Un timeout no significa siempre lo mismo:

- **`Timeout in Mount Request`:** el reproductor no completó el montaje NFS/SMB. **Puede aparecer al navegar carpetas, usar Probar ruta o iniciar una película**, porque HCC utiliza el mismo servicio de montaje en las tres operaciones. En un caso real, después de encender el Chinoppo fallaba la API de red; entrar una vez en su menú de carpetas NFS permitía continuar. Comprueba que **IP Control** está activo, espera a que el reproductor termine de arrancar y prueba de nuevo una sola vez.
- **`Timeout in Play Request`:** el reproductor no respondió a tiempo a la orden de reproducción. **No demuestra que la ruta sea incorrecta.**
- **Timeout esperando que comience la reproducción:** la película no llega a confirmarse como activa. No es necesariamente un problema de mapeo; revisa el estado del reproductor y el último error de HCC.

Si se repite, abre **Diagnóstico** y envía el informe junto al log de la prueba, siguiendo [Contacto y soporte](#contacto-y-soporte). HCC prepara la API de control antes del montaje y reintenta una vez un montaje NFS que falle por timeout; si vuelve a fallar, hace falta analizar ese caso concreto, no aumentar los tiempos a ciegas.

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
