#!/usr/bin/env python3
"""Pruebas de las historias del calendario.

    python3 content-studio/tests/test_plan.py

Espejo de las pruebas de piezas: `historias()` tiene que devolver el mismo
contexto (marca, año, mes, semana, tema) que agrega `piezas()`, filtrar por
mes igual que ella, y tolerar una marca sin calendario todavía —el camino
por defecto de una cartera recién cargada— sin romper.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from plan import historias  # noqa: E402

fallos = []


def check(nombre, ok, detalle=""):
    print(f"[{'  ok  ' if ok else ' falla'}] {nombre}" + (f" — {detalle}" if detalle else ""))
    if not ok:
        fallos.append(nombre)


MARCA = {
    "slug": "calzufre",
    "meses": [
        {
            "anio": 2026,
            "mes": 9,
            "semanas": [
                {
                    "numero": 1,
                    "tema": "Salinidad no es sodicidad",
                    "piezas": [],
                    "historias": [
                        {
                            "id": "calzufre-2026-09-s1-martes-h",
                            "dia": "martes",
                            "mecanica": "encuesta",
                            "que": "Dos lotes después de la misma lluvia",
                            "interaccion": "¿Cuál de los dos tiene problema de sodio?",
                        }
                    ],
                }
            ],
        }
    ],
}

# --- devuelve el contexto del mes y la semana ----------------------------
salida = historias(MARCA)
h = salida[0] if salida else {}
check(
    "historias devuelve el contexto del mes y la semana",
    len(salida) == 1
    and h.get("id") == "calzufre-2026-09-s1-martes-h"
    and h.get("marca") == "calzufre"
    and h.get("anio") == 2026
    and h.get("mes") == 9
    and h.get("semana") == 1
    and h.get("tema") == "Salinidad no es sodicidad",
    str(h),
)

# --- filtra por mes -------------------------------------------------------
check(
    "historias filtra por mes",
    historias(MARCA, anio=2026, mes=10) == [],
)

# --- tolera una marca sin meses -------------------------------------------
check(
    "historias tolera una marca sin meses",
    historias({"slug": "x", "meses": []}) == [],
)

print("\n" + "-" * 56)
if fallos:
    print(f"{len(fallos)} falla(s): {', '.join(fallos)}")
    raise SystemExit(1)
print("todo en orden")
