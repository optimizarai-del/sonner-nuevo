"""Historial de conversación del Agente Principal (Tomi), sobre `n8n_chat_histories`.

Se reusa la MISMA tabla que usa n8n hoy para no perder contexto y poder correr el
agente en código en paralelo con n8n durante el corte.

Schema de la tabla (formato LangChain, escrito por n8n):
    id          bigint (PK, autoincrement)
    session_id  text     → teléfono del cliente con prefijo '+' (ej. '+5492954...')
    message     jsonb    → {"type": "human"|"ai"|"tool", "content": str,
                            "additional_kwargs": {}, "response_metadata": {}}

Detalles del formato que n8n dejó y que respetamos:
- El mensaje humano viene envuelto en un template:
      "recibes el siguiente mensaje \n{texto}\n\nestas hablando con: {nombre}"
- La respuesta del agente ("ai") se guarda como JSON string: {"output":{"respuesta": "..."}}
- Además n8n persiste el scratchpad del agente: filas "ai" tipo "Calling Think with
  input: ..." y filas "tool". Al reconstruir el historial LIMPIO las salteamos:
  solo nos quedan los turnos human→user y la respuesta final ai→assistant.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from .. import credentials as creds_service

logger = logging.getLogger("agente.historial")

# El agente EXTERNO (cliente, YCloud) usa external_chat_histories;
# los agentes INTERNOS (página + telegram) usan n8n_chat_histories.
TABLE_EXTERNO = "external_chat_histories"
TABLE_INTERNO = "n8n_chat_histories"
DEFAULT_TABLE = TABLE_EXTERNO
# Cuántos turnos recientes (user/assistant) se reinyectan como contexto.
CONTEXT_LIMIT = 12
# Cuántas filas crudas leer para reconstruir esos turnos (hay ruido de tool/think).
RAW_FETCH = 60


def _sb():
    sb = creds_service._admin()
    if sb is None:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY no configurada — historial deshabilitado")
    return sb


def normalizar_session(telefono: str) -> str:
    """Normaliza el teléfono al formato de session_id que usa n8n ('+<digitos>')."""
    s = str(telefono or "").strip()
    if not s:
        return s
    digitos = "".join(ch for ch in s if ch.isdigit())
    return "+" + digitos if digitos else s


def _parse_message(raw: Any) -> dict[str, Any]:
    """El campo `message` puede venir como dict o como string JSON."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}
    return {}


def _desenvolver_humano(content: str) -> str:
    """Quita el template 'recibes el siguiente mensaje ... estas hablando con: ...'."""
    if not content:
        return ""
    texto = content
    marca_ini = "recibes el siguiente mensaje"
    if marca_ini.lower() in texto.lower():
        idx = texto.lower().find(marca_ini.lower())
        texto = texto[idx + len(marca_ini):].lstrip(" \n:")
    marca_fin = "estas hablando con"
    pos = texto.lower().find(marca_fin.lower())
    if pos != -1:
        texto = texto[:pos]
    return texto.strip()


def _extraer_respuesta_ai(content: str) -> str | None:
    """De la fila 'ai' final saca el texto de {"output":{"respuesta": "..."}}.

    Devuelve None si es scratchpad (p.ej. 'Calling Think with input: ...') para saltearla.
    """
    if not content:
        return None
    c = content.strip()
    if c.lower().startswith("calling "):  # scratchpad del agente LangChain
        return None
    try:
        obj = json.loads(c)
        if isinstance(obj, dict):
            out = obj.get("output")
            if isinstance(out, dict) and out.get("respuesta"):
                return str(out["respuesta"]).strip()
            if isinstance(obj.get("respuesta"), str):
                return obj["respuesta"].strip()
    except Exception:
        pass
    # Texto plano de la IA (sin envoltura JSON) → lo tomamos tal cual.
    return c


def cargar(telefono: str, limit: int = CONTEXT_LIMIT, tabla: str = DEFAULT_TABLE) -> list[dict[str, str]]:
    """Últimos turnos limpios en orden cronológico como [{role, content}].

    role ∈ {"user", "assistant"}. Saltea filas tool y scratchpad ('Calling ...').
    """
    session_id = normalizar_session(telefono)
    if not session_id:
        return []
    try:
        res = (
            _sb().table(tabla)
            .select("id, message")
            .eq("session_id", session_id)
            .order("id", desc=True)
            .limit(RAW_FETCH)
            .execute()
        )
        rows = res.data or []
    except Exception as e:  # noqa: BLE001
        logger.warning("No se pudo cargar historial de %s: %s", session_id, e)
        return []

    rows.reverse()  # cronológico (viejo → nuevo)
    turnos: list[dict[str, str]] = []
    for r in rows:
        msg = _parse_message(r.get("message"))
        tipo = msg.get("type")
        content = msg.get("content") or ""
        if tipo == "human":
            texto = _desenvolver_humano(content)
            if texto:
                turnos.append({"role": "user", "content": texto})
        elif tipo == "ai":
            resp = _extraer_respuesta_ai(content)
            if resp:
                turnos.append({"role": "assistant", "content": resp})
        # tipo == "tool" u otros → ruido de scratchpad, se saltea
    return turnos[-limit:]


def _insert(session_id: str, tipo: str, content: str, tabla: str) -> None:
    _sb().table(tabla).insert({
        "session_id": session_id,
        "message": {
            "type": tipo,
            "content": content,
            "additional_kwargs": {},
            "response_metadata": {},
        },
    }).execute()


def guardar_usuario(telefono: str, texto: str, nombre_contacto: str = "", tabla: str = DEFAULT_TABLE) -> None:
    """Guarda el mensaje entrante del cliente en el mismo template que usa n8n."""
    session_id = normalizar_session(telefono)
    if not session_id or not texto:
        return
    envuelto = f"recibes el siguiente mensaje \n{texto}"
    if nombre_contacto:
        envuelto += f"\n\nestas hablando con: {nombre_contacto}"
    try:
        _insert(session_id, "human", envuelto, tabla)
    except Exception as e:  # noqa: BLE001
        logger.warning("No se pudo guardar mensaje de usuario %s: %s", session_id, e)


def guardar_agente(telefono: str, respuesta: str, tabla: str = DEFAULT_TABLE) -> None:
    """Guarda la respuesta final del agente en formato {"output":{"respuesta":...}}."""
    session_id = normalizar_session(telefono)
    if not session_id or not respuesta:
        return
    payload = json.dumps({"output": {"respuesta": respuesta}}, ensure_ascii=False)
    try:
        _insert(session_id, "ai", payload, tabla)
    except Exception as e:  # noqa: BLE001
        logger.warning("No se pudo guardar respuesta del agente %s: %s", session_id, e)
