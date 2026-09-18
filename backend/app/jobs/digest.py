"""Resumen diario del agente por Telegram.

No es una alerta: es el mensaje que hace que alguien mire los números aunque no se haya
roto nada. Mensajes atendidos, cuántos terminaron con un humano, cuánto costó y qué
errores nuevos aparecieron.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

from ..obs import alertas

log = logging.getLogger("jobs.digest")

_TZ_AR = timezone(timedelta(hours=-3))


def _sb():
    from ..services import credentials as creds_service

    return creds_service._admin()


def _percentil(valores: list[int], p: float) -> int:
    if not valores:
        return 0
    ordenados = sorted(valores)
    return ordenados[min(int(len(ordenados) * p), len(ordenados) - 1)]


def resumen(horas: int = 24) -> dict[str, object]:
    sb = _sb()
    if sb is None:
        return {}
    desde = (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat()
    try:
        res = (sb.table("agent_runs")
               .select("canal, audiencia, ok, degradado, motivo_corte, latencia_ms, costo_usd")
               .gte("creado_en", desde).limit(5000).execute())
        filas = res.data or []
    except Exception as e:  # noqa: BLE001
        log.warning("no se pudo armar el resumen: %s", e)
        return {}

    atendidas = [f for f in filas if not f.get("motivo_corte")]
    latencias = [int(f["latencia_ms"]) for f in atendidas if f.get("latencia_ms")]
    return {
        "total": len(filas),
        "atendidas": len(atendidas),
        "cortadas": Counter(f["motivo_corte"] for f in filas if f.get("motivo_corte")),
        "handoffs": sum(1 for f in atendidas if f.get("degradado")),
        "fallidas": sum(1 for f in filas if f.get("ok") is False),
        "por_canal": Counter(f.get("canal") or "?" for f in atendidas),
        "latencia_p50_s": round(_percentil(latencias, 0.50) / 1000, 1),
        "latencia_p95_s": round(_percentil(latencias, 0.95) / 1000, 1),
        "costo_usd": round(sum(float(f.get("costo_usd") or 0) for f in filas), 4),
    }


def errores_nuevos(horas: int = 24) -> list[dict]:
    sb = _sb()
    if sb is None:
        return []
    desde = (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat()
    try:
        res = (sb.table("agent_errors").select("firma, tipo, mensaje, nodo, cantidad")
               .eq("resuelto", False).gte("last_seen", desde)
               .order("cantidad", desc=True).limit(5).execute())
        return res.data or []
    except Exception as e:  # noqa: BLE001
        log.warning("no se pudieron leer los errores: %s", e)
        return []


def formatear(datos: dict[str, object], errores: list[dict]) -> str:
    canales = ", ".join(f"{c}: {n}" for c, n in datos["por_canal"].most_common()) or "—"
    lineas = [
        f"Atendidas: {datos['atendidas']} ({canales})",
        f"Derivadas a un humano: {datos['handoffs']}",
        f"Latencia: p50 {datos['latencia_p50_s']}s · p95 {datos['latencia_p95_s']}s",
        f"Costo estimado: US$ {datos['costo_usd']}",
    ]
    if datos["cortadas"]:
        lineas.append("Cortadas: " + ", ".join(
            f"{m} {n}" for m, n in datos["cortadas"].most_common()))
    if datos["fallidas"]:
        lineas.append(f"⚠️ Con error: {datos['fallidas']}")
    if errores:
        lineas.append("\nErrores abiertos:")
        lineas += [f"· [{e['nodo']}] {e['tipo']} ×{e['cantidad']}" for e in errores]
    return "\n".join(lineas)


def enviar() -> bool:
    """Arma y manda el resumen. Se llama una vez por día desde el scheduler."""
    datos = resumen()
    if not datos:
        log.info("sin datos para el resumen diario")
        return False
    hoy = datetime.now(_TZ_AR)
    # clave con la fecha: el rate-limit por firma no puede tapar el resumen de mañana.
    return alertas.notificar(f"resumen del {hoy:%d/%m}",
                             formatear(datos, errores_nuevos()),
                             clave=f"digest:{hoy:%Y-%m-%d}")
