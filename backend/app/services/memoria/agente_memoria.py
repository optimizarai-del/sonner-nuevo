"""Sub-agente Memoria con LLM (Claude primario, OpenAI de reserva).

Flujo:
1. El Agente Principal manda un comando ("buscar en materiales: parlantes", etc).
2. Un LLM (Claude por defecto, OpenAI si Claude falla) elige la/s fuente/s y
   llama la tool `buscar_memoria`, que ejecuta la búsqueda pgvector determinística.
3. El LLM redacta el contrato {origen, encontrado, respuesta} en español de
   Argentina, VERBATIM desde los chunks, aplicando las reglas de privacidad.
4. Si los dos LLM fallan (sin API key, caídos, etc.) → cae al parser
   determinístico `memoria.consultar`, así NUNCA se queda sin responder.

NUNCA inventa: la respuesta sale del contenido devuelto por la tool.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from ...config import settings
from . import memoria as det
from . import vectorstore as vs

log = logging.getLogger("memoria.agente")

SYSTEM_PROMPT = """Sos el bibliotecario técnico de SONNER (sonido e iluminación para eventos).
Tu CLIENTE es el Agente Principal, NO el usuario final. Hablás en español de Argentina (voseo).

TU ÚNICA SALIDA es UN objeto JSON, sin texto afuera:
{"origen": "...", "encontrado": "si|no", "respuesta": "..."}

FUENTES (usá la tool `buscar_memoria` con el parámetro `fuente`):
- materiales            → stock, equipos, cantidades.
- eventos               → histórico de eventos, fechas, salones, estados.
- modelo_eventos        → configuraciones técnicas estándar (códigos CFG-XXX): equipos incluidos y precio sugerido.
- informacion_interna   → políticas, procedimientos, condiciones internas (seña, reservas, etc).
Si no sabés la fuente o la consulta toca varias, llamá la tool SIN `fuente` (busca en todas)
o llamala varias veces (máximo 3 llamadas en total).

REGLAS:
- NO INVENTES. Reportá SOLO lo que devuelva la tool. Si un dato no viene, decí "sin dato".
  Si no hay resultados: encontrado:"no" y respuesta "No se encontró información sobre [X]".
- VERBATIM: la `respuesta` sale del contenido de los chunks; no reformules cifras, marcas ni equipos.
- PRIVACIDAD: todo precio, monto o composición técnica (modelo_eventos) e info interna es INTERNO.
  Prefijá esos datos con el texto EXACTO y LITERAL "[INTERNO — NO COMUNICAR AL CLIENTE] "
  (copialo tal cual, NO lo reformules como "[MODELO TÉCNICO]", "[STOCK]", "[INFORMACIÓN]" ni nada parecido;
  el Agente Principal busca ESE texto literal para saber qué ocultarle al cliente). Aclará que el precio
  depende de logística. El stock de materiales NO es interno (podés mencionarlo sin prefijo).
- Para códigos CFG usá EXCLUSIVAMENTE la fuente modelo_eventos.
- `origen`: "materiales" | "eventos" | "modelo eventos" | "interna" | "mixto".
- `encontrado`: "si" si existe el registro (stock 0 igual es "si").
- Si combinás fuentes, numerá 1) 2) 3) dentro de `respuesta`.

Respondé SOLO el JSON."""

# ── Tool compartida por ambos proveedores ─────────────────────────────────────
_TOOL_NAME = "buscar_memoria"
_TOOL_DESC = ("Busca chunks en el vector store de SONNER (Supabase pgvector). "
              "Pasá la consulta tal cual y, si la conocés, la fuente.")
_TOOL_PARAMS = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Consulta a buscar (sin el prefijo de comando)."},
        "fuente": {
            "type": "string",
            "enum": list(vs.FUENTES_VALIDAS),
            "description": "materiales|eventos|modelo_eventos|informacion_interna. Omitir para buscar en todas.",
        },
        "k": {"type": "integer", "description": "Top-K chunks (default 5).", "default": 5},
    },
    "required": ["query"],
}


def _dispatch(args: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecuta la búsqueda y devuelve chunks crudos para que el LLM redacte."""
    fuente = args.get("fuente")
    if fuente and fuente not in vs.FUENTES_VALIDAS:
        fuente = None
    k = int(args.get("k") or settings.MEMORIA_TOPK)
    chunks = vs.buscar(
        args.get("query", ""),
        fuente=fuente,
        k=k,
        min_similarity=settings.MEMORIA_MIN_SIMILARITY,
    )
    return {
        "fuente": fuente or "(todas)",
        "encontrados": len(chunks),
        "chunks": [
            {"fuente": c.get("fuente"), "similarity": c.get("similarity"), "content": c.get("content")}
            for c in chunks
        ],
    }


