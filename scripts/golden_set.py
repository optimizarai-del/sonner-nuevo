"""Golden set del agente externo: conversaciones reales contra el grafo nuevo.

Los tests de backend/tests corren contra un LLM falso. Esto es lo contrario: toma
mensajes reales que ya atendió el agente viejo, se los pasa al grafo nuevo por HTTP
con el modelo de verdad, y compara.

Dos pasos:

    extraer   csm_analisis → agent_golden_cases
    correr    agent_golden_cases → POST /api/agente/probar → reporte

La referencia de cada caso sale de lo que revisó un humano en el panel de CSM, en
este orden de preferencia: `respuesta_corregida` > `respuesta_agente` con rating
"good" > `respuesta_agente` sin revisar. Los casos con rating "bad" también entran:
sirven para verificar que el grafo nuevo no repita el error.

Evaluación en dos capas:
- Reglas duras (`REGLAS`): se cumplen o no. Una sola falla vuelve el exit code 1.
- Juez LLM (`--juez`): compara con la referencia y dice igual / mejor / peor. Es
  orientativo; lo que decide es la lectura humana del reporte.

Privacidad: los casos son mensajes reales de clientes. Viven en Supabase y el reporte
se escribe en backend/.golden/, que está en .gitignore. Nunca van al repo.

Uso (desde la raíz del repo, con el venv del backend):

    set SUPABASE_URL=...  SUPABASE_SERVICE_ROLE_KEY=...
    python scripts/golden_set.py extraer --n 40 [--dry-run]
    python scripts/golden_set.py correr --url https://staging... --key <MEMORIA_INTERNAL_KEY> [--juez]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

SALIDA = Path(__file__).resolve().parents[1] / "backend" / ".golden"
# Teléfono sintético: sin historial previo y reconocible en agent_runs.
TELEFONO_GOLDEN = "+5400000000{:04d}"


# ── Reglas duras ─────────────────────────────────────────────────────────────
# Cada regla recibe la salida de /probar y devuelve None si pasa o el motivo si no.
Regla = Callable[[dict[str, Any]], "str | None"]

_ERROR_TECNICO = re.compile(
    r"(?i)\b(error|inconveniente t[ée]cnico|problema t[ée]cnico|no pude procesar|"
    r"falla del sistema|intent[aá] (de nuevo|m[aá]s tarde))\b")
_MONTO = re.compile(r"\$\s?\d|\b\d{1,3}(\.\d{3})+\s?(pesos|ars)\b", re.I)


def _respuesta(salida: dict[str, Any]) -> str:
    return str(salida.get("respuesta") or "")


def regla_respuesta_no_vacia(s: dict[str, Any]) -> str | None:
    return None if _respuesta(s).strip() else "respuesta vacía"


def regla_comando_valido(s: dict[str, Any]) -> str | None:
    comando = s.get("comando")
    return None if comando in ("mensaje_gabi", "nada") else f"comando inválido: {comando!r}"


def regla_sin_error_tecnico(s: dict[str, Any]) -> str | None:
    """Al cliente nunca le llega un error técnico (ver nodes/guard.py)."""
    m = _ERROR_TECNICO.search(_respuesta(s))
    return f"menciona un error: «{m.group(0)}»" if m else None


def regla_sin_montos(s: dict[str, Any]) -> str | None:
    """Precios y señas son internos: el agente no cotiza por WhatsApp."""
    m = _MONTO.search(_respuesta(s))
    return f"expone un monto: «{m.group(0)}»" if m else None


def regla_sin_marca_interna(s: dict[str, Any]) -> str | None:
    """El prefijo de memoria es para el agente; si llega al cliente, se filtró."""
    return "filtró el prefijo [INTERNO]" if "[INTERNO" in _respuesta(s).upper() else None


def regla_sin_json_crudo(s: dict[str, Any]) -> str | None:
    r = _respuesta(s).strip()
    if r.startswith("{") or '"respuesta"' in r or '"comando"' in r:
        return "le llega JSON crudo al cliente"
    return None


def regla_no_degradado(s: dict[str, Any]) -> str | None:
    """Degradado = el grafo no pudo producir un contrato (no es una derivación normal)."""
    meta = s.get("_meta") or {}
    if meta.get("degradado_handoff"):
        return f"degradó a handoff ({meta.get('motivo_handoff') or meta.get('error') or '?'})"
    return None


REGLAS: dict[str, Regla] = {
    "respuesta_no_vacia": regla_respuesta_no_vacia,
    "comando_valido": regla_comando_valido,
    "sin_error_tecnico": regla_sin_error_tecnico,
    "sin_montos": regla_sin_montos,
    "sin_marca_interna": regla_sin_marca_interna,
    "sin_json_crudo": regla_sin_json_crudo,
    "no_degradado": regla_no_degradado,
}


def evaluar_reglas(salida: dict[str, Any], nombres: list[str] | None = None) -> list[str]:
    """Motivos de falla (lista vacía = pasó todas)."""
    fallas = []
    for nombre in nombres or list(REGLAS):
        regla = REGLAS.get(nombre)
        motivo = regla(salida) if regla else None
        if motivo:
            fallas.append(f"{nombre}: {motivo}")
    return fallas


# ── Selección de casos ───────────────────────────────────────────────────────
def referencia(fila: dict[str, Any]) -> tuple[str, str] | None:
    """(texto, fuente) de la respuesta contra la que se compara, o None si no hay."""
    if (fila.get("respuesta_corregida") or "").strip():
        return fila["respuesta_corregida"].strip(), "corregida"
    if not (fila.get("respuesta_agente") or "").strip():
        return None
    fuente = {"good": "aprobada", "bad": "rechazada", "mejorable": "mejorable"}.get(
        fila.get("rating") or "", "sin_revisar")
    return fila["respuesta_agente"].strip(), fuente


def _clave_duplicado(mensaje: str) -> str:
    return re.sub(r"\W+", " ", (mensaje or "").lower()).strip()[:80]


def seleccionar(filas: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    """Elige hasta `n` casos: primero los revisados por un humano, sin duplicados,
    balanceando minoristas y mayoristas. Pura: se testea sin Supabase."""
    vistos: set[str] = set()
    candidatos = []
    for f in filas:
        msg = (f.get("mensaje_cliente") or "").strip()
        clave = _clave_duplicado(msg)
        if len(msg) < 3 or clave in vistos or referencia(f) is None:
            continue
        vistos.add(clave)
        candidatos.append(f)

    prioridad = {"corregida": 0, "aprobada": 1, "rechazada": 2, "mejorable": 3, "sin_revisar": 4}
    candidatos.sort(key=lambda f: prioridad[referencia(f)[1]])  # type: ignore[index]

    por_tipo: dict[str, list[dict[str, Any]]] = {}
    for f in candidatos:
        por_tipo.setdefault(f.get("tipo_cliente") or "minorista", []).append(f)

    elegidos: list[dict[str, Any]] = []
    while len(elegidos) < n and any(por_tipo.values()):
        for tipo in sorted(por_tipo):
            if por_tipo[tipo] and len(elegidos) < n:
                elegidos.append(por_tipo[tipo].pop(0))
    return elegidos


def a_caso(fila: dict[str, Any]) -> dict[str, Any]:
    texto, fuente = referencia(fila)  # type: ignore[misc]
    return {
        "nombre": f"csm-{fila['id']}",
        "canal": "whatsapp",
        "audiencia": "externo",
        "mensaje": fila["mensaje_cliente"].strip(),
        "esperado": {
            "csm_id": fila["id"],
            "referencia": texto,
            "fuente_referencia": fuente,
            "tipo_cliente": fila.get("tipo_cliente") or "minorista",
            "cliente_nombre": fila.get("cliente_nombre") or "",
            "nota_revisor": fila.get("nota"),
        },
        "asserts": list(REGLAS),
    }


# ── Supabase ─────────────────────────────────────────────────────────────────
def _supabase():
    from supabase import create_client

    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not (url and key):
        sys.exit("Faltan SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY en el entorno.")
    return create_client(url, key)


def cmd_extraer(args: argparse.Namespace) -> int:
    sb = _supabase()
    filas = (sb.table("csm_analisis")
             .select("id, mensaje_cliente, respuesta_agente, respuesta_corregida, rating, "
                     "tipo_cliente, cliente_nombre, nota, agente, canal")
             .eq("canal", "whatsapp").order("created_at", desc=True)
             .limit(args.pool).execute().data or [])
    filas = [f for f in filas if (f.get("agente") or "principal") == "principal"]

    ya = {(c.get("esperado") or {}).get("csm_id")
          for c in (sb.table("agent_golden_cases").select("esperado").execute().data or [])}
    nuevos = [a_caso(f) for f in seleccionar([f for f in filas if f["id"] not in ya], args.n)]

    fuentes: dict[str, int] = {}
    for c in nuevos:
        k = c["esperado"]["fuente_referencia"]
        fuentes[k] = fuentes.get(k, 0) + 1
    print(f"pool: {len(filas)} filas de csm_analisis · ya importados: {len(ya - {None})}")
    print(f"nuevos: {len(nuevos)} · por referencia: {fuentes}")

    if args.dry_run or not nuevos:
        print("(dry-run: no se escribió nada)" if args.dry_run else "nada para importar")
        return 0
    sb.table("agent_golden_cases").insert(nuevos).execute()
    print(f"insertados {len(nuevos)} casos en agent_golden_cases")
    return 0


# ── Ejecución ────────────────────────────────────────────────────────────────
_JUEZ_SISTEMA = """Sos evaluador de un agente de ventas por WhatsApp de SONNER (sonido e \
iluminación para eventos, La Pampa). Compará la RESPUESTA NUEVA con la de REFERENCIA \
para el mismo mensaje del cliente.

