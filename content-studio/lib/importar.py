"""Importar un plan de contenidos a un pack.

Core reutilizable. La fuente de verdad de un plan vive donde la agencia ya
la tiene —una app, una planilla, un CMS— y este módulo la normaliza al
esquema del pack sin pretender reemplazarla.

Dos decisiones que valen la pena explicar:

**La entrada canónica es JSON, no TypeScript.** Parsear TS desde Python es
frágil y se rompe con cualquier refactor de quien mantiene la fuente. Si el
plan vive en un proyecto TS, ese proyecto sabe compilarlo: se corre
`scripts/exportar-plan.mjs` con su propio toolchain y se importa el JSON
resultante. El extractor de literales que hay más abajo es una comodidad
para arrancar, no el camino recomendado.

**Importar no completa nada.** Lo que la fuente no trae queda declarado
como hueco con su nombre. Un importador que rellena con valores plausibles
produce exactamente el problema que el resto del plugin existe para evitar.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import studio
from studio import StudioError

# Rubros que activan el gate de sector regulado. Se infiere para no
# depender de que alguien se acuerde de marcarlo, pero queda sobrescribible
# en el pack: un falso negativo acá es una promesa clínica publicada.
INDICIOS_REGULADO = [
    "salud", "médic", "medic", "clínic", "clinic", "farmac", "odontol",
    "diagnóstic", "diagnostic", "terapia", "tratamiento", "paciente",
    "sanitari", "bioquímic", "bioquimic", "laboratorio", "nutrici",
    "financier", "banc", "seguro", "crédit", "credit", "legal", "jurídic",
]


def es_regulado(marca: dict) -> bool:
    texto = studio.normalizar(
        " ".join(str(marca.get(k, "")) for k in ("rubro", "nombre"))
        + " " + str((marca.get("ficha") or {}).get("cluster", ""))
    )
    return any(studio.normalizar(i) in texto for i in INDICIOS_REGULADO)


def normalizar_marca(slug: str, cruda: dict) -> dict:
    """Lleva una marca de la fuente al esquema del pack.

    Los campos que el core necesita y la fuente no suele tener —permisos
    editoriales, identidad visual, canal de conversión, inventario— quedan
    explícitamente vacíos, nunca inventados. `plan.huecos()` los reporta
    después con nombre.
    """
    ficha = cruda.get("ficha") or {}
    return {
        "nombre": cruda.get("nombre") or slug,
        "numero": cruda.get("numero"),
        "rubro": cruda.get("rubro"),
        "ficha": {
            "objetivo": ficha.get("objetivo"),
            "frecuencia": ficha.get("frecuencia"),
            "plataforma": ficha.get("plataforma"),
            "metrica": ficha.get("metrica"),
            "tono": ficha.get("tono"),
            "cluster": ficha.get("cluster"),
        },
        "voz": cruda.get("voz") or {"tono": ficha.get("tono"), "muletillas": []},
        # Tri-estado: la ausencia bloquea y pregunta. No se hereda del cluster.
        "permisos": cruda.get("permisos") or {},
        "sector_regulado": cruda.get("sector_regulado", es_regulado(cruda)),
        "grilla": cruda.get("grilla") or [],
        "tipos": cruda.get("tipos") or [],
        "guiones": cruda.get("guiones") or [],
        "meses": cruda.get("meses") or [],
        "conversion": cruda.get("conversion") or {},
        "identidad_visual": cruda.get("identidad_visual") or {
            "disponible": False,
            "faltan": ["logo", "paleta", "tipografia"],
        },
        "inventario": cruda.get("inventario") or [],
        "prohibido": cruda.get("prohibido") or [],
        "presets": cruda.get("presets") or [],
        "audio": cruda.get("audio") or {},
        "validar": _lista(cruda.get("validar")),
        "responsable": cruda.get("responsable"),
        "huecos": cruda.get("huecos") or [],
    }


def _lista(v: Any) -> list[str]:
    if not v:
        return []
    if isinstance(v, str):
        return [t.strip() for t in re.split(r"[;\n]", v) if t.strip()]
    return list(v)


def construir_pack(
    nombre: str,
    marcas_crudas: dict[str, dict],
    *,
    agencia: str | None = None,
    pares_peligrosos: list[list[str]] | None = None,
    presets: dict[str, dict] | None = None,
) -> dict:
    marcas = {s: normalizar_marca(s, m) for s, m in marcas_crudas.items()}
    return {
        "nombre": nombre,
        "agencia": agencia or nombre,
        "descripcion": f"Plan de contenidos de {agencia or nombre}",
        "convenciones": {
            "id_pieza": "<slug>-<anio>-<mm>-s<semana>-<dia>",
            "id_guion": "<slug>-guion-<sufijo>",
        },
        "marcas": marcas,
        "pares_peligrosos": pares_peligrosos or sugerir_pares(marcas),
        "presets": presets or {},
    }


def sugerir_pares(marcas: dict[str, dict]) -> list[list[str]]:
    """Pares de marcas que se confundirían entre sí, por cluster o rubro.

    Es una sugerencia para revisar a mano, no un veredicto: quien conoce la
    cartera sabe cuáles se parecen de verdad. Pero arrancar con la lista
    vacía garantiza que el gate de contaminación de voz no proteja nada.
    """
    pares: set[tuple[str, str]] = set()
    items = list(marcas.items())
    for i, (a, ma) in enumerate(items):
        for b, mb in items[i + 1:]:
            cluster_a = (ma.get("ficha") or {}).get("cluster")
            cluster_b = (mb.get("ficha") or {}).get("cluster")
            mismo_cluster = cluster_a and cluster_a == cluster_b
            rubro_a = studio.normalizar(ma.get("rubro") or "")
            rubro_b = studio.normalizar(mb.get("rubro") or "")
            comparten = bool(set(rubro_a.split()) & set(rubro_b.split()) - {"y", "de", "para"})
            if mismo_cluster or comparten:
                pares.add(tuple(sorted((a, b))))
    return [list(p) for p in sorted(pares)]


# ------------------------------------------------------------------ entradas


def desde_json(ruta: str | Path) -> dict[str, dict]:
    """Marcas desde un JSON. Acepta `{slug: marca}` o una lista con `slug`."""
    data = json.loads(Path(ruta).expanduser().read_text(encoding="utf-8"))
    if isinstance(data, dict) and "marcas" in data:
        data = data["marcas"]
    if isinstance(data, list):
        salida = {}
        for m in data:
            s = m.get("slug") or studio.slug(m.get("nombre", ""))
            if not s:
                raise StudioError("Hay una marca sin `slug` ni `nombre` en el JSON.")
            salida[s] = m
        return salida
    if isinstance(data, dict):
        return data
    raise StudioError("El JSON no tiene forma de plan: esperaba objeto o lista de marcas.")


def desde_ts(directorio: str | Path) -> dict[str, dict]:
    """Extractor tolerante de literales TS. Comodidad, no camino recomendado.

    Lee lo que puede de `export const X = {...}` y avisa de lo que no. Si la
    fuente usa imports, spreads o valores calculados, esto los pierde en
    silencio — por eso `scripts/exportar-plan.mjs` existe y es lo que
    conviene usar cuando el plan importa de verdad.
    """
    d = Path(directorio).expanduser()
    if not d.is_dir():
        raise StudioError(f"{d} no es un directorio.")

    marcas: dict[str, dict] = {}
    for archivo in sorted(d.glob("*.ts")):
        if archivo.stem in ("index", "tipos", "esquemas") or archivo.stem.endswith(".test"):
            continue
        texto = archivo.read_text(encoding="utf-8")
        cuerpo = _objeto_literal(texto)
        if cuerpo is None:
            continue
        try:
            marcas[archivo.stem] = json.loads(_ts_a_json(cuerpo))
        except json.JSONDecodeError:
            marcas[archivo.stem] = {
                "nombre": _campo(texto, "nombre") or archivo.stem,
                "rubro": _campo(texto, "rubro"),
                "huecos": [
                    f"No se pudo parsear {archivo.name} como literal. Exportalo "
                    "con scripts/exportar-plan.mjs, que usa el toolchain del proyecto."
                ],
            }
    if not marcas:
        raise StudioError(
            f"No encontré marcas en {d}. Si el plan vive en TypeScript, usá "
            "scripts/exportar-plan.mjs para exportarlo a JSON y after importá eso."
        )
    return marcas


def _objeto_literal(texto: str) -> str | None:
    m = re.search(r"export\s+const\s+\w+[^=]*=\s*(?:\w+\.parse\()?\s*\{", texto)
    if not m:
        return None
    inicio = texto.index("{", m.end() - 1)
    prof = 0
    for i in range(inicio, len(texto)):
        if texto[i] == "{":
            prof += 1
        elif texto[i] == "}":
            prof -= 1
            if prof == 0:
                return texto[inicio: i + 1]
    return None


def _ts_a_json(cuerpo: str) -> str:
    s = re.sub(r"//[^\n]*", "", cuerpo)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"\bas const\b", "", s)
    s = re.sub(r"(?m)^(\s*)([A-Za-z_]\w*)\s*:", r'\1"\2":', s)   # claves sin comillas
    s = re.sub(r",(\s*[}\]])", r"\1", s)                          # comas finales
    s = s.replace("“", '"').replace("”", '"')
    return s


def _campo(texto: str, nombre: str) -> str | None:
    m = re.search(rf'{nombre}\s*:\s*"([^"]*)"', texto)
    return m.group(1) if m else None


# ------------------------------------------------------------------ escritura


def escribir_pack(pack: dict, destino: str | Path) -> dict:
    d = Path(destino).expanduser()
    (d / "presets").mkdir(parents=True, exist_ok=True)
    limpio = {k: v for k, v in pack.items() if not k.startswith("_")}
    studio.escribir_json(d / studio.PACK_FILE, limpio)

    import plan as _plan

    resumen = _plan.cobertura({**limpio, "_dir": str(d)})
    (d / "README.md").write_text(_readme(limpio, resumen), encoding="utf-8")
    return {
        "pack": str(d),
        "marcas": resumen["marcas"],
        "piezas": resumen["piezas_totales"],
        "sin_calendario": resumen["marcas_sin_calendario"],
        "siguiente": (
            "Revisá el pack: los permisos editoriales, el canal de conversión y "
            "la identidad visual quedaron vacíos a propósito. Cargalos antes de "
            "producir, o el core va a bloquear pidiéndolos."
        ),
    }


def _readme(pack: dict, resumen: dict) -> str:
    filas = "\n".join(
        f"| `{f['marca']}` | {f['nombre']} | {f['piezas']} | {f['guiones']} | "
        f"{f['huecos']} | {'sí' if f['sector_regulado'] else 'no'} |"
        for f in resumen["detalle"]
    )
    return f"""# Pack `{pack.get('nombre')}`

{pack.get('descripcion', '')}

Generado con `studio_importar`. **Este directorio no va a git**: contiene
datos de negocio de clientes de terceros.

| Marca | Nombre | Piezas | Guiones | Huecos | Regulado |
|---|---|---|---:|---:|---|
{filas}

- Marcas: {resumen['marcas']}
- Piezas con id: {resumen['piezas_totales']}
- Sin calendario: {', '.join(resumen['marcas_sin_calendario']) or 'ninguna'}

## Antes de producir

Los campos que la fuente no trae quedaron vacíos y el core los va a pedir:

- `permisos` — trend, humor y crudo, por marca. La ausencia **bloquea**: no
  se hereda de otra marca del mismo cluster.
- `conversion` — canal y palabra clave. Sin esto, todo CTA cae al vacío.
- `identidad_visual` — logo, paleta, tipografía. Sin esto las piezas salen
  marcadas `incompleta`, que es lo correcto: una placa que parece terminada
  puede llegar a publicarse.
- `prohibido` — las frases que cada cliente vedó.
- `pares_peligrosos` — revisá la lista sugerida: está inferida por cluster y
  rubro, y quien conoce la cartera sabe cuáles se confunden de verdad.

Listalos en cualquier momento con `studio_huecos`.
"""
