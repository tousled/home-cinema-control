# Telemetría seudónima y opcional

[English](telemetry.en.md) · [Cómo participar](participar.md)

La telemetría de HCC es opcional y está desactivada por defecto. Cuando se activa, HCC envía señales técnicas
mínimas para medir adopción y fiabilidad de reproducción. Usa un código seudónimo de instalación para relacionar
avisos de una misma instalación sin conocer la identidad personal de quien la usa.

En la reedición corregida de 1.4.2, las imágenes oficiales incluyen el destino y la clave pública de ingesta.
Basta con activar la telemetría en HCC; no es necesario añadir variables en Compose o Portainer. Esa clave distribuida no concede
acceso administrativo. Para un hub propio, las variables `HCC_TELEMETRY_ENDPOINT_URL` y
`HCC_TELEMETRY_INGEST_KEY` permiten sustituir el destino; también se admiten `telemetry.endpoint_url` y
`telemetry.ingest_key` en la configuración. La prioridad es entorno del despliegue, configuración e imagen.

La imagen original de 1.4.2 omitió esos valores y se ha retirado. Al actualizar desde 1.4.1 o 1.4.2, HCC conserva
el consentimiento y el identificador seudónimo existente, y reintenta los eventos pendientes al arrancar. No vuelve
a preguntar si ya existe una decisión; si no existe, muestra la explicación y solicita una elección. La cola conserva como
máximo 100 eventos durante siete días con la configuración predeterminada; los eventos descartados no se
pueden recuperar. La actualización no activa telemetría para quienes la mantienen desactivada.

Los eventos de reproducción nuevos incluyen:

- `event_id`: identificador aleatorio del evento individual, usado para deduplicar reintentos.
- `attempt_id`: identificador aleatorio de una reproducción completa, compartido por el intento, el inicio, el fallo y la finalización.
- `component`: componente diagnosticado, como `oppo`, `path`, `av` o `media_server`.
- `error_code`: código diagnóstico normalizado cuando existe.
- `operation` y `failure_kind`: operación y fase técnica permitidas cuando HCC las conoce; en otro caso se marca
  `failure_kind: unknown`, sin enviar excepciones ni texto libre.
- `occurred_at`: instante UTC en que HCC produjo el evento. El hub lo mantiene
  separado de la hora a la que recibió el envío cuando la versión desplegada
  del receptor admite el contrato v3. HCC conserva el valor incluso cuando
  reintenta el payload desde su cola local.

`/ping` envía un snapshot técnico al activar la telemetría o cuando cambia una
configuración permitida. No se usa como latido periódico y los snapshots
equivalentes se coalescen. `/heartbeat` envía como máximo un contacto mínimo
por 24 horas, solo mientras existe consentimiento vigente. No incluye
configuración ni hechos de reproducción. `last_heartbeat_at` es el último
heartbeat entregado con éxito, no un intento fallido ni la hora de un evento.

Al desactivar la telemetría, HCC bloquea nuevos envíos, vacía la cola persistente
y el trabajo asíncrono pendiente, y realiza un único intento *best effort* de
enviar `install_opt_out` asociado al mismo identificador seudónimo. Ese hecho
no se guarda localmente ni se reintenta; si no hay conexión, puede no llegar.
Sirve para registrar una revocación explícita, no para borrar el histórico ni
para concluir que HCC se ha desinstalado. La falta de contacto tampoco acredita
desinstalación, reproducción o uso del cine.

Cuando Home Assistant está activado y tiene URL y webhook configurados, el
snapshot añade únicamente `home_assistant` a `features_enabled`. No transmite
la URL, el identificador del webhook, tokens ni ninguna otra configuración de
Home Assistant. Una configuración parcial no se contabiliza.

El receptor debe desplegarse antes que este contrato de productor: acepta
productores legacy que publican su antiguo heartbeat por `/ping`, y productores
nuevos que usan `/heartbeat`, `/ping` y `/event`. Debe conservar `event_id`,
`attempt_id` y `occurred_at`, y registrar `install_opt_out` como revocación
observada sin eliminar el histórico. Hasta entonces, el dashboard solo puede
ordenar por recepción. No debe inferirse cronología de origen ni latencia de
entrega si el receptor no persiste ambas horas.

