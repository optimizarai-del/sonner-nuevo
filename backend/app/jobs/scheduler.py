"""Scheduler de los jobs de fondo. Reemplaza los crons que vivían en n8n.

Corre dentro del proceso del agente, con un detalle que importa: si hay varios workers,
todos despiertan a la misma hora. Sin coordinación, el resumen diario llegaría N veces.
`_me_toca()` resuelve un `SET NX` en Redis por tick: gana uno y los demás se saltean.

Sin Redis hay un solo worker por definición (lo dice el arranque), así que no hay nada
que coordinar y el guard deja pasar.

No usa hilos propios: APScheduler ya maneja su pool y se apaga con la app.
"""
from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from . import digest, watchdog

log = logging.getLogger("jobs.scheduler")

_scheduler: BackgroundScheduler | None = None
# Zona horaria de Argentina, para que "20:00" sea las 20 de acá y no UTC.
_TZ = "America/Argentina/Buenos_Aires"


def _me_toca(clave: str, ttl: int) -> bool:
    """True si a este worker le toca correr el job en este tick."""
    from ..agents.nodes import _redis

    r = _redis.cliente()
    if r is None:
        return True
    try:
        return bool(r.set(f"sonner:job:{clave}", "1", nx=True, ex=ttl))
    except Exception as e:  # noqa: BLE001
        log.warning("no se pudo coordinar el job %s (%s) — corro igual", clave, e)
        return True


def _correr(nombre: str, fn, ttl: int) -> None:
    marca = datetime.now().strftime("%Y%m%d%H%M")
    if not _me_toca(f"{nombre}:{marca}", ttl):
        return
    try:
        resultado = fn()
        log.info("job %s ok", nombre, extra={"job": nombre, "resultado": str(resultado)[:200]})
    except Exception as e:  # noqa: BLE001
        log.exception("job %s falló: %s", nombre, e)


def iniciar() -> BackgroundScheduler | None:
    """Arranca los jobs. Idempotente: llamarlo dos veces no duplica nada."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    sched = BackgroundScheduler(timezone=_TZ)
    sched.add_job(
        lambda: _correr("watchdog", watchdog.revisar, ttl=240),
        IntervalTrigger(minutes=5), id="watchdog", replace_existing=True,
    )
    sched.add_job(
        lambda: _correr("digest", digest.enviar, ttl=3600),
        CronTrigger(hour=20, minute=0), id="digest", replace_existing=True,
    )
    sched.start()
    _scheduler = sched
    log.info("scheduler arrancado: watchdog cada 5 min, resumen diario 20:00 AR")
    return sched


def detener() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
