"""Applets de Flow: redactar la especificación, crear la sesión, cablear el pack.

Core reutilizable. Una applet es la herramienta que corre dentro de Google
Labs Flow; el plugin `google-flow` sabe *operarlas*, y este módulo sabe
*pedirlas*: traduce los presets de un pack a la especificación que el
agente de creación de Flow entiende.

## Qué está verificado y qué no

Verificado contra la API real (agosto 2026), todo sin gastar créditos:

    POST   flowCreationAgent/sessions        {"projectId": …}
             → {"sessionInfo": {"agentSessionId", "sessionContext"}}
    GET    flowCreationAgent/sessions?projectId=…      → {"sessions": [...]}
    GET    flowCreationAgent/sessions/{id}             → sessionInfo
    DELETE flowCreationAgent/sessions/{id}             → {}
    GET    flowAppletAgent/applets                     → catálogo
    GET    flowAppletAgent/applets/{id}/versions/{v}   → codeFiles + appletSession.events

**No verificado: cómo se le manda el mensaje a la sesión.** Se sondearon
doce rutas plausibles (`:sendMessage`, `:generateContent`, `/messages`,
`:respond`, a nivel sesión y a nivel colección, más `flowAppletAgent`) y
todas responden 404 con HTML, o sea que ninguna existe con ese nombre. El
envío probablemente viaja por el frontend (`labs.google/fx/api/trpc/…`) o
por un endpoint de streaming.

Descubrirlo por fuerza bruta contra la API no corresponde: se hace
observando el tráfico real del frontend mientras se crea una applet, con
DevTools abierto, y se anota acá. Hasta entonces `enviar_mensaje` falla con
instrucciones en vez de adivinar.

Mientras tanto el ciclo funciona igual, con un paso manual de una vez:

    especificacion()  →  se pega en el agente de Flow  →  descubrir()

y `descubrir()` cablea sola el `appletId` en el pack.
"""

from __future__ import annotations

import json
from typing import Any

import labs
import studio
from studio import StudioError

# Los nombres van al SDK tal cual, emoji y espaciado incluidos.
MODELOS = ["🍌 Nano Banana Pro", "🍌 Nano Banana 2", "🍌 Nano Banana 2 Lite"]


# ------------------------------------------------------------ especificación


def especificacion(
    nombre: str,
    proposito: str,
    controles: list[dict],
    boton: str,
    *,
    prompt_base: str = "",
    notas: list[str] | None = None,
) -> str:
    """El pedido para el agente de creación de Flow, en markdown.

    Incluye siempre el selector de modelo, y no es opcional. Cada modelo
    tiene su cuota diaria propia, y cuando una se agota el backend contesta
    `FALLO EN GENERACIÓN / Image generation failed` y nada más: la sesión
    sigue válida, los créditos intactos, y el mismo prompt andaba diez
    minutos antes. Es indistinguible de un error transitorio, así que la
    reacción natural es reintentar — que es justamente lo que no hay que
    hacer. Con el desplegable se cambia de modelo y sigue andando.

    Agregarlo después significa editar la applet en medio de una
    producción, así que va desde el principio.
    """
    filas = []
    for c in controles:
        tipo = c.get("tipo", "texto")
        etiqueta = c["etiqueta"]
        if tipo == "desplegable":
            valores = ", ".join(f"`{v}`" for v in c.get("valores", []))
            filas.append(f"- `{etiqueta}` (desplegable): {c.get('para_que','')}\n  Valores: {valores}")
        elif tipo == "galeria":
            filas.append(f"- `{etiqueta}` (galería): {c.get('para_que','')} — usa `Flow.media.select`.")
        else:
            obligatorio = " **obligatorio**" if c.get("obligatorio") else ""
            filas.append(f"- `{etiqueta}` ({tipo}){obligatorio}: {c.get('para_que','')}")

    extras = "\n".join(f"- {n}" for n in (notas or []))
    modelos = "\n".join(f"  '{m}'," for m in MODELOS)

    return f"""\
Construí una herramienta llamada **{nombre}**.

{proposito}

## Controles de entrada

{chr(10).join(filas)}

## Selector de modelo (obligatorio)

Agregá un desplegable real rotulado `Modelo`, conectado a un campo del
estado compartido para que la elección aplique a todos los pasos de la
cadena. Tiene que ser un desplegable de verdad (no un grupo de botones),
para poder operarlo desde automatización, y tiene que aparecer también en
la pestaña donde se genera el grueso, no sólo en la primera.

```js
const MODEL_OPTIONS = [
{modelos}
];
```

Nunca fijes `modelDisplayName` en el código.

## Prompt

{prompt_base or "Ensamblá el prompt a partir de los controles."}

Reglas que el prompt tiene que respetar siempre, en todas las salidas:

- **Sin texto**: ni títulos, ni cifras, ni rótulos, ni cotas, ni etiquetas,
  ni marcas de agua dentro de la imagen. La tipografía se compone después,
  aparte, con el dato ya validado.
- **Sin marcas de terceros**: ni logos, ni modelos, ni patentes, ni
  packaging identificable de ningún fabricante.
- **Sin personas identificables** presentadas como reales.
- Dejá espacio negativo declarado por tercios, para poder rotular encima.

## Botón de generación

El botón principal se rotula exactamente `{boton}`.

{extras}
"""


def desde_preset(nombre_preset: str, preset: dict) -> str:
    """Especificación derivada de un preset del pack."""
    controles = [
        {"etiqueta": "Prompt", "tipo": "texto largo", "obligatorio": True,
         "para_que": "descripción de la escena, sin marcas ni texto"},
        {"etiqueta": "Formato", "tipo": "desplegable",
         "valores": ["9:16", "4:5", "1:1", "16:9"],
         "para_que": "relación de aspecto según destino"},
    ]
    for extra in preset.get("controles") or []:
        controles.append(extra)
    return especificacion(
        nombre=preset.get("titulo") or nombre_preset,
        proposito=preset.get("para_que", ""),
        controles=controles,
        boton=preset.get("boton") or "GENERAR",
        prompt_base=preset.get("prompt", ""),
        notas=preset.get("notas"),
    )


