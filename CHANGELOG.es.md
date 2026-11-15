# Registro de cambios

**Español** · [English](CHANGELOG.md)

Las mejoras de HCC, explicadas para quienes quieren disfrutar de su cine en casa.

## [Unreleased]

- **Reproduce desde Kodi.** Conéctalo por HTTP y usa bibliotecas NFS o SMB desde Emby o Jellyfin.
  La prueba de conexión explica los errores de acceso y red. El perfil de OPPO conserva sus rutas
  y Kodi guarda sus credenciales por separado. Las carpetas locales, las fuentes de complementos
  y la experiencia equivalente con menús Blu-ray quedan fuera de esta versión.
- **Configura la sala paso a paso.** El asistente prepara los ajustes de TV y receptor para que
  puedas revisarlos. Las guías en español e inglés explican cómo reproducir por primera vez,
  relacionar carpetas y configurar la sala y Home Assistant si los usas.
- **Entérate de qué ha pasado al actualizar.** Si falla la petición a Portainer, HCC muestra el
  error. Si se corta la conexión, sigue comprobando la versión instalada. Las consultas de
  versión respetan los límites de GitHub.
- **Consulta las incidencias que afectan a la reproducción.** Una lista de sesiones vacía en
  Emby o Jellyfin, o que la aplicación deje de estar en pantalla durante la reproducción en
  el OPPO, ya no genera un aviso incorrecto de dispositivo ausente.

## [1.4.6] - 2026-11-15

- **Vuelve a lo que estabas viendo.** El OPPO o Chinoppo llega con más fiabilidad
  al punto guardado en Emby o Jellyfin, aunque tarde un momento en aceptar el salto. Si activas
  «Repetir los últimos 2 segundos al continuar», puedes recuperar el hilo al retomar un archivo
  de vídeo compatible. La reproducción empieza hasta dos segundos antes de donde te quedaste. La opción está
  desactivada por defecto.
- **Tu progreso, siempre al día.** HCC guarda mejor tu avance al parar o cambiar de título y conserva
  el punto guardado si paras un Blu-ray antes de que empiece la reproducción. Al volver a Jellyfin, evita
  retrocesos inesperados y muestra la despedida con más fiabilidad.
- **Retoma tus Blu-ray aunque el menú solo ofrezca «Reproducir».** Antes, algunos discos empezaban
  desde cero aunque eligieras «Continuar» en Emby o Jellyfin. Con la reanudación experimental
  activada, HCC intenta retomar la reproducción donde te quedaste. Para empezar de cero, elige
  «Reproducir desde el principio» en Emby o Jellyfin.

## [1.4.5] - 2026-11-04

- **Tus películas Blu-ray, sin problemas de reproducción.** Algunas películas guardadas en carpetas Blu-ray o UHD Blu-ray no se iniciaban correctamente desde Jellyfin. HCC ahora reconoce la estructura del disco y permite reproducirlas en el OPPO/Chinoppo.

## [1.4.4] - 2026-11-02

- **Cambia de película sin sorpresas.** Al empezar otro contenido, el OPPO ya no se apaga inesperadamente.
- **Una transición más segura hacia tu sala de cine.** Si el reproductor o la ruta no están preparados, HCC evita cambios molestos en la TV y el receptor y deja en la aplicación original el contenido que no puede gestionar.
- **Avisos que se entienden.** Si algo impide empezar la reproducción, HCC explica qué revisar sin abrumarte con información técnica.

## [1.4.3] - 2026-10-28

- **Participa en el futuro de HCC.** La nueva sección «Participa» te permite votar ideas y compartir sugerencias cuando quieras.
- **Diagnósticos más útiles.** Es más fácil entender qué ocurre si falla una reproducción, manteniendo siempre bajo tu control el envío opcional de datos técnicos.

## [1.4.2] - 2026-10-23

- **Instalar y actualizar HCC es más sencillo.** Las guías paso a paso te ayudan a empezar o actualizar sin perder tu configuración.
- **Menos interrupciones al empezar.** HCC sale del salvapantallas del OPPO antes de iniciar la película.

## [1.4.1] - 2026-10-17

- **Tu lista «Continuar viendo», siempre en orden.** HCC conserva mejor los puntos de reanudación cuando detienes una película o no llega a iniciarse.
- **Audio y subtítulos como los elegiste.** Mejor selección de pistas desde Emby y arranque más fiable en el OPPO.
- **Prepara la sala desde el primer momento.** Home Assistant puede reaccionar en cuanto HCC detecta que vas a reproducir contenido.

## [1.4.0] - 2026-10-12

- **Tu sala de cine cobra vida.** Conecta HCC con Home Assistant para automatizar luces y otros elementos cuando empieza, se pausa o termina una película.
- **Una experiencia más fiable.** Mejor coordinación de reproducción, diagnósticos y configuración de Home Assistant.

## [1.3.3] - 2026-10-09

- **Reproducción de archivos STRM corregida.** Los contenidos STRM de Emby vuelven a localizarse correctamente al enviarlos al OPPO.

## [1.3.2] - 2026-10-09

- **Rutas multimedia más fiables.** HCC encuentra las carpetas compartidas aunque Windows y Linux utilicen separadores distintos.

## [1.3.1] - 2026-09-17

- **Menos interrupciones al reproducir.** Mayor fiabilidad con las pistas de audio y subtítulos, al volver a Emby/Jellyfin y cuando un contenido no está disponible.

## [1.3.0] - 2026-08-13

