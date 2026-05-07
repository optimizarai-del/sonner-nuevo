"""
Tools de analítica para el Analista IA.
Cada función consulta Supabase y devuelve datos agregados — solo lectura.
"""
from datetime import datetime, timedelta, timezone
from typing import Any
from .supabase_client import get_supabase


def _iso_dias(dias: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()


def _iso_inicio_mes() -> str:
    n = datetime.now(timezone.utc)
    return n.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()


# ── Tools del agente ──────────────────────────────────────────────────────────

def stats_contratos(periodo: str = "total") -> dict[str, Any]:
    """
    Estadísticas de contratos generados.
    periodo: "total" | "mes" | "semana" | "hoy"
    """
    sb = get_supabase()
    now = datetime.now(timezone.utc)

    q_total = sb.table("contratos").select("id", count="exact").execute()
    q_mes   = sb.table("contratos").select("id", count="exact").gte("created_at", _iso_inicio_mes()).execute()
    q_sem   = sb.table("contratos").select("id", count="exact").gte("created_at", _iso_dias(7)).execute()
    q_hoy   = sb.table("contratos").select("id", count="exact").gte("created_at", now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()).execute()

    # Suma del valor de los contratos del mes
    montos = sb.table("contratos").select("monto_total_pesos").gte("created_at", _iso_inicio_mes()).execute()
    valor_mes = sum((r.get("monto_total_pesos") or 0) for r in (montos.data or []))

    return {
        "total":       q_total.count or 0,
        "este_mes":    q_mes.count or 0,
        "esta_semana": q_sem.count or 0,
        "hoy":         q_hoy.count or 0,
        "facturado_mes_pesos": valor_mes,
    }


def listar_contratos(limit: int = 5) -> list[dict]:
    """Últimos N contratos con datos clave."""
    sb = get_supabase()
    res = sb.table("contratos").select(
        "nombre_prestatario, lugar_evento, dia_evento, monto_total_pesos, created_at"
    ).order("created_at", desc=True).limit(limit).execute()
    return res.data or []


def stats_whatsapp(dias: int = 30) -> dict[str, Any]:
    """Stats del agente WhatsApp en los últimos N días."""
    sb = get_supabase()
    desde = _iso_dias(dias)

    q_in   = sb.table("whatsapp_messages").select("id", count="exact").eq("direction", "in").gte("created_at", desde).execute()
    q_out  = sb.table("whatsapp_messages").select("id", count="exact").eq("direction", "out").gte("created_at", desde).execute()
    q_hoy  = sb.table("whatsapp_messages").select("id", count="exact").gte("created_at", datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()).execute()

    contactos = sb.table("whatsapp_messages").select("contacto").gte("created_at", desde).execute()
    unicos = len({r["contacto"] for r in (contactos.data or []) if r.get("contacto")})

    return {
        "recibidos":           q_in.count or 0,
        "enviados":            q_out.count or 0,
        "total":               (q_in.count or 0) + (q_out.count or 0),
        "intercambios_hoy":    q_hoy.count or 0,
        "contactos_unicos":    unicos,
        "tasa_respuesta_pct":  round((q_out.count or 0) / (q_in.count or 1) * 100, 1) if q_in.count else 0,
    }


def top_contactos_whatsapp(dias: int = 30, limit: int = 5) -> list[dict]:
    """Contactos con más mensajes intercambiados."""
    sb = get_supabase()
    res = sb.table("whatsapp_messages").select("contacto, contacto_nombre").gte("created_at", _iso_dias(dias)).execute()
    counts: dict[str, dict] = {}
    for r in (res.data or []):
        k = r.get("contacto")
        if not k:
            continue
        if k not in counts:
            counts[k] = {"contacto": k, "nombre": r.get("contacto_nombre"), "total": 0}
        counts[k]["total"] += 1
        if r.get("contacto_nombre"):
            counts[k]["nombre"] = r["contacto_nombre"]
    return sorted(counts.values(), key=lambda x: x["total"], reverse=True)[:limit]


def stats_blocklist() -> dict[str, int]:
    """Total de contactos bloqueados."""
    sb = get_supabase()
    res = sb.table("blocklist").select("id", count="exact").execute()
    return {"total_bloqueados": res.count or 0}


def stats_crm() -> dict[str, Any]:
    """Distribución de leads por etapa + valor del pipeline activo."""
    sb = get_supabase()
    res = sb.table("crm_leads").select("etapa, valor_total").execute()
    leads = res.data or []

    por_etapa: dict[str, int] = {}
    pipeline_activo = 0
    etapas_activas = {"NUEVO_CLIENTE", "FECHA_CONFIRMADA", "CONTRATO_FIRMADO", "EN_PREPARACION"}

    for l in leads:
        etapa = l.get("etapa", "—")
        por_etapa[etapa] = por_etapa.get(etapa, 0) + 1
        if etapa in etapas_activas:
            pipeline_activo += l.get("valor_total") or 0

    return {
        "total_leads":         len(leads),
        "por_etapa":           por_etapa,
        "pipeline_activo_pesos": pipeline_activo,
    }


def stats_chat_externo(dias: int = 30) -> dict[str, Any]:
    """Mensajes y conversaciones del agente WhatsApp (memoria)."""
    sb = get_supabase()
    total = sb.table("external_chat_histories").select("id", count="exact").execute()
    sesiones = sb.table("external_chat_histories").select("session_id").execute()
    unicos = len({r.get("session_id") for r in (sesiones.data or []) if r.get("session_id")})
    return {
        "mensajes_totales":    total.count or 0,
        "conversaciones":       unicos,
    }


# ── Definición JSON de las tools para Anthropic ───────────────────────────────
TOOLS = [
    {
        "name": "stats_contratos",
        "description": "Obtener cantidad de contratos generados (total, este mes, esta semana, hoy) y dinero facturado este mes.",
        "input_schema": {
            "type": "object",
            "properties": {"periodo": {"type": "string", "enum": ["total", "mes", "semana", "hoy"], "default": "total"}},
        },
    },
    {
        "name": "listar_contratos",
        "description": "Listar los últimos contratos generados con prestatario, lugar, fecha y monto.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 5}},
        },
    },
    {
        "name": "stats_whatsapp",
        "description": "Estadísticas del agente WhatsApp: mensajes recibidos, enviados, intercambios hoy, contactos únicos, tasa de respuesta. Usa los últimos N días.",
        "input_schema": {
            "type": "object",
            "properties": {"dias": {"type": "integer", "default": 30}},
        },
    },
    {
        "name": "top_contactos_whatsapp",
        "description": "Contactos de WhatsApp con más mensajes intercambiados en los últimos N días.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dias":  {"type": "integer", "default": 30},
                "limit": {"type": "integer", "default": 5},
            },
        },
    },
    {
        "name": "stats_blocklist",
        "description": "Total de contactos bloqueados (lista negra del agente externo).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "stats_crm",
        "description": "Distribución de leads por etapa del CRM y valor total del pipeline activo (en pesos).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "stats_chat_externo",
        "description": "Cantidad de mensajes en la memoria del agente WhatsApp y conversaciones únicas.",
        "input_schema": {
            "type": "object",
            "properties": {"dias": {"type": "integer", "default": 30}},
        },
    },
]


# Mapa nombre → función para invocar desde el agente
TOOL_FNS = {
    "stats_contratos":         stats_contratos,
    "listar_contratos":        listar_contratos,
    "stats_whatsapp":          stats_whatsapp,
    "top_contactos_whatsapp":  top_contactos_whatsapp,
    "stats_blocklist":         stats_blocklist,
    "stats_crm":               stats_crm,
    "stats_chat_externo":      stats_chat_externo,
}
