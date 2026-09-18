"""Estado compartido del grafo de agentes.

Un solo `SonnerState` para los dos grafos (externo e interno) y los tres transportes
(whatsapp, telegram, web). Lo que cambia entre ellos son las tools bindeadas y el prompt,
no la forma del estado.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

Canal = Literal["whatsapp", "telegram", "web"]
Audiencia = Literal["externo", "interno"]

# "directo": el mensaje entra por nuestro webhook, así que el grafo hace todo
#            (media, kill-switch, blocklist, debounce, envío, CRM/CSM).
# "relay":   n8n ya hizo el gate, el debounce y va a enviar él; el grafo solo piensa.
#            Es el modo en que corre producción hoy, vía POST /api/agente/n8n.
Modo = Literal["directo", "relay"]


class SonnerState(TypedDict, total=False):
    # ── Identidad de la corrida ──────────────────────────────────────────────
    run_id: str
    canal: Canal
    audiencia: Audiencia
    chat_id: str            # teléfono (whatsapp) o chat de Telegram / sesión web
    nombre: str

    # ── Entrada ──────────────────────────────────────────────────────────────
    inbound: dict[str, Any]  # payload crudo normalizado por el transporte
    mensaje_actual: str      # texto ya resuelto (audio/imagen transcriptos)
    modo: Modo
    persistir: bool          # False en el endpoint de prueba, para no ensuciar el historial

    # ── Conversación ─────────────────────────────────────────────────────────
    messages: Annotated[list[AnyMessage], add_messages]

    # ── Contexto de negocio ──────────────────────────────────────────────────
    # None = todavía no se resolvió; el nodo `contexto` lo completa. El transporte
    # puede precargarlos (n8n ya los manda) para ahorrar dos consultas.
    tipo_cliente: Optional[Literal["minorista", "mayorista"]]
    reunion: Optional[dict[str, Any]]

    # ── Salida ───────────────────────────────────────────────────────────────
    respuesta: Optional[str]
    # El comando y su carga dependen de la audiencia (ver nodes/guard.py):
    #   externo → comando mensaje_gabi|nada  + mensaje_comando (datos del lead)
    #   interno → comando eventos|informacion|materiales|nada + contenido (a ingestar)
    comando: Optional[str]
    mensaje_comando: Optional[str]
    contenido: Optional[str]
    fragmentos: list[str]

    # ── Control ──────────────────────────────────────────────────────────────
    degradado: bool
    motivo_corte: Optional[str]   # kill_switch | blocklist | sin_texto | debounce
    meta: dict[str, Any]


def nuevo(
    *,
    run_id: str,
    canal: Canal,
    audiencia: Audiencia,
    chat_id: str,
    modo: Modo,
    inbound: dict[str, Any] | None = None,
    nombre: str = "",
    mensaje_actual: str = "",
    tipo_cliente: str | None = None,
    reunion: dict[str, Any] | None = None,
    persistir: bool = True,
) -> SonnerState:
    """Estado inicial con los defaults seguros (sin esto cada nodo tendría que usar .get)."""
    return SonnerState(
        run_id=run_id,
        canal=canal,
        audiencia=audiencia,
        chat_id=chat_id,
        nombre=nombre or chat_id,
        inbound=inbound or {},
        mensaje_actual=mensaje_actual,
        modo=modo,
        persistir=persistir,
        messages=[],
        tipo_cliente=tipo_cliente,  # type: ignore[arg-type]
        reunion=reunion,
        respuesta=None,
        comando=None,
        mensaje_comando=None,
        contenido=None,
        fragmentos=[],
        degradado=False,
        motivo_corte=None,
        meta={},
    )
