#!/usr/bin/env python3
"""Precondiciones al arrancar la sesión.

Puramente local: lee el pack del disco. No toca la red — un hook que sale a
internet en cada arranque es exactamente lo que no queremos.

Sólo habla cuando hay algo que hacer. Si el pack está sano, se calla.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))


def plural(n: int, singular: str, plural_: str) -> str:
    return f"{n} {singular if n == 1 else plural_}"


def emitir(contexto: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": contexto,
        }
    }))


def main() -> int:
    # Ninguna falla de un plugin puede romper el arranque de la sesión.
    try:
        import gates
        import plan
        import studio
    except Exception:
        return 0

    try:
        pack = studio.cargar_pack()
    except Exception:
        return 0  # sin pack no hay nada que advertir: puede no usarse acá

    try:
        cob = plan.cobertura(pack)
    except Exception:
        return 0

    avisos = []

    idi = gates.idioma(pack)
    if idi["estado"] != gates.OK:
        avisos.append(idi["entregable"]["advertencia"])

    sin_cal = cob.get("marcas_sin_calendario") or []
    if sin_cal:
        avisos.append(
            f"{len(sin_cal)} de {cob['marcas']} marcas sin calendario "
            f"({', '.join(sin_cal[:5])}{'…' if len(sin_cal) > 5 else ''}). "
            "Sus assets van a staging SIN id. No acuñes ids de pieza."
        )

    sin_permisos = []
    for slug in plan.marcas(pack):
        m = plan.marca(slug, pack)
        if any(plan.permiso(m, k) == plan.NO_DECLARADO for k in ("trend", "humor", "crudo")):
            sin_permisos.append(slug)
    if sin_permisos:
        avisos.append(
            f"{plural(len(sin_permisos), 'marca tiene', 'marcas tienen')} "
            "los permisos editoriales sin declarar "
            f"({', '.join(sin_permisos[:5])}{'…' if len(sin_permisos) > 5 else ''}). "
            "La ausencia bloquea y pregunta: no se hereda de otra marca del cluster."
        )

    if not avisos:
        return 0

    emitir(
        f"[content-studio] Pack activo: {pack.get('nombre')} "
        f"({cob['marcas']} marcas, {cob['piezas_totales']} piezas con id).\n"
        + "\n".join(f"- {a}" for a in avisos)
        + "\nCorré studio_huecos para el detalle antes de producir."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
