#!/usr/bin/env python3
"""Verifica que el plugin tenga todo lo que necesita.

    python3 content-studio/doctor.py

Chequea python, el pack, la sesión de Flow y el handshake MCP, y explica
qué hacer con lo que falte. No genera nada, no gasta créditos y no descarga
nada.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
OK, FAIL, WARN = "  ok  ", " falla", " aviso"
problemas: list[str] = []


def check(etiqueta: str, ok: bool, detalle: str = "", arreglo: str = "", aviso: bool = False):
    tag = OK if ok else (WARN if aviso else FAIL)
    print(f"[{tag}] {etiqueta}" + (f" — {detalle}" if detalle else ""))
    if not ok:
        if arreglo:
            print(f"          → {arreglo}")
        if not aviso:
            problemas.append(etiqueta)


def main() -> int:
    print(f"content-studio doctor\n{'-' * 62}")
    print(f"\npython {sys.version.split()[0]} ({sys.executable})")
    check("python >= 3.9", sys.version_info >= (3, 9))

    print()
    sys.path.insert(0, str(AQUI / "lib"))
    try:
        import gates
        import labs
        import plan
        import studio
    except Exception as e:  # noqa: BLE001
        check("importar lib/", False, detalle=str(e))
        return _resumen()
    check("importar lib/", True, detalle="studio, plan, gates, labs, applets")

    print()
    packs = studio.packs_disponibles()
    reales = [p for p in packs if not p["nombre"].startswith("_")]
    check(
        "packs instalados",
        bool(reales),
        detalle=", ".join(p["nombre"] for p in packs) or "sólo el de ejemplo",
        arreglo="Importá tu plan con studio_importar, o mirá packs/README.md",
        aviso=True,
    )
    try:
        pack = studio.cargar_pack()
        cob = plan.cobertura(pack)
        check("pack activo", True,
              detalle=f"{pack.get('nombre')}: {cob['marcas']} marcas, "
                      f"{cob['piezas_totales']} piezas con id")
        idi = gates.idioma(pack)
        check("idioma de los gates", idi["estado"] == gates.OK,
              detalle=f"patrones en {gates.IDIOMA_PATRONES!r}",
              arreglo=idi.get("entregable", {}).get("accion", ""),
              aviso=True)
        if cob["marcas_sin_calendario"]:
            check("calendarios", False, aviso=True,
                  detalle=f"{len(cob['marcas_sin_calendario'])} marcas sin calendario",
                  arreglo="Es normal al empezar: esos assets van a staging sin id.")
    except studio.PackError as e:
        check("pack activo", False, aviso=True, detalle=str(e).split("\n")[0],
              arreglo="Elegí uno con STUDIO_PACK_NAME o importá un plan.")

    print()
    try:
        ruta = labs.ruta_cookies()
        check("cookies de labs.google", True, detalle=str(ruta))
        modo = oct(ruta.stat().st_mode)[-3:]
        check("permisos de las cookies", modo == "600", detalle=f"modo {modo}",
              arreglo=f"chmod 600 '{ruta}' — es una sesión completa de Google.",
              aviso=True)
        st = labs.estado()
        check("sesión de Flow", bool(st.get("valida")),
              detalle=f"vence {st.get('vence')}",
              arreglo="Re-exportá las cookies de labs.google.")
    except labs.LabsAuthError as e:
        check("cookies de labs.google", False, aviso=True,
              detalle=str(e).split("\n")[0],
              arreglo="Sólo hace falta para crear y descubrir applets. "
                      "El resto del plugin anda sin esto.")

    print()
    try:
        proc = subprocess.run(
            [sys.executable, str(AQUI / "mcp" / "server.py")],
            input='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{}}}\n'
                  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n',
            capture_output=True, text=True, timeout=30,
        )
        lineas = [json.loads(x) for x in proc.stdout.splitlines() if x.strip()]
        tools = next((m["result"]["tools"] for m in lineas if "tools" in m.get("result", {})), [])
        check("handshake MCP", bool(tools), detalle=f"{len(tools)} herramientas")
        for t in tools:
            print(f"            · {t['name']}")
    except Exception as e:  # noqa: BLE001
        check("handshake MCP", False, detalle=str(e))

    return _resumen()


def _resumen() -> int:
    print(f"\n{'-' * 62}")
    if problemas:
        print(f"{len(problemas)} sin resolver: {', '.join(problemas)}")
        return 1
    print("todo en orden")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
