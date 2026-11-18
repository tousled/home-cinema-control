# Registro de cambios

**Español** · [English](CHANGELOG.en.md)

Las mejoras de HCC, explicadas para quienes quieren disfrutar de su cine en casa.

## [Unreleased]

### Añadido

- **Kodi llega a HCC.** Ahora también puedes utilizar Kodi para reproducir tus películas y series desde Emby o Jellyfin, mediante carpetas compartidas NFS o SMB. HCC coordina la reproducción con tu televisor y receptor, permite controlar Kodi desde su mando web e incorpora una configuración guiada para ponerlo todo en marcha. Incluye guías de instalación en español e inglés.
- **Enciende y apaga tu OPPO automáticamente.** HCC puede encender tu OPPO o Chinoppo cuando empiezas una película desde Emby o Jellyfin y apagarlo cuando terminas. Puedes elegir cuánto tiempo debe esperar antes de apagarse; si empiezas otra reproducción durante ese tiempo, el apagado se cancela. Esta función es experimental y depende de las capacidades de tu reproductor.
- **Configura tu sala de cine más fácilmente.** Los asistentes te ayudan a conectar y configurar tus dispositivos, incluido el televisor, el receptor y Home Assistant. Puedes revisar los ajustes y cancelar antes de guardarlos.

### Mejorado

- **Un diagnóstico que te cuenta qué está pasando.** Ahora puedes consultar varias incidencias al mismo tiempo, identificar cuáles requieren atención y ver cuáles siguen activas, se han resuelto o has descartado. El historial conserva la información de los problemas anteriores.
- **Sigue el progreso de las actualizaciones.** Al actualizar HCC desde la aplicación, verás una cuenta atrás, cuántas veces se ha comprobado la nueva versión y si HCC responde durante el proceso. Así podrás distinguir si la actualización ha terminado o todavía está pendiente de confirmación.
- **Un control más claro de los diagnósticos automáticos.** Hemos rediseñado la opción para compartir diagnósticos de forma voluntaria. Ahora es más fácil encontrarla, entender si está activada y cambiar tu decisión, tanto desde el ordenador como desde el móvil.
- **Cambia la dirección de tu servidor sin perder la conexión.** Si necesitas modificar la dirección de Emby o Jellyfin, HCC mantiene funcionando la conexión anterior hasta que autorices la nueva. Si algo falla, podrás seguir utilizando tu servidor como antes.
- **Actualizaciones más fiables, incluso si se interrumpe la conexión.** Si Portainer rechaza una solicitud de actualización, HCC te avisa. Y si la aplicación deja de responder temporalmente durante el proceso, continúa comprobando la versión instalada para confirmar el resultado.
- **Avanza y retrocede en tus Blu-ray sin perder tu progreso.** Puedes desplazarte por la película desde la barra de progreso de Emby o Jellyfin cuando el disco y el reproductor lo permiten. Además, HCC protege el punto guardado cuando aparecen los menús del Blu-ray, evitando que pierdas tu avance antes de volver a la película.

### Corregido

- **Menos avisos incorrectos en Emby y Jellyfin.** Cuando el servidor devuelve temporalmente una lista de sesiones vacía, HCC ya no muestra un aviso engañoso de dispositivo ausente.
- **Sin falsas alarmas al salir de la aplicación.** Si sales de Emby o Jellyfin mientras el OPPO continúa reproduciendo, HCC ya no muestra incorrectamente un aviso indicando que el dispositivo ha desaparecido.
- **Audio y subtítulos correctos al elegir otra versión en Jellyfin.** Cuando una película tiene varias versiones, HCC utiliza las pistas de audio y subtítulos correspondientes al archivo que has elegido, evitando seleccionar por error las de otra versión.

## [1.4.6] - 2026-11-15

### Añadido

- **Recupera el hilo, dos segundos antes.** Activa «Repetir los últimos 2 segundos al continuar» para retomar
  un archivo de vídeo compatible hasta dos segundos antes de donde te quedaste. La opción está desactivada
  por defecto.

### Corregido

- **Vuelve a lo que estabas viendo.** El OPPO o Chinoppo llega con más fiabilidad
  al punto guardado en Emby o Jellyfin, aunque tarde un momento en aceptar el salto.
- **Tu progreso, siempre al día.** HCC guarda mejor tu avance al parar o cambiar de título y conserva
  el punto guardado si paras un Blu-ray antes de que empiece la reproducción. Al volver a Jellyfin, evita
  retrocesos inesperados y muestra la despedida con más fiabilidad.
