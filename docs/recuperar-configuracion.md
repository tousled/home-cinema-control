# Recuperar la configuración de HCC

[Inicio](../README.md) · [Instalación](../INSTALL.md) · [English](recover-configuration.en.md)

Si acabas de actualizar HCC y aparece el asistente como si fuera una instalación nueva, **no significa necesariamente que hayas perdido los ajustes**. Puede que el contenedor esté utilizando otro volumen.

**No completes de nuevo el asistente ni borres el volumen.**

## 1. Comprueba qué almacenamiento utiliza HCC

**Si usas Portainer:**

1. Ve a **Containers** y abre el contenedor de HCC.
2. Busca la sección **Volumes** o **Mounts**.
3. Fíjate en la entrada que termina en `/config`. Debe apuntar al **mismo volumen o carpeta del NAS que tenías antes**. Revisa también el stack original en **Stacks**; no crees otro.

**Si usas Docker Compose:**

Ejecuta este comando en el servidor Docker:

```bash
docker inspect home-cinema-control --format '{{range .Mounts}}{{println .Name .Source "->" .Destination}}{{end}}'
```

Busca la línea que termina en `/config`. Si tu contenedor tiene otro nombre, utilízalo en el comando.

## 2. Si aparece otro volumen o carpeta

Vuelve al stack o al archivo Compose **original** y recupera el montaje que utilizabas antes. No crees un stack nuevo, no cambies el nombre del proyecto y no borres el volumen que has encontrado.

Si no recuerdas el volumen original, puedes buscarlo desde **Volumes** en Portainer o con `docker volume ls` en el terminal. **No pruebes volúmenes al azar**: identifica primero dónde estaban tus archivos.

## 3. Si el volumen original se borró

Solo una **copia de seguridad o snapshot** del NAS/servidor puede recuperar los datos anteriores. Antes de empezar de cero, comprueba que no exista todavía otra carpeta o volumen con la configuración.

Los archivos importantes están dentro de `/config`: `config.json` y `secrets.json`.

Para evitar este problema en el futuro, conserva el mismo montaje de `/config` al actualizar y haz copias de seguridad. Si necesitas una copia manual, consulta [operaciones Docker avanzadas](operaciones-docker-avanzadas.md).
