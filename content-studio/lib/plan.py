"""El plan de contenidos: marcas, grilla, piezas y guiones.

Core reutilizable. Este módulo sabe la FORMA de un plan de contenidos de
agencia —una cartera de marcas, cada una con su ficha, su grilla semanal y
sus piezas fechadas— pero no conoce ninguna marca concreta. Las marcas
entran por el pack.

Dos reglas de este módulo que no son negociables y por eso viven acá y no
en el pack:

**No se acuñan ids.** Un id de pieza es permanente y de él cuelgan los
comentarios del cliente. Un id inventado que después colisiona con el real
no se puede deshacer sin perder esos comentarios. Los assets se adjuntan a
un id existente, o van a un área de staging sin id.

**El hueco se reporta con nombre.** Una fuente incompleta no se completa
con un valor plausible: se devuelve el nombre de lo que falta. En la
práctica es el camino por defecto, no el caso borde — una cartera recién
cargada tiene casi todas las marcas sin calendario.
"""

from __future__ import annotations

import re
from typing import Any

import studio
from studio import GateError, StudioError

# Tri-estado de permisos editoriales. La ausencia NO es permiso: una marca
# que no figura en la política de la agencia es un dato faltante, y se
# bloquea preguntando en vez de heredar el permiso de sus vecinas.
PERMITIDO = "permitido"
PROHIBIDO = "prohibido"
NO_DECLARADO = "no_declarado"

RE_ID_PIEZA = re.compile(r"^[a-z0-9-]+-\d{4}-\d{2}-s\d+-[a-z]+$")


def marcas(pack: dict | None = None) -> dict[str, dict]:
    pack = pack or studio.cargar_pack()
    return pack.get("marcas") or {}


def marca(slug: str, pack: dict | None = None) -> dict:
    """Una marca del pack, o un error que dice cuáles hay."""
    pack = pack or studio.cargar_pack()
    todas = marcas(pack)
    if slug in todas:
        return {**todas[slug], "slug": slug}
    # Tolerar el nombre visible además del slug: quien escribe el nombre de
    # la marca no se está equivocando, sólo no memorizó el slug.
    for s, m in todas.items():
        if studio.slug(m.get("nombre", "")) == studio.slug(slug):
            return {**m, "slug": s}
    raise StudioError(
        f"La marca {slug!r} no está en el pack {pack.get('nombre')!r}. "
        f"Marcas disponibles: {', '.join(sorted(todas)) or 'ninguna'}."
    )


def permiso(m: dict, clave: str) -> str:
    """Permiso editorial de una marca: permitido, prohibido o no declarado.

    El default es `no_declarado` a propósito. Es la diferencia entre "esta
    marca puede usar trends" y "nadie escribió si esta marca puede usar
    trends", y sólo la segunda justifica preguntar antes de producir.
    """
    valor = (m.get("permisos") or {}).get(clave)
    if valor in (PERMITIDO, PROHIBIDO):
        return valor
    return NO_DECLARADO


def piezas(m: dict, anio: int | None = None, mes: int | None = None) -> list[dict]:
    """Piezas fechadas de una marca, opcionalmente filtradas por mes."""
    salida: list[dict] = []
    for mm in m.get("meses") or []:
        if anio is not None and mm.get("anio") != anio:
            continue
        if mes is not None and mm.get("mes") != mes:
            continue
        for semana in mm.get("semanas") or []:
            for p in semana.get("piezas") or []:
                salida.append(
                    {
                        **p,
                        "marca": m["slug"],
                        "anio": mm.get("anio"),
                        "mes": mm.get("mes"),
                        "semana": semana.get("numero"),
                        "tema": semana.get("tema"),
                    }
                )
    return salida


def pieza(id_pieza: str, pack: dict | None = None) -> dict:
    """Busca una pieza por su id en toda la cartera.

    Falla si no existe, y el mensaje explica por qué no se puede inventar.
    """
    pack = pack or studio.cargar_pack()
    for slug_marca in marcas(pack):
        m = marca(slug_marca, pack)
        for p in piezas(m):
            if p.get("id") == id_pieza:
                return p
    raise GateError(
        f"No existe ninguna pieza con id {id_pieza!r} en el pack.",
        entregable={
            "regla": "no se acuñan ids de pieza",
            "por_que": (
                "Los ids son permanentes y de ellos cuelgan los comentarios "
                "del cliente. Uno inventado colisiona de forma irreversible "
                "cuando se cargue el mes real."
            ),
            "opciones": [
                "Adjuntar el asset a un id que ya exista (studio_piezas los lista).",
                "Mandarlo a staging: <marca>/sin-mes/, sin fecha en el nombre.",
                "Cargar el mes en la fuente y volver a importar el plan.",
            ],
        },
    )


