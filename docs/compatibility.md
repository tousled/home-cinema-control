# Compatibilidad

La compatibilidad depende del modelo, firmware, red y configuración de cada
sala. La siguiente tabla resume el alcance documentado de HCC.

| Área | Estado |
| --- | --- |
| Emby | Compatible como servidor multimedia |
| Jellyfin | Compatible como servidor multimedia |
| OPPO UDP-203/205 | Compatible mediante la API de control del reproductor |
| Chinoppo M9702/M9201/M9203/M9205 | Compatible cuando expone la API compatible con OPPO |
| Rutas multimedia | NFS o SMB/CIFS por biblioteca, con verificación |
| TV LG WebOS | Cambio de entrada y retorno a la aplicación, si se configura |
| Sony BRAVIA (2013+) | API REST local y Pre-Shared Key; validar el modelo concreto |
| AVR Denon, Marantz, Yamaha, NAD y Onkyo | Control disponible según modelo y configuración |
| Trinnov Altitude | Flujo documentado; validar el hardware concreto antes de depender de él |
| Scripts de sala | Disponibles para equipos que no tengan un adaptador específico |
| Home Assistant | Webhook opcional para eventos de reproducción |
| Docker | Imágenes para linux/amd64 y linux/arm64 |

## Recomendaciones

- Usa una IP estable o una reserva DHCP para el reproductor y los equipos de
  la sala.
- Comprueba que Emby/Jellyfin y el OPPO pueden ver las rutas multimedia que
  vas a mapear.
- Prueba cada mapeo desde HCC antes de reproducir una película.
- Mantén TV y AVR desactivados si no forman parte del flujo de la sala.
- Consulta las notas de la versión instalada antes de actualizar.