- **Trinnov Altitude se suma a tu sala de cine.** Llega el control nativo del receptor, con un emparejamiento LG más fiable y una detección de reproducción más precisa.

## [1.2.1] - 2026-07-08

- **Finales más precisos y avisos más claros.** HCC detecta mejor cuándo termina el contenido en el OPPO y muestra de forma más sencilla si hay actualizaciones.

## [1.2.0] - 2026-07-07

- **Llega la compatibilidad con Sony BRAVIA.** Configura televisores Sony compatibles y comparte diagnósticos de forma sencilla cuando necesites ayuda.

## [1.1.4] - 2026-06-30

- **Reproducción SMB más fiable.** Corregido un problema que podía dejar el OPPO sin responder después de reproducir contenido por SMB.

## [1.1.3] - 2026-06-29

- **Tu opinión cuenta para el futuro de HCC.** Puedes compartir sugerencias y datos opcionales para orientar las próximas mejoras. También se ha perfeccionado la detección de entradas del receptor.

## [1.1.2] - 2026-06-27

- **Copia tus diagnósticos sin complicaciones.** Los botones para copiar información funcionan en más navegadores.

## [1.1.1] - 2026-06-27

- **Más compatibilidad con Jellyfin y registros más fáciles de compartir.** Autenticación actualizada y controles de logs mejorados en el móvil.

## [1.1.0] - 2026-06-26

- **Emby y Jellyfin en una misma experiencia.** Elige tu servidor multimedia y configura bibliotecas, dispositivos y rutas de forma más sencilla.
- **Una reproducción más fiable con Jellyfin.** Mejoras en los avisos, la gestión de sesiones y el regreso desde el OPPO.

## [1.0.5] - 2026-06-22

- **Una sesión de cine sin sobresaltos.** Más fiabilidad al iniciar películas, mostrar avisos y gestionar carpetas compartidas.

## [1.0.4] - 2026-06-21

- **Los Blu-ray terminan como deben.** Mejor gestión de contenidos vistos y de la parada del OPPO al finalizar un disco.

## [1.0.3] - 2026-06-21

- **Conexiones al OPPO más resistentes.** Mejor exploración de carpetas, recuperación de recursos de red y comportamiento durante las pausas y el salvapantallas.

## [1.0.2] - 2026-06-20

- **Configuración de Emby más fiable.** Mejor protección de las credenciales y menos falsos errores al conectar el servidor.

## [1.0.0] - 2026-06-19

- **Bienvenido a HCC 1.0.** Una interfaz renovada y más cinematográfica, con configuración, diagnósticos y actualizaciones más claros.

## [0.9.1] - 2026-06-18

- **Toda la reproducción de un vistazo.** Un mando OPPO más completo, información del contenido en pantalla y guías de instalación mejoradas en ambos idiomas.

## [0.9.0] - 2026-06-18

- **De la biblioteca al reproductor, sin complicaciones.** Configuración guiada de rutas, diagnósticos claros y compatibilidad con NFS y SMB.

## [0.8.1] - 2026-06-13

- **Actualiza HCC con más confianza.** Consulta nuevas versiones, inicia actualizaciones y encuentra instrucciones para volver a una versión anterior.

## [0.8.0] - 2026-06-13

- **Un HCC renovado y más fácil de usar.** Nueva interfaz web, configuración guiada, detección de dispositivos y navegación adaptada al móvil.

## [0.7.2] - 2026-06-09

- **Instalaciones Docker más fiables.** Solucionado un problema que impedía desplegar HCC en algunos entornos Docker y Portainer.

## [0.7.1] - 2026-06-09

- **Mejor selección de audio en discos Blu-ray.** HCC puede elegir la pista correcta cuando termina el menú del disco y empieza la película.

## [0.7.0] - 2026-06-09

- **Seguimiento de reproducción más preciso.** Mejor detección de lo que reproduce el OPPO y recuperación cuando se interrumpe la comunicación.

## [0.6.1] - 2026-06-06

- **Los registros aparecen cuando los necesitas.** Docker y Portainer muestran los mensajes de HCC sin retrasos innecesarios.

## [0.6.0] - 2026-06-06

- **OPPO y Emby, mejor sincronizados.** El seguimiento opcional informa de pausas, reanudaciones y cambios de audio o subtítulos.

## [0.5.1] - 2026-06-01

- **Sin esperas al terminar la película.** HCC detecta mejor el final del contenido y devuelve la sala a su estado habitual.

## [0.5.0] - 2026-05-31

- **Tus dispositivos, trabajando juntos.** Reproducción, cambio de entradas, control remoto y recuperación de la sala en un único flujo.

## [0.4.0] - 2026-05-23

- **Más receptores compatibles.** Control de Denon, Marantz, NAD, Onkyo y Yamaha, además de opciones mediante scripts.

## [0.3.0] - 2026-05-23

- **Paradas y subtítulos más precisos.** Mejor detección del OPPO para evitar pérdidas de progreso y problemas al seleccionar subtítulos.

## [0.2.0] - 2026-05-22

- **HCC llega a Docker y Portainer.** Configuración persistente e instalación más sencilla en NAS.

## [0.1.1] - 2026-05-22

- **Una pequeña actualización de mantenimiento.** Registros de diagnóstico más claros y mejor protección de los datos sensibles.

## [0.1.0] - 2026-05-22

- **El comienzo de HCC.** Primera versión funcional y mejoras de conexión con Emby.
