"""Tests offline del grafo externo. No tocan la red: el LLM está reemplazado por un doble.

Cubren lo que tiene que seguir siendo verdad después de la migración a LangGraph:
el contrato de salida, la degradación a handoff, el troceo y —sobre todo— que el agente
externo no tenga ninguna herramienta de escritura.
"""
from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage

from app.agents.graphs import externo as grafo
from app.agents.nodes import agente as nodo_agente
from app.agents.nodes.guard import HANDOFF_RESPUESTA
from app.agents.tools import registry


class LLMFalso:
    """Devuelve respuestas prefijadas en vez de llamar al proveedor."""

    def __init__(self, *respuestas: AIMessage) -> None:
        self.respuestas = list(respuestas)
        self.invocaciones: list[list] = []

    def invoke(self, mensajes, **_kwargs) -> AIMessage:
        self.invocaciones.append(list(mensajes))
        return self.respuestas.pop(0) if self.respuestas else AIMessage(content="")


@pytest.fixture
def con_llm(monkeypatch):
    """Instala un LLM falso y devuelve la función que corre el grafo en modo relay."""

    def _instalar(*respuestas: AIMessage) -> LLMFalso:
        falso = LLMFalso(*respuestas)
        monkeypatch.setattr(nodo_agente, "_modelo", lambda _audiencia: falso)
        return falso

    return _instalar


def _correr(**kwargs):
    base = dict(modo="relay", chat_id="+5492954111111", mensaje="hola",
                nombre="Fede", tipo_cliente="minorista",
                reunion={"tiene": False}, persistir=False)
    return grafo.correr(**{**base, **kwargs})


# ── Contrato ─────────────────────────────────────────────────────────────────
def test_json_valido_se_convierte_en_contrato(con_llm):
    con_llm(AIMessage(content=json.dumps({
        "respuesta": "¡Hola! ¿Para qué fecha es el evento?",
        "comando": "nada",
    })))
    out = _correr()
    assert out["respuesta"] == "¡Hola! ¿Para qué fecha es el evento?"
    assert out["comando"] == "nada"
    assert out["mensaje_comando"] is None
    assert out["_meta"]["degradado_handoff"] is False


def test_json_en_fences_tambien_se_parsea(con_llm):
    con_llm(AIMessage(content='```json\n{"respuesta": "listo", "comando": "nada"}\n```'))
    assert _correr()["respuesta"] == "listo"


def test_comando_desconocido_cae_a_nada(con_llm):
    con_llm(AIMessage(content=json.dumps({
        "respuesta": "ok", "comando": "borrar_todo", "mensaje_comando": "x",
    })))
    out = _correr()
    assert out["comando"] == "nada"
    assert out["mensaje_comando"] is None  # sin comando no hay mensaje de comando


def test_mensaje_gabi_conserva_el_lead(con_llm):
    con_llm(AIMessage(content=json.dumps({
        "respuesta": "Le paso tu consulta a Gabriel.",
        "comando": "mensaje_gabi",
        "mensaje_comando": "Fede|2026-12-13|Royal|150",
    })))
    out = _correr()
    assert out["comando"] == "mensaje_gabi"
    assert out["mensaje_comando"] == "Fede|2026-12-13|Royal|150"


def test_prosa_sin_json_se_usa_igual(con_llm):
    """El modelo se olvidó del envoltorio: el texto sirve, no hay que tirarlo."""
    con_llm(AIMessage(content="Claro, contame para cuándo es la fiesta."))
    out = _correr()
    assert out["respuesta"] == "Claro, contame para cuándo es la fiesta."
    assert out["_meta"]["parse_prosa"] is True
    assert out["_meta"]["degradado_handoff"] is False


# ── Degradación ──────────────────────────────────────────────────────────────
def test_sin_respuesta_deriva_a_gabriel(con_llm):
    con_llm(AIMessage(content=""))
    out = _correr()
    assert out["respuesta"] == HANDOFF_RESPUESTA
    assert out["comando"] == "mensaje_gabi"
    assert out["_meta"]["degradado_handoff"] is True


