# Primeros pasos dentro de HCC

[Inicio](../README.md) · [Instalación](../INSTALL.md) · [English](getting-started.en.md)

**HCC ya está funcionando.** Ahora solo tienes que seguir las pantallas: **Media Server**, **Media Player**, **Media Paths** y **Sala** (TV y/o receptor AV). HCC incluye herramientas para encontrar dispositivos y probar conexiones; no hace falta introducir todos los datos a mano. Home Assistant puede esperar.

## Configura HCC en cinco pasos

1. **[Media Server](#2-conecta-emby-o-jellyfin):** elige Emby o Jellyfin, introduce los datos del servidor y autoriza la conexión.
2. **[Media Player](#3-conecta-el-oppochinoppo):** encuentra tu OPPO/Chinoppo y pulsa **Probar OPPO**.
3. **[Media Paths](configurar-rutas.md):** elige la biblioteca, pulsa **Explorar OPPO** para localizar su carpeta y después **Probar ruta**. Si sale **Ruta verificada** en verde, está lista.
4. **[Sala: TV y receptor AV](#5-tv-y-receptor-av-opcional):** configura la TV, el receptor o ambos y prueba su conexión. Si no tienes receptor, configura solo la TV.
5. Reproduce una película desde el dispositivo Emby/Jellyfin que hayas elegido.

**Resultado esperado:** el OPPO reproduce tu película. Si falla, abre [solución de problemas](solucionar-problemas.md).

## Capturas de cada pantalla

### 1. Instalación nueva o migración

Si HCC encuentra datos antiguos, puedes importarlos. Si no, elige **Configurar desde cero**. Si HCC ya funcionaba y aparece vacío sin esperarlo, **detente** y sigue [recuperar configuración](recuperar-configuracion.md). Si aparece algún error, consulta [Diagnóstico](solucionar-problemas.md#consulta-el-diagnóstico-de-hcc).

<p align="center">
  <img src="../assets/screenshots/install/01-migration.png" alt="Pantalla de migración de configuración anterior" width="860"/>
</p>

### 2. Conecta Emby o Jellyfin

Abre **Media Server**, elige **Emby** o **Jellyfin**, escribe la dirección del servidor y autoriza la conexión. Después selecciona el dispositivo Emby/Jellyfin cuya reproducción debe detectar HCC. Si ya utilizas el servidor multimedia, no necesitas configurar sus bibliotecas de nuevo.

<p align="center">
  <img src="../assets/screenshots/install/02-media-server.png" alt="Pantalla Media Server de Home Cinema Control" width="860"/>
</p>

<p align="center">
  <img src="../assets/screenshots/install/02-media-server-pending.png" alt="Media Server con Jellyfin seleccionado pero pendiente de autorización" width="860"/>
</p>

Si ves el estado **pendiente**, completa la autorización antes de continuar. HCC debería mostrar tus dispositivos y bibliotecas al actualizarlos. Si no aparecen, abre [Diagnóstico](solucionar-problemas.md#consulta-el-diagnóstico-de-hcc) y consulta el mensaje de error.

### 3. Conecta el OPPO/Chinoppo

**Antes de conectarlo, comprueba que el control por red está activo.** En un **OPPO UDP-203/205**, pulsa **SETUP** en el mando y entra en **Network Setup → IP Control → On** (opción activada por defecto). Es el ajuste que permite controlar el reproductor desde HCC. Puedes comprobarlo en el [manual de OPPO UDP-203](https://www.oppodigital.com/blu-ray-udp-203/blu-ray-udp-203-Support.aspx). En los **Chinoppo/clones** busca la opción equivalente de control IP/red: según el firmware puede cambiar el nombre o la ubicación del menú; no hemos verificado la ruta exacta en todos los modelos.

Abre **Media Player**. Si aparece **Escanear red**, **púlsalo**: HCC buscará dispositivos de tu red para que no tengas que adivinar sus direcciones. Después pulsa el campo de **IP** y comienza a escribir: verás sugerencias filtradas por **IP, nombre o fabricante**, cuando esos datos estén disponibles. Selecciona tu OPPO/Chinoppo de la lista.

<p align="center">
  <img src="../assets/screenshots/install/03-media-player.png" alt="Pantalla Media Player de Home Cinema Control" width="860"/>
</p>

<p align="center">
  <img src="../assets/screenshots/install/03-media-player-ip-discovery.png" alt="Descubrimiento de IP del OPPO filtrando por nombre" width="860"/>
</p>

Una vez elegida la IP, pulsa **Probar conexión** y guarda. Si no aparece **Escanear red**, escribe la IP manualmente. El descubrimiento depende de que HCC y los dispositivos estén en la misma red local y de que el host permita el escaneo; conserva **`network_mode: host`** en tu archivo Compose. El nombre solo aparecerá si la red o el router lo facilita. Si la prueba falla, revisa [Diagnóstico](solucionar-problemas.md#consulta-el-diagnóstico-de-hcc).

### 4. Conecta tus carpetas de películas

Sigue la [guía de Media Paths](configurar-rutas.md), con capturas. **Usa el navegador «Explorar OPPO» para elegir la carpeta**, pulsa **Probar ruta** y comprueba que aparece **Ruta verificada** en verde. Si algo falla, HCC muestra una explicación y puedes revisar [Diagnóstico](solucionar-problemas.md#consulta-el-diagnóstico-de-hcc).

### 5. TV y receptor AV (opcional)

Entra en **Sala** para conectar tu **TV, el receptor AV o ambos**. Activa cada dispositivo que tengas, elige su modelo y configura la IP. Si aparece **Escanear red**, púlsalo y utiliza las sugerencias al escribir la dirección, igual que en Media Player. Pulsa **Probar conexión** antes de seleccionar entradas o funciones de la TV. Si no tienes receptor AV, configura solo la TV.

<p align="center">
  <img src="../assets/screenshots/install/05-room.png" alt="Configuración de sala con TV y receptor AV" width="860"/>
</p>

<p align="center">
  <img src="../assets/screenshots/install/05-room-ip-discovery.png" alt="Descubrimiento de IP en la pantalla Sala de Home Cinema Control" width="860"/>
</p>

Si las sugerencias no aparecen, puedes escribir la IP manualmente; HCC y los dispositivos deben poder comunicarse en tu red local (mantén **`network_mode: host`**). El nombre visible depende de la información que facilite tu red o router.

En televisores LG, acepta el emparejamiento en pantalla si aparece. En Sony puede ser necesario activar el control IP/PSK en los ajustes de la TV. Si alguna prueba falla, consulta [Diagnóstico](solucionar-problemas.md#consulta-el-diagnóstico-de-hcc); si el receptor cambia solo a TV Audio, consulta [solución de problemas](solucionar-problemas.md#el-avr-cambia-solo-de-entrada).

### 6. Reproduce tu primera película

Abre Emby/Jellyfin en el dispositivo que elegiste en **Media Server** y reproduce una película de una biblioteca que hayas verificado. Comprueba que el OPPO la reproduce. Prueba también pausa, reanudación y parada.

Si algo falla, abre **Diagnóstico** y sigue [solución de problemas](solucionar-problemas.md).

**HCC ya está listo.** ¿Quieres automatizar también las luces? [Home Assistant es opcional](home-assistant.md).