def guiones(m: dict) -> list[dict]:
    return m.get("guiones") or []


def guion(m: dict, id_guion: str) -> dict | None:
    return next((g for g in guiones(m) if g.get("id") == id_guion), None)


def slot(m: dict, funcion: str) -> dict | None:
    """Fila de la grilla semanal para una función (atrae/demuestra/convierte)."""
    for fila in m.get("grilla") or []:
        if fila.get("funcion") == funcion:
            return fila
    return None


# ------------------------------------------------------------------ huecos


def huecos(m: dict) -> list[dict]:
    """Qué le falta a una marca para poder producirse sin inventar nada.

    Es una lista de campos con nombre, no un booleano. La diferencia
    importa: "falta el WhatsApp de la marca" se puede pedir; "la marca está
    incompleta" no le sirve a nadie.
    """
    faltan: list[dict] = []

    if not (m.get("meses") or []):
        faltan.append(
            {
                "campo": "meses",
                "detalle": "No hay ningún mes armado, así que no hay ids de pieza.",
                "consecuencia": "Los assets sólo pueden ir a staging, sin id.",
            }
        )

    iv = m.get("identidad_visual") or {}
    if not iv.get("disponible"):
        faltan.append(
            {
                "campo": "identidad_visual",
                "detalle": "Faltan: " + ", ".join(iv.get("faltan") or ["logo", "paleta", "tipografia"]),
                "consecuencia": (
                    "Las piezas salen marcadas `incompleta` y sin marca gráfica. "
                    "No se elige una tipografía ni una paleta plausible: una placa "
                    "que parece terminada puede llegar a publicarse."
                ),
            }
        )

    conv = m.get("conversion") or {}
    if not conv.get("canal"):
        faltan.append(
            {
                "campo": "conversion.canal",
                "detalle": "No hay WhatsApp, formulario ni link donde caiga el CTA.",
                "consecuencia": "Los CTA de esta marca caen al vacío y la métrica no mide nada.",
            }
        )

    for clave in ("trend", "humor", "crudo"):
        if permiso(m, clave) == NO_DECLARADO:
            faltan.append(
                {
                    "campo": f"permisos.{clave}",
                    "detalle": f"No está declarado si esta marca puede usar {clave}.",
                    "consecuencia": (
                        "Se bloquea y se pregunta. No se hereda de otra marca del "
                        "mismo cluster: dentro de un cluster conviven marcas con el "
                        "permiso dado y marcas con el permiso vedado por escrito."
                    ),
                }
            )

    if not m.get("inventario"):
        faltan.append(
            {
                "campo": "inventario",
                "detalle": "No se declara qué fotos, videos o testimonios ya existen.",
                "consecuencia": (
                    "No se puede saber si un slot probatorio se cubre con material "
                    "propio o hay que agendar rodaje."
                ),
            }
        )

    for h in m.get("huecos") or []:
        faltan.append({"campo": "declarado", "detalle": h, "consecuencia": ""})

    return faltan


def cobertura(pack: dict | None = None) -> dict:
    """Estado de toda la cartera de un vistazo.

    Sirve para lo mismo que un `git status`: saber en qué punto está el
    trabajo antes de empezar a producir.
    """
    pack = pack or studio.cargar_pack()
    filas = []
    for slug_marca in sorted(marcas(pack)):
        m = marca(slug_marca, pack)
        ps = piezas(m)
        filas.append(
            {
                "marca": slug_marca,
                "nombre": m.get("nombre"),
                "piezas": len(ps),
                "guiones": len(guiones(m)),
                "meses": len(m.get("meses") or []),
                "huecos": len(huecos(m)),
                "sector_regulado": bool(m.get("sector_regulado")),
                "identidad_visual": bool((m.get("identidad_visual") or {}).get("disponible")),
            }
        )
    return {
        "pack": pack.get("nombre"),
        "marcas": len(filas),
        "piezas_totales": sum(f["piezas"] for f in filas),
        "marcas_sin_calendario": [f["marca"] for f in filas if f["piezas"] == 0],
        "detalle": filas,
    }


# -------------------------------------------------------------------- ids


def validar_id(id_pieza: str, convenciones: dict[str, Any] | None = None) -> bool:
    """¿Tiene forma de id de pieza? No dice si existe: eso lo dice `pieza()`."""
    patron = (convenciones or {}).get("re_id_pieza")
    return bool(re.match(patron, id_pieza) if patron else RE_ID_PIEZA.match(id_pieza))


def destino_staging(m: dict) -> str:
    """Dónde van los assets de una marca que todavía no tiene calendario.

    Sin fecha en el nombre, a propósito: una fecha en el path de staging se
    lee después como si la pieza estuviera programada para ese día.
    """
    return f"{m['slug']}/sin-mes"
