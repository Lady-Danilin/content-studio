# Configuración

Todo se resuelve por variables de entorno. Ninguna es obligatoria.

## Qué pack se usa

| Variable | Por defecto | Para qué |
|---|---|---|
| `STUDIO_PACK` | — | Ruta a un directorio con `pack.json` |
| `STUDIO_PACK_NAME` | — | Nombre de un pack instalado |
| `STUDIO_CONFIG_DIR` | `~/.config/content-studio` | Dónde viven los packs |

`STUDIO_PACK` gana sobre `STUDIO_PACK_NAME`. Con **un solo** pack real
instalado se usa ése sin configurar nada; con varios no se elige por orden
alfabético — se pide que se aclare.

Una ruta explícita que no existe es un **error**, no una invitación a buscar
en otro lado: usar el pack de otro cliente en silencio publica el contenido
de una marca con la voz de otra.

## Dónde se deja lo producido

| Variable | Por defecto | Para qué |
|---|---|---|
| `STUDIO_OUT` | `./studio-out` | Paquetes: copy, manifiesto, pendientes, assets |

Relativo al directorio donde corre el servidor, que es el proyecto en el que
se está trabajando — no el del plugin.

## Credenciales de Flow

Sólo hacen falta para `studio_applet_spec` y `studio_applet_descubrir`. El
resto del plugin no toca la red.

| Variable | Por defecto | Para qué |
|---|---|---|
| `FLOW_COOKIES` | busca desde el cwd hacia arriba, después `FLOW_CONFIG_DIR` | Cookies de labs.google |
| `FLOW_CONFIG_DIR` | `~/.config/google-flow` | Dónde viven |
| `FLOW_TOKEN_CACHE` | `$FLOW_CONFIG_DIR/.flow-token.json` | Caché del bearer |

Es el mismo archivo que usa el plugin `google-flow`: si ya lo tenés, no hace
falta exportar de nuevo.

```bash
mkdir -p ~/.config/google-flow
# exportar las cookies de labs.google desde el navegador
chmod 600 ~/.config/google-flow/labs.google.cookies.json
```

La cookie de sesión dura meses; el bearer, horas, y se vuelve a derivar
solo. Sólo hay que re-exportar cuando la sesión vence del todo.

El archivo es una sesión completa de Google. `chmod 600` no es ceremonia.

## Ejemplo

```bash
export STUDIO_PACK_NAME=mi-agencia
export STUDIO_OUT=./entregables
```

Verificá con `python3 content-studio/doctor.py`.
