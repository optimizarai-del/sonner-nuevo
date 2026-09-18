"""Tests offline del agente interno. Sin red: el LLM y Google están dobleteados.

Lo que más importa acá son los permisos de escritura. El agente interno SÍ crea, edita
y borra cosas reales, así que las reglas que en n8n vivían en un prompt ("fiestas
tijereta y fiestas cromo son solo lectura") tienen que ser imposibles de violar, no
difíciles.
"""
from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage

from app.agents.graphs import interno as grafo
from app.agents.nodes import agente as nodo_agente
from app.agents.nodes.guard import FALLA_INTERNA, ContratoInterno
from app.agents.tools import registry
from app.services.agente_interno import calendario as cal
from app.services.agente_interno import djs


class LLMFalso:
    def __init__(self, *respuestas: AIMessage) -> None:
        self.respuestas = list(respuestas)
        self.invocaciones: list[list] = []

    def invoke(self, mensajes, **_kwargs) -> AIMessage:
        self.invocaciones.append(list(mensajes))
        return self.respuestas.pop(0) if self.respuestas else AIMessage(content="")


@pytest.fixture
def con_llm(monkeypatch):
    def _instalar(*respuestas: AIMessage) -> LLMFalso:
        falso = LLMFalso(*respuestas)
        monkeypatch.setattr(nodo_agente, "_modelo", lambda _audiencia: falso)
        return falso

    return _instalar


def _correr(**kwargs):
    base = dict(chat_id="6124095544", mensaje="qué eventos hay en diciembre",
                canal="telegram", nombre="Gabi", persistir=False)
    return grafo.correr(**{**base, **kwargs})


# ── Permisos de escritura ────────────────────────────────────────────────────
def test_solo_dos_calendarios_admiten_escritura():
    assert cal.ESCRIBIBLES == {"eventos_sonner", "reuniones_gabi"}


@pytest.mark.parametrize("calendario", ["fiestas_tijereta", "fiestas_cromo"])
def test_no_se_puede_escribir_en_calendarios_de_terceros(calendario):
    """Ni creando, ni actualizando, ni borrando: la llamada ni siquiera sale."""
    with pytest.raises(cal.CalendarioNoEscribible):
        cal.crear(calendario, "Fiesta trucha", "2026-12-13T21:00")
    with pytest.raises(cal.CalendarioNoEscribible):
        cal.actualizar(calendario, "evt123", titulo="otro")
    with pytest.raises(cal.CalendarioNoEscribible):
        cal.borrar(calendario, "evt123")


def test_los_de_terceros_si_se_leen():
    assert "fiestas_tijereta" in cal.DE_EVENTOS
    assert "fiestas_cromo" in cal.DE_EVENTOS


def test_las_tools_de_escritura_no_reciben_el_calendario_como_argumento():
    """Si el destino fuera un argumento, un prompt inyectado podría cambiarlo."""
    escriben = ["crear_evento", "actualizar_evento", "borrar_evento",
                "crear_reunion", "actualizar_reunion", "borrar_reunion"]
    por_nombre = registry.por_nombre("interno")
    for nombre in escriben:
        assert "calendario" not in por_nombre[nombre].args


def test_el_externo_no_gano_ninguna_tool_al_agregar_el_interno():
    """La regresión a evitar: sumar tools de escritura y que se filtren al cliente."""
    externo = {t.name for t in registry.para("externo")}
    assert externo == {"memoria", "calendario", "salones", "pensar"}
    solo_internas = {t.name for t in registry.para("interno")} - externo
    assert solo_internas and not (solo_internas & externo)


def test_el_interno_tiene_las_trece_tools():
    nombres = {t.name for t in registry.para("interno")}
    assert nombres == {
        "memoria", "pensar",
        "buscar_evento", "crear_evento", "actualizar_evento", "borrar_evento",
        "buscar_reunion", "crear_reunion", "actualizar_reunion", "borrar_reunion",
        "consultar_dj", "registrar_dj", "actualizar_dj",
    }


# ── Contrato interno ─────────────────────────────────────────────────────────
def test_contrato_interno_acepta_los_cuatro_comandos():
    for comando in ("eventos", "informacion", "materiales", "nada"):
        assert ContratoInterno(respuesta="ok", comando=comando).comando == comando


def test_comando_inventado_cae_a_nada():
    c = ContratoInterno(respuesta="ok", comando="borrar_base", contenido="algo")
    assert c.comando == "nada"
    assert c.contenido is None


def test_sin_comando_no_se_guarda_el_contenido_literal():
    """El prompt manda contenido:"nada" cuando no hay que guardar; no puede ingestarse."""
    assert ContratoInterno(respuesta="hola", comando="nada", contenido="nada").contenido is None


def test_respuesta_del_agente_interno(con_llm):
    con_llm(AIMessage(content=json.dumps({
        "respuesta": "Tenés 3 eventos en diciembre.",
        "comando": "nada", "contenido": "nada",
    })))
    out = _correr()
    assert out["respuesta"] == "Tenés 3 eventos en diciembre."
    assert out["comando"] == "nada"
    assert out["contenido"] is None


def test_al_equipo_si_se_le_avisa_que_fallo(con_llm):
    """Al cliente se le oculta el error; al equipo no, porque ellos pueden actuar."""
    con_llm(AIMessage(content=""))
    out = _correr()
    assert out["respuesta"] == FALLA_INTERNA
    assert "no se ejecutó ningún cambio" in out["respuesta"].lower()
    assert out["_meta"]["degradado_handoff"] is True


