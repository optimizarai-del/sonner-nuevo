"""Vigilancia periódica del agente.

Mira lo que los healthchecks no ven: una corrida que arrancó y nunca cerró, o una tasa
de derivación a humano que se disparó. Las dos cosas son silenciosas —el servicio
responde 200, las métricas suben— y son exactamente las que dejan a un cliente esperando.

Se apoya en que `agent_runs` guarda la fila al ARRANCAR: `cerrado_en is null` con
`creado_en` viejo es, por definición, una corrida que murió a mitad de camino.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from ..obs import alertas

log = logging.getLogger("jobs.watchdog")

# Una corrida normal tarda segundos; con debounce, la ventana + unos segundos más.
SEGUNDOS_TRABADA = 180
# Por debajo de esta cantidad de corridas el porcentaje no dice nada.
MINIMO_PARA_EVALUAR_TASA = 10
UMBRAL_HANDOFF = 0.30


def _sb():
    from ..services import credentials as creds_service

    return creds_service._admin()


def corridas_trabadas() -> int:
    """Corridas abiertas hace demasiado. Devuelve cuántas encontró."""
    sb = _sb()
    if sb is None:
        return 0
    corte = (datetime.now(timezone.utc) - timedelta(seconds=SEGUNDOS_TRABADA)).isoformat()
    try:
        res = (sb.table("agent_runs")
               .select("run_id, canal, chat_id, creado_en")
               .is_("cerrado_en", "null").lt("creado_en", corte)
               .order("creado_en", desc=False).limit(20).execute())
        filas = res.data or []
    except Exception as e:  # noqa: BLE001
        log.warning("no se pudo revisar corridas trabadas: %s", e)
        return 0

    if filas:
        detalle = "\n".join(
            f"· {f.get('canal')} {f.get('chat_id')} — {f.get('creado_en')}" for f in filas[:10])
        alertas.notificar(
            f"{len(filas)} corrida(s) sin cerrar",
            f"Arrancaron hace más de {SEGUNDOS_TRABADA}s y nunca terminaron. "
            f"Alguien puede estar esperando una respuesta que no va a llegar.\n\n{detalle}",
            clave="watchdog:trabadas",
        )
    return len(filas)


def tasa_de_handoff(horas: int = 1) -> float | None:
    """Proporción de corridas que terminaron derivando a un humano en la última hora."""
    sb = _sb()
    if sb is None:
        return None
    desde = (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat()
    try:
        res = (sb.table("agent_runs").select("degradado")
               .gte("creado_en", desde).not_.is_("cerrado_en", "null")
               .limit(1000).execute())
        filas = res.data or []
    except Exception as e:  # noqa: BLE001
        log.warning("no se pudo calcular la tasa de handoff: %s", e)
        return None

    if len(filas) < MINIMO_PARA_EVALUAR_TASA:
        return None
    tasa = sum(1 for f in filas if f.get("degradado")) / len(filas)
    if tasa >= UMBRAL_HANDOFF:
        alertas.notificar(
            f"tasa de derivación alta: {tasa:.0%}",
            f"{sum(1 for f in filas if f.get('degradado'))} de {len(filas)} conversaciones "
            f"de la última hora terminaron derivando a un humano. Suele significar que el "
            f"LLM o alguna herramienta están fallando.",
            clave="watchdog:handoff",
        )
    return tasa


def revisar() -> dict[str, object]:
    """Una pasada completa. Nunca lanza: es un job de fondo."""
    salida: dict[str, object] = {}
    for nombre, fn in (("trabadas", corridas_trabadas), ("tasa_handoff", tasa_de_handoff)):
        try:
            salida[nombre] = fn()
        except Exception as e:  # noqa: BLE001
            log.exception("watchdog %s falló: %s", nombre, e)
            salida[nombre] = None
    return salida
