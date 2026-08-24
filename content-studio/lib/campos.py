"""De la ficha de la marca a los campos de generación.

Core reutilizable. Traduce lo que la marca declara —voz, rubro, paleta,
prohibiciones— a los campos concretos que un preset necesita para generar.

Lo que emite es un **borrador**, y la distinción es el punto entero del
módulo. Sacar los campos a mano, pieza por pieza, es el trabajo que
conviene hacer una sola vez y en código; pero la ficha manda, y si algo
del borrador la contradice, el bug está en esta traducción, no en la
ficha. Por eso cada campo viaja con su origen y con lo que le falta.

El patrón viene de un pipeline de producción de personajes que hace lo
mismo con fichas canónicas: emite borradores, se repasan, y el canon
decide.
"""

from __future__ import annotations

from typing import Any

import formatos
import plan

# Prohibiciones que van en TODO prompt de generación, sin importar la
# marca. No son estilo: son los gates escritos en el prompt, para que el
# modelo no tenga que adivinarlos.
#
# Van ADELANTE, y eso no es una preferencia de redacción. Los endpoints
# generativos truncan los prompts largos en silencio: la imagen vuelve, y
# vuelve bien, así que nada avisa que se cortó la cola. Como lo último que
# se agrega es lo primero que se pierde, poner las prohibiciones al final
# significa que la truncación desactiva justo la regla en la que se estaba
# confiando — y el resultado parece correcto hasta que un día no lo es.
PROHIBICIONES_BASE = [
    "sin texto, sin números, sin rótulos ni cotas",
    "sin logos ni marcas de agua",
    "sin marcas, modelos, patentes ni packaging de terceros",
    "sin personas identificables",
]

# Techo del prompt en Flow, medido: más allá de esto se recorta **en
# silencio** — la imagen igual vuelve, y bien, así que la pérdida no se ve.
#
# Con las prohibiciones adelante, lo que se pierde al truncar es la cola:
# la situación primero, y después la dirección visual del preset. Es la
# pérdida barata, y es a propósito. Aun así se mide, porque una pieza que
# perdió su dirección visual sale genérica sin que nada lo diga.
TECHO_PROMPT = 2126
MARGEN_AVISO = 150


def medir_prompt(prompt: str) -> dict:
    """Cuánto mide lo que se va a enviar, contra el techo.

    Medir es la única defensa contra un recorte que no avisa. Es barato y no
    depende de mirar un contador en pantalla.
    """
    largo = len(prompt)
    return {
        "largo": largo,
        "techo": TECHO_PROMPT,
        "margen": TECHO_PROMPT - largo,
        "se_trunca": largo > TECHO_PROMPT,
        "sobra": max(0, largo - TECHO_PROMPT),
        "al_limite": TECHO_PROMPT - MARGEN_AVISO <= largo <= TECHO_PROMPT,
    }


