# Telemetría y privacidad

HCC incluye una telemetría opcional para medir estabilidad, entender qué
integraciones se utilizan y priorizar el roadmap. Está desactivada por defecto
y se activa desde la pantalla de Diagnóstico.

## Qué puede enviar

Cuando está activada, HCC envía datos mínimos y anónimos como:

- versión instalada;
- proveedor multimedia seleccionado;
- estado configurado de TV y receptor AV;
- resultado general de intentos de reproducción;
- eventos técnicos anónimos necesarios para agrupar fallos repetidos;
- preferencias de roadmap que el usuario decida enviar.

La instalación utiliza un identificador aleatorio que no identifica
personalmente al usuario.

## Qué nunca envía

La telemetría no envía:

- direcciones IP, nombres de host ni direcciones de red;
- rutas de archivos, bibliotecas ni nombres de carpetas;
- títulos, metadatos o nombres de servidores;
- contraseñas, tokens, claves ni credenciales;
- logs completos, scripts, comandos personalizados ni contenido multimedia;
- identificadores o datos del webhook de Home Assistant.

Si el servicio de telemetría no está disponible, los eventos filtrados pueden
quedar temporalmente en la configuración local para reintentarse más tarde.

## Control del usuario

Puedes activar o desactivar la telemetría, regenerar el identificador anónimo
y vaciar los eventos pendientes desde la pantalla de Diagnóstico. Desactivarla
no afecta a la reproducción ni a las integraciones de HCC.

Para preguntas sobre privacidad, abre un issue sin adjuntar configuración,
credenciales ni datos de red.