def _extraer_json(texto: str) -> Optional[Dict[str, Any]]:
    if not texto:
        return None
    texto = texto.strip()
    # quitar fences ```json ... ```
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto, flags=re.I).strip()
    try:
        obj = json.loads(texto)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    m = re.search(r"\{.*\}", texto, re.S)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                return obj
        except Exception:
            return None
    return None


def _normalizar_contrato(obj: Dict[str, Any]) -> Dict[str, Any]:
    origen = str(obj.get("origen") or "mixto").strip().lower()
    enc = str(obj.get("encontrado") or "no").strip().lower()
    enc = "si" if enc in ("si", "sí", "true", "yes") else "no"
    return {
        "origen": origen,
        "encontrado": enc,
        "respuesta": str(obj.get("respuesta") or "").strip(),
    }


# ── Driver Anthropic (Claude) ─────────────────────────────────────────────────
def _responder_anthropic(mensaje: str, historial: List[Dict[str, str]], max_iter: int) -> Dict[str, Any]:
    import anthropic

    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY no configurada")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=30, max_retries=1)
    tools = [{"name": _TOOL_NAME, "description": _TOOL_DESC, "input_schema": _TOOL_PARAMS}]

    messages: List[Dict[str, Any]] = []
    for h in (historial or [])[-6:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": mensaje})

    usados = 0
    for _ in range(max_iter):
        resp = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=tools,
        )
        messages.append({"role": "assistant", "content": resp.content})

        tool_uses = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
        if not tool_uses:
            texto = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text")
            obj = _extraer_json(texto)
            if obj:
                return _normalizar_contrato(obj)
            raise RuntimeError("Claude no devolvió JSON parseable")

        results = []
        for tu in tool_uses:
            usados += 1
            try:
                out = _dispatch(tu.input or {}) if usados <= 3 else {"error": "límite de búsquedas"}
            except Exception as e:
                out = {"error": str(e)}
            results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": json.dumps(out, ensure_ascii=False),
            })
        messages.append({"role": "user", "content": results})

    raise RuntimeError("Claude: máx iteraciones sin respuesta final")


# ── Driver OpenAI (reserva) ───────────────────────────────────────────────────
def _responder_openai(mensaje: str, historial: List[Dict[str, str]], max_iter: int) -> Dict[str, Any]:
    from openai import OpenAI

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY no configurada")
    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=30, max_retries=1)
    tools = [{
        "type": "function",
        "function": {"name": _TOOL_NAME, "description": _TOOL_DESC, "parameters": _TOOL_PARAMS},
    }]

    messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in (historial or [])[-6:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": mensaje})

    usados = 0
    for _ in range(max_iter):
        resp = client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0,
        )
        msg = resp.choices[0].message
        asst: Dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            asst["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]
        messages.append(asst)

        if not msg.tool_calls:
            obj = _extraer_json(msg.content or "")
            if obj:
                return _normalizar_contrato(obj)
            raise RuntimeError("OpenAI no devolvió JSON parseable")

        for tc in msg.tool_calls:
            usados += 1
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            try:
                out = _dispatch(args) if usados <= 3 else {"error": "límite de búsquedas"}
            except Exception as e:
                out = {"error": str(e)}
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(out, ensure_ascii=False),
            })

    raise RuntimeError("OpenAI: máx iteraciones sin respuesta final")


# ── Orquestador con fallback en cadena ────────────────────────────────────────
def responder(
    mensaje: str,
    historial: Optional[List[Dict[str, str]]] = None,
    max_iter: int = 4,
) -> Dict[str, Any]:
    """Claude → OpenAI → parser determinístico. Devuelve {origen, encontrado, respuesta, _meta}."""
    t0 = time.time()
    if not mensaje or not mensaje.strip():
        return {"origen": "mixto", "encontrado": "no",
                "respuesta": "Comando vacío: no se ejecutó ninguna búsqueda."}

    historial = historial or []
    intentos: List[str] = []

    for proveedor, fn in (("claude", _responder_anthropic), ("openai", _responder_openai)):
        try:
            out = fn(mensaje, historial, max_iter)
            out["_meta"] = {"proveedor": proveedor, "tiempo_ms": int((time.time() - t0) * 1000),
                            "intentos": intentos}
            return out
        except Exception as e:
            log.warning("memoria LLM %s falló: %s", proveedor, e)
            intentos.append(f"{proveedor}: {e}")

    # Último recurso: parser determinístico (sin LLM).
    out = det.consultar(mensaje)
    out.setdefault("_meta", {})
    out["_meta"].update({"proveedor": "deterministico", "intentos": intentos,
                         "tiempo_ms": int((time.time() - t0) * 1000)})
    return out