def test_json_roto_deriva_pero_no_avisa_al_cliente(con_llm):
    con_llm(AIMessage(content='{"respuesta": "se cortó'))
    out = _correr()
    assert out["respuesta"] == HANDOFF_RESPUESTA
    assert "error" not in out["respuesta"].lower()
    assert "problema" not in out["respuesta"].lower()


def test_si_el_grafo_explota_igual_hay_respuesta(monkeypatch):
    def _explotar(_audiencia):
        raise RuntimeError("proveedor caído")

    monkeypatch.setattr(nodo_agente, "_modelo", _explotar)
    out = _correr()
    assert out["respuesta"] == HANDOFF_RESPUESTA
    assert out["comando"] == "mensaje_gabi"


# ── Loop de herramientas ─────────────────────────────────────────────────────
def test_ejecuta_la_tool_y_vuelve_al_agente(con_llm, monkeypatch):
    llamadas = []

    def _calendario_falso(fecha: str) -> dict:
        llamadas.append(fecha)
        return {"estado": "disponible", "cantidad_eventos": 0}

    monkeypatch.setattr(registry.calendario, "func", _calendario_falso)

    con_llm(
        AIMessage(content="", tool_calls=[{
            "name": "calendario", "args": {"fecha": "2026-12-13"}, "id": "t1"}]),
        AIMessage(content=json.dumps({"respuesta": "Esa fecha está libre", "comando": "nada"})),
    )
    out = _correr()
    assert llamadas == ["2026-12-13"]
    assert out["respuesta"] == "Esa fecha está libre"
    assert out["_meta"]["iteraciones"] == 2


def test_tool_que_falla_no_rompe_la_conversacion(con_llm, monkeypatch):
    def _romper(fecha: str) -> dict:
        raise RuntimeError("Google no responde")

    monkeypatch.setattr(registry.calendario, "func", _romper)
    con_llm(
        AIMessage(content="", tool_calls=[{
            "name": "calendario", "args": {"fecha": "2026-12-13"}, "id": "t1"}]),
        AIMessage(content=json.dumps({
            "respuesta": "Dejame confirmarlo con Gabriel", "comando": "mensaje_gabi"})),
    )
    out = _correr()
    assert out["respuesta"] == "Dejame confirmarlo con Gabriel"


def test_tool_fuera_de_alcance_no_se_ejecuta(con_llm):
    con_llm(
        AIMessage(content="", tool_calls=[{
            "name": "crear_evento", "args": {"fecha": "2026-12-13"}, "id": "t1"}]),
        AIMessage(content=json.dumps({"respuesta": "ok", "comando": "nada"})),
    )
    out = _correr()
    assert out["respuesta"] == "ok"  # el modelo recibe el error y sigue, no se cae


def test_tope_de_iteraciones(con_llm):
    """Un modelo que solo pide tools no puede girar para siempre."""
    pedido = AIMessage(content="", tool_calls=[{
        "name": "pensar", "args": {"pensamiento": "mmm"}, "id": "t"}])
    con_llm(*[pedido] * 20)
    out = _correr()
    assert out["_meta"]["iteraciones"] <= 6
    assert out["respuesta"] == HANDOFF_RESPUESTA  # nunca se queda sin contestar


# ── Alcance de herramientas (la regla que no se negocia) ─────────────────────
def test_el_externo_no_tiene_herramientas_de_escritura():
    nombres = {t.name for t in registry.para("externo")}
    assert nombres == {"memoria", "calendario", "salones", "pensar"}
    assert not any(v in n for n in nombres for v in registry.VERBOS_DE_ESCRITURA)


def test_audiencia_desconocida_falla_fuerte():
    """Mejor un error que un toolbelt vacío: un agente sin tools contesta cualquier cosa."""
    with pytest.raises(ValueError):
        registry.para("proveedores")


# ── Grafo ────────────────────────────────────────────────────────────────────
def test_el_grafo_compila_con_todos_sus_nodos():
    nodos = set(grafo.compilado().get_graph().nodes)
    assert {"ingesta", "gate", "debounce", "contexto", "agente", "herramientas",
            "guard", "persistencia", "troceo", "salida", "efectos"} <= nodos


