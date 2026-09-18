"""Tests offline de la capa de observabilidad: healthchecks, métricas y alertas."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.agente_main import app
from app.obs import alertas, runs


@pytest.fixture(scope="module")
def cliente() -> TestClient:
    return TestClient(app)


# ── Healthchecks ─────────────────────────────────────────────────────────────
def test_health_responde_sin_tocar_dependencias(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_da_503_si_falta_una_dependencia_critica(cliente):
    """Sin SUPABASE_SERVICE_ROLE_KEY (el entorno de test) no está listo para atender."""
    r = cliente.get("/health/ready")
    assert r.status_code == 503
    assert r.json()["chequeos"]["supabase"]["estado"] == "error"


def test_deps_separa_criticas_de_degradables(cliente):
    cuerpo = cliente.get("/health/deps").json()
    assert set(cuerpo["criticas"]) == {"supabase", "llm"}
    assert set(cuerpo["degradables"]) == {"redis", "google"}
    # Redis sin configurar no es un error: el debounce cae a memoria.
    assert cuerpo["degradables"]["redis"]["estado"] == "ok"


# ── Métricas ─────────────────────────────────────────────────────────────────
def test_metrics_expone_las_series_del_agente(cliente):
    r = cliente.get("/metrics")
    assert r.status_code == 200
    for serie in ("sonner_mensajes_total", "sonner_respuestas_total",
                  "sonner_latencia_segundos", "sonner_handoffs_total"):
        assert serie in r.text


# ── Firma de errores ─────────────────────────────────────────────────────────
def test_misma_falla_misma_firma_aunque_cambien_los_ids():
    a = alertas.firmar("RuntimeError", "timeout al consultar chat 5492954111111", "agente")
    b = alertas.firmar("RuntimeError", "timeout al consultar chat 5492954999999", "agente")
    assert a == b


def test_fallas_distintas_firmas_distintas():
    a = alertas.firmar("RuntimeError", "timeout", "agente")
    b = alertas.firmar("ValueError", "timeout", "agente")
    c = alertas.firmar("RuntimeError", "timeout", "salida")
    assert len({a, b, c}) == 3


# ── Redacción ────────────────────────────────────────────────────────────────
def test_no_se_persisten_secretos_en_los_pasos():
    limpio = runs.redactar({
        "consulta": "verificar salon Royal",
        "api_key": "sk-abc123",
        "anidado": {"Authorization": "Bearer xyz", "ok": 1},
    })
    assert limpio["consulta"] == "verificar salon Royal"
    assert limpio["api_key"] == "«redactado»"
    assert limpio["anidado"]["Authorization"] == "«redactado»"
    assert limpio["anidado"]["ok"] == 1


def test_una_corrida_sin_supabase_no_rompe():
    """La observabilidad nunca puede ser el motivo de que no haya respuesta."""
    run = runs.iniciar(canal="whatsapp", audiencia="externo", chat_id="+549", entrada="hola")
    with runs.activa(run):
        with runs.paso("gate"):
            pass
    run.cerrar(respuesta="ok", comando="nada")
    assert run.cerrado is True
    assert len(run.pasos) == 1
