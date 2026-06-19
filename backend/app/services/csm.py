"""
Service de Análisis de CSM: registro y evaluación de las respuestas del agente.

Loop de mejora:
  1. n8n / el agente registra cada interacción  -> insert_log
  2. Un admin la puntúa y/o corrige             -> review
  3. Métricas y export del dataset Q/A          -> stats / export

La tabla `csm_analisis` está protegida con RLS — se accede solo con service_role.
"""
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from . import credentials as creds_service

logger = logging.getLogger(__name__)

TABLE = "csm_analisis"
RATINGS = ("good", "mejorable", "bad")


def _sb():
    sb = creds_service._admin()
    if sb is None:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY no configurada — Análisis de CSM deshabilitado")
    return sb


def insert_log(data: dict) -> dict | None:
    """Registra una interacción del agente como pendiente de revisión."""
    payload = {
        "mensaje_cliente":  data["mensaje_cliente"],
        "respuesta_agente": data.get("respuesta_agente"),
        "canal":            data.get("canal"),
        "tipo_cliente":     data.get("tipo_cliente"),
        "agente":           data.get("agente"),
        "wa_id":            data.get("wa_id"),
        "cliente_nombre":   data.get("cliente_nombre"),
        "status":           "pending",
    }
    res = _sb().table(TABLE).insert(payload).execute()
    return res.data[0] if res.data else None


def list_items(
    status: str | None = None,
    rating: str | None = None,
    canal: str | None = None,
    tipo_cliente: str | None = None,
    agente: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    q = _sb().table(TABLE).select("*")
    if status:        q = q.eq("status", status)
    if rating:        q = q.eq("rating", rating)
    if canal:         q = q.eq("canal", canal)
    if tipo_cliente:  q = q.eq("tipo_cliente", tipo_cliente)
    if agente:        q = q.eq("agente", agente)
    res = q.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return res.data or []


def review(item_id: int, fields: dict, reviewer_email: str) -> dict | None:
    """El admin/asesor puntúa y/o corrige una interacción."""
    sb = _sb()
    existing = sb.table(TABLE).select("id").eq("id", item_id).maybe_single().execute()
    if not (existing and existing.data):
        return None

    update: dict[str, Any] = {}
    if fields.get("rating") is not None:
        if fields["rating"] not in RATINGS:
            raise ValueError("rating debe ser 'good', 'mejorable' o 'bad'")
        update["rating"] = fields["rating"]
    if fields.get("respuesta_corregida") is not None:
        update["respuesta_corregida"] = fields["respuesta_corregida"]
    if fields.get("tags") is not None:
        update["tags"] = fields["tags"]
    if fields.get("tipo_cliente") is not None:
        update["tipo_cliente"] = fields["tipo_cliente"]
    if fields.get("nota") is not None:
        update["nota"] = fields["nota"]
    update["status"] = "reviewed"
    update["reviewed_by"] = reviewer_email
    update["reviewed_at"] = datetime.now(timezone.utc).isoformat()

    res = sb.table(TABLE).update(update).eq("id", item_id).execute()
    return res.data[0] if res.data else None


def stats() -> dict:
    rows = _sb().table(TABLE).select("*").execute().data or []
    total = len(rows)
    pendientes = sum(1 for r in rows if r.get("status") == "pending")
    revisadas  = sum(1 for r in rows if r.get("status") == "reviewed")
    good       = sum(1 for r in rows if r.get("rating") == "good")
    mejorable  = sum(1 for r in rows if r.get("rating") == "mejorable")
    bad        = sum(1 for r in rows if r.get("rating") == "bad")
    calificadas = good + mejorable + bad
    tasa = round(good / calificadas, 3) if calificadas else 0.0

    # Top etiquetas de los casos malos/mejorables
    tag_counter: Counter = Counter()
    for r in rows:
        if r.get("rating") in ("bad", "mejorable") and isinstance(r.get("tags"), list):
            tag_counter.update(r["tags"])
    top_tags = [{"tag": t, "count": c} for t, c in tag_counter.most_common(10)]

    # Desglose por tipo de cliente
    by: dict[str, dict] = {}
    for r in rows:
        if r.get("rating") not in RATINGS:
            continue
        key = r.get("tipo_cliente") or "sin_clasificar"
        s = by.setdefault(key, {"good": 0, "mejorable": 0, "bad": 0})
        s[r["rating"]] += 1
    por_tipo = []
    for k, s in sorted(by.items()):
        tot = s["good"] + s["mejorable"] + s["bad"]
        por_tipo.append({
            "tipo_cliente": k,
            "total": tot,
            "good": s["good"],
            "mejorable": s["mejorable"],
            "bad": s["bad"],
            "tasa": round(s["good"] / tot, 3) if tot else 0.0,
        })

    return {
        "total": total,
        "pendientes": pendientes,
        "revisadas": revisadas,
        "good": good,
        "mejorable": mejorable,
        "bad": bad,
        "tasa_aprobacion": tasa,
        "top_tags_malos": top_tags,
        "por_tipo": por_tipo,
    }


def export_dataset(only_good: bool = True) -> dict:
    """Dataset Q/A para reentrenar/ajustar el prompt offline."""
    rows = _sb().table(TABLE).select("*").order("created_at", desc=False).execute().data or []
    dataset = []
    for r in rows:
        respuesta = r.get("respuesta_corregida") or (
            r.get("respuesta_agente") if r.get("rating") == "good" else None
        )
        if only_good and not respuesta:
            continue
        dataset.append({
            "mensaje_cliente": r.get("mensaje_cliente"),
            "respuesta": respuesta or r.get("respuesta_agente"),
            "canal": r.get("canal"),
            "tipo_cliente": r.get("tipo_cliente"),
            "agente": r.get("agente"),
            "rating": r.get("rating"),
            "fue_corregida": bool(r.get("respuesta_corregida")),
        })
    return {"count": len(dataset), "dataset": dataset}
