#!/usr/bin/env python3
"""Servidor MCP de content-studio.

JSON-RPC 2.0 sobre stdio con la stdlib solamente. Corre tal cual:

    printf '%s\\n' \\
      '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{}}}' \\
      '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \\
      | python3 content-studio/mcp/server.py

Las herramientas no producen contenido: lo habilitan o lo frenan. La
redacción del copy y la generación del asset las hace el agente —o el
plugin `google-flow`— y este servidor dice qué se puede producir, con qué
formato, y qué queda pendiente de validar.

Nada específico de una agencia vive acá. Eso va en `packs/<agencia>/`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

import applets  # noqa: E402
import campos  # noqa: E402
import formatos  # noqa: E402
import gates  # noqa: E402
import importar  # noqa: E402
import inventario  # noqa: E402
import labs  # noqa: E402
import paquete  # noqa: E402
import plan  # noqa: E402
import studio  # noqa: E402
from studio import GateError, PackError, StudioError  # noqa: E402

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "content-studio"
SERVER_VERSION = "0.1.0"

TOOLS: list[dict] = []
HANDLERS: dict[str, Callable[[dict], Any]] = {}


def tool(name: str, description: str, schema: dict, **anotaciones):
    def deco(fn):
        TOOLS.append(
            {
                "name": name,
                "description": description,
                "inputSchema": {
                    "type": "object",
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", []),
                },
                "annotations": {"title": anotaciones.pop("title", name), **anotaciones},
            }
        )
        HANDLERS[name] = fn
        return fn

    return deco


def _marca(args: dict) -> tuple[dict, dict]:
    pack = studio.cargar_pack(args.get("pack"))
    return plan.marca(args["marca"], pack), pack


# ------------------------------------------------------------------ estado


@tool(
    "studio_estado",
    "Estado del plan: qué pack está activo, cuántas marcas tiene, cuáles no "
    "tienen calendario y si la sesión de Flow sirve. Es local salvo por el "
    "chequeo de sesión, no gasta nada, y conviene correrlo ANTES de la "
    "primera operación de una sesión de trabajo para saber sobre qué cartera "
    "se está trabajando.",
    {"properties": {
        "pack": {"type": "string", "description": "Ruta a un pack. Opcional."},
        "con_sesion": {"type": "boolean", "description": "Chequear también la sesión de labs.google. Por defecto sí."},
    }},
    title="Estado del plan",
    readOnlyHint=True,
)
def _estado(args: dict) -> dict:
    salida: dict[str, Any] = {"packs_instalados": studio.packs_disponibles()}
    try:
        salida["cobertura"] = plan.cobertura(studio.cargar_pack(args.get("pack")))
    except PackError as e:
        salida["pack"] = None
        salida["problema"] = str(e)

    if args.get("con_sesion", True):
        try:
            salida["flow"] = labs.estado()
        except labs.LabsAuthError as e:
            salida["flow"] = {"valida": False, "problema": str(e).split("\n")[0]}
    return salida


@tool(
    "studio_marca",
    "Ficha completa de una marca: objetivo, plataforma, métrica, tono, voz, "
    "grilla semanal, permisos editoriales, qué hay que validar y qué frases "
    "tiene prohibidas. Leelo ANTES de escribir un copy o pedir un asset para "
    "esa marca — la voz es intransferible y el tono es parte del producto.",
    {"properties": {
        "marca": {"type": "string", "description": "Slug o nombre de la marca."},
        "pack": {"type": "string"},
    }, "required": ["marca"]},
    title="Ficha de marca",
    readOnlyHint=True,
)
def _marca_tool(args: dict) -> dict:
    m, _ = _marca(args)
    return {
        **{k: v for k, v in m.items() if k not in ("meses",)},
        "permisos_resueltos": {
            k: plan.permiso(m, k) for k in ("trend", "humor", "crudo")
        },
        "piezas_con_id": len(plan.piezas(m)),
        "huecos": len(plan.huecos(m)),
    }


@tool(
    "studio_piezas",
    "Piezas fechadas de una marca, con su id permanente. Usalo para saber a "
    "qué id adjuntar un asset. Si devuelve vacío, la marca no tiene "
    "calendario: el material va a staging SIN id. Nunca inventes un id de "
    "pieza — son permanentes y de ellos cuelgan los comentarios del cliente.",
    {"properties": {
        "marca": {"type": "string"},
        "anio": {"type": "integer"},
        "mes": {"type": "integer", "description": "1 a 12."},
        "pack": {"type": "string"},
    }, "required": ["marca"]},
    title="Piezas de una marca",
    readOnlyHint=True,
)
def _piezas(args: dict) -> dict:
    m, _ = _marca(args)
    ps = plan.piezas(m, args.get("anio"), args.get("mes"))
    return {
        "marca": m["slug"],
        "piezas": ps,
        "total": len(ps),
        "staging": plan.destino_staging(m) if not ps else None,
        "nota": None if ps else (
            "Esta marca no tiene calendario cargado. Los assets van a staging "
            "sin id. No se acuña un id: uno inventado colisiona de forma "
            "irreversible cuando se cargue el mes real."
        ),
    }


@tool(
    "studio_huecos",
    "Qué le falta a una marca —o a toda la cartera— para poder producir sin "
    "inventar nada: calendario, identidad visual, canal de conversión, "
    "permisos editoriales, inventario de material. Devuelve cada faltante con "
    "nombre y con su consecuencia. Corrélo cuando una marca parezca lista "
    "pero algo no cierre.",
    {"properties": {
        "marca": {"type": "string", "description": "Omitilo para ver toda la cartera."},
        "pack": {"type": "string"},
    }},
    title="Huecos del plan",
    readOnlyHint=True,
)
def _huecos(args: dict) -> dict:
    pack = studio.cargar_pack(args.get("pack"))
    if args.get("marca"):
        m = plan.marca(args["marca"], pack)
        return {"marca": m["slug"], "huecos": plan.huecos(m)}
    return {
        "pack": pack.get("nombre"),
        "por_marca": {
            s: plan.huecos(plan.marca(s, pack)) for s in sorted(plan.marcas(pack))
        },
    }


# ------------------------------------------------------------------- gates


@tool(
    "studio_gate",
    "Evalúa si un asset se puede generar, ANTES de gastar un crédito. Corre "
    "el clasificador probatorio (¿el asset PRUEBA un hecho o ILUSTRA un "
    "concepto?), el gate de marcas y personas de terceros, el de texto dentro "
    "de la imagen y el contrato de formato. Si bloquea, devuelve un plan de "
    "rodaje o el camino correcto: NO reformules el pedido para esquivarlo.",
    {"properties": {
        "peticion": {"type": "string", "description": "Qué se quiere generar, en palabras."},
        "funcion": {"type": "string", "description": "'prueba' o 'ilustra'. Obligatorio: sin esto se bloquea."},
        "marca": {"type": "string"},
        "destino": {"type": "string", "description": "reel, historia, feed, carrusel, placa, ads, youtube, linkedin."},
        "aspecto": {"type": "string"},
        "pack": {"type": "string"},
    }, "required": ["peticion"]},
    title="Gate de generación",
    readOnlyHint=True,
)
def _gate(args: dict) -> dict:
    peticion = args["peticion"]
    resultados = [
        gates.probatorio(peticion, args.get("funcion")),
        gates.terceros_y_personas(peticion),
        gates.sin_texto(peticion),
    ]
    salida: dict[str, Any] = {}

    if args.get("destino"):
        v = formatos.validar(args["destino"], args.get("aspecto"))
        salida["formato"] = v
        if not v["ok"]:
            resultados.append(
                {"gate": "formato", "estado": gates.AVISO,
                 "hallazgos": v["problemas"], "entregable": {"usar_aspecto": v["contrato"]["aspecto"]}}
            )

    if args.get("marca"):
        m, _ = _marca(args)
        resultados.append(gates.identidad_visual(m))
        salida["marca"] = m["slug"]

    salida["veredicto"] = gates.evaluar(resultados)
    return salida


@tool(
    "studio_revisar",
    "Pasa un copy ya escrito por los gates de texto: frases prohibidas por el "
    "cliente, verbos de resultado en sectores regulados, datos duros que "
    "requieren validación, identidad visual y canal de conversión. Corrélo "
    "SIEMPRE antes de dar por terminado un copy. Los datos duros que vienen "
    "de la fuente se escriben y quedan marcados como pendientes; los que no "
    "están en ninguna fuente bloquean, porque eso es inventarlos.",
    {"properties": {
        "marca": {"type": "string"},
        "copy": {"type": "string", "description": "El texto completo: hook, desarrollo, copy y CTA."},
        "fuentes": {"type": "array", "items": {"type": "string"},
                    "description": "Textos de origen (guión, brief, ficha) donde puede estar cada dato duro. "
                                   "Pasalo SIEMPRE que el copy tenga un precio, un plazo, una fecha o un "
                                   "teléfono: sin fuentes no hay con qué distinguir un dato del brief de uno "
                                   "inventado, y el gate frena. Lista vacía si de verdad no hay fuente."},
        "origen_voz": {"type": "string",
                       "description": "Si el copy se derivó de otra marca, su slug. Dispara el gate de contaminación de voz."},
        "pack": {"type": "string"},
    }, "required": ["marca", "copy", "fuentes"]},
    title="Revisar copy",
    readOnlyHint=True,
)
def _revisar(args: dict) -> dict:
    m, pack = _marca(args)
    return paquete.revisar(
        m, args["copy"],
        fuentes=args.get("fuentes"),
        pack=pack,
        origen_voz=args.get("origen_voz"),
    )


@tool(
    "studio_formato",
    "Contrato de formato de un destino: relación de aspecto, medio y "
    "duración. Resolvelo antes de generar — generar en el aspecto equivocado "
    "obliga a generar dos veces, y es la falla más barata de prevenir.",
    {"properties": {
        "destino": {"type": "string"},
        "aspecto": {"type": "string"},
        "duracion_s": {"type": "number"},
    }, "required": ["destino"]},
    title="Contrato de formato",
    readOnlyHint=True,
    openWorldHint=False,
)
def _formato(args: dict) -> dict:
    return formatos.validar(args["destino"], args.get("aspecto"), args.get("duracion_s"))


def _preset(pack: dict, nombre: str) -> dict:
    presets = pack.get("presets") or {}
    if nombre not in presets:
        raise StudioError(
            f"El preset {nombre!r} no está en el pack. "
            f"Disponibles: {', '.join(sorted(presets)) or 'ninguno'}."
        )
    return presets[nombre]


@tool(
    "studio_campos",
    "Traduce la ficha de una marca a los campos concretos de generación de un "
    "preset: prompt armado, aspecto según destino, y las prohibiciones base ya "
    "escritas adentro del prompt. Usalo ANTES de escribir un prompt a mano — "
    "así el prompt sale de la ficha y no se improvisa en cada pieza. Devuelve "
    "un BORRADOR: la ficha manda, y si algún campo la contradice el error está "
    "en la traducción. Cada campo viene con su origen y con lo que le falta.",
    {"properties": {
        "marca": {"type": "string"},
        "preset": {"type": "string", "description": "Nombre del preset en el pack."},
        "destino": {"type": "string", "description": "reel, feed, carrusel, placa… fija el aspecto."},
        "situacion": {"type": "string", "description": "Lo que cambia entre una pieza y otra."},
        "pack": {"type": "string"},
    }, "required": ["marca", "preset"]},
    title="Ficha a campos",
    readOnlyHint=True,
    openWorldHint=False,
)
def _campos(args: dict) -> dict:
    m, pack = _marca(args)
    return campos.borrador(
        m, _preset(pack, args["preset"]),
        destino=args.get("destino"), situacion=args.get("situacion"),
    )


@tool(
    "studio_matriz",
    "Expande un lote como producto cartesiano de ejes (momento, encuadre, "
    "formato…) para producir una semana o un mes de una vez. Devuelve la cuenta "
    "de variantes ANTES de generar: un lote de tres es una prueba, uno de "
    "veintiocho es una tarde de créditos de otra persona. Probá siempre con dos "
    "o tres antes del lote entero.",
    {"properties": {
        "marca": {"type": "string"},
        "preset": {"type": "string"},
        "ejes": {"type": "object", "description": 'Ejes a combinar, p. ej. {"Momento":["mañana","tarde"]}'},
        "pack": {"type": "string"},
    }, "required": ["marca", "preset", "ejes"]},
    title="Matriz de lote",
    readOnlyHint=True,
    openWorldHint=False,
)
def _matriz(args: dict) -> dict:
    m, pack = _marca(args)
    return campos.matriz(m, _preset(pack, args["preset"]), args["ejes"])


# ---------------------------------------------------------------- entregable


@tool(
    "studio_paquete",
    "Arma la carpeta entregable de una pieza: copy, manifiesto de procedencia "
    "de cada asset con su no-atribución, y pendientes.md con lo que falta "
    "validar y con quién. Usalo al terminar una pieza. Si la marca no tiene "
    "calendario, el paquete va a staging sin id, que es lo correcto.",
    {"properties": {
        "marca": {"type": "string"},
        "copy": {"type": "string"},
        "pieza_id": {"type": "string", "description": "Id existente. Omitilo para staging. Nunca lo inventes."},
        "assets": {"type": "array", "description": "Manifiestos de los assets generados.",
                   "items": {"type": "object"}},
        "fuentes": {"type": "array", "items": {"type": "string"},
                    "description": "Las mismas que usás en studio_revisar: sin ellas el gate de dato frena."},
        "pack": {"type": "string"},
    }, "required": ["marca", "copy", "fuentes"]},
    title="Armar paquete",
)
def _paquete(args: dict) -> dict:
    m, pack = _marca(args)
    pieza_id = args.get("pieza_id")
    if pieza_id:
        plan.pieza(pieza_id, pack)  # existe, o GateError con el camino correcto
    veredicto = paquete.revisar(m, args["copy"], fuentes=args.get("fuentes"), pack=pack)
    if not veredicto["puede_producir"]:
        return {"bloqueado": True, "veredicto": veredicto,
                "nota": "No se escribió nada. Resolvé los bloqueos y volvé a intentar."}
    return {
        "veredicto": veredicto,
        **paquete.armar(m, copy=args["copy"], pieza_id=pieza_id,
                        manifiestos=args.get("assets"), veredicto=veredicto),
    }


@tool(
    "studio_check",
    "Verifica un paquete ya armado: que cada asset se pueda medir de verdad, "
    "que el manifiesto y el disco coincidan, y que ningún archivo esté sin "
    "procedencia. Un asset cuenta como entregado sólo cuando pasó las tres. "
    "Corrélo antes de dar una pieza por terminada — un PNG de 0 bytes y uno "
    "bueno se ven igual en un listado de archivos.",
    {"properties": {
        "carpeta": {"type": "string", "description": "Carpeta del paquete."},
        "escribir_inventario": {"type": "boolean", "description": "Dejar inventario.json. Por defecto no."},
    }, "required": ["carpeta"]},
    title="Verificar paquete",
    readOnlyHint=True,
    openWorldHint=False,
)
def _check(args: dict) -> dict:
    r = inventario.verificar(args["carpeta"])
    if args.get("escribir_inventario"):
        r["inventario"] = str(inventario.escribir(args["carpeta"]))
    return r


# -------------------------------------------------------------------- packs


@tool(
    "studio_importar",
    "Importa un plan de contenidos a un pack nuevo. Acepta un JSON exportado "
    "o un directorio de archivos TypeScript con literales. Lo que la fuente "
    "no trae queda declarado como hueco, nunca completado con un valor "
    "plausible. El pack se escribe fuera del repositorio por defecto: "
    "contiene datos de negocio de clientes.",
    {"properties": {
        "origen": {"type": "string", "description": "Ruta a un JSON o a un directorio con .ts"},
        "nombre": {"type": "string", "description": "Nombre del pack."},
        "agencia": {"type": "string"},
        "destino": {"type": "string", "description": "Por defecto ~/.config/content-studio/packs/<nombre>"},
    }, "required": ["origen", "nombre"]},
    title="Importar plan",
)
def _importar(args: dict) -> dict:
    origen = Path(args["origen"]).expanduser()
    crudas = importar.desde_ts(origen) if origen.is_dir() else importar.desde_json(origen)
    pack = importar.construir_pack(
        args["nombre"], crudas, agencia=args.get("agencia")
    )
    destino = Path(
        args.get("destino") or (studio.CONFIG_DIR / "packs" / args["nombre"])
    ).expanduser()
    return importar.escribir_pack(pack, destino)


# ------------------------------------------------------------------ applets


@tool(
    "studio_applet_spec",
    "Redacta la especificación de una applet de Google Labs Flow a partir de "
    "un preset del pack: controles, vocabularios, y el selector de modelo "
    "obligatorio. Se pega en el agente de Flow para que la construya. El "
    "selector de modelo no es opcional: sin él, una cuota diaria agotada se "
    "ve idéntica a un error transitorio y la reacción natural es reintentar.",
    {"properties": {
        "preset": {"type": "string", "description": "Nombre del preset en el pack."},
        "pack": {"type": "string"},
    }, "required": ["preset"]},
    title="Especificación de applet",
    readOnlyHint=True,
)
def _applet_spec(args: dict) -> dict:
    pack = studio.cargar_pack(args.get("pack"))
    nombre = args["preset"]
    return {
        "preset": nombre,
        "especificacion": applets.desde_preset(nombre, _preset(pack, nombre)),
        "como_usarla": [
            "Abrir labs.google/fx/tools/flow y pedirle al agente que construya la herramienta.",
            "Pegar la especificación tal cual.",
            "Cuando termine, correr studio_applet_descubrir para cablear el appletId.",
            "Y después studio_applet_verificar: el agente de Flow recorta bloques "
            "al copiarlos y reporta el cambio como hecho. No alcanza con que diga "
            "que los puso.",
        ],
    }


@tool(
    "studio_applet_verificar",
    "Baja el código de una applet ya construida y comprueba que cada cláusula "
    "que se le pidió esté adentro. Corrélo después de crear o editar una "
    "applet en Flow, SIEMPRE: el agente de Flow recorta bloques al copiarlos y "
    "reporta el cambio como hecho, y el resultado no delata la pérdida — las "
    "imágenes salen bien igual hasta que una no. Sólo lee: no gasta créditos.",
    {"properties": {
        "applet_id": {"type": "string", "description": "El appletId, como lo devuelve studio_applet_descubrir."},
        "clausulas": {"type": "array", "items": {"type": "string"},
                      "description": "Frases que tienen que estar en el código. "
                                     "Las prohibiciones del prompt son las que más importan."},
    }, "required": ["applet_id", "clausulas"]},
    title="Verificar applet",
    readOnlyHint=True,
)
def _applet_verificar(args: dict) -> dict:
    return applets.verificar(args["applet_id"], args["clausulas"])


@tool(
    "studio_applet_descubrir",
    "Lista las applets de la cuenta de Flow y las mapea contra las que el "
    "pack espera, para cablear los appletId. Corrélo después de crear applets "
    "en Flow. Sólo lee: no crea ni gasta nada.",
    {"properties": {
        "pack": {"type": "string"},
    }},
    title="Descubrir applets",
    readOnlyHint=True,
)
def _applet_descubrir(args: dict) -> dict:
    pack = studio.cargar_pack(args.get("pack"))
    esperadas = {
        nombre: (p.get("titulo") or nombre)
        for nombre, p in (pack.get("presets") or {}).items()
    }
    return applets.descubrir(esperadas)


# ------------------------------------------------------------------ JSON-RPC
# De acá para abajo es infraestructura: es igual para cualquier plugin.


def _result(rid, payload):
    return {"jsonrpc": "2.0", "id": rid, "result": payload}


def _text(rid, payload, is_error=False):
    body = {"content": [{"type": "text", "text": payload}]}
    if is_error:
        body["isError"] = True
    return _result(rid, body)


def handle(msg: dict) -> dict | None:
    method = msg.get("method")
    rid = msg.get("id")

    if method == "initialize":
        # Devolvemos la versión que pida el cliente: los hosts van de
        # 2024-11-05 a 2025-11-25 y fijar una rompe con el resto.
        pedida = (msg.get("params") or {}).get("protocolVersion")
        return _result(rid, {
            "protocolVersion": pedida or PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })

    if method and method.startswith("notifications/"):
        return None

    if method == "ping":
        return _result(rid, {})

    if method == "tools/list":
        return _result(rid, {"tools": TOOLS})

    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        fn = HANDLERS.get(name)
        if fn is None:
            return _text(rid, f"La herramienta {name!r} no existe. "
                              f"Disponibles: {', '.join(sorted(HANDLERS))}", is_error=True)
        args = params.get("arguments") or {}

        # Validar los requeridos contra el propio esquema de la herramienta.
        # Va acá y no en cada handler: un KeyError pelado no le dice a nadie
        # qué falta, y el resto del plugin se toma el trabajo de que cada
        # error diga qué hacer.
        esquema = next((t for t in TOOLS if t["name"] == name), {})
        faltan = [
            c for c in esquema.get("inputSchema", {}).get("required", [])
            if args.get(c) in (None, "")
        ]
        if faltan:
            props = esquema.get("inputSchema", {}).get("properties", {})
            detalle = "\n".join(
                f"  · {c}: {props.get(c, {}).get('description', 'sin descripción')}"
                for c in faltan
            )
            return _text(
                rid,
                f"A {name} le falta: {', '.join(faltan)}.\n{detalle}",
                is_error=True,
            )

        try:
            return _text(rid, json.dumps(fn(args), indent=2, ensure_ascii=False))
        except GateError as e:
            # Un gate no es un error del programa: es el programa haciendo su
            # trabajo. Devolvemos el camino correcto y prohibimos el rodeo.
            return _text(rid, json.dumps({
                "bloqueado_por_gate": str(e),
                "entregable": e.entregable,
                "no_hagas": "No reformules el pedido para esquivar el gate. "
                            "Seguí el entregable, o preguntale al usuario.",
            }, indent=2, ensure_ascii=False), is_error=True)
        except labs.LabsAuthError as e:
            return _text(rid, f"AUTENTICACIÓN: {e}\n\nNo reintentes ni pruebes "
                              "otras herramientas: pedile al usuario que "
                              "re-exporte las cookies.", is_error=True)
        except (PackError, StudioError) as e:
            return _text(rid, str(e), is_error=True)
        except Exception as e:  # noqa: BLE001
            return _text(rid, f"{type(e).__name__}: {e}", is_error=True)

    return {"jsonrpc": "2.0", "id": rid,
            "error": {"code": -32601, "message": f"Método no soportado: {method}"}}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
