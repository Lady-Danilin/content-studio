from lib.plan import historias

MARCA = {
    "slug": "calzufre",
    "meses": [
        {
            "anio": 2026,
            "mes": 9,
            "semanas": [
                {
                    "numero": 1,
                    "tema": "Salinidad no es sodicidad",
                    "piezas": [],
                    "historias": [
                        {
                            "id": "calzufre-2026-09-s1-martes-h",
                            "dia": "martes",
                            "mecanica": "encuesta",
                            "que": "Dos lotes después de la misma lluvia",
                            "interaccion": "¿Cuál de los dos tiene problema de sodio?",
                        }
                    ],
                }
            ],
        }
    ],
}


def test_historias_devuelve_el_contexto_del_mes_y_la_semana():
    salida = historias(MARCA)
    assert len(salida) == 1
    h = salida[0]
    assert h["id"] == "calzufre-2026-09-s1-martes-h"
    assert h["marca"] == "calzufre"
    assert h["anio"] == 2026
    assert h["mes"] == 9
    assert h["semana"] == 1
    assert h["tema"] == "Salinidad no es sodicidad"


def test_historias_filtra_por_mes():
    assert historias(MARCA, anio=2026, mes=10) == []


def test_historias_tolera_una_marca_sin_meses():
    assert historias({"slug": "x", "meses": []}) == []
