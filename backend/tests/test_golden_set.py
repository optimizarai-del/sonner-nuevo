"""Tests del evaluador del golden set (scripts/golden_set.py).

Si las reglas duras tienen falsos negativos, el golden set aprueba respuestas que no
debería; si tienen falsos positivos, nadie le cree al reporte. Por eso se testean.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import golden_set as gs  # noqa: E402

from app.agents.nodes.guard import HANDOFF_RESPUESTA  # noqa: E402


def _salida(respuesta: str, comando: str = "nada", **meta) -> dict:
    return {"respuesta": respuesta, "comando": comando, "_meta": meta}


# ── Reglas duras ─────────────────────────────────────────────────────────────
def test_una_respuesta_normal_pasa_todo():
    s = _salida("¡Hola! Contame para qué fecha es el evento y en qué salón.")
    assert gs.evaluar_reglas(s) == []


def test_la_derivacion_normal_a_gabriel_pasa():
    """Derivar es comportamiento válido: no puede contar como falla."""
    s = _salida(HANDOFF_RESPUESTA, comando="mensaje_gabi", degradado_handoff=False)
    assert gs.evaluar_reglas(s) == []


@pytest.mark.parametrize("texto", [
    "Tuve un error procesando tu mensaje",
    "Hubo un inconveniente técnico, intentá de nuevo",
    "No pude procesar tu consulta",
])
def test_detecta_errores_tecnicos(texto):
    assert any("sin_error_tecnico" in f for f in gs.evaluar_reglas(_salida(texto)))


@pytest.mark.parametrize("texto", [
    "El paquete sale $ 350.000",
    "Serían $350000 con la seña",
    "Te queda en 180.000 pesos",
])
def test_detecta_montos(texto):
    assert any("sin_montos" in f for f in gs.evaluar_reglas(_salida(texto)))


def test_una_cantidad_de_personas_no_es_un_monto():
    assert gs.evaluar_reglas(_salida("Para 150 personas el Royal va perfecto")) == []


def test_detecta_la_marca_interna_filtrada():
    s = _salida("[INTERNO — NO COMUNICAR AL CLIENTE] CFG-02 incluye 4 parlantes")
    assert any("sin_marca_interna" in f for f in gs.evaluar_reglas(s))


def test_detecta_json_crudo():
    s = _salida('{"respuesta": "hola", "comando": "nada"}')
    assert any("sin_json_crudo" in f for f in gs.evaluar_reglas(s))


def test_degradado_es_falla_aunque_la_respuesta_sea_amable():
    """El cliente no lo nota, pero el sistema no pudo armar una respuesta."""
    s = _salida(HANDOFF_RESPUESTA, comando="mensaje_gabi",
                degradado_handoff=True, motivo_handoff="el modelo no devolvió texto")
    fallas = gs.evaluar_reglas(s)
    assert any("no_degradado" in f and "no devolvió texto" in f for f in fallas)


def test_comando_invalido():
    assert any("comando_valido" in f for f in gs.evaluar_reglas(_salida("ok", comando="x")))


def test_se_pueden_elegir_reglas():
    assert gs.evaluar_reglas(_salida("$ 100"), ["respuesta_no_vacia"]) == []


# ── Referencia y selección ───────────────────────────────────────────────────
def _fila(id_, msg, resp="respuesta vieja", rating=None, corregida=None, tipo="minorista"):
    return {"id": id_, "mensaje_cliente": msg, "respuesta_agente": resp, "rating": rating,
            "respuesta_corregida": corregida, "tipo_cliente": tipo}


def test_la_correccion_humana_gana_sobre_la_respuesta_original():
    assert gs.referencia(_fila(1, "hola", rating="bad", corregida="mejor")) == ("mejor", "corregida")


@pytest.mark.parametrize("rating,fuente", [
    ("good", "aprobada"), ("bad", "rechazada"), ("mejorable", "mejorable"), (None, "sin_revisar"),
])
def test_fuente_de_la_referencia(rating, fuente):
    assert gs.referencia(_fila(1, "hola", rating=rating))[1] == fuente


def test_sin_respuesta_no_hay_referencia():
    assert gs.referencia(_fila(1, "hola", resp="")) is None


def test_seleccion_prioriza_lo_revisado_y_balancea_tipos():
    filas = [
        _fila(1, "precio de sonido", tipo="minorista"),
        _fila(2, "tienen luces?", rating="good", tipo="minorista"),
        _fila(3, "necesito 20 cabezales", corregida="ok", tipo="mayorista"),
        _fila(4, "disponible el 13?", tipo="mayorista"),
        _fila(5, "hola", rating="bad", tipo="minorista"),
    ]
    elegidos = gs.seleccionar(filas, 4)
    ids = [f["id"] for f in elegidos]
    assert len(ids) == 4
    assert 3 in ids and 2 in ids                     # corregida y aprobada primero
    tipos = [f["tipo_cliente"] for f in elegidos]
    assert tipos.count("mayorista") == 2            # balanceado


def test_seleccion_descarta_duplicados_y_mensajes_vacios():
    filas = [_fila(1, "Hola!"), _fila(2, "hola"), _fila(3, "  "), _fila(4, "ok", resp=None)]
    assert [f["id"] for f in gs.seleccionar(filas, 10)] == [1]


def test_el_caso_guarda_la_referencia_y_todas_las_reglas():
    caso = gs.a_caso(_fila(7, "  tienen humo?  ", rating="good", tipo="mayorista"))
    assert caso["nombre"] == "csm-7"
    assert caso["mensaje"] == "tienen humo?"
    assert caso["esperado"]["fuente_referencia"] == "aprobada"
    assert caso["esperado"]["tipo_cliente"] == "mayorista"
    assert caso["asserts"] == list(gs.REGLAS)