- **Retoma tus Blu-ray aunque el menú solo ofrezca «Reproducir».** Antes, algunos discos empezaban
  desde cero aunque eligieras «Continuar» en Emby o Jellyfin. Con la reanudación experimental
  activada, HCC intenta retomar la reproducción donde te quedaste. Para empezar de cero, elige
  «Reproducir desde el principio» en Emby o Jellyfin.

## [1.4.5] - 2026-11-04

### Corregido

- **Tus películas Blu-ray, sin problemas de reproducción.** Algunas películas guardadas en carpetas Blu-ray o UHD
  Blu-ray no se iniciaban correctamente desde Jellyfin. HCC ahora reconoce la estructura del disco y permite
  reproducirlas en el OPPO/Chinoppo.

## [1.4.4] - 2026-11-02

### Mejorado

- **Una transición más segura hacia tu sala de cine.** Si el reproductor o la ruta no están preparados, HCC evita
  cambios molestos en la TV y el receptor y deja en la aplicación original el contenido que no puede gestionar.
- **Avisos que se entienden.** Si algo impide empezar la reproducción, HCC explica qué revisar sin abrumarte con
  información técnica.

### Corregido

- **Cambia de película sin sorpresas.** Al empezar otro contenido, el OPPO ya no se apaga inesperadamente.

## [1.4.3] - 2026-10-28

### Añadido

- **Participa en el futuro de HCC.** La nueva sección «Participa» te permite votar ideas y compartir sugerencias cuando
  quieras.

### Mejorado

- **Diagnósticos más útiles.** Es más fácil entender qué ocurre si falla una reproducción, manteniendo siempre bajo tu
  control el envío opcional de datos técnicos.

## [1.4.2] - 2026-10-23

### Mejorado

- **Instalar y actualizar HCC es más sencillo.** Las guías paso a paso te ayudan a empezar o actualizar sin perder tu
  configuración.

### Corregido

- **Menos interrupciones al empezar.** HCC sale del salvapantallas del OPPO antes de iniciar la película.

## [1.4.1] - 2026-10-17

### Añadido

- **Prepara la sala desde el primer momento.** Home Assistant puede reaccionar en cuanto HCC detecta que vas a
  reproducir contenido.

### Mejorado

- **Audio y subtítulos como los elegiste.** Mejor selección de pistas desde Emby y arranque más fiable en el OPPO.

### Corregido

- **Tu lista «Continuar viendo», siempre en orden.** HCC conserva mejor los puntos de reanudación cuando detienes una
  película o no llega a iniciarse.

## [1.4.0] - 2026-10-12

### Añadido

- **Tu sala de cine cobra vida.** Conecta HCC con Home Assistant para automatizar luces y otros elementos cuando
  empieza, se pausa o termina una película.

### Mejorado

- **Una experiencia más fiable.** Mejor coordinación de reproducción, diagnósticos y configuración de Home Assistant.

## [1.3.3] - 2026-10-09

### Corregido

- **Reproducción de archivos STRM corregida.** Los contenidos STRM de Emby vuelven a localizarse correctamente al
  enviarlos al OPPO.

## [1.3.2] - 2026-10-09

### Corregido

- **Rutas multimedia más fiables.** HCC encuentra las carpetas compartidas aunque Windows y Linux utilicen separadores
  distintos.

## [1.3.1] - 2026-09-17

### Mejorado

- **Menos interrupciones al reproducir.** Mayor fiabilidad con las pistas de audio y subtítulos, al volver a
  Emby/Jellyfin y cuando un contenido no está disponible.

## [1.3.0] - 2026-08-13

### Añadido

- **Trinnov Altitude se suma a tu sala de cine.** Llega el control nativo del receptor, con un emparejamiento LG más
  fiable y una detección de reproducción más precisa.

## [1.2.1] - 2026-07-08

### Mejorado

- **Finales más precisos y avisos más claros.** HCC detecta mejor cuándo termina el contenido en el OPPO y muestra de
  forma más sencilla si hay actualizaciones.

## [1.2.0] - 2026-07-07

### Añadido

- **Llega la compatibilidad con Sony BRAVIA.** Configura televisores Sony compatibles y comparte diagnósticos de forma
  sencilla cuando necesites ayuda.

## [1.1.4] - 2026-06-30

### Corregido

- **Reproducción SMB más fiable.** Corregido un problema que podía dejar el OPPO sin responder después de reproducir
  contenido por SMB.

## [1.1.3] - 2026-06-29

### Añadido

- **Tu opinión cuenta para el futuro de HCC.** Puedes compartir sugerencias y datos opcionales para orientar las
  próximas mejoras. También se ha perfeccionado la detección de entradas del receptor.

## [1.1.2] - 2026-06-27

### Corregido

- **Copia tus diagnósticos sin complicaciones.** Los botones para copiar información funcionan en más navegadores.

## [1.1.1] - 2026-06-27

### Corregido

