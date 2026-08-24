#!/usr/bin/env python3
"""Pruebas del gate de dato sin validar.

    python3 content-studio/tests/test_gates_dato.py

Los dos casos que motivaron estas pruebas, los dos medidos contra el código
anterior:

**Dejaba pasar una fecha inventada.** Un copy que decía «válida hasta el 5 de
enero» contra una fuente que decía «válida hasta el 30 de septiembre` volvía
como aviso con origen «fuente». Lo único que se comparaba era el marcador
«válida hasta», que sí estaba. La fecha —que es el dato— no la miraba nadie,
y es exactamente la condición comercial inventada que este gate existe para
frenar.

**Y bloqueaba lo legítimo.** Un precio que estaba en el brief como
«1.500.000 pesos», escrito en el copy como «$1.500.000», se reportaba como
inventado: el signo pesos alcanzaba para que no fuera substring.

Los dos salían de lo mismo — comparar el string de superficie en vez del
número—, así que se arreglan juntos.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

import gates  # noqa: E402

MARCA = {"nombre": "Grupo Altara", "slug": "altara", "responsable": "Dani"}
fallos = []


def caso(nombre, copy, fuentes, estado, tipo=None):
    r = gates.dato_sin_validar(copy, MARCA, fuentes)
    real_tipo = r["entregable"].get("tipo")
    ok = r["estado"] == estado and (tipo is None or real_tipo == tipo)
    print(f"[{'  ok  ' if ok else 'FALLA '}] {nombre} — {r['estado']}"
          + (f" / {real_tipo}" if real_tipo else ""))
    if not ok:
        fallos.append(f"{nombre}: esperaba {estado}/{tipo}, vino {r['estado']}/{real_tipo}")
    return r


# --- el dato es el dato, no cómo se lo escribió ----------------------------
caso("mismo precio, otra grafía en la fuente",
     "Aprovechá: $1.500.000 hasta el 30 de septiembre.",
     ["El valor de lista es 1.500.000 pesos, vigente hasta el 30 de septiembre."],
     "aviso")

caso("el signo pesos al revés",
     "Desde 250.000 pesos",
     ["Precio de lanzamiento: $250.000"],
     "aviso")

caso("separador de miles con espacio",
     "Desde $1 500 000",
     ["El valor es 1.500.000 pesos"],
     "aviso")

# --- lo inventado se frena -------------------------------------------------
caso("fecha inventada, la fuente dice otra",
     "Promo válida hasta el 5 de enero.",
     ["La promoción es válida hasta el 30 de septiembre."],
     "bloqueo", "dato_inventado")

caso("precio inventado",
     "Desde $99.000",
     ["El valor de lista es 1.500.000 pesos"],
     "bloqueo", "dato_inventado")

caso("plazo inventado, la fuente dice otro",
     "Entrega en 30 días.",
     ["El plazo de entrega es de 90 días."],
     "bloqueo", "dato_inventado")

# --- sin fuentes no se acusa de inventar: se pide con qué comparar ---------
r = caso("sin fuentes, con datos duros",
         "Entrega en 30 días. Consultá al 351 555 1234.",
         None,
         "bloqueo", "sin_fuentes")
if "fuentes" not in r["entregable"].get("accion", ""):
    fallos.append("sin_fuentes: la acción no dice que hay que pasar fuentes")

caso("sin fuentes y sin datos duros no molesta",
     "Conocé nuestra propuesta de valor.",
     None,
     "ok")

# --- el marcador solo no valida ------------------------------------------
r = gates.dato_sin_validar(
    "Válida hasta el 5 de enero.",
    MARCA,
    ["Válida hasta el 30 de septiembre."],
)
if any(h["origen"] == "fuente" for h in r["hallazgos"]):
    fallos.append("un marcador presente en la fuente sigue validando el dato que lo sigue")
else:
    print("[  ok  ] el marcador presente en la fuente ya no valida la fecha")

print("\n" + "-" * 56)
if fallos:
    for f in fallos:
        print("  ✗", f)
    sys.exit(1)
print("todo en orden")
