"""Contrato de formato: qué relación de aspecto y qué duración por destino.

Core reutilizable, y de las pocas cosas de este plugin que son idénticas en
cualquier agencia y cualquier cartera. Lo que varía por cliente es la
paleta y el prompt, nunca el aspecto de un reel.

Se valida ANTES de gastar un crédito. Es la falla más barata de prevenir:
generar en 1:1 lo que iba a ser un reel obliga a generar dos veces.
"""

from __future__ import annotations

DESTINOS = {
    "reel":      {"aspecto": "9:16", "medio": "video", "duracion_s": (15, 60), "nota": "Vertical. Los primeros 3 s deciden el alcance."},
    "historia":  {"aspecto": "9:16", "medio": "imagen", "duracion_s": (5, 15), "nota": "Vertical. Zona segura: evitar el 15% superior e inferior."},
    "feed":      {"aspecto": "4:5",  "medio": "imagen", "duracion_s": None,    "nota": "Vertical corto: ocupa más pantalla que el 1:1."},
    "carrusel":  {"aspecto": "4:5",  "medio": "imagen", "duracion_s": None,    "nota": "Todas las slides con el mismo aspecto o se recortan."},
    "placa":     {"aspecto": "1:1",  "medio": "imagen", "duracion_s": None,    "nota": "Cuadrado clásico, seguro en cualquier grilla."},
    "ads":       {"aspecto": "1:1",  "medio": "imagen", "duracion_s": None,    "nota": "Una sola oferta clara por placa."},
    "youtube":   {"aspecto": "16:9", "medio": "video",  "duracion_s": (30, 600), "nota": "Horizontal."},
    "linkedin":  {"aspecto": "1:1",  "medio": "imagen", "duracion_s": None,    "nota": "Cuadrado o 4:5; el horizontal rinde peor."},
}

ALIAS = {
    "reels": "reel", "story": "historia", "stories": "historia",
    "post": "feed", "carousel": "carrusel", "anuncio": "ads",
    "yt": "youtube", "shorts": "reel", "tiktok": "reel",
}


def resolver(destino: str) -> dict:
    """Contrato de formato para un destino, o un error que lista los válidos."""
    clave = ALIAS.get(destino.strip().lower(), destino.strip().lower())
    if clave not in DESTINOS:
        raise ValueError(
            f"Destino {destino!r} desconocido. Válidos: {', '.join(sorted(DESTINOS))}."
        )
    return {"destino": clave, **DESTINOS[clave]}


def validar(destino: str, aspecto: str | None = None,
            duracion_s: float | None = None) -> dict:
    """Compara lo pedido con el contrato del destino."""
    c = resolver(destino)
    problemas = []
    if aspecto and aspecto != c["aspecto"]:
        problemas.append(
            f"El aspecto pedido ({aspecto}) no es el de un {c['destino']} ({c['aspecto']}). "
            "Generar así obliga a recortar o a generar de nuevo."
        )
    if duracion_s is not None and c["duracion_s"]:
        lo, hi = c["duracion_s"]
        if not (lo <= duracion_s <= hi):
            problemas.append(
                f"Duración {duracion_s}s fuera del rango de un {c['destino']} ({lo}-{hi}s)."
            )
    return {"contrato": c, "ok": not problemas, "problemas": problemas}