- **Más compatibilidad con Jellyfin y registros más fáciles de compartir.** Autenticación actualizada y controles de
  logs mejorados en el móvil.

## [1.1.0] - 2026-06-26

### Añadido

- **Emby y Jellyfin en una misma experiencia.** Elige tu servidor multimedia y configura bibliotecas, dispositivos y
  rutas de forma más sencilla.

### Corregido

- **Una reproducción más fiable con Jellyfin.** Mejoras en los avisos, la gestión de sesiones y el regreso desde el
  OPPO.

## [1.0.5] - 2026-06-22

### Mejorado

- **Una sesión de cine sin sobresaltos.** Más fiabilidad al iniciar películas, mostrar avisos y gestionar carpetas
  compartidas.

## [1.0.4] - 2026-06-21

### Corregido

- **Los Blu-ray terminan como deben.** Mejor gestión de contenidos vistos y de la parada del OPPO al finalizar un disco.

## [1.0.3] - 2026-06-21

### Mejorado

- **Conexiones al OPPO más resistentes.** Mejor exploración de carpetas, recuperación de recursos de red y
  comportamiento durante las pausas y el salvapantallas.

## [1.0.2] - 2026-06-20

### Corregido

- **Configuración de Emby más fiable.** Mejor protección de las credenciales y menos falsos errores al conectar el
  servidor.

## [1.0.0] - 2026-06-19

### Añadido

- **Bienvenido a HCC 1.0.** Una interfaz renovada y más cinematográfica, con configuración, diagnósticos y
  actualizaciones más claros.

## [0.9.1] - 2026-06-18

### Añadido

- **Toda la reproducción de un vistazo.** Un mando OPPO más completo, información del contenido en pantalla y guías de
  instalación mejoradas en ambos idiomas.

## [0.9.0] - 2026-06-18

### Añadido

- **De la biblioteca al reproductor, sin complicaciones.** Configuración guiada de rutas, diagnósticos claros y
  compatibilidad con NFS y SMB.

## [0.8.1] - 2026-06-13

### Añadido

- **Actualiza HCC con más confianza.** Consulta nuevas versiones, inicia actualizaciones y encuentra instrucciones para
  volver a una versión anterior.

## [0.8.0] - 2026-06-13

### Añadido

- **Un HCC renovado y más fácil de usar.** Nueva interfaz web, configuración guiada, detección de dispositivos y
  navegación adaptada al móvil.

## [0.7.2] - 2026-06-09

### Corregido

- **Instalaciones Docker más fiables.** Solucionado un problema que impedía desplegar HCC en algunos entornos Docker y
  Portainer.

## [0.7.1] - 2026-06-09

### Corregido

- **Mejor selección de audio en discos Blu-ray.** HCC puede elegir la pista correcta cuando termina el menú del disco y
  empieza la película.

## [0.7.0] - 2026-06-09

### Mejorado

- **Seguimiento de reproducción más preciso.** Mejor detección de lo que reproduce el OPPO y recuperación cuando se
  interrumpe la comunicación.

## [0.6.1] - 2026-06-06

### Corregido

- **Los registros aparecen cuando los necesitas.** Docker y Portainer muestran los mensajes de HCC sin retrasos
  innecesarios.

## [0.6.0] - 2026-06-06

### Añadido

- **OPPO y Emby, mejor sincronizados.** El seguimiento opcional informa de pausas, reanudaciones y cambios de audio o
  subtítulos.

## [0.5.1] - 2026-06-01

### Corregido

- **Sin esperas al terminar la película.** HCC detecta mejor el final del contenido y devuelve la sala a su estado
  habitual.

## [0.5.0] - 2026-05-31

### Añadido

- **Tus dispositivos, trabajando juntos.** Reproducción, cambio de entradas, control remoto y recuperación de la sala en
  un único flujo.

## [0.4.0] - 2026-05-23

### Añadido

- **Más receptores compatibles.** Control de Denon, Marantz, NAD, Onkyo y Yamaha, además de opciones mediante scripts.

## [0.3.0] - 2026-05-23

### Corregido

- **Paradas y subtítulos más precisos.** Mejor detección del OPPO para evitar pérdidas de progreso y problemas al
  seleccionar subtítulos.

## [0.2.0] - 2026-05-22

### Añadido

- **HCC llega a Docker y Portainer.** Configuración persistente e instalación más sencilla en NAS.

## [0.1.1] - 2026-05-22

### Mejorado

- **Una pequeña actualización de mantenimiento.** Registros de diagnóstico más claros y mejor protección de los datos
  sensibles.

## [0.1.0] - 2026-05-22

### Añadido

- **El comienzo de HCC.** Primera versión funcional y mejoras de conexión con Emby.
