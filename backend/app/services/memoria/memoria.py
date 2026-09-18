"""Orquestador determinístico del sub-agente Memoria de SONNER.

Recibe un comando del Agente Principal y devuelve el contrato JSON:
    { "origen": ..., "encontrado": "si|no", "respuesta": "<texto plano>" }

Comandos soportados (igual que el prompt n8n):
    "buscar en materiales: [ITEM]"      → fuente materiales
    "buscar en eventos: [CONSULTA]"     → fuente eventos
    "buscar configuracion: CFG-XXX"     → fuente modelo_eventos
    "buscar info interna: [CONSULTA]"   → fuente informacion_interna
    "buscar mixto: [CONSULTA]"          → todas las fuentes

Si el comando no encaja, clasifica por keywords; si tampoco, hace broad search.
NUNCA inventa: la respuesta sale verbatim de los chunks de Supabase.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from ...config import settings
from . import vectorstore as vs

log = logging.getLogger("memoria.memoria")

# fuente interna (source) → etiqueta `origen` que espera el Agente Principal
ORIGEN_LABEL = {
    "materiales": "materiales",
    "eventos": "eventos",
    "modelo_eventos": "modelo eventos",
    "informacion_interna": "interna",
}

# Fuentes cuyo contenido es INTERNO (precios, composición técnica, políticas).
FUENTES_INTERNAS = {"modelo_eventos", "informacion_interna"}
PREFIJO_INTERNO = "[INTERNO — NO COMUNICAR AL CLIENTE] "

# Keywords para clasificar cuando no hay comando explícito.
KEYWORDS: Dict[str, List[str]] = {
    "modelo_eventos": ["cfg", "configuracion", "configuración", "modelo de evento", "paquete"],
    "materiales": ["stock", "material", "equipo", "parlante", "luces", "consola", "micrófono",
                   "microfono", "cable", "trípode", "tripode", "estructura", "disponible"],
    "eventos": ["evento", "fiesta", "casamiento", "cumpleaños", "cumpleanos", "salon", "salón",
                "histórico", "historico", "agendado"],
    "informacion_interna": ["politica", "política", "procedimiento", "condicion", "condición",
                            "interno", "interna", "seña", "reserva", "horario laboral"],
}

# Patrones de comando → fuente
_COMANDOS: List[Tuple[re.Pattern, Optional[str]]] = [
    (re.compile(r"^\s*buscar\s+en\s+materiales\s*:", re.I), "materiales"),
    (re.compile(r"^\s*buscar\s+en\s+eventos\s*:", re.I), "eventos"),
    (re.compile(r"^\s*buscar\s+configuraci[oó]n\s*:", re.I), "modelo_eventos"),
    (re.compile(r"^\s*buscar\s+info\s+interna\s*:", re.I), "informacion_interna"),
    (re.compile(r"^\s*buscar\s+mixto\s*:", re.I), None),  # None = todas
]
_RE_CFG = re.compile(r"\bCFG[-\s]?\d+\b", re.I)


def _normalizar(s: str) -> str:
    s = (s or "").lower()
    for a, b in {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}.items():
        s = s.replace(a, b)
    return s


def _parsear(mensaje: str) -> Tuple[List[Optional[str]], str, bool]:
    """Devuelve (fuentes, query_limpia, fue_mixto).

    fuentes: lista de fuentes a consultar; [None] = broad search en todas.
    """
    msg = (mensaje or "").strip()

    # 1) Comando explícito
    for patron, fuente in _COMANDOS:
        m = patron.search(msg)
        if m:
            query = msg[m.end():].strip() or msg
            if fuente is None:  # mixto
                return list(vs.FUENTES_VALIDAS), query, True
            return [fuente], query, False

    # 2) Heurística: si menciona un CFG, es modelo_eventos
    if _RE_CFG.search(msg):
        return ["modelo_eventos"], msg, False

    # 3) Clasificación por keywords
    q = _normalizar(msg)
    matches: List[Tuple[str, int]] = []
    for fuente, kws in KEYWORDS.items():
        n = sum(1 for kw in kws if _normalizar(kw) in q)
        if n:
            matches.append((fuente, n))
    if matches:
        matches.sort(key=lambda x: -x[1])
        return [matches[0][0]], msg, False

    # 4) Sin pistas: broad search
    return [None], msg, True


def consultar(mensaje: str, k: Optional[int] = None, fuente: Optional[str] = None) -> Dict[str, Any]:
    """Punto de entrada. Devuelve {origen, encontrado, respuesta} + meta de debug.

    `fuente` explícita (la elige el agente principal) evita el parseo del comando:
    "todas" busca en todo, un valor inválido se ignora y se cae al parser.
    """
    t0 = time.time()
    k = k or settings.MEMORIA_TOPK
    min_sim = settings.MEMORIA_MIN_SIMILARITY

    if not mensaje or not mensaje.strip():
        return {"origen": "mixto", "encontrado": "no",
                "respuesta": "Comando vacío: no se ejecutó ninguna búsqueda."}

    if fuente == "todas":
        fuentes, query, fue_mixto = [None], mensaje.strip(), True
    elif fuente in vs.FUENTES_VALIDAS:
        fuentes, query, fue_mixto = [fuente], mensaje.strip(), False
    else:
        fuentes, query, fue_mixto = _parsear(mensaje)

    resultados: Dict[str, List[Dict[str, Any]]] = {}
    errores: List[str] = []
    for f in fuentes:
        try:
            chunks = vs.buscar(query, fuente=f, k=k, min_similarity=min_sim)
        except Exception as e:
            errores.append(f"{f or 'todas'}: {e}")
            chunks = []
        resultados[f or "todas"] = chunks

    total = sum(len(v) for v in resultados.values())

    # Fallback: filtramos por una fuente y no trajo nada → reintentar broad.
    if total == 0 and not errores and fuentes != [None]:
        try:
            resultados["todas"] = vs.buscar(query, fuente=None, k=k, min_similarity=min_sim)
            total = len(resultados["todas"])
            fue_mixto = True
        except Exception as e:
            errores.append(f"todas: {e}")

    origen = _origen(fuentes, fue_mixto)

    # Error de herramienta → encontrado:"no" con explicación (no inventar).
    if errores and total == 0:
        return {
            "origen": origen, "encontrado": "no",
            "respuesta": "Error al consultar la base de memoria: " + "; ".join(errores)
            + ". Requiere revisión.",
            "_meta": {"errores": errores, "query": query},
        }

    respuesta = _render(resultados, fuentes, query, fue_mixto)
    return {
        "origen": origen,
        "encontrado": "si" if total > 0 else "no",
        "respuesta": respuesta,
        "_meta": {
            "query": query,
            "fuentes": [f for f in fuentes if f] or ["(todas)"],
            "chunks": total,
            "tiempo_ms": int((time.time() - t0) * 1000),
            "errores": errores,
        },
    }


def _origen(fuentes: List[Optional[str]], fue_mixto: bool) -> str:
    if fue_mixto or len([f for f in fuentes if f]) != 1:
        return "mixto"
    return ORIGEN_LABEL.get(fuentes[0], "mixto")


def _render(
    resultados: Dict[str, List[Dict[str, Any]]],
    fuentes: List[Optional[str]],
    query: str,
    fue_mixto: bool,
) -> str:
    """Arma la `respuesta` en texto plano, verbatim desde los chunks.

    Aplica el prefijo [INTERNO — NO COMUNICAR AL CLIENTE] a fuentes sensibles.
    Si combina fuentes, numera 1) 2) 3).
    """
    # Aplanar todos los chunks únicos, ordenados por similarity DESC
    vistos: set = set()
    items: List[Dict[str, Any]] = []
    for chunks in resultados.values():
        for c in chunks:
            if c["id"] in vistos:
                continue
            vistos.add(c["id"])
            items.append(c)
    items.sort(key=lambda c: -c.get("similarity", 0))

    if not items:
        nombres = ", ".join(ORIGEN_LABEL.get(f, "todas") for f in fuentes) if any(fuentes) else "las memorias"
        return f"No se encontró información sobre «{query}» en {nombres}."

    partes: List[str] = []
    numerar = fue_mixto or len(items) > 1
    for i, c in enumerate(items, 1):
        fuente = c.get("fuente") or "?"
        contenido = (c.get("content") or "").strip()
        etiqueta = ORIGEN_LABEL.get(fuente, fuente).upper()
        prefijo = PREFIJO_INTERNO if fuente in FUENTES_INTERNAS else ""
        encabezado = f"{i}) " if numerar else ""
        partes.append(f"{encabezado}{prefijo}{etiqueta}: {contenido}")

    cuerpo = "\n\n".join(partes)
    if any(f in FUENTES_INTERNAS for f in (c.get("fuente") for c in items)):
        cuerpo += ("\n\nNota: los datos marcados [INTERNO] (precios/composición técnica/políticas) "
                   "son de uso del Agente Principal y no deben comunicarse al cliente. "
                   "Los precios dependen de logística.")
    return cuerpo
