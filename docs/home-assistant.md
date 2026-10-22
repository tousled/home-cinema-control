# Conecta Home Assistant (opcional)

[Inicio](../README.md) · [Instalación](../INSTALL.md) · [Primeros pasos](primeros-pasos.md) · [English](home-assistant.en.md)

**No necesitas Home Assistant para utilizar HCC.** Esta función opcional envía eventos de reproducción a Home Assistant para que puedas automatizar las luces o la sala. Sigue estos pasos solo si ya utilizas Home Assistant.

## 9. Conecta HCC con Home Assistant

Con esta integración, HCC avisa a Home Assistant cuando detecta una reproducción, empieza, se pausa, continúa o termina.
Después,
Home Assistant decide qué hacer: encender luces, activar una escena, enviar un aviso o simplemente guardar el evento en
el
registro. HCC no crea automatizaciones por su cuenta; tú eliges la reacción en Home Assistant.

<p align="center">
  <img src="../assets/screenshots/install/10-home-assistant.png" alt="Pantalla de configuración de Home Assistant en HCC" width="860"/>
</p>

### 9.1 Crea la automatización en Home Assistant

En Home Assistant crea una automatización con un disparador **Webhook**. Puedes copiar este ejemplo completo. De momento
solo escribe cada cambio en el registro de Home Assistant, para que puedas comprobar que la conexión funciona antes de
añadir luces, escenas o notificaciones.

```yaml
alias: HCC - eventos de reproducción
triggers:
  - trigger: webhook
    webhook_id: reemplaza-esto-por-un-id-largo-y-aleatorio
    allowed_methods:
      - POST
    local_only: true
conditions:
  - condition: template
    value_template: >-
      {{ trigger.json.event | default('') in ['detected', 'started', 'paused', 'resumed', 'stopped'] }}
actions:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ trigger.json.event == 'detected' }}"
        sequence:
          - action: logbook.log
            data:
              name: HCC
              message: "Reproducción detectada: {{ trigger.json.title | default('') }}"
      - conditions:
          - condition: template
            value_template: "{{ trigger.json.event == 'started' }}"
        sequence:
          - action: logbook.log
            data:
              name: HCC
              message: "Reproducción iniciada: {{ trigger.json.title | default('') }}"
      - conditions:
          - condition: template
            value_template: "{{ trigger.json.event == 'paused' }}"
        sequence:
          - action: logbook.log
            data:
              name: HCC
              message: "Reproducción pausada: {{ trigger.json.title | default('') }}"
      - conditions:
          - condition: template
            value_template: "{{ trigger.json.event == 'resumed' }}"
        sequence:
          - action: logbook.log
            data:
              name: HCC
              message: "Reproducción reanudada: {{ trigger.json.title | default('') }}"
      - conditions:
          - condition: template
            value_template: "{{ trigger.json.event == 'stopped' }}"
        sequence:
          - action: logbook.log
            data:
              name: HCC
              message: "Reproducción detenida: {{ trigger.json.title | default('') }}"
mode: queued
```

El texto `reemplaza-esto-por-un-id-largo-y-aleatorio` es un ejemplo. Sustitúyelo por un identificador nuevo y guárdalo:
será el código que permitirá a HCC enviar eventos a esta automatización. Trátalo como una contraseña: no lo publiques ni
lo compartas.

Deja `local_only: true` si HCC y Home Assistant están en tu red local. Así Home Assistant no acepta este webhook desde
Internet. El método `POST` es el que utiliza HCC para enviar los datos.

Para aprender más sobre automatizaciones, consulta la
[documentación oficial de Home Assistant](https://www.home-assistant.io/docs/automation/). Para las opciones del
disparador,
consulta la [documentación oficial del Webhook](https://www.home-assistant.io/docs/automation/trigger/#webhook-trigger).

### 9.2 Configura HCC

En la pantalla **Home Assistant** de HCC:

1. Activa **Enviar eventos de HCC a Home Assistant**.
2. Escribe la dirección de Home Assistant, por ejemplo `http://homeassistant.local:8123`. Escribe solo la dirección
   base;
   no añadas `/api/webhook`.
3. Escribe el mismo código en **ID del webhook** que has puesto en la automatización.
4. Pulsa **Guardar**.
5. Pulsa **Reiniciar HCC** en el enlace que aparece debajo del botón para aplicar la configuración.

El ajuste de timeout de **Ajustes avanzados** normalmente no tienes que cambiarlo. Solo úsalo si Home Assistant tarda
más
de lo normal en responder.

### 9.3 Comprueba que funciona

HCC envía estos cinco eventos:

- `detected`: HCC ha detectado una reproducción válida en el dispositivo monitorizado y ha aceptado el handoff.
- `started`: la reproducción ha comenzado.
- `paused`: la reproducción está pausada.
- `resumed`: la reproducción continúa.
- `stopped`: la reproducción ha terminado o se ha detenido.

El contenido de un evento se parece a esto:

```json
{
  "event": "started",
  "event_id": "57438c115b84467dafcf843368d9bef6",
  "session_id": "33feec42b11b48799f749bf6534e371c",
  "media_type": "movie",
  "title": "Interstellar",
  "source": "emby",
  "player": "oppo"
}
```

`event` indica qué ha ocurrido. `event_id` identifica ese envío y `session_id` agrupa los eventos de la misma
reproducción.
El título, el servidor y el reproductor aparecen cuando HCC dispone de esos datos.

Para probarlo, inicia una reproducción desde el dispositivo que HCC monitoriza y revisa el **Registro** de Home
Assistant.
La pantalla de HCC también muestra la última entrega real. Antes de enviar el primer evento aparecerá como pendiente; no
se envía una petición de prueba automática.

Si Home Assistant no responde, HCC registra el error y la reproducción continúa. Si cambias la dirección o el ID del
webhook, el estado vuelve a pendiente hasta que HCC consiga enviar un evento con la nueva configuración.

Si HCC no puede cargar esta pantalla, muestra un error con la opción **Reintentar** en lugar de rellenar el formulario
con
valores que podrían no ser los tuyos.