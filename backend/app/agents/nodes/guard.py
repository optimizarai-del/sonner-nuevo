"""Nodo `guard`: convierte la salida del LLM en el contrato, o degrada.

Hay un contrato por audiencia, porque los dos agentes tienen salidas distintas:

    externo  {respuesta, comando ∈ (mensaje_gabi|nada), mensaje_comando}
    interno  {respuesta, comando ∈ (eventos|informacion|materiales|nada), contenido}

Tres caminos, en orden:
1. La respuesta trae JSON (con o sin fences) → se valida con Pydantic.
2. La respuesta es prosa sin llaves → el modelo se olvidó del envoltorio pero el texto
   sirve igual; se usa tal cual en vez de tirarlo.
3. No hay nada usable → se degrada.

La degradación es distinta según quién esté del otro lado, y la diferencia importa:

- Al **cliente** nunca le llega un error técnico. Se deriva a Gabriel con un mensaje
  natural, indistinguible de las derivaciones normales. Un "tuve un problema procesando
  tu mensaje" es una conversación de venta perdida.
- Al **equipo** sí se le dice que falló, porque son quienes pueden hacer algo al
  respecto. Fingir normalidad ahí esconde el problema y encima los deja esperando una
  acción que nunca se ejecutó.
"""
from __future__ import annotations

import logging
from typing import Literal, Optional

from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field, ValidationError, field_validator

from ...obs import runs
from ...services.agente_core import extraer_json
from ..state import SonnerState

log = logging.getLogger("agents.nodes.guard")

HANDOFF_RESPUESTA = (
    "¡Gracias por tu mensaje! 🙌 Dame un momento que le paso tu consulta a "
    "Gabriel y en breve se comunica con vos con todos los detalles."
)
FALLA_INTERNA = (
    "No pude completar esa acción por un error del sistema. "
    "No se ejecutó ningún cambio — probá de nuevo en un momento."
)

_NULOS = {"", "null", "none", "undefined"}


def _limpiar_opcional(v: object) -> Optional[str]:
    if not isinstance(v, str) or v.strip().lower() in _NULOS:
        return None
    return v.strip()


class ContratoExterno(BaseModel):
    respuesta: str = Field(default="")
    comando: Literal["mensaje_gabi", "nada"] = "nada"
    mensaje_comando: Optional[str] = None

    @field_validator("comando", mode="before")
    @classmethod
    def _comando_conocido(cls, v: object) -> str:
        texto = str(v or "nada").strip()
        return texto if texto in ("mensaje_gabi", "nada") else "nada"

    @field_validator("mensaje_comando", mode="before")
    @classmethod
    def _limpiar(cls, v: object) -> Optional[str]:
        return _limpiar_opcional(v)

    def model_post_init(self, _ctx: object) -> None:
        if self.comando == "nada":
            object.__setattr__(self, "mensaje_comando", None)


class ContratoInterno(BaseModel):
    respuesta: str = Field(default="")
    comando: Literal["eventos", "informacion", "materiales", "nada"] = "nada"
    contenido: Optional[str] = None

    @field_validator("comando", mode="before")
    @classmethod
    def _comando_conocido(cls, v: object) -> str:
        texto = str(v or "nada").strip().lower()
        return texto if texto in ("eventos", "informacion", "materiales", "nada") else "nada"

    @field_validator("contenido", mode="before")
    @classmethod
    def _limpiar(cls, v: object) -> Optional[str]:
        return _limpiar_opcional(v)

    def model_post_init(self, _ctx: object) -> None:
        # Sin comando de guardado no hay nada que guardar; el prompt manda "nada"
        # literal como contenido y eso no puede terminar en el vector store.
        if self.comando == "nada":
            object.__setattr__(self, "contenido", None)


CONTRATOS = {"externo": ContratoExterno, "interno": ContratoInterno}


def _texto_final(state: SonnerState) -> str:
    for mensaje in reversed(state.get("messages") or []):
        if isinstance(mensaje, AIMessage):
            contenido = mensaje.content
            if isinstance(contenido, list):  # Anthropic devuelve bloques
                contenido = "".join(
                    b.get("text", "") for b in contenido if isinstance(b, dict)
                )
            return str(contenido or "").strip()
    return ""


def _degradar(state: SonnerState, meta: dict) -> dict:
    audiencia = state.get("audiencia") or "externo"
    chat_id = state.get("chat_id") or ""
    nombre = state.get("nombre") or ""
    meta["motivo_handoff"] = meta.get("parse_error", "sin_respuesta")
    log.warning("degradado (audiencia=%s chat=%s meta=%s)", audiencia, chat_id, meta)

    if audiencia == "interno":
        return {"respuesta": FALLA_INTERNA, "comando": "nada", "contenido": None,
                "degradado": True, "meta": meta}
    return {
        "respuesta": HANDOFF_RESPUESTA,
        "comando": "mensaje_gabi",
        "mensaje_comando": nombre if nombre and nombre != chat_id else None,
        "degradado": True,
        "meta": meta,
    }


def guard(state: SonnerState) -> dict:
    audiencia = state.get("audiencia") or "externo"
    Contrato = CONTRATOS.get(audiencia, ContratoExterno)
    meta = dict(state.get("meta") or {})
    contrato: BaseModel | None = None

    with runs.paso("guard"):
        crudo = _texto_final(state)
        objeto = extraer_json(crudo)
        if objeto:
            try:
                contrato = Contrato(**objeto)
            except ValidationError as e:
                meta["parse_error"] = str(e)[:300]
        elif crudo and "{" not in crudo and "}" not in crudo:
            contrato = Contrato(respuesta=crudo)
            meta["parse_prosa"] = True
        elif crudo:
            meta["parse_error"] = "hay llaves pero no se pudo extraer un JSON válido"
        else:
            meta["parse_error"] = "el modelo no devolvió texto"

    if contrato is None or not contrato.respuesta.strip():
        return _degradar(state, meta)

    salida = {"respuesta": contrato.respuesta.strip(), "comando": contrato.comando,
              "degradado": False, "meta": meta}
    if isinstance(contrato, ContratoInterno):
        salida["contenido"] = contrato.contenido
    else:
        salida["mensaje_comando"] = contrato.mensaje_comando
    return salida
