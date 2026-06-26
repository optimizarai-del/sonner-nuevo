"""
Tools de analítica para el Analista IA.
Cada función consulta Supabase y devuelve datos agregados — solo lectura.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from .supabase_client import get_supabase
from . import credentials as creds_service
from . import csm as csm_service

logger = logging.getLogger(__name__)


def _admin():
    """Cliente service_role: necesario para tablas con RLS (csm_analisis, users, etc.).
    Cae al cliente anon si no hay service_role configurada."""
    sb = creds_service._admin()
    return sb or get_supabase()


# Tablas que el analista NUNCA puede leer (secretos) y columnas a ocultar.
TABLAS_BLOQUEADAS = {"credentials"}
COLUMNAS_OCULTAS = {"password", "password_hash", "hashed_password", "clave", "api_key", "token"}


def _redactar(rows: list[dict]) -> list[dict]:
    """Elimina columnas sensibles (passwords, keys) de los resultados."""
    out = []
    for r in rows:
        if isinstance(r, dict):
            out.append({k: v for k, v in r.items() if k.lower() not in COLUMNAS_OCULTAS})
        else:
            out.append(r)
    return out


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


# ── Acceso genérico a TODAS las tablas de Supabase ────────────────────────────

def listar_tablas() -> dict[str, Any]:
    """Lista todas las tablas del esquema public con su cantidad estimada de filas.

    Usa la función analista_list_tables(). Excluye las tablas bloqueadas (secretos).
    """
    sb = _admin()
    try:
        res = sb.rpc("analista_list_tables", {}).execute()
        rows = res.data or []
    except Exception as e:
        logger.warning("listar_tablas (rpc) falló: %s", e)
        return {"error": "no se pudo introspeccionar el esquema", "detalle": str(e)}
    tablas = [r for r in rows if r.get("tabla") not in TABLAS_BLOQUEADAS]
    return {"tablas": tablas, "total": len(tablas)}


def consultar_tabla(
    tabla: str,
    columnas: str = "*",
    limit: int = 20,
    order_by: str | None = None,
    descendente: bool = True,
    filtro_columna: str | None = None,
    filtro_valor: str | None = None,
) -> Any:
    """Lee filas de CUALQUIER tabla del esquema public (solo lectura).

    - tabla: nombre exacto (usá listar_tablas para descubrirlas).
    - columnas: "*" o lista separada por comas (ej "id, mensaje_cliente, rating").
    - filtro_columna/filtro_valor: igualdad opcional (ej "rating" = "bad").
    Oculta columnas sensibles (passwords, keys) y bloquea tablas de secretos.
    """
    if tabla in TABLAS_BLOQUEADAS:
        return {"error": f"La tabla '{tabla}' no está disponible para consulta."}
    limit = max(1, min(int(limit or 20), 200))
    sb = _admin()
    try:
        q = sb.table(tabla).select(columnas or "*")
        if filtro_columna and filtro_valor is not None:
            q = q.eq(filtro_columna, filtro_valor)
        if order_by:
            q = q.order(order_by, desc=bool(descendente))
        res = q.limit(limit).execute()
        return {"tabla": tabla, "filas": _redactar(res.data or [])}
    except Exception as e:
        logger.warning("consultar_tabla(%s) falló: %s", tabla, e)
        return {"error": f"no se pudo leer '{tabla}'", "detalle": str(e)}


def contar_tabla(
    tabla: str,
    filtro_columna: str | None = None,
    filtro_valor: str | None = None,
) -> dict[str, Any]:
    """Cuenta filas de cualquier tabla, con filtro de igualdad opcional."""
    if tabla in TABLAS_BLOQUEADAS:
        return {"error": f"La tabla '{tabla}' no está disponible."}
    sb = _admin()
    try:
        q = sb.table(tabla).select("*", count="exact")
        if filtro_columna and filtro_valor is not None:
            q = q.eq(filtro_columna, filtro_valor)
        res = q.limit(1).execute()
        return {"tabla": tabla, "total": res.count or 0}
    except Exception as e:
        logger.warning("contar_tabla(%s) falló: %s", tabla, e)
        return {"error": f"no se pudo contar '{tabla}'", "detalle": str(e)}


# ── Análisis de CSM (feedback de Gabi sobre las respuestas del agente) ─────────

def stats_csm() -> dict[str, Any]:
    """Métricas del feedback de CSM: total, pendientes, revisadas, good/mejorable/bad,
    tasa de aprobación, top etiquetas de los casos malos y desglose por tipo de cliente."""
    try:
        return csm_service.stats()
    except Exception as e:
        logger.warning("stats_csm falló: %s", e)
        return {"error": str(e)}


def listar_csm(rating: str | None = None, status: str | None = None,
               agente: str | None = None, limit: int = 20) -> Any:
    """Lista interacciones evaluadas en CSM. Filtros opcionales: rating
    (good|mejorable|bad), status (pending|reviewed), agente (principal|calendario|salones)."""
    try:
        items = csm_service.list_items(status=status, rating=rating, agente=agente, limit=min(limit, 100))
        # Recortamos a lo relevante para el análisis (sin inflar el contexto)
        return [{
            "mensaje_cliente": r.get("mensaje_cliente"),
            "respuesta_agente": r.get("respuesta_agente"),
            "respuesta_corregida": r.get("respuesta_corregida"),
            "rating": r.get("rating"),
            "tags": r.get("tags"),
            "tipo_cliente": r.get("tipo_cliente"),
            "agente": r.get("agente"),
            "nota": r.get("nota"),
            "created_at": r.get("created_at"),
        } for r in items]
    except Exception as e:
        logger.warning("listar_csm falló: %s", e)
        return {"error": str(e)}


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
    {
        "name": "listar_tablas",
        "description": "Descubrir TODAS las tablas disponibles en la base de datos (Supabase) con su cantidad estimada de filas. Usala primero cuando te pregunten por datos que no cubren las otras herramientas, para saber qué tabla consultar.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "consultar_tabla",
        "description": "Leer filas de CUALQUIER tabla de la base (solo lectura). Sirve para datos que no tienen una herramienta dedicada. Primero usá listar_tablas para conocer los nombres. Podés elegir columnas, ordenar y filtrar por igualdad.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tabla": {"type": "string", "description": "Nombre exacto de la tabla."},
                "columnas": {"type": "string", "description": "'*' o columnas separadas por coma.", "default": "*"},
                "limit": {"type": "integer", "default": 20},
                "order_by": {"type": "string", "description": "Columna para ordenar (opcional)."},
                "descendente": {"type": "boolean", "default": True},
                "filtro_columna": {"type": "string", "description": "Columna para filtrar por igualdad (opcional)."},
                "filtro_valor": {"type": "string", "description": "Valor del filtro (opcional)."},
            },
            "required": ["tabla"],
        },
    },
    {
        "name": "contar_tabla",
        "description": "Contar filas de cualquier tabla, con filtro de igualdad opcional.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tabla": {"type": "string"},
                "filtro_columna": {"type": "string"},
                "filtro_valor": {"type": "string"},
            },
            "required": ["tabla"],
        },
    },
    {
        "name": "stats_csm",
        "description": "Análisis de CSM: feedback que deja Gabi sobre las respuestas del agente. Devuelve total, pendientes, revisadas, cuántas good/mejorable/bad, tasa de aprobación, etiquetas más comunes de los casos malos y desglose por tipo de cliente. Usala cuando pregunten por la calidad del agente, el feedback o las correcciones.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "listar_csm",
        "description": "Lista las interacciones evaluadas en CSM (mensaje del cliente, respuesta del agente, corrección, rating, tags, nota). Filtros opcionales: rating (good|mejorable|bad), status (pending|reviewed), agente. Usala para revisar casos concretos del feedback.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rating": {"type": "string", "enum": ["good", "mejorable", "bad"]},
                "status": {"type": "string", "enum": ["pending", "reviewed"]},
                "agente": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
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
    "listar_tablas":           listar_tablas,
    "consultar_tabla":         consultar_tabla,
    "contar_tabla":            contar_tabla,
    "stats_csm":               stats_csm,
    "listar_csm":              listar_csm,
}
