<div align="center">
  <img src="assets/brand/hcc-logo.png" alt="Home Cinema Control" width="920"/>

<h3>La experiencia integrada para Emby o Jellyfin, OPPO/Chinoppo y tu sala de cine.</h3>

  <p>
    HCC convierte un <strong>Play</strong> en Emby o Jellyfin en una secuencia completa:
    ruta correcta, montaje en el reproductor, cambio de entradas, control de sala y seguimiento de progreso.
  </p>

  <p>
    <img src="https://img.shields.io/github/v/tag/tousled/home-cinema-control?label=version&color=gold&sort=semver" alt="version"/>
    <img src="https://img.shields.io/badge/license-proprietary-lightgrey" alt="proprietary license"/>
    <img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white" alt="docker"/>
  </p>

  <p>
    <a href="README.en.md">English</a> ·
    <a href="INSTALL.md">Instalación</a> ·
    <a href="LICENSE">Licencia</a> ·
    <a href="CHANGELOG.md">Changelog</a>
  </p>
</div>

**[Ver HCC en acción: vídeo de demostración (45 segundos)](assets/videos/hcc-demo.mp4)**

Home Cinema Control conecta tu biblioteca de Emby o Jellyfin con el reproductor y los dispositivos de tu sala. Elige una
película desde tu aplicación habitual: HCC prepara la reproducción en el equipo elegido, coordina las entradas de TV y
receptor AV que hayas configurado y comunica el progreso al servidor multimedia.

El vídeo muestra una sala compatible; no garantiza las mismas funciones en todos los equipos.

> Documentación preparada para la futura **1.5.0**, todavía sin publicar. La última versión estable publicada es
> **1.4.5**. Las funciones de Kodi descritas aquí corresponden a la 1.5.0; instalar `latest` no las añade antes de su
> publicación.

## ¿Qué quieres hacer con HCC?

Elige el recorrido que necesitas:

- [Instalar HCC con Portainer o Docker Compose](INSTALL.md).
- [Configurar Emby/Jellyfin, OPPO o Kodi y realizar la primera reproducción](docs/primeros-pasos.md).
- [Relacionar las carpetas del servidor con las del reproductor](docs/configurar-rutas.md).
- Actualizar sin perder ajustes: [Portainer](docs/actualizar-portainer.md)
  o [Docker Compose](docs/actualizar-compose.md).
- [Recuperar una configuración que parece haber desaparecido](docs/recuperar-configuracion.md).
- [Resolver un problema y pedir ayuda](docs/solucionar-problemas.md).
- Consultar [opciones avanzadas](docs/referencia-avanzada.md)
  o [copias de seguridad y operaciones Docker](docs/operaciones-docker-avanzadas.md).

## Qué ocurre cuando pulsas Play

1. Abres Emby o Jellyfin en el dispositivo que has elegido para que HCC lo supervise y seleccionas una película.
2. HCC comprueba el reproductor y la carpeta configurada antes de preparar la sala y entregar la reproducción.
3. El reproductor abre la película desde tu NAS o carpeta compartida. HCC sigue su estado y actualiza el progreso en el
   servidor multimedia.
4. Al terminar, HCC aplica las acciones de cierre que hayas configurado. Si utilizas Home Assistant, también puede
   comunicarle los eventos de reproducción para tus automatizaciones.

La TV, el receptor AV y Home Assistant son opcionales. Puedes empezar con servidor multimedia, reproductor y carpetas, y
añadir el resto después.

## Con qué funciona

Cada equipo conserva su función: Emby/Jellyfin organiza tu biblioteca y el reproductor abre los archivos de la red.

| Equipo                       | Compatibilidad                                                                                                                                                |
|------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Servidor multimedia          | Emby o Jellyfin; selecciona en HCC el dispositivo cuya reproducción quieres supervisar.                                                                       |
| OPPO/Chinoppo                | OPPO UDP-203/205 y clones con control de red compatible. Acceso a carpetas mediante NFS o SMB; las opciones dependen del firmware.                            |
| Kodi, desde HCC 1.5.0        | Control por HTTP y carpetas NFS/SMB configuradas en Kodi. HCC puede explorarlas, probarlas e iniciar y seguir la reproducción.                                |
| TV y receptor AV, opcionales | LG webOS, Sony BRAVIA y las marcas de receptor disponibles en la pantalla Sala. Trinnov Altitude tiene pruebas de contrato; falta validación con equipo real. |
| Home Assistant, opcional     | Recibe eventos para ejecutar las automatizaciones que tú configures.                                                                                          |

