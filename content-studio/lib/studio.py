"""Núcleo de content-studio: configuración, packs y errores accionables.

Este archivo es el **core reutilizable**. No contiene el nombre de ninguna
marca, ningún cliente ni ninguna agencia: sólo sabe cómo encontrar un pack
y cómo fallar de forma útil.

Todo lo que identifica a una agencia concreta —sus clientes, sus presets,
su voz, sus palabras clave de conversión— vive en `packs/<agencia>/`, que
por defecto se busca fuera del repositorio. Ver `packs/README.md`.

Sin dependencias fuera de la stdlib: el Python de Homebrew está bajo
PEP 668 y no queremos forzar `--break-system-packages`.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

PLUGIN = "content-studio"
PACK_FILE = "pack.json"

# Directorio de configuración del usuario. Los packs reales viven acá y no
# en el repositorio, porque un pack contiene datos de negocio de clientes
# de terceros: direcciones, aranceles, nombres de profesionales, y qué
# puede y qué no puede decir cada cuenta.
CONFIG_DIR = Path(os.environ.get("STUDIO_CONFIG_DIR", Path.home() / ".config" / PLUGIN))


class StudioError(RuntimeError):
    """Falla operativa. El mensaje siempre dice qué hacer."""


class PackError(StudioError):
    """No hay pack, o el que hay no se puede leer."""


class GateError(StudioError):
    """Una regla del core bloqueó la operación.

    No es un fallo del programa: es el programa haciendo su trabajo. Quien
    la reciba no debe reintentar ni reformular el pedido para esquivarla —
    debe leer el `entregable` que la acompaña, que dice cómo resolverlo
    bien.
    """

    def __init__(self, mensaje: str, entregable: dict | None = None):
        super().__init__(mensaje)
        self.entregable = entregable or {}


# --------------------------------------------------------------- ubicación


def pack_dir(explicito: str | os.PathLike | None = None) -> Path | None:
    """Directorio del pack activo, o None si no hay ninguno configurado.

    Un path explícito es una afirmación sobre QUÉ agencia usar: si no
    existe, fallamos en vez de buscar en otro lado. Usar el pack de otro
    cliente en silencio es peor que un error.
    """
    if explicito:
        p = Path(explicito).expanduser()
        if not (p / PACK_FILE).is_file():
            raise PackError(
                f"El pack indicado ({p}) no tiene {PACK_FILE}. No busco en otro "
                "lado: usar el pack equivocado publica el contenido de un "
                "cliente con la voz de otro."
            )
        return p

    env = os.environ.get("STUDIO_PACK")
    if env:
        p = Path(env).expanduser()
        if not (p / PACK_FILE).is_file():
            raise PackError(
                f"STUDIO_PACK apunta a {p}, que no tiene {PACK_FILE}. "
                "Corregí la variable o quitala."
            )
        return p

    nombre = os.environ.get("STUDIO_PACK_NAME")
    if nombre:
        for base in (CONFIG_DIR / "packs", Path(__file__).resolve().parents[1] / "packs"):
            p = base / nombre
            if (p / PACK_FILE).is_file():
                return p
        raise PackError(
            f"No encontré el pack {nombre!r}. Busqué en {CONFIG_DIR / 'packs'} "
            "y en los packs incluidos en el plugin."
        )

    # Sin variables: si hay exactamente un pack real instalado, se usa ése.
    # Con varios no se elige por orden alfabético — se pregunta.
    reales = [p for p in packs_disponibles() if not p["nombre"].startswith("_")]
    if len(reales) == 1:
        return Path(reales[0]["path"])
    return None


def packs_disponibles() -> list[dict]:
    """Packs instalados, en el config del usuario y en el plugin."""
    salida: list[dict] = []
    for base, origen in (
        (CONFIG_DIR / "packs", "config"),
        (Path(__file__).resolve().parents[1] / "packs", "plugin"),
    ):
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if (d / PACK_FILE).is_file():
                salida.append({"nombre": d.name, "path": str(d), "origen": origen})
    return salida


def cargar_pack(explicito: str | os.PathLike | None = None) -> dict:
    """Pack activo ya parseado, con `_dir` agregado."""
    d = pack_dir(explicito)
    if d is None:
        disponibles = [p["nombre"] for p in packs_disponibles()]
        raise PackError(
            "No hay ningún pack activo, así que no sé de qué agencia ni de qué "
            "marcas estamos hablando. El core no trae ningún cliente adentro, "
            "a propósito.\n"
            f"Packs instalados: {disponibles or 'ninguno'}.\n"
            "Elegí uno con STUDIO_PACK_NAME, apuntá STUDIO_PACK a un directorio "
            f"con {PACK_FILE}, o importá un plan con studio_importar."
        )
    try:
        data = json.loads((d / PACK_FILE).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise PackError(f"{d / PACK_FILE} no es JSON válido: {e}") from e
    data["_dir"] = str(d)
    return data


# ------------------------------------------------------------------ salida


def out_dir() -> Path:
    """Dónde se dejan los paquetes producidos.

    Relativo al directorio donde corre el servidor, que es el proyecto en
    el que se está trabajando — no el del plugin.
    """
    return Path(os.environ.get("STUDIO_OUT", "./studio-out")).expanduser()


def escribir_json(destino: Path, data: Any) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return destino


def slug(texto: str) -> str:
    n = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", n.lower())).strip("-")


def normalizar(texto: str) -> str:
    """Minúsculas sin tildes, para comparar texto de forma robusta.

    Se usa en la blocklist: `«90 días»` y `«90 dias»` son la misma frase
    prohibida, y quien la escriba de la segunda forma no está esquivando
    nada a propósito — pero el resultado publicado es el mismo.
    """
    n = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in n if not unicodedata.combining(c))
