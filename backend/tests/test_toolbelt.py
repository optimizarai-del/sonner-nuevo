"""Tests de las reglas de negocio del toolbelt. Sin red: son funciones puras.

Estas reglas vivían en los prompts de los subagentes de n8n ("0 eventos disponible,
1 ocupado_parcial, 2 o más ocupado", "vetá por electricidad o habilitación", "no expongas
montos"). Mientras estaban en un prompt no se podían testear y el modelo podía
desobedecerlas. Acá son código y esto es la prueba.
"""
from __future__ import annotations

import pytest

from app.agents.tools import registry
from app.services.agente_externo import tools_google as tg


# ── Calendario: umbrales de ocupación ────────────────────────────────────────
@pytest.mark.parametrize("cantidad,esperado", [
    (0, "disponible"),
    (1, "ocupado_parcial"),
    (2, "ocupado"),
    (7, "ocupado"),
])
def test_umbrales_de_ocupacion(cantidad, esperado):
    assert tg.estado_por_eventos(cantidad) == esperado


def test_los_titulos_no_filtran_montos_ni_senas():
    """Regla de privacidad del subagente de calendario: nunca exponer plata."""
    eventos = [
        {"summary": "Casamiento Pérez $150.000"},
        {"summary": "Cumple 15 — seña abonada 50%"},
        {"summary": "Fiesta empresa"},
    ]
    titulos = tg.titulos_sin_montos(eventos)
    unidos = " ".join(titulos)
    assert "$" not in unidos
    assert "seña" not in unidos.lower()
    assert "150.000" not in unidos
    assert "Fiesta empresa" in titulos


def test_evento_sin_titulo_no_ensucia_la_lista():
    assert tg.titulos_sin_montos([{"summary": ""}, {}, {"summary": "$5000"}]) == []


@pytest.mark.parametrize("texto,esperado", [
    ("2026-12-13", "2026-12-13"),
    ("13/12/2026", "2026-12-13"),
    ("13-12-26", "2026-12-13"),
    ("verificar disponibilidad evento 2026-12-13", "2026-12-13"),  # comando viejo de n8n
    ("el sábado que viene", None),
    ("", None),
])
def test_normalizacion_de_fecha(texto, esperado):
    assert tg.normalizar_fecha(texto) == esperado


# ── Salones: vetos y capacidad ───────────────────────────────────────────────
def _salon(**campos):
    base = {"nombre": "Royal", "tipo": "externo", "capacidad": "200",
            "electricidad": "SI", "habilitado": "SI", "exclusividad": "",
            "observaciones": None}
    return {**base, **campos}


def test_salon_apto_dentro_de_capacidad():
    r = tg.evaluar_salon(_salon(), pax=150)
    assert r["compatibilidad"] == "compatible"
    assert r["capacidad_ok"] is True


def test_veto_tecnico_por_electricidad():
    r = tg.evaluar_salon(_salon(electricidad="NO"), pax=50)
    assert r["compatibilidad"] == "incompatible"
    assert "técnico" in r["motivo"]


def test_veto_tecnico_por_habilitacion():
    assert tg.evaluar_salon(_salon(habilitado="NO"), pax=50)["compatibilidad"] == "incompatible"


def test_veto_comercial_por_exclusividad():
    r = tg.evaluar_salon(_salon(exclusividad="Sonido Del Sur"), pax=50)
    assert r["compatibilidad"] == "incompatible"
    assert "exclusividad" in r["motivo"]


@pytest.mark.parametrize("valor", ["", "no", "Ninguno", "NINGUNA"])
def test_exclusividad_vacia_no_veta(valor):
    assert tg.evaluar_salon(_salon(exclusividad=valor), pax=50)["compatibilidad"] == "compatible"


def test_el_veto_tecnico_gana_sobre_la_capacidad():
    """Un salón sin habilitación es incompatible aunque la capacidad sobre."""
    r = tg.evaluar_salon(_salon(habilitado="NO", capacidad="1000"), pax=10)
    assert r["compatibilidad"] == "incompatible"
    assert "técnico" in r["motivo"]