Para Kodi, empieza con un archivo de vídeo habitual, como MKV. La compatibilidad de formatos depende de Kodi y del
dispositivo; no se garantiza la misma experiencia de ISO, carpetas Blu-ray o menús que en OPPO. Las carpetas locales de
Kodi quedan fuera de la 1.5.0 y se reservan para una actualización 1.5.x, sin fecha anunciada. Tampoco se admiten
fuentes `plugin://` ni otros protocolos distintos de NFS/SMB.

HCC conserva los ajustes y las rutas de OPPO y Kodi por separado. Puedes alternar entre ellos y recuperar lo que ya
habías configurado, sin volver a introducir las carpetas.

## Qué necesitas para empezar

Necesitas Docker en un NAS u ordenador de 64 bits, Emby o Jellyfin funcionando y un reproductor capaz de abrir tus
películas desde la red. Todos deben poder comunicarse en tu red local. La guía explica Docker, las credenciales y las
carpetas cuando hacen falta; no necesitas editar archivos de configuración de HCC.

Sigue la [instalación](INSTALL.md) y después los [primeros pasos](docs/primeros-pasos.md). Si ya tienes HCC, conserva el
volumen `home-cinema-control-config` y sigue la guía de actualización de tu instalación.

## Ayuda, privacidad y participación

Abre **Diagnóstico** si falla una conexión o reproducción.
La [guía de solución de problemas](docs/solucionar-problemas.md) explica cómo enviar información útil y contactar con
soporte. Para errores de HCC,
puedes [abrir una incidencia en GitHub](https://github.com/tousled/home-cinema-control/issues/new); para preguntas de
instalación, escribe a [soporte](mailto:llorente.software.solutions@gmail.com).

La [telemetría](docs/telemetry.md) está desactivada por defecto y requiere tu
consentimiento. [Participar](docs/participar.md) permite responder preguntas y proponer mejoras sin cuenta ni correo
electrónico. No es necesario participar para usar HCC y los votos no prometen una implementación.

Consulta la [guía de Home Assistant](docs/home-assistant.md) para añadir luces o escenas a tus propias automatizaciones.
Para preparar recursos compartidos en un NAS o un OPPO,
el [tutorial histórico de AVPasión](https://foro.avpasion.com/t/xnoppo-lo-mejor-de-emby-en-tu-oppo-203-205-y-chinoppo-clones-m9702-m9201-m9203-m9205.2779/page-21#post-73867)
aporta contexto; utiliza los pasos Docker de HCC para instalar esta aplicación.

## Documentación

- [Instalación](INSTALL.md)
- [Guía de instalación en inglés](INSTALL.en.md)
- [Compatibilidad](docs/compatibility.md)
- [Telemetría](docs/telemetry.md)
- [Política de releases](RELEASE_POLICY.md)
- [Historia de releases](RELEASE_HISTORY.md)
- [Changelog](CHANGELOG.md)
- [Soporte](SUPPORT.md)
- [Seguridad](SECURITY.md)

## Licencia

HCC se distribuye bajo la **Home Cinema Control Proprietary Software License 2.0**. No es software open source y esta licencia no concede acceso al código fuente.

Home Cinema Control<br>
Copyright © 2026 Llorente Software Solutions, S.L.<br>
Developed/distributed under the Bytehund brand.

Consulta [LICENSE](LICENSE) para los términos completos.

## Atribución

Home Cinema Control nace inspirado por la idea original de
[Xnoppo](https://github.com/siberian-git/Xnoppo), creado por **siberian-git**, y por el conocimiento compartido en la
comunidad de AVPasion. HCC es una implementación independiente desarrollada sobre una arquitectura nueva.