Criterios, en orden: 1) no inventa datos ni fechas, 2) avanza la venta o deriva a \
Gabriel cuando corresponde, 3) tono humano en voseo argentino, 4) no pide datos de a \
muchos juntos.

Si la referencia está marcada como "rechazada", fue una MALA respuesta: la nueva gana si \
no repite ese error.

Contestá SOLO un JSON: {"veredicto": "mejor|igual|peor", "motivo": "una frase"}"""


def juzgar(mensaje: str, nueva: str, ref: str, fuente: str) -> dict[str, str]:
    import anthropic

    cliente = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=60)
    r = cliente.messages.create(
        model=os.environ.get("GOLDEN_JUEZ_MODEL", "claude-sonnet-5"),
        max_tokens=300, system=_JUEZ_SISTEMA,
        messages=[{"role": "user", "content":
                   f"MENSAJE DEL CLIENTE:\n{mensaje}\n\nREFERENCIA ({fuente}):\n{ref}\n\n"
                   f"RESPUESTA NUEVA:\n{nueva}"}],
    )
    texto = "".join(getattr(b, "text", "") for b in r.content)
    m = re.search(r"\{.*\}", texto, re.S)
    try:
        out = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        out = {}
    return {"veredicto": out.get("veredicto", "sin_veredicto"), "motivo": out.get("motivo", texto[:200])}


@dataclass
class Resultado:
    caso: dict[str, Any]
    salida: dict[str, Any] = field(default_factory=dict)
    fallas: list[str] = field(default_factory=list)
    juez: dict[str, str] | None = None
    segundos: float = 0.0
    error_http: str | None = None


def correr_caso(caso: dict[str, Any], url: str, key: str, idx: int) -> Resultado:
    import httpx

    esperado = caso.get("esperado") or {}
    res = Resultado(caso=caso)
    inicio = time.monotonic()
    try:
        r = httpx.post(
            f"{url.rstrip('/')}/api/agente/probar",
            headers={"X-Memoria-Key": key} if key else {},
            json={"mensaje": caso["mensaje"], "telefono": TELEFONO_GOLDEN.format(idx),
                  "nombre": esperado.get("cliente_nombre") or "",
                  "tipo_cliente": esperado.get("tipo_cliente") or "minorista",
                  "persistir": False},
            timeout=120,
        )
        r.raise_for_status()
        res.salida = r.json()
    except Exception as e:  # noqa: BLE001
        res.error_http = f"{type(e).__name__}: {e}"
    res.segundos = round(time.monotonic() - inicio, 1)
    if res.error_http is None:
        res.fallas = evaluar_reglas(res.salida, caso.get("asserts") or None)
    return res


def reporte_md(resultados: list[Resultado], url: str) -> str:
    total = len(resultados)
    errores_http = [r for r in resultados if r.error_http]
    con_fallas = [r for r in resultados if r.fallas]
    veredictos: dict[str, int] = {}
    for r in resultados:
        if r.juez:
            veredictos[r.juez["veredicto"]] = veredictos.get(r.juez["veredicto"], 0) + 1
    tiempos = sorted(r.segundos for r in resultados if not r.error_http)
    p50 = tiempos[len(tiempos) // 2] if tiempos else 0

    lineas = [
        f"# Golden set — {datetime.now():%Y-%m-%d %H:%M}",
        f"Contra: `{url}` · casos: {total}",
        "",
        f"- Reglas duras OK: **{total - len(con_fallas) - len(errores_http)}/{total}**",
        f"- Errores HTTP: {len(errores_http)}",
        f"- Latencia p50: {p50}s",
    ]
    if veredictos:
        lineas.append("- Juez: " + " · ".join(f"{k} {v}" for k, v in sorted(veredictos.items())))
    lineas.append("")

    def bloque(titulo: str, lista: list[Resultado]) -> None:
        if not lista:
            return
        lineas.append(f"## {titulo}\n")
        for r in lista:
            e = r.caso.get("esperado") or {}
            lineas += [
                f"### {r.caso['nombre']} ({e.get('tipo_cliente')}, ref {e.get('fuente_referencia')})",
                f"**Cliente:** {r.caso['mensaje']}",
                f"**Referencia:** {e.get('referencia')}",
                f"**Nueva:** {r.salida.get('respuesta') or '—'}  (comando: {r.salida.get('comando')})",
            ]
            if r.error_http:
                lineas.append(f"**Error HTTP:** {r.error_http}")
            if r.fallas:
                lineas.append("**Reglas:** " + "; ".join(r.fallas))
            if r.juez:
                lineas.append(f"**Juez:** {r.juez['veredicto']} — {r.juez['motivo']}")
            lineas.append("")

    bloque("Fallas de reglas duras", con_fallas + errores_http)
    bloque("Peor que la referencia", [r for r in resultados if r.juez
                                       and r.juez["veredicto"] == "peor" and not r.fallas])
    return "\n".join(lineas)


def cmd_correr(args: argparse.Namespace) -> int:
    sb = _supabase()
    casos = (sb.table("agent_golden_cases").select("*").eq("activo", True)
             .eq("audiencia", "externo").order("id").limit(args.limite).execute().data or [])
    if not casos:
        print("No hay casos activos. Corré primero: golden_set.py extraer")
        return 1
    if args.juez and not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("--juez necesita ANTHROPIC_API_KEY en el entorno.")

    resultados = []
    for i, caso in enumerate(casos, 1):
        r = correr_caso(caso, args.url, args.key, i)
        if args.juez and not r.error_http and r.salida.get("respuesta"):
            e = caso.get("esperado") or {}
            try:
                r.juez = juzgar(caso["mensaje"], r.salida["respuesta"],
                                e.get("referencia") or "", e.get("fuente_referencia") or "")
            except Exception as ex:  # noqa: BLE001
                r.juez = {"veredicto": "sin_veredicto", "motivo": str(ex)[:200]}
        marca = "ERR" if r.error_http else ("FALLA" if r.fallas else "ok")
        extra = f" · juez {r.juez['veredicto']}" if r.juez else ""
        print(f"[{i:02d}/{len(casos)}] {marca:5s} {r.segundos:5.1f}s {caso['nombre']}{extra}")
        resultados.append(r)

    SALIDA.mkdir(parents=True, exist_ok=True)
    sello = datetime.now().strftime("%Y%m%d-%H%M")
    md = SALIDA / f"reporte-{sello}.md"
    md.write_text(reporte_md(resultados, args.url), encoding="utf-8")
    (SALIDA / f"reporte-{sello}.json").write_text(json.dumps(
        [{"caso": r.caso["nombre"], "salida": r.salida, "fallas": r.fallas,
          "juez": r.juez, "segundos": r.segundos, "error_http": r.error_http}
         for r in resultados], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nreporte: {md}")

    rotos = [r for r in resultados if r.fallas or r.error_http]
    print(f"reglas duras: {len(resultados) - len(rotos)}/{len(resultados)} OK")
    return 1 if rotos else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Golden set del agente externo de SONNER.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extraer", help="csm_analisis → agent_golden_cases")
    e.add_argument("--n", type=int, default=40, help="cuántos casos nuevos importar")
    e.add_argument("--pool", type=int, default=1000, help="cuántas filas recientes mirar")
    e.add_argument("--dry-run", action="store_true")

    c = sub.add_parser("correr", help="corre los casos contra un servicio")
    c.add_argument("--url", required=True, help="base del servicio (staging, nunca prod)")
    c.add_argument("--key", default=os.environ.get("MEMORIA_INTERNAL_KEY", ""))
    c.add_argument("--juez", action="store_true", help="comparar con la referencia vía Claude")
    c.add_argument("--limite", type=int, default=200)

    args = ap.parse_args(argv)
    return cmd_extraer(args) if args.cmd == "extraer" else cmd_correr(args)


if __name__ == "__main__":
    raise SystemExit(main())
