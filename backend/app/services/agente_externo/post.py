"""Post-proceso del agente externo: enviar respuesta + avisar a Gabi + CRM + CSM.

Reemplaza las 4 ramas post-agente de n8n:
- Trocear mensaje (≤4) → YCloud sendDirectly (con pausas).
- Switch comando=mensaje_gabi → Telegram a Gabi con el lead.
- Basic LLM Chain → crm_registrar_interaccion.
- Mapear CSM → /api/csm/log (acá: csm.insert_log directo).
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional

import httpx

from ...config import settings
from .. import credentials as creds_service
from .. import csm
from ..agente_core import responder as motor_responder, extraer_json
from . import canal_ycloud

log = logging.getLogger("agente_externo.post")


# ── Trocear en ≤4 mensajes (misma lógica que n8n) ─────────────────────────────
def trocear(respuesta: str, maximo: int = 4) -> list[str]:
    texto = (respuesta or "").strip()
    if not texto:
        return []
    bloques = [b.strip() for b in re.split(r"\n{2,}", texto) if b.strip()]
    if len(bloques) == 1:
        bloques = [s.strip() for s in re.split(r"(?<=[.!?])\s+", texto) if s.strip()]
    if len(bloques) <= maximo:
        return bloques
    grupos: list[list[str]] = [[] for _ in range(maximo)]
    por_grupo = max(1, -(-len(bloques) // maximo))  # ceil
    for i, b in enumerate(bloques):
        grupos[min(i // por_grupo, maximo - 1)].append(b)
    return [" ".join(g) for g in grupos if g]


def enviar_respuesta(inbound: dict[str, Any], respuesta: str, pausa: float = 2.0) -> int:
    """Envía la respuesta troceada por YCloud. Devuelve cuántos mensajes se enviaron."""
    partes = trocear(respuesta)
    enviados = 0
    for i, parte in enumerate(partes):
        ok = canal_ycloud.enviar(inbound.get("usuario"), inbound.get("nosotros"), parte)
        enviados += 1 if ok else 0
        if i < len(partes) - 1:
            time.sleep(pausa)
    return enviados


# ── Aviso a Gabi por Telegram ─────────────────────────────────────────────────
def avisar_gabi(inbound: dict[str, Any], mensaje_comando: Optional[str]) -> bool:
    token = creds_service.get("TELEGRAM_BOT_TOKEN", settings.TELEGRAM_BOT_TOKEN) or ""
    chat_id = creds_service.get("GABI_TELEGRAM_CHAT_ID", settings.GABI_TELEGRAM_CHAT_ID) or ""
    if not (token and chat_id):
        log.warning("TELEGRAM_BOT_TOKEN/GABI_TELEGRAM_CHAT_ID sin configurar — no aviso a Gabi")
        return False
    partes = [p.strip() for p in (mensaje_comando or "").split("|")]
    nombre = partes[0] if len(partes) > 0 else ""
    fecha = partes[1] if len(partes) > 1 else ""
    salon = partes[2] if len(partes) > 2 else ""
    pax = partes[3] if len(partes) > 3 else ""
    cliente = inbound.get("usuario") or ""
    t = "🔔 NUEVO LEAD - Contactar\n\n"
    if nombre and nombre.lower() != "null": t += f"👤 Cliente: {nombre}\n"
    if fecha and fecha.lower() != "null":   t += f"📅 Fecha: {fecha}\n"
    if salon and salon.lower() != "null":   t += f"📍 Salón: {salon}\n"
    if pax and pax.lower() != "null":       t += f"👥 PAX: {pax}\n"
    if cliente:                              t += f"📱 WhatsApp: {cliente}"
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": t.strip(), "disable_web_page_preview": True},
            timeout=20,
        )
        return r.status_code < 300
    except Exception as e:  # noqa: BLE001
        log.warning("avisar_gabi falló: %s", e)
        return False


# ── CRM ───────────────────────────────────────────────────────────────────────
_CRM_SYS = (
    "Sos un analista de CRM. Tu única salida es un objeto JSON válido, sin texto extra ni "
    "bloques de código. Campos: nota (resumen Cliente / Interés / Situación / Acción), "
    "tipo_evento (string o \"\"), lugar_evento (string o \"\"), fecha_evento (YYYY-MM-DD o \"\"). "
    "Si un dato no aparece, dejá string vacío; nunca inventes."
)


def _extraer_crm(texto_cliente: str, respuesta: str) -> dict[str, str]:
    try:
        out = motor_responder(
            system=_CRM_SYS,
            mensaje=f"[MENSAJE]: {texto_cliente}\n[RESPUESTA IA]: {respuesta}",
            historial=[], herramientas=[], max_iter=1, max_tokens=400,
        )
        obj = extraer_json(out.get("texto") or "") or {}
    except Exception as e:  # noqa: BLE001
        log.warning("extraer_crm falló: %s", e)
        obj = {}
    return {
        "nota": str(obj.get("nota") or "").strip(),
        "tipo_evento": str(obj.get("tipo_evento") or "").strip(),
        "lugar_evento": str(obj.get("lugar_evento") or "").strip(),
        "fecha_evento": str(obj.get("fecha_evento") or "").strip(),
    }


def registrar_crm(inbound: dict[str, Any], texto_cliente: str, respuesta: str) -> bool:
    """LLM extrae datos → RPC crm_registrar_interaccion(telefono,nombre,nota,tipo,lugar,fecha)."""
    datos = _extraer_crm(texto_cliente, respuesta)
    sb = creds_service._admin()
    if sb is None:
        return False
    args = [inbound.get("usuario") or "", inbound.get("nombre") or "",
            datos["nota"], datos["tipo_evento"], datos["lugar_evento"], datos["fecha_evento"]]
    # La función es positional ($1..$6); probamos esquemas de nombres comunes de supabase-rpc.
    esquemas = [
        {"p_telefono": args[0], "p_nombre": args[1], "p_nota": args[2],
         "p_tipo_evento": args[3], "p_lugar_evento": args[4], "p_fecha_evento": args[5]},
        {"telefono": args[0], "nombre": args[1], "nota": args[2],
         "tipo_evento": args[3], "lugar_evento": args[4], "fecha_evento": args[5]},
    ]
    for params in esquemas:
        try:
            sb.rpc("crm_registrar_interaccion", params).execute()
            return True
        except Exception:
            continue
    log.warning("crm_registrar_interaccion: ningún esquema de parámetros funcionó (revisar firma real)")
    return False


# ── CSM ───────────────────────────────────────────────────────────────────────
def registrar_csm(inbound: dict[str, Any], texto_cliente: str, respuesta: str, tipo_cliente: str) -> bool:
    try:
        csm.insert_log({
            "mensaje_cliente": texto_cliente,
            "respuesta_agente": respuesta,
            "canal": "whatsapp",
            "tipo_cliente": tipo_cliente or "minorista",
            "agente": "principal",
            "wa_id": inbound.get("usuario"),
            "cliente_nombre": inbound.get("nombre"),
        })
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("registrar_csm falló: %s", e)
        return False