def test_pax_por_encima_de_la_capacidad():
    r = tg.evaluar_salon(_salon(capacidad="120"), pax=300)
    assert r["compatibilidad"] == "incompatible"
    assert r["capacidad_ok"] is False


def test_sin_pax_queda_para_relevamiento():
    r = tg.evaluar_salon(_salon(), pax=None)
    assert r["compatibilidad"] == "especial"
    assert r["capacidad_ok"] is None


def test_sin_dato_de_capacidad_queda_para_relevamiento():
    assert tg.evaluar_salon(_salon(capacidad=""), pax=50)["compatibilidad"] == "especial"


def test_capacidad_en_rango_usa_el_maximo():
    """La planilla a veces dice '80 a 250'."""
    assert tg.evaluar_salon(_salon(capacidad="80 a 250"), pax=200)["capacidad_ok"] is True
    assert tg.evaluar_salon(_salon(capacidad="80 a 250"), pax=400)["capacidad_ok"] is False


# ── Salones: lectura de la planilla ──────────────────────────────────────────
HEADERS = ["Nombre", "Tipo", "Capacidad", "Electricidad", "Habilitado",
           "Exclusividad", "Observaciones"]
FILAS = [
    ["Royal", "EXTERNO", "250", "SI", "SI", "", "entrada angosta"],
    ["Salón Los Álamos", "PROPIO", "120", "SI", "NO", "", ""],
]


def test_busca_el_salon_ignorando_acentos_y_mayusculas():
    assert tg.buscar_fila(HEADERS, FILAS, "los alamos") == FILAS[1]
    assert tg.buscar_fila(HEADERS, FILAS, "ROYAL") == FILAS[0]


def test_salon_inexistente_no_matchea():
    assert tg.buscar_fila(HEADERS, FILAS, "Quinta La Rosa") is None


def test_los_datos_de_la_fila_se_mapean_por_encabezado():
    datos = tg._datos_fila(HEADERS, FILAS[0])
    assert datos["nombre"] == "Royal"
    assert datos["tipo"] == "externo"
    assert datos["capacidad"] == "250"
    assert datos["observaciones"] == "entrada angosta"


def test_fila_corta_no_rompe():
    """La planilla la editan a mano: las filas vienen con columnas faltantes."""
    datos = tg._datos_fila(HEADERS, ["Quinta Nueva", "PROPIO"])
    assert datos["nombre"] == "Quinta Nueva"
    assert datos["capacidad"] == ""
    assert tg.evaluar_salon(datos, pax=100)["compatibilidad"] == "especial"


# ── Envoltorio estilo n8n (camino de rollback) ───────────────────────────────
@pytest.mark.parametrize("consulta,nombre,pax", [
    ("verificar_salon: Royal para 150 personas", "Royal", 150),
    ("verificar_salon: Los Álamos para 80 personas", "Los Álamos", 80),
    ("verificar_salon: Royal", "Royal", None),
])
def test_parseo_del_comando_viejo(consulta, nombre, pax):
    assert tg.parsear_salon_pax(consulta) == (nombre, pax)


# ── Toolbelt ─────────────────────────────────────────────────────────────────
def test_las_tools_declaran_argumentos_tipados():
    """Se acabaron los strings mágicos: el modelo pasa datos, no comandos."""
    esquemas = {t.name: set(t.args.keys()) for t in registry.para("externo")}
    assert esquemas["calendario"] == {"fecha"}
    assert esquemas["salones"] == {"salon", "pax"}
    assert esquemas["memoria"] == {"consulta", "fuente"}


def test_la_fuente_de_memoria_es_un_enum_cerrado():
    """El modelo no puede inventar una fuente: o es una de estas o es None."""
    fuente = registry.memoria.args["fuente"]
    serializado = str(fuente)
    for valida in ("materiales", "eventos", "modelo_eventos", "informacion_interna", "todas"):
        assert valida in serializado


def test_ninguna_tool_del_externo_escribe():
    for t in registry.para("externo"):
        assert not any(v in t.name for v in registry.VERBOS_DE_ESCRITURA)
        assert not any(v in (t.description or "").lower().split()[:5]
                       for v in registry.VERBOS_DE_ESCRITURA)
