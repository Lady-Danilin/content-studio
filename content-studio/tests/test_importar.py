#!/usr/bin/env python3
"""Pruebas del parser de literales TypeScript.

    python3 content-studio/tests/test_importar.py

El caso que motivó estas pruebas: un guión real trae comillas dobles
adentro de un string con comillas simples. Cualquier conversor que aplique
expresiones regulares sobre todo el texto rompe ahí, y el síntoma es
silencioso — la marca cae al camino de respaldo y se importa vacía, con la
ficha, la grilla y el calendario perdidos.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

import importar  # noqa: E402

fallos = []


def check(nombre, ok, detalle=""):
    print(f"[{'  ok  ' if ok else ' falla'}] {nombre}" + (f" — {detalle}" if detalle else ""))
    if not ok:
        fallos.append(nombre)


def parsea(ts: str) -> dict:
    return json.loads(importar._ts_a_json(importar._objeto_literal(ts)))


# --- comillas dobles dentro de un string con comillas simples -----------
d = parsea('''export const x = {
  valor: '"[Nombre] vino desde [localidad]." — plano del cliente',
};''')
check("comillas dobles dentro de comillas simples",
      d["valor"] == '"[Nombre] vino desde [localidad]." — plano del cliente',
      repr(d["valor"])[:60])

# --- comentarios, que no deben comerse contenido ------------------------
d = parsea('''export const x = {
  // DERIVADO: confirmar con la agencia
  rubro: "Concesionaria",  /* al margen */
  tono: "Directo",
};''')
check("comentarios de línea y de bloque", d == {"rubro": "Concesionaria", "tono": "Directo"}, str(d))

# --- una barra dentro de un string no es un comentario ------------------
d = parsea('''export const x = { nombre: "Grupo Altara / Estación", url: "https://a.com" };''')
check("barras dentro de strings",
      d["nombre"] == "Grupo Altara / Estación" and d["url"] == "https://a.com", str(d))

# --- apóstrofo escapado, válido en TS pero no en JSON -------------------
d = parsea(r"""export const x = { t: 'no es lo que crees' };""")
check("string simple sin escapes", d["t"] == "no es lo que crees", str(d))

# --- coma final y `as const` -------------------------------------------
d = parsea('''export const x = { a: ["uno", "dos",], b: "tres", } as const;''')
check("coma final y as const", d == {"a": ["uno", "dos"], "b": "tres"}, str(d))

# --- clave con nombre reservado o con $ ---------------------------------
d = parsea('''export const x = { class: "a", $ref: "b" };''')
check("claves con nombres poco comunes", d == {"class": "a", "$ref": "b"}, str(d))

# --- anidamiento profundo, como un calendario real ----------------------
d = parsea('''export const x = {
  meses: [{ anio: 2026, mes: 9, semanas: [{ numero: 1, piezas: [{ id: "m-2026-09-s1-lunes" }] }] }],
};''')
check("estructura anidada",
      d["meses"][0]["semanas"][0]["piezas"][0]["id"] == "m-2026-09-s1-lunes", "calendario")

# --- sector regulado se infiere del rubro -------------------------------
check("infiere sector regulado",
      importar.es_regulado({"rubro": "Medicina privada y regenerativa"})
      and not importar.es_regulado({"rubro": "Materiales de construcción"}))

print("\n" + "-" * 56)
if fallos:
    print(f"{len(fallos)} falla(s): {', '.join(fallos)}")
    raise SystemExit(1)
print("todo en orden")