### Comentarios voluntarios

En «Participa», la persona puede escribir como máximo 400 caracteres y pulsar
**Enviar comentario**. Ese acto es el único que encola el evento
`suggestion_submitted`; nunca se obtiene automáticamente de diagnósticos,
logs ni campos escritos sin enviar. Requiere consentimiento activo y se usa
el mismo canal protegido y la misma cola de reintentos de HCC. El texto puede
permanecer temporalmente en la cola local y se conserva en el receptor para
el administrador; no se incluye en indicadores públicos.
No deben introducirse IP, rutas, nombres, credenciales ni datos personales.
La revocación cancela los envíos pendientes, pero no borra lo ya recibido.

### Despliegue coordinado

1. Publicar primero una revisión aprobada de `hcc-telemetry-app` que migre el
   almacenamiento sin reescribir eventos y acepte tanto los cuerpos legacy como
   los nuevos. Con datos sintéticos, comprobar `/ping`, `/heartbeat`, un
   `playback_failed` con y sin diagnóstico, duplicados y `install_opt_out`.
2. Confirmar su CI y que el dashboard conserva los hechos históricos, muestra
   la revocación como tal y nunca interpreta el silencio como desinstalación.
3. Publicar después una revisión aprobada de HCC y ejecutar sus pruebas de
   cola, actualización, concurrencia de revocación y compatibilidad. No se
   activa ni publica una imagen 1.4.3 como parte de este procedimiento.
4. Tras el despliegue autorizado, comprobar con una instalación de prueba que
   el opt-in conserva su identificador, `/ping` solo cambia ante un snapshot
   relevante, el heartbeat llega a `/heartbeat` y la revocación no deja cola.

La política del contrato v3 para un receptor compatible es conservar siempre
la hora de recepción y usar la de origen solo si tiene zona horaria, formato
válido y un rango razonable frente a la recepción. Una hora ausente o inválida
no descarta el hecho: queda sin hora de origen y se ordena por recepción. HCC
genera horas UTC y nunca las regenera durante un reintento.

### Significado de reproducción y activación

- `playback_attempted` acredita que HCC admitió un handoff; no acredita que el
  reproductor comenzase.
- `playback_started` acredita que HCC observó el inicio técnico en el
  reproductor. Es la primera señal válida para una primera reproducción
  iniciada con éxito.
- `playback_failed` acredita un fallo técnico del handoff; la ausencia de un
  terminal no equivale a un fallo.
- `playback_finished` acredita una reproducción completada para HCC: el flujo
  iniciado se cerró correctamente, tanto si la película terminó y volvió a
  Emby como si el usuario la detuvo durante los créditos. No distingue el
  motivo natural/manual ni permite afirmar la posición exacta de visionado.
- Las paradas y su causa se mantienen hoy como estado local: no se envía un
  evento nuevo porque el hub desplegado no tiene ese contrato.

El campo `setup_completed` del snapshot solo resume que la configuración
necesaria parece presente. No es una métrica de activación: para medir una
instalación activada deben distinguirse al menos el primer
`playback_attempted` y el primer `playback_started` correlacionado. Los pings
solo indican contacto opt-in y no sirven para inferir actividad o retención.

Los rechazos antes del handoff usan el evento `playback_rejected`. Sólo incluyen el proveedor (`provider`), el componente
(`component`) y el código diagnóstico (`error_code`). Se emiten cuando HCC ha detectado una reproducción en el dispositivo
monitorizado pero la bloquea antes de contactar con el OPPO, por ejemplo por una ruta no verificada. Un dispositivo
monitorizado que no aparece en un sondeo no cuenta como intento de reproducción y sólo genera un diagnóstico local.

