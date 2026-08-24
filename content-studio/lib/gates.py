"""Los gates: lo que el plugin se niega a hacer, y qué devuelve en su lugar.

Core reutilizable, y la parte del plugin que no se configura. Un pack
aporta datos a estos gates (qué frases prohibió un cliente, qué marcas se
parecen entre sí); ninguno de ellos se puede apagar desde un pack, porque
entonces la única protección real dependería de que alguien se acuerde de
escribirla.

Hay un orden y no es casual. El clasificador probatorio corre **primero**,
antes de resolver preset, paleta o aspecto: si el asset que se pide es una
prueba y no una ilustración, no hay que generarlo, y todo lo que se evalúe
después se estaría evaluando sobre algo que no debería existir.

Cada gate devuelve un dict con la misma forma:

    {"gate": str, "estado": "ok" | "aviso" | "bloqueo",
     "hallazgos": [...], "entregable": {...}}

`aviso` no frena: informa y queda registrado en el manifiesto. `bloqueo`
frena, y siempre viene con un `entregable` — el camino correcto para
resolver lo que se pedía. Un rechazo pelado se esquiva reformulando el
pedido, y el segundo intento es justo el que produce el asset falso.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import plan
import studio
from studio import normalizar

OK, AVISO, BLOQUEO = "ok", "aviso", "bloqueo"

# Funciones del asset. La distinción es la frontera entre publicidad e
# información engañosa, y no tiene nada de específico de una agencia.
PRUEBA = "prueba"      # afirma que algo existe, ocurrió, avanzó o es quien dice
ILUSTRA = "ilustra"    # representa un concepto, sin afirmar un hecho particular


def _r(gate: str, estado: str, hallazgos: list, entregable: dict | None = None) -> dict:
    return {
        "gate": gate,
        "estado": estado,
        "hallazgos": hallazgos,
        "entregable": entregable or {},
    }


# ------------------------------------------------------- 1. clasificador probatorio

# Lo que una petición dice cuando en realidad quiere documentar un hecho.
# No alcanza con preguntarle a quien pide: la formulación delata la función.
INDICIOS_PROBATORIOS = [
    (r"\bnuestr[oa]s?\b", "posesivo de primera persona: atribuye el objeto al cliente"),
    (r"\bel (local|salón|salon|depósito|deposito|predio|centro|consultorio|taller|estudio)\b",
     "artículo definido sobre un lugar: afirma que es ESE lugar"),
    (r"\bla (obra|nave|sucursal|sede|planta|clínica|clinica|entrega|instalación|instalacion)\b",
     "artículo definido sobre una instalación o un hecho puntual"),
    (r"\bavance de obra\b", "el avance es el hecho que la pieza afirma"),
    (r"\b(entrega|inauguración|inauguracion|evento|visita) (real|de|del|a la)\b",
     "documenta un acontecimiento con fecha"),
    (r"\b(testimonio|caso|paciente|cliente real|antes y después|antes y despues)\b",
     "afirma la experiencia de una persona concreta"),
    (r"\b(el|la|nuestro|nuestra) (equipo|profesional|doctor|doctora|dr\.|dra\.|técnico|tecnico|docente|agrónomo|agronomo)\b",
     "identifica a una persona real del cliente"),
    (r"\b(stock|mercadería|mercaderia|inventario) (real|disponible|actual)\b",
     "afirma existencias verificables"),
]


def probatorio(peticion: str, funcion_declarada: str | None = None) -> dict:
    """Primer gate: ¿este asset prueba un hecho o ilustra un concepto?

    Se generan ilustraciones. No se generan pruebas: una obra que no se
    construyó, un local que no existe, una entrega que no ocurrió o una
    persona que no trabaja ahí son afirmaciones falsas sobre el negocio de
    un cliente, y el costo lo paga el cliente, no la agencia.
    """
    hallazgos = []
    texto = normalizar(peticion)
    for patron, por_que in INDICIOS_PROBATORIOS:
        m = re.search(patron, texto)
        if m:
            hallazgos.append({"fragmento": m.group(0), "por_que": por_que})

    declarada = (funcion_declarada or "").strip().lower()
    if declarada not in (PRUEBA, ILUSTRA):
        return _r(
            "probatorio",
            BLOQUEO,
            hallazgos,
            {
                "falta": "función del asset",
                "pregunta": (
                    "¿Este asset PRUEBA algo (que el lugar existe, que la obra "
                    "avanzó, que la entrega ocurrió, que la persona es quien se "
                    "dice) o ILUSTRA un concepto?"
                ),
                "valores": [PRUEBA, ILUSTRA],
                "por_que": (
                    "Es el primer gate del pipeline. Se resuelve antes que el "
                    "preset y la paleta, porque si la respuesta es 'prueba' no "
                    "hay nada más que resolver."
                ),
            },
        )

    if declarada == PRUEBA:
        return _r(
            "probatorio",
            BLOQUEO,
            hallazgos,
            plan_de_rodaje(peticion, hallazgos),
        )

    if hallazgos:
        # Se declaró ilustrativo pero el texto afirma hechos. No se bloquea
        # —quien pide sabe qué quiere— pero la contradicción queda escrita.
        return _r(
            "probatorio",
            AVISO,
            hallazgos,
            {
                "advertencia": (
                    "Se declaró ILUSTRA, pero el pedido está redactado como si "
                    "documentara un hecho concreto. Si el asset se rotula después "
                    "con ese lugar, esa obra o esa persona, pasa a ser prueba."
                ),
                "accion": "Reformular el pedido en términos genéricos, sin artículo definido ni posesivo.",
            },
        )

    return _r("probatorio", OK, [])


def plan_de_rodaje(peticion: str, hallazgos: list) -> dict:
    """La negativa productiva.

    Un error pelado deja a la agencia bloqueada y se saltea reformulando el
    pedido. Esto devuelve el camino correcto: qué hay que registrar, quién
    lo autoriza y con qué se cubre el slot mientras tanto.
    """
    return {
        "tipo": "plan_de_rodaje",
        "por_que_no_se_genera": (
            "El asset pedido afirma un hecho sobre el negocio del cliente. "
            "Generarlo produce una afirmación falsa firmada por el cliente."
        ),
        "que_hay_que_registrar": peticion,
        "indicios": [h["fragmento"] for h in hallazgos],
        "checklist": [
            "Agendar el registro en el lugar, con fecha.",
            "Lista de planos: general, detalle, y un plano que dé escala.",
            "Autorización por escrito y PREVIA de quien aparezca o de quien sea dueño del lugar.",
            "Si hay personas identificables, autorización individual de cada una.",
            "Si hay producto de terceros, confirmar que se puede mostrar marca y modelo.",
        ],
        "mientras_tanto": [
            "Cubrir el slot con un formato que no requiera prueba: carrusel explicativo, FAQ, despiece ilustrado.",
            "Reprogramar el slot y dejarlo declarado como pendiente de rodaje.",
            "Saltear el slot antes que llenarlo con un asset que simule el hecho.",
        ],
    }


# ------------------------------------------------------- 2. dato sin validar

# Categorías de dato que ninguna agencia publica sin confirmación del
# responsable de cuenta. La lista es normativa, no estilística.
PATRONES_DATO = [
    ("precio", r"\$\s?\d[\d.\s]*|\b\d[\d.]*\s?(pesos|usd|dólares|dolares)\b"),
    ("cuota", r"\bcuotas?\b|\banticipo\b|\bfinanciad[oa]\b|\bsin inter[eé]s\b"),
    ("tasa", r"\btasa\b|\btna\b|\bcft\b|\b\d+\s?%\s?(anual|mensual)?\b"),
    ("plazo", r"\b\d+\s?(d[ií]as|semanas|meses|años|anos)\b|\bentrega en\b|\bplazo de\b"),
    ("stock", r"\bstock\b|\b\d+\s?(unidades|lotes|cupos|vacantes)\b|\búltim[oa]s?\b|\bultim[oa]s?\b"),
    ("vencimiento", r"\bhasta el\b|\bválid[ao] hasta\b|\bvalid[ao] hasta\b|\bvence\b"),
    ("dosis", r"\bdosis\b|\b\d+\s?(kg|g|ml|mg|l|tn)\s?(/|por)\s?(ha|hect|m2|m²)\b"),
    ("especificacion_tecnica", r"\b\d+\s?(mm|cm|kg/m|mpa|kn|w|kva|rpm)\b|\bnorma\s+[A-Z]"),
    ("contacto", r"\b\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}\b|\bwhatsapp\b|@[\w.]+\.(com|ar)\b"),
    ("cobertura_geografica", r"\benv[ií]os? a\b|\bcobertura\b|\ba todo el pa[ií]s\b"),
]


def dato_sin_validar(texto: str, m: dict, fuentes: list[str] | None = None) -> dict:
    """Datos duros presentes en el copy, y de dónde salieron.

    Comportamiento configurado para este plugin: el copy se **escribe** con
    la cifra que traiga la fuente (guión, brief, ficha) y el dato queda
    marcado como pendiente de validación en el manifiesto. Lo que sí se
    bloquea es la cifra que no aparece en ninguna fuente: eso no es
    republicar un dato viejo, es inventarlo.

    La distinción importa porque el marco de una agencia suele decir que
    las cifras históricas del brief son contexto, no permiso — así que la
    advertencia viaja siempre, incluso cuando el dato tiene origen.
    """
    fuente_norm = normalizar(" \n ".join(fuentes or []))
    hallazgos, sin_origen = [], []

    for categoria, patron in PATRONES_DATO:
        for m_re in re.finditer(patron, texto, re.I):
            valor = m_re.group(0).strip()
            tiene_origen = bool(fuente_norm) and normalizar(valor) in fuente_norm
            item = {
                "categoria": categoria,
                "valor": valor,
                "origen": "fuente" if tiene_origen else "sin origen en la fuente",
                "requiere": "confirmación del responsable de cuenta antes de publicar",
            }
            hallazgos.append(item)
            if not tiene_origen:
                sin_origen.append(item)

    if sin_origen:
        return _r(
            "dato_sin_validar",
            BLOQUEO,
            hallazgos,
            {
                "tipo": "dato_inventado",
                "datos": sin_origen,
                "por_que": (
                    "Estos valores no aparecen en ninguna fuente del plan. "
                    "Escribirlos sería inventar una condición comercial, un "
                    "plazo o una especificación del cliente."
                ),
                "accion": (
                    "Pedir el dato al responsable de cuenta, o dejar el "
                    "marcador explícito en su lugar y publicarlo recién cuando "
                    "vuelva confirmado."
                ),
            },
        )

    if hallazgos:
        return _r(
            "dato_sin_validar",
            AVISO,
            hallazgos,
            {
                "advertencia": (
                    f"El copy de «{m.get('nombre', m.get('slug'))}» contiene "
                    f"{len(hallazgos)} dato(s) duro(s) tomados de la fuente. "
                    "Van al manifiesto como pendientes: el dato histórico del "
                    "brief es contexto, no autorización para republicarlo."
                ),
                "validar_con": m.get("responsable") or "responsable de cuenta",
            },
        )

    return _r("dato_sin_validar", OK, [])


# ------------------------------------------------------- 3. sector regulado

# Verbos de resultado en indicativo. Un generador tiende a cerrar con
# beneficio afirmativo, que es exactamente el claim que un sector regulado
# prohíbe. La forma admitida es modalizada: "puede contribuir", "según
# evaluación profesional".
VERBOS_RESULTADO = [
    "cura", "curan", "elimina", "eliminan", "garantiza", "garantizan",
    "resuelve", "resuelven", "regenera", "regeneran", "alivia", "alivian",
    "revierte", "revierten", "corrige", "corrigen", "asegura", "aseguran",
]


def sector_regulado(texto: str, m: dict) -> dict:
    """En salud, farma, financiero o legal se valida el texto COMPLETO.

    No un campo suelto: una frase mal modalizada convierte una pieza
    educativa en una promesa clínica sin tocar ningún dato duro, así que
    revisar sólo los números no alcanza.
    """
    if not m.get("sector_regulado"):
        return _r("sector_regulado", OK, [])

    t = normalizar(texto)
    hallazgos = [
        {"verbo": v, "por_que": "afirma un resultado en indicativo"}
        for v in VERBOS_RESULTADO
        if re.search(rf"\b{v}\b", t)
    ]

    entregable = {
        "tipo": "firma_nominada",
        "alcance": "texto completo: hook, desarrollo, copy y CTA",
        "requiere": (
            "Firma nominada de la fuente responsable (profesional con "
            "matrícula, servicio técnico, responsable de obra o fabricante)."
        ),
        "forma_admitida": [
            "puede contribuir a…",
            "según evaluación profesional",
            "en algunos casos se observa…",
        ],
    }
    if hallazgos:
        return _r("sector_regulado", BLOQUEO, hallazgos, entregable)
    return _r("sector_regulado", AVISO, [], entregable)


# ------------------------------------------------------- 4. frases prohibidas


def blocklist(texto: str, m: dict) -> dict:
    """Frases que este cliente prohibió, verificadas contra la SALIDA.

    Se verifica el texto producido, no se confía en habérselo pedido al
    modelo en el prompt. El motivo es concreto: estas frases suelen estar
    escritas en el propio archivo de la marca —como prohibición— y un
    generador que lee ese archivo las ve como copy disponible y las repite
    por inercia.
    """
    t = normalizar(texto)
    hallazgos = [
        {"frase": f, "por_que": "está en la lista de frases prohibidas de la marca"}
        for f in (m.get("prohibido") or [])
        if normalizar(f) in t
    ]
    if hallazgos:
        return _r(
            "blocklist",
            BLOQUEO,
            hallazgos,
            {
                "tipo": "frase_prohibida",
                "accion": "Reescribir sin esas frases. No se publican ni citadas ni entre comillas.",
                "nota": (
                    "Si la frase aparece en el archivo de la marca, está ahí "
                    "como prohibición, no como copy disponible."
                ),
            },
        )
    return _r("blocklist", OK, [])


# ------------------------------------------------------- 5. identidad visual


def identidad_visual(m: dict) -> dict:
    """Sin logo, paleta y tipografía reales, la pieza sale marcada incompleta.

    No se elige una fuente ni un color plausibles. Una placa con identidad
    inventada parece terminada y por lo tanto puede llegar a publicarse;
    una obviamente incompleta, no. El riesgo de la pieza que parece lista
    es mayor que el de la pieza que falta.
    """
    iv = m.get("identidad_visual") or {}
    if iv.get("disponible"):
        return _r("identidad_visual", OK, [])
    return _r(
        "identidad_visual",
        AVISO,
        [{"faltan": iv.get("faltan") or ["logo", "paleta", "tipografia"]}],
        {
            "tipo": "pieza_incompleta",
            "marcar_como": "incompleta",
            "regla": "Se entrega sin logo ni tipografía, visiblemente sin terminar.",
            "accion": "Pedir el manual de marca o los assets al responsable de cuenta.",
        },
    )


# ------------------------------------------------------- 6. vecindad de voz


def vecindad(slug_marca: str, slug_origen: str, pack: dict) -> dict:
    """Impide reutilizar la voz de una marca en otra declarada como vecina.

    Es el modo de falla nativo de un generador: un solo prompt base funde
    dos marcas del mismo rubro. Y el atajo es tentador justamente donde
    más daño hace — la marca con el mes completo y los guiones cargados es
    la plantilla obvia para producir las que están vacías.
    """
    if slug_marca == slug_origen:
        return _r("vecindad", OK, [])
    pares = [tuple(sorted(p)) for p in (pack.get("pares_peligrosos") or [])]
    if tuple(sorted((slug_marca, slug_origen))) in pares:
        return _r(
            "vecindad",
            BLOQUEO,
            [{"par": [slug_origen, slug_marca]}],
            {
                "tipo": "contaminacion_de_voz",
                "por_que": (
                    "Están declaradas como par de vecindad peligrosa: comparten "
                    "rubro o cluster y se confunden con facilidad. La voz es "
                    "intransferible y es parte del producto."
                ),
                "accion": (
                    "Escribir los hooks y el esqueleto de guión desde la ficha "
                    f"de {slug_marca}, no desde los de {slug_origen}."
                ),
            },
        )
    return _r("vecindad", OK, [])


# ------------------------------------------------------- 7. just in time


def just_in_time(fila_grilla: dict, ahora: datetime | None = None,
                 publicacion: datetime | None = None) -> dict:
    """Un slot atado a un trend, a un stock del día o a una promo con fecha
    no se pre-produce por lote fuera de su ventana.

    Preproducir con una semana de anticipación un slot de tendencia publica
    un trend muerto. El motor de caducidad es genérico; la ventana concreta
    y qué slots la usan son dato del pack.
    """
    jit = fila_grilla.get("just_in_time")
    if not jit:
        return _r("just_in_time", OK, [])
    horas = jit.get("ventana_horas")
    if not horas or publicacion is None:
        return _r(
            "just_in_time",
            AVISO,
            [{"slot": fila_grilla.get("slot"), "ventana_horas": horas}],
            {"accion": "Producir dentro de la ventana, cerca de la fecha de publicación."},
        )
    ahora = ahora or datetime.now(timezone.utc)
    faltan = (publicacion - ahora).total_seconds() / 3600
    if faltan > horas:
        return _r(
            "just_in_time",
            BLOQUEO,
            [{"slot": fila_grilla.get("slot"), "faltan_horas": round(faltan, 1),
              "ventana_horas": horas}],
            {
                "tipo": "fuera_de_ventana",
                "por_que": (
                    f"Faltan {faltan:.0f} h para la publicación y la ventana de "
                    f"este slot es de {horas} h. Lo que se produzca hoy llega "
                    "vencido."
                ),
                "accion": f"Reprogramar la producción para dentro de la ventana.",
            },
        )
    return _r("just_in_time", OK, [])


# ------------------------------------------------------- 8. terceros y personas

PATRONES_TERCEROS = [
    (r"\b(logo|logotipo|isotipo|marca registrada)\b", "identidad de un tercero"),
    (r"\b(patente|matr[ií]cula del veh)\b", "identificación registral"),
    (r"\b(etiqueta|packaging|envase) (de|con marca)\b", "packaging de un fabricante"),
    (r"\bmodelo\s+[A-Z0-9]{2,}\b", "modelo concreto de catálogo ajeno"),
]

PATRONES_PERSONA = [
    (r"\b(retrato|primer plano|selfie|rostro) de\b", "persona identificable"),
    (r"\b(testimonio|paciente|cliente|docente|profesional|m[eé]dic[oa]|doctor[a]?)\b",
     "persona presentada como real"),
    (r"\bnuestro equipo\b", "personal del cliente"),
]


def terceros_y_personas(prompt: str) -> dict:
    """Marca ajena y persona sintética presentada como real.

    Dos pisos independientes. El de terceros cubre el riesgo de marca y
    también el inverso: un producto verosímil pero inventado se lee como el
    producto que se vende y desinforma a quien compara por modelo. El de
    personas es derecho de imagen, y en salud además responsabilidad
    profesional.
    """
    t = normalizar(prompt)
    hallazgos = []
    for patron, por_que in PATRONES_TERCEROS:
        mm = re.search(patron, t)
        if mm:
            hallazgos.append({"fragmento": mm.group(0), "tipo": "tercero", "por_que": por_que})
    for patron, por_que in PATRONES_PERSONA:
        mm = re.search(patron, t)
        if mm:
            hallazgos.append({"fragmento": mm.group(0), "tipo": "persona", "por_que": por_que})

    if hallazgos:
        return _r(
            "terceros_y_personas",
            BLOQUEO,
            hallazgos,
            {
                "tipo": "no_generable",
                "regla": (
                    "No se generan marcas, logos, modelos, patentes ni etiquetas "
                    "de terceros, ni personas identificables presentadas como "
                    "reales (equipo, cliente, paciente, docente, profesional)."
                ),
                "accion": [
                    "Producto de catálogo: fotografía del producto real.",
                    "Persona: rodaje con la persona y autorización previa por escrito.",
                    "Si sólo hace falta ambiente, reformular sin marca ni rostro.",
                ],
            },
        )
    return _r("terceros_y_personas", OK, [])


# ------------------------------------------------------- 9. sin texto

PATRONES_TEXTO_EN_IMAGEN = [
    (r"\bcon (el )?(texto|t[ií]tulo|cartel|r[oó]tulo|leyenda|copy)\b", "pide texto dentro de la imagen"),
    (r"\bque diga\b", "dicta texto a renderizar"),
    (r"\b(precio|cifra|n[uú]mero|porcentaje|cota|medida) (en|sobre) (la )?(imagen|placa|pantalla)\b",
     "pide un dato duro horneado en el pixel"),
    (r"\b(infograf[ií]a|tabla|gr[aá]fico) con datos\b", "datos legibles dentro del asset"),
]


def sin_texto(prompt: str) -> dict:
    """Los assets se generan sin texto. El texto se compone aparte.

    Dos motivos independientes. La generación de glifos es poco confiable, y
    un rótulo mal escrito en una pieza técnica es contenido incorrecto
    firmado por el cliente. El segundo es estructural y más grave: un número
    horneado en un pixel esquiva la revisión de copy, o sea que sin esta
    regla el gate de dato sin validar tiene una puerta trasera.
    """
    t = normalizar(prompt)
    hallazgos = [
        {"fragmento": re.search(p, t).group(0), "por_que": por_que}
        for p, por_que in PATRONES_TEXTO_EN_IMAGEN
        if re.search(p, t)
    ]
    if hallazgos:
        return _r(
            "sin_texto",
            BLOQUEO,
            hallazgos,
            {
                "tipo": "texto_en_imagen",
                "accion": (
                    "Generar el fondo sin texto, reservando espacio negativo, y "
                    "componer la tipografía encima en diseño con el dato ya validado."
                ),
                "sugerencia": "Agregar al prompt: sin texto, sin números, sin logos, sin marcas de agua.",
            },
        )
    return _r("sin_texto", OK, [])


# ------------------------------------------------------- 10. canal de conversión


def conversion(m: dict) -> dict:
    """Un CTA que cae al vacío anula la métrica de toda la campaña.

    Y tiene una consecuencia que conviene decir en voz alta: más piezas
    producidas significan más consultas, así que la capacidad real de
    responder es una precondición de producción, no un detalle posterior.
    """
    conv = m.get("conversion") or {}
    faltan = [k for k in ("canal", "palabra_clave") if not conv.get(k)]
    if faltan:
        return _r(
            "conversion",
            BLOQUEO,
            [{"faltan": faltan}],
            {
                "tipo": "canal_sin_verificar",
                "accion": [
                    "Confirmar que la palabra clave sigue activa.",
                    "Confirmar que el número o el link existe y responde.",
                    "Confirmar que el CTA corresponde al canal (orgánico comenta la palabra; Ads entra por formulario).",
                    "Confirmar que hay alguien atendiendo, con capacidad para el volumen que la pieza va a generar.",
                ],
            },
        )
    if not conv.get("verificado"):
        return _r(
            "conversion",
            AVISO,
            [{"canal": conv.get("canal"), "palabra_clave": conv.get("palabra_clave")}],
            {"accion": "Verificar el canal antes de publicar; queda registrado como pendiente."},
        )
    return _r("conversion", OK, [])


# ------------------------------------------------------------------ agregado


def evaluar(resultados: list[dict]) -> dict:
    """Junta varios gates en un veredicto.

    Un solo bloqueo alcanza para frenar. Los avisos no frenan pero viajan
    enteros al manifiesto: son lo que la etapa de edición y el responsable
    de cuenta tienen que leer antes de publicar.
    """
    bloqueos = [r for r in resultados if r["estado"] == BLOQUEO]
    avisos = [r for r in resultados if r["estado"] == AVISO]
    return {
        "estado": BLOQUEO if bloqueos else (AVISO if avisos else OK),
        "puede_producir": not bloqueos,
        "bloqueos": bloqueos,
        "avisos": avisos,
        "gates_evaluados": [r["gate"] for r in resultados],
    }