def borrador(
    m: dict,
    preset: dict,
    *,
    destino: str | None = None,
    situacion: str | None = None,
) -> dict:
    """Campos de generación para una marca y un preset.

    `situacion` es lo que cambia entre una pieza y otra: el resto sale de
    la ficha y del preset, y por eso no se improvisa cada vez.
    """
    iv = m.get("identidad_visual") or {}
    tiene_iv = bool(iv.get("disponible"))

    contrato = formatos.resolver(destino) if destino else None
    aspecto = (contrato or {}).get("aspecto") or preset.get("aspecto") or "4:5"

    # Orden deliberado: primero lo que no se puede perder.
    partes = [", ".join(PROHIBICIONES_BASE)]
    if tiene_iv and iv.get("paleta"):
        partes.append(f"paleta: {iv['paleta']}")
    partes.append(preset.get("prompt", "").strip())
    if situacion:
        partes.append(situacion.strip())

    prompt = ". ".join(p for p in partes if p)
    largo = medir_prompt(prompt)

    campos: dict[str, Any] = {
        "marca": m["slug"],
        "preset": preset.get("titulo") or "",
        "prompt": prompt,
        "aspecto": aspecto,
        "medio": preset.get("medio") or (contrato or {}).get("medio") or "imagen",
        "boton": preset.get("boton") or "GENERAR",
    }

    # Cada campo dice de dónde salió: sin eso, revisar el borrador obliga a
    # abrir la ficha y compararla a mano, que es justo lo que se quiso evitar.
    origen = {
        "prompt": "preset" + (" + situación" if situacion else "")
                  + (" + paleta de la marca" if tiene_iv and iv.get("paleta") else ""),
        "aspecto": f"contrato de formato ({destino})" if destino else "preset",
        "medio": "preset",
    }

    pendientes = []
    if largo["se_trunca"]:
        pendientes.append({
            "campo": "prompt",
            "detalle": (
                f"El prompt mide {largo['largo']} caracteres y el techo de Flow "
                f"es {TECHO_PROMPT}: se van a perder {largo['sobra']} del final."
            ),
            "consecuencia": (
                "Las prohibiciones van adelante y sobreviven al recorte, así "
                "que no se pierde el freno; lo que se pierde es la cola: la "
                "situación y parte de la dirección visual del preset. La "
                "pieza sale genérica sin que nada lo avise. Acortar la "
                "situación."
            ),
        })
    if not tiene_iv:
        pendientes.append({
            "campo": "paleta",
            "detalle": "La marca no tiene identidad visual cargada.",
            "consecuencia": "El asset sale sin color de marca y la pieza queda `incompleta`.",
        })
    if not preset.get("prompt"):
        pendientes.append({
            "campo": "prompt",
            "detalle": f"El preset {preset.get('titulo')!r} no trae prompt base.",
            "consecuencia": "El prompt sale sólo de la situación, sin la dirección visual de la marca.",
        })

    for clave in ("trend", "humor", "crudo"):
        if plan.permiso(m, clave) == plan.NO_DECLARADO:
            pendientes.append({
                "campo": f"permisos.{clave}",
                "detalle": f"No está declarado si esta marca puede usar {clave}.",
                "consecuencia": "Bloquea antes de generar. Hay que preguntarlo, no deducirlo.",
            })

    return {
        "campos": campos,
        "largo_prompt": largo,
        "origen": origen,
        "borrador": True,
        "pendientes": pendientes,
        "no_generable": m.get("no_generable") or [],
        "prohibido_en_copy": m.get("prohibido") or [],
        "nota": (
            "Esto es un borrador: la ficha de la marca manda. Si algún campo "
            "la contradice, el error está en esta traducción, no en la ficha. "
            "Repasalo antes de generar."
        ),
    }


def matriz(m: dict, preset: dict, ejes: dict[str, list]) -> dict:
    """Expande un lote como producto cartesiano de los ejes dados.

    Sirve para producir una semana o un mes de una vez. Devuelve la cuenta
    por separado para poder decidir con el número a la vista: un lote de
    tres es una prueba, uno de veintiocho es una tarde de generación y de
    créditos de otra persona.
    """
    nombres = list(ejes)
    combinaciones: list[dict] = [{}]
    for eje in nombres:
        combinaciones = [{**c, eje: v} for c in combinaciones for v in ejes[eje]]

    variantes = []
    for c in combinaciones:
        situacion = ", ".join(f"{k}: {v}" for k, v in c.items())
        b = borrador(m, preset, situacion=situacion)
        variantes.append({
            "ejes": c,
            "prompt": b["campos"]["prompt"],
            "medida": b["largo_prompt"],
        })

    truncan = [v for v in variantes if v["medida"]["se_trunca"]]
    return {
        "marca": m["slug"],
        "preset": preset.get("titulo"),
        "ejes": {k: len(v) for k, v in ejes.items()},
        "variantes": len(variantes),
        "truncan": len(truncan),
        "lote": variantes,
        "antes_de_lanzar": (
            "Probá con dos o tres primero. Un lote entero que falla en la "
            "variante 14 de 28 gasta las trece anteriores."
        ),
    }