El hub relaciona estos eventos con el `instance_hash`, un hash HMAC del identificador local de instalación. Esto permite
ver qué instalación tiene fallos repetidos sin guardar el UUID original. Es un
identificador seudónimo y estable dentro del hub, no una garantía de anonimato.

Los diagnósticos se limitan a códigos y vocabularios técnicos cerrados. HCC no
envía excepciones, comentarios libres, rutas, archivos, IPs, tokens ni otros
datos sensibles. Cuando no conoce un código, conserva solo el componente y la
operación o fase segura disponible, indicando explícitamente lo desconocido.

No se envían títulos, rutas, IPs, tokens, URLs, nombres de servidores, bibliotecas, IDs del servidor multimedia,
credenciales, logs, scripts ni comandos personalizados. Los IDs de sesión y los identificadores de contenido internos
de HCC tampoco se incluyen en el payload de red.

Los eventos históricos anteriores a este contrato pueden aparecer como `legacy`: tienen instalación y categoría
agregable, pero no pueden enlazarse a un intento concreto.

### Respuestas estructuradas de 1.4.3

`question_answer_submitted` reutiliza el sobre v4 de `/event`. Exige `event_id`
y una fecha de origen `occurred_at` que coincide con `attributes.submitted_at`,
con zona horaria. Los reintentos conservan esos valores.

| Atributo           | Tipo             | Valor permitido                                                          |
|--------------------|------------------|--------------------------------------------------------------------------|
| `question_id`      | cadena           | `emby_jellyfin_priorities`                                               |
| `question_version` | entero           | `1`                                                                      |
| `catalog_version`  | entero           | `1`                                                                      |
| `option_ids`       | lista de cadenas | `use_both_servers`, `sync_history`, `browse_both_catalogs`, `not_needed` |
| `submitted_at`     | cadena           | Fecha original con zona horaria                                          |

La lista no puede estar vacía ni tener duplicados. `not_needed` excluye las
demás opciones. El receptor rechaza campos, preguntas, versiones y opciones
desconocidos. Conserva el historial y cuenta la última respuesta recibida por
pregunta e instalación, según el orden de recepción. Separa eventos de
respuesta, instalaciones únicas y respuestas vigentes. El voto legacy sigue
siendo compatible. El comentario libre se elimina porque no llegaba al hub.

El catálogo viene empaquetado con HCC. Añadir preguntas remotas sin otra
versión requeriría una decisión de producto independiente. El estado local
vista/respondida/pospuesta/descartada persiste por identificador de pregunta,
también para las retiradas. Una pregunta nueva no sobrescribe respuestas
anteriores. Abrir o descartar no envía un evento ni activa el consentimiento.
Revocarlo cancela los pendientes y no los reenvía al reabrir la sección.

El receptor compatible debe desplegarse y validarse antes de habilitar este
productor. Comprueba respuestas sintéticas, duplicados, ediciones, combinaciones
inválidas, votos legacy y revocación en un entorno de prueba autorizado.
Implementar la issue no autoriza un despliegue, una release ni cambios en
producción. Consulta [cómo participar](participar.md) para las instrucciones de uso.

### Informes de soporte y telemetría automática

Los informes de soporte siguen un proceso distinto: tú decides revisar y
compartir manualmente un informe que puede incluir logs y otros datos de
diagnóstico. Las exclusiones anteriores se refieren al canal automático de
telemetría. El snapshot de red no incluye la marca del receptor AV.

### Invitación excepcional de 1.4.3

La actualización conserva el consentimiento existente y nunca reactiva la telemetría automáticamente. Como excepción
única para `telemetry-1.4.3`, una instalación que ya había rechazado o desactivado la telemetría puede ver una sola
invitación para conocer las mejoras de diagnóstico. Aceptarla activa la telemetría; rechazarla o cerrarla deja la
telemetría desactivada y no vuelve a mostrar esa invitación. Las instalaciones sin decisión previa reciben solo la
invitación habitual. Esta campaña no es un mecanismo reutilizable para futuras actualizaciones.
