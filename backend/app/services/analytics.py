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


# Tablas de historial de chat del agente (LangChain/n8n): columnas id, session_id, message(jsonb).
# El session_id es el teléfono del contacto; message.type ∈ {human, ai, tool}.
# OJO: estas tablas NO tienen timestamp, así que las stats son HISTÓRICAS (no por período).
CHAT_TABLE_PRINCIPAL = "n8n_chat_histories"       # agente principal (Tomi)
CHAT_TABLE_EXTERNO   = "external_chat_histories"  # agente externo


def _chat_rows(tabla: str) -> list[dict]:
    sb = _admin()
    return sb.table(tabla).select("session_id, message").execute().data or []


# Sesiones que NO son contactos reales (estados de WhatsApp, keep-alive, tests web).
_SESIONES_SISTEMA = {"+status", "status", "healthcheck", "test"}


def _es_contacto_real(session_id: str | None) -> bool:
    """True si la sesión parece un teléfono real (no un estado/keep-alive/test web)."""
    if not session_id:
        return False
    s = session_id.strip().lower()
    if s in _SESIONES_SISTEMA or s.startswith("web-") or s.startswith("test"):
        return False
    # teléfono: mayormente dígitos (con + opcional), al menos 8 cifras
    digitos = sum(c.isdigit() for c in s)
    return digitos >= 8


def _resumen_chat(rows: list[dict]) -> dict[str, Any]:
    recibidos = enviados = 0
    contactos: set = set()
    for r in rows:
        if not _es_contacto_real(r.get("session_id")):
            continue  # descartar estados de WhatsApp, keep-alive y tests
        msg = r.get("message") or {}
        tipo = msg.get("type")
        contactos.add(r["session_id"])
        if tipo == "human":
            recibidos += 1
        elif tipo == "ai" and "respuesta" in (msg.get("content") or ""):
            # solo contamos las respuestas reales al cliente (no los pasos de tool)
            enviados += 1
    return {
        "recibidos": recibidos,
        "enviados": enviados,
        "contactos_unicos": len(contactos),
        "conversaciones": len(contactos),
        "tasa_respuesta_pct": round(enviados / recibidos * 100, 1) if recibidos else 0,
        "nota": "Histórico total: la tabla de conversaciones no guarda fecha, no hay corte por período.",
    }


def stats_whatsapp(dias: int = 30) -> dict[str, Any]:
    """Stats históricas del agente WhatsApp principal (Tomi): mensajes recibidos,
    respuestas enviadas, contactos únicos y tasa de respuesta. El parámetro 'dias'
    se ignora: la tabla de conversaciones no guarda fecha."""
    try:
        return _resumen_chat(_chat_rows(CHAT_TABLE_PRINCIPAL))
    except Exception as e:
        logger.warning("stats_whatsapp falló: %s", e)
        return {"error": str(e)}


def top_contactos_whatsapp(dias: int = 30, limit: int = 5) -> list[dict]:
    """Contactos (teléfonos) con más mensajes intercambiados con el agente principal."""
    try:
        rows = _chat_rows(CHAT_TABLE_PRINCIPAL)
    except Exception as e:
        logger.warning("top_contactos_whatsapp falló: %s", e)
        return []
    counts: dict[str, int] = {}
    for r in rows:
        k = r.get("session_id")
        if _es_contacto_real(k):
            counts[k] = counts.get(k, 0) + 1
    ordenados = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [{"contacto": k, "total": n} for k, n in ordenados]


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
    """Mensajes y conversaciones del AGENTE EXTERNO (histórico total)."""
    try:
        rows = _chat_rows(CHAT_TABLE_EXTERNO)
    except Exception as e:
        logger.warning("stats_chat_externo falló: %s", e)
        return {"error": str(e)}
    r = _resumen_chat(rows)
    return {
        "mensajes_totales": len(rows),
        "conversaciones": r["conversaciones"],
        "recibidos": r["recibidos"],
        "enviados": r["enviados"],
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
        "description": "Estadísticas HISTÓRICAS del agente WhatsApp principal (Tomi): mensajes recibidos, respuestas enviadas, contactos únicos y tasa de respuesta. Es histórico total (la tabla de conversaciones no guarda fecha), así que no hay corte por período.",
        "input_schema": {
            "type": "object",
            "properties": {"dias": {"type": "integer", "default": 30}},
        },
    },
    {
        "name": "top_contactos_whatsapp",
        "description": "Contactos (teléfonos) con más mensajes intercambiados con el agente principal (histórico total).",
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
        "description": "Mensajes y conversaciones del AGENTE EXTERNO (histórico total): mensajes totales, conversaciones únicas, recibidos y enviados.",
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