def test_directo_recorre_todo_el_camino(con_llm, monkeypatch):
    """El camino completo: media → gate → debounce → agente → troceo → envío → efectos."""
    from app.agents.nodes import efectos as nodo_efectos
    from app.agents.nodes import salida as nodo_salida

    enviados: list[str] = []
    avisos: list[str | None] = []
    monkeypatch.setattr(nodo_salida.canal_ycloud, "enviar",
                        lambda *a: enviados.append(a[2]) or True)
    monkeypatch.setattr(nodo_salida, "PAUSA_SEGUNDOS", 0)
    monkeypatch.setattr(nodo_efectos.post, "avisar_gabi",
                        lambda _i, mc: avisos.append(mc) or True)
    monkeypatch.setattr(nodo_efectos.post, "registrar_crm", lambda *a: True)
    monkeypatch.setattr(nodo_efectos.post, "registrar_csm", lambda *a: True)

    con_llm(AIMessage(content=json.dumps({
        "respuesta": "¡Hola Fede!\n\nContame para qué fecha es.",
        "comando": "mensaje_gabi",
        "mensaje_comando": "Fede|2026-12-13|Royal|150",
    })))

    out = grafo.correr(
        modo="directo", canal="whatsapp", chat_id="+5492954111111", nombre="Fede",
        inbound={"usuario": "+5492954111111", "nosotros": "+5490000",
                 "nombre": "Fede", "tipo": "text", "texto": "hola",
                 "message_id": "wamid.test.directo.1"},
        persistir=False,
    )

    assert out["comando"] == "mensaje_gabi"
    assert enviados == ["¡Hola Fede!", "Contame para qué fecha es."]  # troceado por párrafo
    assert avisos == ["Fede|2026-12-13|Royal|150"]


def test_directo_ignora_el_reintento_del_mismo_mensaje(con_llm, monkeypatch):
    """YCloud reintenta si tardamos: el cliente no puede recibir la respuesta dos veces."""
    from app.agents.nodes import salida as nodo_salida

    monkeypatch.setattr(nodo_salida.canal_ycloud, "enviar", lambda *a: True)
    con_llm(AIMessage(content=json.dumps({"respuesta": "hola", "comando": "nada"})))
    inbound = {"usuario": "+5492954222222", "tipo": "text", "texto": "hola",
               "message_id": "wamid.repetido"}

    primero = grafo.correr(modo="directo", chat_id="+5492954222222",
                           inbound=inbound, persistir=False)
    segundo = grafo.correr(modo="directo", chat_id="+5492954222222",
                           inbound=inbound, persistir=False)

    assert primero["respuesta"] == "hola"
    assert segundo["_meta"]["cortado"] == "duplicado"


def test_kill_switch_corta_antes_de_gastar_un_llm(con_llm, monkeypatch):
    from app.agents.nodes import gate as nodo_gate

    monkeypatch.setattr(nodo_gate.supabase_ops, "automatizacion_activa", lambda: False)
    falso = con_llm(AIMessage(content='{"respuesta": "no deberia", "comando": "nada"}'))

    out = grafo.correr(modo="directo", chat_id="+5492954333333", persistir=False,
                       inbound={"usuario": "+5492954333333", "tipo": "text",
                                "texto": "hola", "message_id": "wamid.killswitch"})

    assert out["_meta"]["cortado"] == "kill_switch"
    assert out["respuesta"] == ""
    assert falso.invocaciones == []


def test_relay_le_pasa_al_modelo_el_mensaje_del_cliente(con_llm):
    """En relay el texto entra tal cual: n8n ya agrupó y ya resolvió el audio/imagen."""
    falso = con_llm(AIMessage(content=json.dumps({"respuesta": "hola", "comando": "nada"})))
    _correr(mensaje="necesito sonido para 200 personas")

    enviados = falso.invocaciones[0]
    assert enviados[0].type == "system"
    ultimo_humano = [m for m in enviados if m.type == "human"][-1]
    assert "necesito sonido para 200 personas" in ultimo_humano.content
    assert "tipo de cliente: minorista" in ultimo_humano.content
