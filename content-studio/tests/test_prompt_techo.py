#!/usr/bin/env python3
"""Pruebas del techo del prompt.

    python3 content-studio/tests/test_prompt_techo.py

Por qué existe: en Flow el prompt se recorta a ~2126 caracteres **en
silencio**. La imagen igual vuelve, y bien, así que la pérdida no se ve.

El orden en que se arma el prompt es la defensa principal, y por eso está
cubierto acá: `PROHIBICIONES_BASE` va **primera**. Si fuera al final, lo
primero en caerse al truncar sería justo lo que impide texto, logos y
personas identificables adentro de la imagen — el gate reportaría OK, la
pieza volvería con un rótulo, y nada en el pipeline se enteraría.

Con las prohibiciones adelante lo que se pierde es la cola, que es la
pérdida barata. Se mide igual: una pieza que perdió su dirección visual
sale genérica y tampoco avisa.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

import campos  # noqa: E402

fallos = []


def chequear(nombre, condicion, detalle=""):
    print(f"[{'  ok  ' if condicion else 'FALLA '}] {nombre}{' — ' + detalle if detalle else ''}")
    if not condicion:
        fallos.append(nombre)


MARCA = {"slug": "altara", "nombre": "Altara", "identidad_visual": {}}
PRESET = {"titulo": "Fondo", "prompt": "Plano general de una nave industrializada"}

corto = campos.borrador(MARCA, PRESET, situacion="luz de media tarde")
chequear("un prompt normal no se trunca", not corto["largo_prompt"]["se_trunca"],
         f"{corto['largo_prompt']['largo']} de {campos.TECHO_PROMPT}")
chequear("no ensucia los pendientes cuando entra",
         not any(p["campo"] == "prompt" for p in corto["pendientes"]))

largo = campos.borrador(MARCA, PRESET, situacion="detalle " * 400)
L = largo["largo_prompt"]
chequear("un prompt largo se marca como truncado", L["se_trunca"], f"{L['largo']} caracteres")
chequear("dice cuánto se pierde", L["sobra"] > 0, f"sobran {L['sobra']}")
pend = [p for p in largo["pendientes"] if p["campo"] == "prompt"]
chequear("y aparece como pendiente", bool(pend))
if pend:
    chequear("explicando qué se pierde y qué sobrevive",
             "prohibiciones" in pend[0]["consecuencia"])

# La defensa principal: las prohibiciones van adelante, así que el recorte
# se come la cola —lo prescindible— y no el freno.
p = corto["campos"]["prompt"]
chequear("las prohibiciones van primeras en el prompt",
         p.startswith(campos.PROHIBICIONES_BASE[0]),
         f"arranca en {p[:38]!r}")
chequear("y siguen enteras aun con una situación desmedida",
         all(x in largo["campos"]["prompt"][:400] for x in campos.PROHIBICIONES_BASE))

print("\n" + "-" * 56)
if fallos:
    sys.exit(1)
print("todo en orden")
