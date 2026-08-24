"""Inventario: qué existe de verdad, medido.

Core reutilizable. Un archivo se gana entrar a `assets/` **por estar
medido**, no por haber sido generado. Es la diferencia entre un entregable
y una carpeta con cosas adentro: un PNG de 0 bytes, un video truncado o un
render a medias se ven igual que uno bueno en un listado de archivos.

Por eso el paquete separa dos árboles:

    work/     el proceso: intermedios, descartes, versiones
    assets/   lo que se entrega, y sólo si se pudo medir

Confundirlos es el error caro. `work/` se puede tirar; `assets/` es lo que
el cliente recibe.

La medición usa la stdlib para imágenes —los encabezados de PNG, JPEG,
GIF y WebP alcanzan para ancho y alto— y `ffprobe` para audio y video si
está instalado. Lo que no se puede medir se marca como no medible en vez
de darse por bueno.
"""

from __future__ import annotations

import json
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Any

import studio

IMAGENES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
AV = {".mp4", ".mov", ".webm", ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def dimensiones(p: Path) -> tuple[int, int] | None:
    """Ancho y alto leyendo el encabezado. Sin dependencias."""
    try:
        with p.open("rb") as f:
            cab = f.read(32)
            if cab[:8] == b"\x89PNG\r\n\x1a\n":
                w, h = struct.unpack(">II", cab[16:24])
                return int(w), int(h)
            if cab[:3] == b"GIF":
                w, h = struct.unpack("<HH", cab[6:10])
                return int(w), int(h)
            if cab[:4] == b"RIFF" and cab[8:12] == b"WEBP":
                f.seek(0)
                datos = f.read(40)
                if datos[12:16] == b"VP8X":
                    w = int.from_bytes(datos[24:27], "little") + 1
                    h = int.from_bytes(datos[27:30], "little") + 1
                    return w, h
                return None
            if cab[:2] == b"\xff\xd8":  # JPEG: recorrer los segmentos
                f.seek(2)
                while True:
                    b = f.read(1)
                    if not b:
                        return None
                    if b != b"\xff":
                        continue
                    marcador = f.read(1)
                    while marcador == b"\xff":
                        marcador = f.read(1)
                    if marcador in (b"\xc0", b"\xc1", b"\xc2", b"\xc3"):
                        f.read(3)
                        h, w = struct.unpack(">HH", f.read(4))
                        return int(w), int(h)
                    largo = struct.unpack(">H", f.read(2))[0]
                    f.seek(largo - 2, 1)
    except Exception:
        return None
    return None


def duracion(p: Path) -> float | None:
    """Segundos, vía ffprobe. None si no está instalado o el archivo no sirve."""
    if not shutil.which("ffprobe"):
        return None
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(p)],
            capture_output=True, text=True, timeout=30,
        )
        return round(float(r.stdout.strip()), 2)
    except Exception:
        return None


def medir(p: Path) -> dict:
    """Medición de un archivo. `medible` es el campo que decide."""
    p = Path(p)
    if not p.is_file():
        return {"archivo": p.name, "medible": False, "problema": "no existe"}

    bytes_ = p.stat().st_size
    m: dict[str, Any] = {"archivo": p.name, "bytes": bytes_, "medible": bytes_ > 0}
    if bytes_ == 0:
        m["problema"] = "0 bytes"
        return m

    ext = p.suffix.lower()
    if ext in IMAGENES:
        d = dimensiones(p)
        if d:
            m["ancho"], m["alto"] = d
            m["aspecto"] = _aspecto(*d)
        else:
            m["medible"] = False
            m["problema"] = "no se pudieron leer las dimensiones: puede estar truncado"
    elif ext in AV:
        s = duracion(p)
        if s is not None:
            m["duracion_s"] = s
            if s <= 0:
                m["medible"] = False
                m["problema"] = "duración cero"
        else:
            m["medible"] = shutil.which("ffprobe") is None
            m["problema"] = (
                "sin ffprobe no se puede medir; se asume presente pero no verificado"
                if shutil.which("ffprobe") is None
                else "ffprobe no pudo leerlo: probablemente truncado"
            )
    return m


