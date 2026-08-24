"""Manifiesto de procedencia: qué es cada archivo y qué NO es.

Core reutilizable. Es el mecanismo que hace exigible la regla de
no-atribución más allá de la llamada de generación: sin él, «no rotules
este plano como el predio» es una nota al pie que se pierde entre quien
genera y quien edita.

Todo asset generado sale acompañado de un manifiesto. La etapa de edición
lo lee antes de montar, y el responsable de cuenta antes de aprobar.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import studio


def sha256(ruta: str | Path) -> str | None:
    """Huella del archivo. Es lo que permite decir después «este es el
    mismo asset que se aprobó», cuando el nombre ya no alcanza."""
    p = Path(ruta)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def nuevo(
    archivo: str,
    marca: str,
    prompt: str,
    *,
    destino: str,
    aspecto: str,
    no_atribuible_a: list[str],
    pieza_id: str | None = None,
    preset: str | None = None,
    avisos: list | None = None,
    incompleta: bool = False,
    ruta: str | Path | None = None,
    costo: float | None = None,
) -> dict:
    """Manifiesto de un asset generado.

    `no_atribuible_a` es el campo que más trabajo hace y el que no se puede
    dejar vacío: nombra explícitamente el lugar, la obra, el caso o la
    persona a los que ese plano no puede atribuirse al momento de montar.
    """
    if not no_atribuible_a:
        raise ValueError(
            "no_atribuible_a no puede estar vacío: es lo que impide que un "
            "recurso genérico se rotule después como un lugar o un hecho real."
        )
    return {
        "archivo": archivo,
        "sha256": sha256(ruta) if ruta else None,
        "costo": costo,
        "generado": True,
        "sin_texto": True,
        "marca": marca,
        "pieza_id": pieza_id,
        "preset": preset,
        "destino": destino,
        "aspecto": aspecto,
        "prompt": prompt,
        "no_atribuible_a": no_atribuible_a,
        "incompleta": incompleta,
        "avisos": avisos or [],
        "creado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "leer_antes_de": "montar, rotular o publicar",
    }


def escribir(destino_dir: Path, manifiestos: list[dict]) -> Path:
    """Deja el manifiesto junto a los assets, no en otro lado."""
    return studio.escribir_json(Path(destino_dir) / "manifiesto.json", manifiestos)
