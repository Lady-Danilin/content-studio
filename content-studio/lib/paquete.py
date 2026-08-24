"""El paquete entregable de una pieza.

Core reutilizable. Una pieza terminada no es un archivo suelto: es una
carpeta que alguien tiene que poder revisar y aprobar sin volver a
preguntar nada. Por eso el paquete lleva, además del material, el registro
de qué quedó pendiente y con quién se valida.

    <salida>/<marca>/<id-o-staging>/
    ├── copy.md            el texto, listo para revisar
    ├── manifiesto.json    procedencia de cada asset y su no-atribución
    ├── pendientes.md      qué falta validar, con quién y por qué
    ├── work/              el proceso: intermedios, descartes, versiones
    └── assets/            lo que se entrega

`work/` y `assets/` no son lo mismo, y confundirlos es el error caro.
`work/` se puede tirar. Un archivo se gana entrar a `assets/` **por estar
medido**, no por haber sido generado: un PNG de 0 bytes y uno bueno se ven
igual en un listado. `inventario.verificar()` es quien lo decide.

`pendientes.md` es el archivo que hace útil al resto. Un paquete sin él se
lee como aprobado.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import gates
import inventario
import manifiesto as mf
import plan
import studio


def destino(m: dict, pieza_id: str | None = None) -> Path:
    """Carpeta de la pieza, o staging si la marca no tiene calendario.

    Staging no lleva fecha en el nombre a propósito: una fecha ahí se lee
    después como si la pieza estuviera programada para ese día.
    """
    base = studio.out_dir()
    if pieza_id:
        return base / m["slug"] / pieza_id
    return base / plan.destino_staging(m)


def armar(
    m: dict,
    *,
    copy: str,
    pieza_id: str | None = None,
    manifiestos: list[dict] | None = None,
    veredicto: dict | None = None,
    fuentes: list[str] | None = None,
) -> dict:
    """Escribe el paquete y devuelve qué quedó adentro.

    No decide si el contenido está bien: eso ya lo dijeron los gates. Acá
    se registra, que es lo que permite que otra persona lo revise después
    sin repetir el análisis.
    """
    carpeta = destino(m, pieza_id)
    (carpeta / "assets").mkdir(parents=True, exist_ok=True)
    (carpeta / "work").mkdir(parents=True, exist_ok=True)

    incompleta = any(
        a.get("gate") == "identidad_visual" for a in (veredicto or {}).get("avisos", [])
    )

    encabezado = (
        f"# {m.get('nombre')} — {pieza_id or 'sin id (staging)'}\n\n"
        + ("> **PIEZA INCOMPLETA**: sin logo ni tipografía de marca. "
           "No publicar así.\n\n" if incompleta else "")
    )
    (carpeta / "copy.md").write_text(encabezado + copy.strip() + "\n", encoding="utf-8")

    mf.escribir(carpeta, manifiestos or [])
    (carpeta / "pendientes.md").write_text(
        _pendientes(m, veredicto or {}, pieza_id), encoding="utf-8"
    )

    return {
        "carpeta": str(carpeta),
        "pieza_id": pieza_id,
        "staging": pieza_id is None,
        "incompleta": incompleta,
        "assets": len(manifiestos or []),
        "pendientes": len((veredicto or {}).get("avisos", [])),
        "archivos": ["copy.md", "manifiesto.json", "pendientes.md", "work/", "assets/"],
        "verificacion": inventario.verificar(carpeta),
    }


def _pendientes(m: dict, veredicto: dict, pieza_id: str | None) -> str:
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    responsable = m.get("responsable") or "responsable de cuenta"

    lineas = [
        f"# Pendientes — {m.get('nombre')}",
        "",
        f"Pieza: `{pieza_id or 'staging, sin id'}`  ·  Generado: {ahora}",
        "",
        "Nada de esto se publica sin confirmación. El dato histórico de un",
        "brief es contexto, no autorización para republicarlo.",
        "",
    ]

    avisos = veredicto.get("avisos") or []
    if not avisos:
        lineas += ["No quedaron pendientes registrados.", ""]
    for a in avisos:
        lineas.append(f"## {a['gate']}")
        lineas.append("")
        ent = a.get("entregable") or {}
        if ent.get("advertencia"):
            lineas += [ent["advertencia"], ""]
        for h in a.get("hallazgos") or []:
            if isinstance(h, dict):
                detalle = " · ".join(f"{k}: {v}" for k, v in h.items() if v)
                lineas.append(f"- {detalle}")
        acciones = ent.get("accion")
        if isinstance(acciones, str):
            acciones = [acciones]
        for x in acciones or []:
            lineas.append(f"- [ ] {x}")
        lineas.append("")

    if not (m.get("identidad_visual") or {}).get("disponible"):
        lineas += [
            "## identidad visual",
            "",
            "- [ ] Pedir manual de marca: logo, paleta y tipografía.",
            "- La pieza sale visiblemente incompleta a propósito: una placa que",
            "  parece terminada puede llegar a publicarse.",
            "",
        ]

    lineas += [f"Validar con: **{responsable}**.", ""]
    return "\n".join(lineas)


def revisar(m: dict, copy: str, *, fuentes: list[str] | None = None,
            pack: dict | None = None, origen_voz: str | None = None) -> dict:
    """Pasa un copy por todos los gates de texto y devuelve el veredicto.

    El orden importa poco acá —son independientes entre sí— pero la
    agregación sí: un solo bloqueo frena, los avisos viajan al manifiesto.
    """
    resultados = [
        gates.blocklist(copy, m),
        gates.sector_regulado(copy, m),
        gates.dato_sin_validar(copy, m, fuentes),
        gates.identidad_visual(m),
        gates.conversion(m),
    ]
    if origen_voz and pack:
        resultados.append(gates.vecindad(m["slug"], origen_voz, pack))
    return gates.evaluar(resultados)