def _aspecto(w: int, h: int) -> str:
    from math import gcd

    g = gcd(w, h) or 1
    a, b = w // g, h // g
    for nombre, (x, y) in {"9:16": (9, 16), "4:5": (4, 5), "1:1": (1, 1),
                           "16:9": (16, 9), "3:4": (3, 4)}.items():
        if abs(w / h - x / y) < 0.02:
            return nombre
    return f"{a}:{b}"


def construir(carpeta: str | Path) -> dict:
    """Inventario de un paquete, conservando la procedencia del manifiesto.

    El disco no sabe qué prompt produjo un archivo. Por eso el manifiesto
    se lee y se cruza: si se pierde, se pierde el único registro de qué es
    cada cosa y a qué no puede atribuirse.
    """
    carpeta = Path(carpeta).expanduser()
    assets = carpeta / "assets"
    manifiesto = {}
    mp = carpeta / "manifiesto.json"
    if mp.is_file():
        try:
            manifiesto = {m["archivo"]: m for m in json.loads(mp.read_text(encoding="utf-8"))}
        except (json.JSONDecodeError, KeyError, TypeError):
            manifiesto = {}

    items = []
    if assets.is_dir():
        for f in sorted(assets.rglob("*")):
            if not f.is_file() or f.name.startswith("."):
                continue
            m = medir(f)
            proc = manifiesto.get(f.name, {})
            items.append({
                **m,
                "ruta": str(f.relative_to(carpeta)),
                "procedencia": {
                    k: proc.get(k)
                    for k in ("generado", "sin_texto", "prompt", "preset",
                              "no_atribuible_a", "pieza_id", "marca")
                    if k in proc
                } or None,
            })

    huerfanos = [n for n in manifiesto if not (assets / n).is_file()]
    return {
        "carpeta": str(carpeta),
        "assets": items,
        "total": len(items),
        "medibles": sum(1 for i in items if i["medible"]),
        "sin_procedencia": [i["archivo"] for i in items if not i["procedencia"]],
        "en_manifiesto_pero_no_en_disco": huerfanos,
    }


def verificar(carpeta: str | Path) -> dict:
    """Falla por tres cosas, todas reales.

    - **no medible** — un PNG de 0 bytes, un audio truncado
    - **desincronizado** — el manifiesto declara un archivo que el disco no
      tiene, o al revés
    - **sin procedencia** — un asset del que no se sabe qué prompt lo hizo
      ni a qué no puede atribuirse

    Un asset cuenta como entregado sólo cuando pasó las tres.
    """
    inv = construir(carpeta)
    problemas = []
    for i in inv["assets"]:
        if not i["medible"]:
            problemas.append({"archivo": i["archivo"], "tipo": "no medible",
                              "detalle": i.get("problema")})
    for n in inv["en_manifiesto_pero_no_en_disco"]:
        problemas.append({"archivo": n, "tipo": "desincronizado",
                          "detalle": "está en el manifiesto pero no en disco"})
    for n in inv["sin_procedencia"]:
        problemas.append({"archivo": n, "tipo": "sin procedencia",
                          "detalle": "no se sabe qué prompt lo produjo ni a qué no puede atribuirse"})
    # Un asset es entregable sólo si cumple las dos condiciones a la vez.
    # Restar los conjuntos daría negativo cuando se solapan: un archivo de
    # 0 bytes sin procedencia cuenta una sola vez, no dos.
    sin_proc = set(inv["sin_procedencia"])
    entregables = sum(
        1 for i in inv["assets"] if i["medible"] and i["archivo"] not in sin_proc
    )
    return {
        "carpeta": inv["carpeta"],
        "ok": not problemas,
        "assets": inv["total"],
        "entregables": entregables,
        "problemas": problemas,
    }


def escribir(carpeta: str | Path) -> Path:
    return studio.escribir_json(Path(carpeta) / "inventario.json", construir(carpeta))