# ------------------------------------------------------------------ sesiones


def crear_sesion(project_id: str) -> dict:
    """Abre una sesión con el agente de creación. Verificado."""
    r = labs.api("POST", "flowCreationAgent/sessions", body={"projectId": project_id})
    return r.get("sessionInfo") or r


def listar_sesiones(project_id: str) -> list[dict]:
    return labs.api(
        "GET", "flowCreationAgent/sessions", params={"projectId": project_id}
    ).get("sessions", [])


def borrar_sesion(agent_session_id: str) -> dict:
    return labs.api("DELETE", f"flowCreationAgent/sessions/{agent_session_id}")


def enviar_mensaje(agent_session_id: str, texto: str) -> dict:
    """Todavía no implementado, y a propósito no se adivina.

    Ver el encabezado del módulo: doce rutas candidatas devuelven 404. El
    paso que falta es capturar el POST real del frontend y anotarlo acá.
    """
    raise StudioError(
        "El envío de mensajes al agente de creación de Flow todavía no está "
        "reverseado: las rutas candidatas responden 404 y no se adivina un "
        "endpoint de escritura sobre la cuenta de alguien.\n\n"
        "Mientras tanto el camino que SÍ funciona, y que sólo se hace una vez:\n"
        "  1. studio_applet_spec genera la especificación completa.\n"
        "  2. Se pega en el agente de Flow (labs.google/fx/tools/flow).\n"
        "  3. studio_applet_descubrir cablea el appletId en el pack, solo.\n\n"
        "Para automatizar el paso 2: abrir DevTools en la pestaña de red, "
        "crear una applet a mano, y anotar el POST que sale — método, ruta y "
        "cuerpo — en lib/applets.py."
    )


# --------------------------------------------------------------- descubrir


def descubrir(esperadas: dict[str, str] | None = None) -> dict:
    """Lista las applets de la cuenta y las mapea contra las esperadas.

    `esperadas` es {clave_del_pack: nombre_visible}. Lo que aparece se
    cablea; lo que falta se informa con la especificación pendiente, en vez
    de fallar entero.
    """
    catalogo = labs.listar_applets()
    por_nombre = {a.get("displayName", ""): a for a in catalogo}

    encontradas, faltantes = {}, []
    for clave, visible in (esperadas or {}).items():
        a = por_nombre.get(visible)
        if a is None:
            # Tolerar el prefijo "Remix of", que Flow agrega al duplicar.
            a = next(
                (x for n, x in por_nombre.items()
                 if n.replace("Remix of ", "").strip() == visible),
                None,
            )
        if a:
            encontradas[clave] = {
                "appletId": a["appletId"],
                "displayName": a.get("displayName"),
                "currentVersionId": a.get("currentVersionId"),
            }
        else:
            faltantes.append({"clave": clave, "nombre_esperado": visible})

    return {
        "applets_en_la_cuenta": len(catalogo),
        "encontradas": encontradas,
        "faltantes": faltantes,
        "siguiente": (
            "Cablear `encontradas` en el pack.json y pedirle al agente de Flow "
            "las que figuran en `faltantes`, con studio_applet_spec."
        ) if faltantes else "Todo cableado.",
    }


def verificar(applet_id: str, clausulas: list[str]) -> dict:
    """¿La applet que construyó el agente de Flow dice lo que se le pidió?

    **El agente de Flow recorta bloques al copiarlos, y no avisa.** Medido:
    pidiéndole un bloque de prohibiciones palabra por palabra, copió la
    primera oración y dejó afuera las cuatro cláusulas siguientes — y reportó
    el cambio como hecho. Lo peligroso es que el resultado no delata la
    pérdida: las imágenes salieron bien igual, porque el resto del prompt
    alcanzaba para esa tanda. El primer caso que no alcance se lleva puesta
    una pieza de cliente.

    Por eso no se confía en lo que el agente dice que hizo: se baja el código
    de la applet y se busca cada cláusula adentro. Es una llamada, no cuesta
    créditos, y convierte un recorte silencioso en algo que se ve.

        verificar(applet_id, ["sin texto", "sin logos", "sin personas"])
    """
    d = labs.obtener_applet(applet_id)
    archivos = d.get("codeFiles") or []
    codigo = studio.normalizar(
        "\n".join(f.get("content", "") for f in archivos)
    )
    presentes, ausentes = [], []
    for c in clausulas:
        (presentes if studio.normalizar(c) in codigo else ausentes).append(c)

    return {
        "appletId": applet_id,
        "archivos": [f.get("path") or f.get("name") for f in archivos],
        "presentes": presentes,
        "ausentes": ausentes,
        "ok": not ausentes,
        "siguiente": (
            "Volver a pedirle al agente de Flow las cláusulas que faltan, una "
            "por una, y verificar de nuevo. No alcanza con que diga que las "
            "puso."
        ) if ausentes else "La applet dice lo que se le pidió.",
    }


def conversacion(applet_id: str) -> list[dict]:
    """La conversación que construyó una applet.

    Sirve para dos cosas: entender qué se le pidió a una herramienta que ya
    funciona, y copiar el formato de un pedido que salió bien.
    """
    d = labs.obtener_applet(applet_id)
    eventos = (d.get("appletSession") or {}).get("events") or []
    return [
        {"autor": e.get("author"), "texto": e.get("text", "")}
        for e in eventos
        if e.get("text")
    ]
