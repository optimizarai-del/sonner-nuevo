"""Persistencia de corridas del agente en `agent_runs` / `agent_steps`.

Una corrida = un mensaje procesado de punta a punta. La fila se inserta al ARRANCAR
(no al terminar) para que una corrida que muere a mitad de camino igual deje rastro:
`cerrado_en is null` con `creado_en` viejo = corrida trabada, que es justo lo que busca
el watchdog.

Todo es best-effort: si Supabase no responde, se loguea y la conversación sigue. La
observabilidad nunca puede ser el motivo por el que un cliente se queda sin respuesta.
"""
from __future__ import annotations

import contextvars
import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator

from . import logs, metrics

log = logging.getLogger("obs.runs")

_MAX_RESULTADO = 4000
_MAX_TEXTO = 8000
_CLAVES_SENSIBLES = ("key", "token", "secret", "password", "authorization", "api_key")


def _sb():
    from ..services import credentials as creds_service

    return creds_service._admin()


def _truncar(valor: Any, limite: int) -> str | None:
    if valor is None:
        return None
    texto = valor if isinstance(valor, str) else str(valor)
    return texto if len(texto) <= limite else texto[:limite] + "…[truncado]"


def redactar(args: Any) -> Any:
    """Quita valores de claves que huelen a secreto antes de persistir."""
    if isinstance(args, dict):
        return {
            k: ("«redactado»" if any(s in k.lower() for s in _CLAVES_SENSIBLES) else redactar(v))
            for k, v in args.items()
        }
    if isinstance(args, list):
        return [redactar(v) for v in args]
    if isinstance(args, str):
        return args[:1000]
    return args


@dataclass
class Paso:
    orden: int
    nodo: str
    tool: str | None = None
    args: Any = None
    resultado: str | None = None
    duracion_ms: int | None = None
    error: str | None = None


@dataclass
class Run:
    run_id: str
    canal: str
    audiencia: str
    chat_id: str
    t0: float = field(default_factory=time.monotonic)
    pasos: list[Paso] = field(default_factory=list)
    cerrado: bool = False

    # ── Pasos ────────────────────────────────────────────────────────────────
    @contextmanager
    def paso(self, nodo: str, tool: str | None = None, args: Any = None) -> Iterator[Paso]:
        p = Paso(orden=len(self.pasos) + 1, nodo=nodo, tool=tool, args=redactar(args))
        self.pasos.append(p)
        inicio = time.monotonic()
        try:
            yield p
        except Exception as e:  # noqa: BLE001
            p.error = f"{type(e).__name__}: {e}"
            raise
        finally:
            p.duracion_ms = int((time.monotonic() - inicio) * 1000)
            if p.tool:
                metrics.TOOL_LLAMADAS.labels(
                    tool=p.tool, resultado="error" if p.error else "ok"
                ).inc()

    def registrar_tool(self, tool: str, args: Any, resultado: Any, duracion_ms: int,
                       error: str | None = None) -> None:
        """Alta directa de un paso ya ejecutado (para el ToolNode de LangGraph)."""
        self.pasos.append(Paso(
            orden=len(self.pasos) + 1, nodo="tools", tool=tool, args=redactar(args),
            resultado=_truncar(resultado, _MAX_RESULTADO), duracion_ms=duracion_ms, error=error,
        ))
        metrics.TOOL_LLAMADAS.labels(tool=tool, resultado="error" if error else "ok").inc()

    # ── Cierre ───────────────────────────────────────────────────────────────
    def cortar(self, motivo: str) -> None:
        """La corrida terminó antes del agente (kill-switch, blocklist, debounce)."""
        metrics.CORTES.labels(motivo=motivo).inc()
        if motivo == "debounce":
            metrics.DEBOUNCE_DESCARTADOS.inc()
        self._cerrar(ok=True, motivo_corte=motivo, resultado="cortado")

    def cerrar(
        self,
        *,
        respuesta: str | None = None,
        comando: str | None = None,
        mensaje_comando: str | None = None,
        degradado: bool = False,
        ok: bool = True,
        meta: dict[str, Any] | None = None,
    ) -> None:
        resultado = "handoff" if degradado else ("ok" if ok else "error")
        if degradado:
            metrics.HANDOFFS.labels(motivo=(meta or {}).get("motivo_handoff", "desconocido")).inc()
        self._cerrar(
            ok=ok, respuesta=respuesta, comando=comando, mensaje_comando=mensaje_comando,
            degradado=degradado, meta=meta, resultado=resultado,
        )

    def _cerrar(self, *, ok: bool, resultado: str, motivo_corte: str | None = None,
                respuesta: str | None = None, comando: str | None = None,
                mensaje_comando: str | None = None, degradado: bool = False,
                meta: dict[str, Any] | None = None) -> None:
        if self.cerrado:
            return
        self.cerrado = True
        latencia_s = time.monotonic() - self.t0
        metrics.LATENCIA.labels(canal=self.canal).observe(latencia_s)
        metrics.RESPUESTAS.labels(canal=self.canal, resultado=resultado).inc()

        meta = meta or {}
        parche: dict[str, Any] = {
            "cerrado_en": datetime.now(timezone.utc).isoformat(),
            "latencia_ms": int(latencia_s * 1000),
            "ok": ok,
            "degradado": degradado,
            "motivo_corte": motivo_corte,
            "respuesta": _truncar(respuesta, _MAX_TEXTO),
            "comando": comando,
            "mensaje_comando": _truncar(mensaje_comando, 1000),
            "proveedor": meta.get("proveedor"),
            "modelo": meta.get("modelo"),
            "tokens_in": meta.get("tokens_in"),
            "tokens_out": meta.get("tokens_out"),
            "costo_usd": meta.get("costo_usd"),
            "meta": redactar(meta),
        }
        sb = _sb()
        if sb is None:
            return
        try:
            sb.table("agent_runs").update(parche).eq("run_id", self.run_id).execute()
        except Exception as e:  # noqa: BLE001
            log.warning("no se pudo cerrar agent_runs %s: %s", self.run_id, e)
        self._flush_pasos(sb)

    def _flush_pasos(self, sb: Any) -> None:
        if not self.pasos:
            return
        filas = [{
            "run_id": self.run_id, "orden": p.orden, "nodo": p.nodo, "tool": p.tool,
            "args": p.args, "resultado": p.resultado, "duracion_ms": p.duracion_ms,
            "error": p.error,
        } for p in self.pasos]
        try:
            sb.table("agent_steps").insert(filas).execute()
        except Exception as e:  # noqa: BLE001
            log.warning("no se pudieron guardar %d pasos de %s: %s", len(filas), self.run_id, e)


