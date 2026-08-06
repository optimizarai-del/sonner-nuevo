"""Motor de agente reusable: loop de tool-calling con fallback de proveedor.

Claude (Anthropic) primario → OpenAI de reserva. Mismo patrón que
`services/memoria/agente_memoria.py`, pero genérico: recibe el system prompt, el
mensaje, el historial y una lista de `Herramienta`, corre el loop de tool-calling y
devuelve el texto final del LLM (que cada agente parsea según su propio contrato JSON).

Diseño:
- Las tools se ejecutan con `Herramienta.correr()` (nunca lanza; devuelve {"error"} si falla).
- `max_tool_calls` frena loops de tools infinitos.
- Si los dos proveedores fallan, se lanza RuntimeError (el agente decide su fallback).
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Optional

from ...config import settings
from .tipos import Herramienta

log = logging.getLogger("agente_core.motor")

# Reintentos extra por proveedor ante errores TRANSITORIOS (sobrecarga, rate-limit,
# timeouts). Backoff en segundos entre reintentos. El intento inicial no cuenta acá.
_MAX_REINTENTOS = 1
_BACKOFF = (1.5, 3.0)


def _es_transitorio(e: Exception) -> bool:
    """True si el error pinta recuperable reintentando (no un error de config/permiso)."""
    s = f"{type(e).__name__} {e}".lower()
    marcas = (
        "overloaded", "overload", "rate limit", "ratelimit", "429", "500", "502",
        "503", "529", "timeout", "timed out", "connection", "temporarily",
        "unavailable", "service_unavailable", "internalservererror", "apiconnection",
    )
    return any(m in s for m in marcas)


# ── Helper: extraer un objeto JSON de la respuesta del LLM ────────────────────
def extraer_json(texto: str) -> Optional[dict[str, Any]]:
    """Devuelve el primer objeto JSON del texto (tolera ```json fences y texto suelto)."""
    if not texto:
        return None
    t = texto.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I).strip()
    try:
        obj = json.loads(t)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    m = re.search(r"\{.*\}", t, re.S)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                return obj
        except Exception:
            return None
    return None


def _historial_valido(historial: Optional[list[dict[str, str]]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for h in (historial or []):
        if h.get("role") in ("user", "assistant") and h.get("content"):
            out.append({"role": h["role"], "content": str(h["content"])})
    return out


# ── Driver Anthropic (Claude) ─────────────────────────────────────────────────
def _via_anthropic(
    system: str,
    mensaje: str,
    historial: list[dict[str, str]],
    herramientas: list[Herramienta],
    max_iter: int,
    max_tool_calls: int,
    max_tokens: int,
    modelo: str,
) -> str:
    import anthropic

    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY no configurada")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=45, max_retries=2)
    tools = [
        {"name": h.nombre, "description": h.descripcion, "input_schema": h.parametros}
        for h in herramientas
    ]
    por_nombre = {h.nombre: h for h in herramientas}

    messages: list[dict[str, Any]] = list(historial)
    messages.append({"role": "user", "content": mensaje})

    usados = 0
    for _ in range(max_iter):
        kwargs: dict[str, Any] = {
            "model": modelo,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        resp = client.messages.create(**kwargs)
        messages.append({"role": "assistant", "content": resp.content})

        tool_uses = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
        if not tool_uses:
            return "".join(
                getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text"
            )

        results = []
        for tu in tool_uses:
            usados += 1
            if usados > max_tool_calls:
                out: Any = {"error": "límite de tool calls alcanzado"}
            else:
                herr = por_nombre.get(tu.name)
                out = herr.correr(tu.input or {}) if herr else {"error": f"tool desconocida: {tu.name}"}
            results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": json.dumps(out, ensure_ascii=False) if not isinstance(out, str) else out,
            })
        messages.append({"role": "user", "content": results})

    raise RuntimeError("Claude: máx iteraciones sin respuesta final")


# ── Driver OpenAI (reserva) ───────────────────────────────────────────────────
def _via_openai(
    system: str,
    mensaje: str,
    historial: list[dict[str, str]],
    herramientas: list[Herramienta],
    max_iter: int,
    max_tool_calls: int,
    max_tokens: int,
    modelo: str,
) -> str:
    from openai import OpenAI

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY no configurada")
    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=45, max_retries=2)
    tools = [
        {"type": "function",
         "function": {"name": h.nombre, "description": h.descripcion, "parameters": h.parametros}}
        for h in herramientas
    ]
    por_nombre = {h.nombre: h for h in herramientas}

    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    messages.extend(historial)
    messages.append({"role": "user", "content": mensaje})

    usados = 0
    for _ in range(max_iter):
        kwargs: dict[str, Any] = {"model": modelo, "messages": messages, "temperature": 0}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        resp = client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        asst: dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            asst["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]
        messages.append(asst)

        if not msg.tool_calls:
            return msg.content or ""

        for tc in msg.tool_calls:
            usados += 1
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            if usados > max_tool_calls:
                out: Any = {"error": "límite de tool calls alcanzado"}
            else:
                herr = por_nombre.get(tc.function.name)
                out = herr.correr(args) if herr else {"error": f"tool desconocida: {tc.function.name}"}
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(out, ensure_ascii=False) if not isinstance(out, str) else out,
            })

    raise RuntimeError("OpenAI: máx iteraciones sin respuesta final")


# ── Orquestador con fallback en cadena ────────────────────────────────────────
def responder(
    *,
    system: str,
    mensaje: str,
    historial: Optional[list[dict[str, str]]] = None,
    herramientas: Optional[list[Herramienta]] = None,
    max_iter: int = 6,
    max_tool_calls: int = 8,
    max_tokens: int = 1500,
    modelo_anthropic: Optional[str] = None,
    modelo_openai: Optional[str] = None,
) -> dict[str, Any]:
    """Corre el agente: Claude → OpenAI. Devuelve {"texto": str, "_meta": {...}}.

    `texto` es la respuesta cruda del LLM (cada agente la parsea a su contrato).
    Lanza RuntimeError sólo si TODOS los proveedores fallan.
    """
    t0 = time.time()
    hist = _historial_valido(historial)
    herrs = herramientas or []
    intentos: list[str] = []

    drivers = (
        ("claude", _via_anthropic, modelo_anthropic or settings.ANTHROPIC_MODEL),
        ("openai", _via_openai, modelo_openai or settings.OPENAI_CHAT_MODEL),
    )
    for proveedor, fn, modelo in drivers:
        for intento in range(1 + _MAX_REINTENTOS):
            try:
                texto = fn(system, mensaje, hist, herrs, max_iter, max_tool_calls, max_tokens, modelo)
                return {
                    "texto": texto,
                    "_meta": {"proveedor": proveedor, "modelo": modelo,
                              "tiempo_ms": int((time.time() - t0) * 1000), "intentos": intentos},
                }
            except Exception as e:  # noqa: BLE001
                transitorio = _es_transitorio(e)
                log.warning("motor %s intento %d/%d falló (%s): %s", proveedor, intento + 1,
                            1 + _MAX_REINTENTOS, "transitorio" if transitorio else "definitivo", e)
                intentos.append(f"{proveedor}#{intento + 1}: {e}")
                if transitorio and intento < _MAX_REINTENTOS:
                    time.sleep(_BACKOFF[min(intento, len(_BACKOFF) - 1)])
                    continue
                break  # error definitivo o sin reintentos → probar el siguiente proveedor

    raise RuntimeError("Todos los proveedores LLM fallaron: " + " | ".join(intentos))
