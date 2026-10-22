# Primeros pasos dentro de HCC

[Inicio](../README.md) · [Instalación](../INSTALL.md) · [English](getting-started.en.md)

**HCC ya está funcionando.** Ahora conecta el servidor multimedia, el OPPO/Chinoppo, las carpetas y la **TV y/o receptor AV**. Estas son las pantallas habituales de configuración. **Home Assistant es opcional** y puedes dejarlo para otro momento.

## Configura HCC en cinco pasos

1. **[Media Server](#2-conecta-emby-o-jellyfin):** elige Emby o Jellyfin, introduce los datos del servidor y autoriza la conexión.
2. **[Media Player](#3-conecta-el-oppochinoppo):** encuentra tu OPPO/Chinoppo y pulsa **Probar OPPO**.
3. **[Media Paths](configurar-rutas.md):** conecta al menos una biblioteca siguiendo las capturas.
4. **[Sala: TV y receptor AV](#5-tv-y-receptor-av-opcional):** configura la TV, el receptor o ambos y prueba su conexión. Si no tienes receptor, configura solo la TV.
5. Reproduce una película desde el dispositivo Emby/Jellyfin que hayas elegido.

**Resultado esperado:** el OPPO reproduce tu película. Si falla, abre [solución de problemas](solucionar-problemas.md).

## Capturas de cada pantalla

### 1. Instalación nueva o migración

Si HCC encuentra datos antiguos, puedes importarlos. Si no, elige **Configurar desde cero**. Si HCC ya funcionaba y ahora aparece vacío sin esperarlo, **detente** y sigue [recuperar configuración](recuperar-configuracion.md).

<p align="center">
  <img src="../assets/screenshots/install/01-migration.png" alt="Pantalla de migración de configuración anterior" width="860"/>
</p>

### 2. Conecta Emby o Jellyfin

Abre **Media Server**, elige Emby o Jellyfin, escribe la dirección del servidor y autoriza la conexión. Después elige el dispositivo Emby/Jellyfin que HCC debe controlar.

<p align="center">
  <img src="../assets/screenshots/install/02-media-server.png" alt="Pantalla Media Server de Home Cinema Control" width="860"/>
</p>

<p align="center">
  <img src="../assets/screenshots/install/02-media-server-pending.png" alt="Media Server con Jellyfin seleccionado pero pendiente de autorización" width="860"/>
</p>

Si ves el estado **pendiente**, termina la autorización antes de continuar. HCC necesita acceder a las bibliotecas que ya tienes en Emby/Jellyfin.

### 3. Conecta el OPPO/Chinoppo

Abre **Media Player**. Introduce la IP del reproductor o utiliza **Escanear red**, si aparece el botón. Pulsa **Probar OPPO**.

<p align="center">
  <img src="../assets/screenshots/install/03-media-player.png" alt="Pantalla Media Player de Home Cinema Control" width="860"/>
</p>

<p align="center">
  <img src="../assets/screenshots/install/03-media-player-ip-discovery.png" alt="Descubrimiento de IP del OPPO filtrando por nombre" width="860"/>
</p>

Si falla, comprueba primero que el reproductor está encendido y en la misma red local. En [solución de problemas](solucionar-problemas.md) encontrarás más comprobaciones.

### 4. Conecta tus carpetas de películas

Sigue la [guía de Media Paths](configurar-rutas.md), con capturas. El OPPO debe poder abrir antes las carpetas compartidas del NAS por SMB o NFS. Cuando HCC confirme una ruta como verificada, vuelve aquí.

### 5. TV y receptor AV (opcional)

Puedes saltarte **Sala** y reproducir películas sin automatizar la TV ni el receptor. Si quieres que HCC cambie las entradas HDMI automáticamente, activa y prueba los dispositivos desde **Sala**.

<p align="center">
  <img src="../assets/screenshots/install/05-room.png" alt="Configuración de sala con TV y receptor AV" width="860"/>
</p>

<p align="center">
  <img src="../assets/screenshots/install/05-room-ip-discovery.png" alt="Descubrimiento de IP en la pantalla Sala de Home Cinema Control" width="860"/>
</p>

En televisores LG, acepta el emparejamiento en la pantalla si aparece. En Sony puede ser necesario activar el control IP/PSK desde los ajustes de la TV. Si el receptor cambia solo a TV Audio, consulta [solución de problemas](solucionar-problemas.md).

### 6. Reproduce tu primera película

Abre Emby/Jellyfin en el dispositivo que elegiste en **Media Server** y reproduce una película de una biblioteca que hayas verificado. Comprueba que el OPPO la reproduce. Prueba también pausa, reanudación y parada.

Si algo falla, abre **Diagnóstico** y sigue [solución de problemas](solucionar-problemas.md).

**HCC ya está listo.** ¿Quieres automatizar también las luces? [Home Assistant es opcional](home-assistant.md).
