"""Tests de los jobs de fondo. Sin red: Supabase está dobleteado.

Reemplazan a los crons y al error handler de n8n. Lo que se verifica acá es que un job
que falla no tumbe nada y que la coordinación entre workers no mande el mismo resumen
varias veces.
"""
from __future__ import annotations

from collections import Counter

import pytest

from app.jobs import digest, scheduler, watchdog


# ── Resumen diario ───────────────────────────────────────────────────────────
DATOS = {
    "total": 120, "atendidas": 100, "handoffs": 7, "fallidas": 2,
    "cortadas": Counter({"debounce": 15, "kill_switch": 5}),
    "por_canal": Counter({"whatsapp": 80, "telegram": 20}),
    "latencia_p50_s": 3.2, "latencia_p95_s": 11.0, "costo_usd": 1.4231,
}


def test_el_resumen_dice_lo_que_importa():
    texto = digest.formatear(DATOS, errores=[])
    assert "Atendidas: 100" in texto
    assert "whatsapp: 80" in texto
    assert "Derivadas a un humano: 7" in texto
    assert "p95 11.0s" in texto
    assert "US$ 1.4231" in texto
    assert "debounce 15" in texto
    assert "Con error: 2" in texto


def test_el_resumen_lista_los_errores_abiertos():
    texto = digest.formatear(DATOS, errores=[
        {"nodo": "agente", "tipo": "RuntimeError", "cantidad": 12, "firma": "abc"},
    ])
    assert "Errores abiertos:" in texto
    assert "[agente] RuntimeError ×12" in texto


def test_un_dia_limpio_no_menciona_errores():
    limpios = {**DATOS, "fallidas": 0, "cortadas": Counter()}
    texto = digest.formatear(limpios, errores=[])
    assert "Con error" not in texto
    assert "Errores abiertos" not in texto


@pytest.mark.parametrize("valores,p,esperado", [
    ([], 0.5, 0),
    ([100], 0.95, 100),
    ([1000, 2000, 3000, 4000], 0.5, 3000),
    ([1000, 2000, 3000, 4000], 0.95, 4000),
])
def test_percentiles(valores, p, esperado):
    assert digest._percentil(valores, p) == esperado


def test_sin_supabase_el_resumen_no_se_manda():
    """En el entorno de test no hay service_role: tiene que devolver False, no romper."""
    assert digest.enviar() is False


# ── Watchdog ─────────────────────────────────────────────────────────────────
def test_el_watchdog_nunca_lanza():
    """Es un job de fondo: si explota, se lleva puesto el scheduler entero."""
    salida = watchdog.revisar()
    assert set(salida) == {"trabadas", "tasa_handoff"}


def test_un_job_roto_no_tumba_la_pasada(monkeypatch):
    def _explotar():
        raise RuntimeError("Supabase caído")

    monkeypatch.setattr(watchdog, "corridas_trabadas", _explotar)
    salida = watchdog.revisar()
    assert salida["trabadas"] is None
    assert "tasa_handoff" in salida


def test_umbrales_del_watchdog():
    """Una tasa alta sobre 3 conversaciones no significa nada."""
    assert watchdog.MINIMO_PARA_EVALUAR_TASA >= 10
    assert 0 < watchdog.UMBRAL_HANDOFF < 1
    assert watchdog.SEGUNDOS_TRABADA > 60  # tiene que superar la ventana de debounce


# ── Coordinación entre workers ───────────────────────────────────────────────
def test_sin_redis_le_toca_a_este_worker():
    """Sin Redis hay un solo worker por definición: no hay nada que coordinar."""
    assert scheduler._me_toca("digest:202609171200", ttl=60) is True


def test_con_redis_solo_gana_uno(monkeypatch):
    class RedisFalso:
        def __init__(self):
            self.claves = set()

        def set(self, clave, _valor, nx=False, ex=None):
            if nx and clave in self.claves:
                return None
            self.claves.add(clave)
            return True

    falso = RedisFalso()
    monkeypatch.setattr("app.agents.nodes._redis.cliente", lambda: falso)

    ganadores = [scheduler._me_toca("digest:202609171200", ttl=60) for _ in range(4)]
    assert ganadores == [True, False, False, False]


def test_si_redis_falla_el_job_corre_igual(monkeypatch):
    """Mejor un resumen duplicado que ninguno."""
    class RedisRoto:
        def set(self, *_a, **_k):
            raise RuntimeError("timeout")

    monkeypatch.setattr("app.agents.nodes._redis.cliente", lambda: RedisRoto())
    assert scheduler._me_toca("watchdog:x", ttl=60) is True


def test_correr_atrapa_la_excepcion_del_job():
    scheduler._correr("prueba", lambda: 1 / 0, ttl=1)  # no debe propagarse