# La corrida en curso. Vive en un contextvar para que los nodos del grafo puedan
# registrar pasos sin recibirla por parámetro ni meterla en el estado (que el
# checkpointer tendría que serializar).
_actual: contextvars.ContextVar[Run | None] = contextvars.ContextVar("run_actual", default=None)


@contextmanager
def activa(run: Run) -> Iterator[Run]:
    """Marca `run` como la corrida en curso dentro del bloque."""
    token = _actual.set(run)
    try:
        with logs.contexto(run.run_id, chat_id=run.chat_id, canal=run.canal):
            yield run
    finally:
        _actual.reset(token)


def actual() -> Run | None:
    return _actual.get()


@contextmanager
def paso(nodo: str, tool: str | None = None, args: Any = None) -> Iterator[Paso | None]:
    """`with runs.paso("gate"):` — no-op si no hay corrida activa (tests, scripts)."""
    run = _actual.get()
    if run is None:
        yield None
        return
    with run.paso(nodo, tool=tool, args=args) as p:
        yield p


def iniciar(*, canal: str, audiencia: str, chat_id: str, entrada: str,
            nombre: str = "") -> Run:
    """Abre una corrida y la deja registrada como 'en curso'."""
    run = Run(run_id=str(uuid.uuid4()), canal=canal, audiencia=audiencia, chat_id=chat_id)
    metrics.MENSAJES.labels(canal=canal, audiencia=audiencia).inc()
    sb = _sb()
    if sb is None:
        return run
    try:
        sb.table("agent_runs").insert({
            "run_id": run.run_id, "canal": canal, "audiencia": audiencia,
            "chat_id": chat_id, "nombre": nombre or None,
            "entrada": _truncar(entrada, _MAX_TEXTO),
        }).execute()
    except Exception as e:  # noqa: BLE001
        log.warning("no se pudo abrir agent_runs: %s", e)
    return run