def test_si_el_grafo_explota_avisa_sin_inventar(monkeypatch):
    def _explotar(_audiencia):
        raise RuntimeError("proveedor caído")

    monkeypatch.setattr(nodo_agente, "_modelo", _explotar)
    out = _correr()
    assert out["respuesta"] == FALLA_INTERNA
    assert out["comando"] == "nada"


# ── Ingesta vectorial ────────────────────────────────────────────────────────
def test_el_comando_dispara_la_ingesta(con_llm, monkeypatch):
    from app.agents.nodes import ingesta_vectorial as nodo

    guardados = []
    monkeypatch.setattr(nodo.vs, "ingestar",
                        lambda contenido, fuente, metadata=None:
                        guardados.append((fuente, contenido)) or {"guardados": 2})

    con_llm(AIMessage(content=json.dumps({
        "respuesta": "Listo, lo cargué.",
        "comando": "materiales",
        "contenido": "10 parlantes JBL SRX835 en depósito",
    })))
    out = _correr(mensaje="cargá 10 parlantes JBL")

    assert guardados == [("materiales", "10 parlantes JBL SRX835 en depósito")]
    assert out["_meta"]["ingesta"]["guardados"] == 2


@pytest.mark.parametrize("comando,fuente", [
    ("eventos", "eventos"),
    ("informacion", "informacion_interna"),
    ("materiales", "materiales"),
])
def test_cada_comando_va_a_su_fuente(comando, fuente):
    from app.agents.nodes.ingesta_vectorial import DESTINO

    assert DESTINO[comando] == fuente


def test_si_la_ingesta_falla_el_equipo_se_entera(con_llm, monkeypatch):
    """Un guardado que falla en silencio es peor que uno que falla: nadie lo busca."""
    from app.agents.nodes import ingesta_vectorial as nodo

    def _romper(*_a, **_k):
        raise RuntimeError("pgvector caído")

    monkeypatch.setattr(nodo.vs, "ingestar", _romper)
    con_llm(AIMessage(content=json.dumps({
        "respuesta": "Listo, lo cargué.", "comando": "materiales", "contenido": "algo",
    })))
    out = _correr()
    assert "no se pudo guardar" in out["respuesta"].lower()
    assert out["_meta"]["ingesta"]["guardados"] == 0


# ── Planilla de DJs ──────────────────────────────────────────────────────────
HEADERS_DJ = djs.COLUMNAS
FILAS_DJ = [
    ["2026-12-13", "Casamiento", "Royal", "Tobi", "150000", "no", "Gabi", ""],
    ["13/12/2026", "Cumple 15", "Cromo", "Lu", "120000", "si", "Gabi", ""],
]


def test_dj_ocupado_aunque_la_fecha_este_en_otro_formato():
    """La planilla la cargan a mano: conviven 2026-12-13 y 13/12/2026."""
    encontrados = djs.buscar_asignaciones(HEADERS_DJ, FILAS_DJ, "Lu", "2026-12-13")
    assert len(encontrados) == 1
    assert encontrados[0][0] == 3  # fila real de la planilla (1 es el encabezado)


def test_dj_libre_en_otra_fecha():
    assert djs.buscar_asignaciones(HEADERS_DJ, FILAS_DJ, "Tobi", "2026-12-20") == []


def test_el_nombre_del_dj_no_distingue_mayusculas():
    assert djs.buscar_asignaciones(HEADERS_DJ, FILAS_DJ, "TOBI", "2026-12-13")


def test_fila_corta_no_rompe_el_registro():
    registro = djs.a_registro(HEADERS_DJ, ["2026-12-13", "Casamiento"])
    assert registro["DJ"] == ""
    assert registro["OBSERVACIONES"] == ""


# ── Grafo ────────────────────────────────────────────────────────────────────
def test_el_grafo_interno_compila():
    nodos = set(grafo.compilado().get_graph().nodes)
    assert {"contexto", "agente", "herramientas", "guard", "persistencia",
            "ingesta_vectorial", "troceo"} <= nodos


def test_el_interno_no_tiene_gate_ni_debounce_ni_salida():
    """Del otro lado está el equipo: no hay kill-switch, y el envío sigue en n8n."""
    nodos = set(grafo.compilado().get_graph().nodes)
    assert not {"gate", "debounce", "salida", "efectos"} & nodos


def test_usa_el_prompt_interno_y_no_el_del_cliente(con_llm):
    falso = con_llm(AIMessage(content=json.dumps({"respuesta": "ok", "comando": "nada"})))
    _correr()
    sistema = falso.invocaciones[0][0]
    assert sistema.type == "system"
    assert "AGENTE DE GESTIÓN INTERNO SONNER" in sistema.content
    assert "Fecha y hora actual:" in sistema.content


def test_telegram_trocea_y_la_web_responde_de_una(con_llm):
    larga = "Primer bloque.\n\nSegundo bloque.\n\nTercer bloque."
    con_llm(AIMessage(content=json.dumps({"respuesta": larga, "comando": "nada"})))
    assert len(_correr(canal="telegram")["fragmentos"]) == 3

    con_llm(AIMessage(content=json.dumps({"respuesta": larga, "comando": "nada"})))
    assert len(_correr(canal="web")["fragmentos"]) == 1
