"""Búsqueda en el vector store de Supabase (tabla `documents`) para SONNER.

- Embebe la query con OpenAI (MISMO modelo con el que se cargaron los chunks: 1536 dims).
- Consulta vía la RPC `match_documents(query_embedding, match_count, filter)`.
- Cachea embeddings y resultados en memoria con TTL para no re-embeber lo mismo.

Sin LLM: la elección de fuente la hace `memoria.py` por parsing de comando.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from ...config import settings
from ..supabase_client import get_supabase_admin

log = logging.getLogger("memoria.vectorstore")

# Fuentes válidas = valores reales de metadata.source en la tabla documents.
# OJO: es "modelo_eventos" (plural). El nodo n8n lo tenía como "modelo_evento"
# (singular) y por eso no devolvía nada — acá queda corregido.
FUENTES_VALIDAS = ("materiales", "eventos", "modelo_eventos", "informacion_interna")


# ── Caché TTL simple, thread-safe ──────────────────────────────────────────────
class _TTLCache:
    def __init__(self, ttl: int = 300, max_size: int = 1000):
        self._store: "OrderedDict[str, Tuple[Any, float]]" = OrderedDict()
        self._lock = threading.Lock()
        self.ttl = ttl
        self.max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            e = self._store.get(key)
            if not e:
                return None
            val, exp = e
            if time.time() > exp:
                self._store.pop(key, None)
                return None
            self._store.move_to_end(key)
            return val

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            elif len(self._store) >= self.max_size:
                self._store.popitem(last=False)
            self._store[key] = (value, time.time() + self.ttl)


_cache = _TTLCache()
_openai: Optional[OpenAI] = None


def _client() -> OpenAI:
    global _openai
    if _openai is None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY no configurada")
        _openai = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=30, max_retries=2)
    return _openai


def _hash(*parts: Any) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:32]


def embeber(query: str) -> List[float]:
    """Embedding de la query (cacheado). Levanta si OpenAI falla."""
    key = f"emb:{_hash(settings.OPENAI_EMBED_MODEL, query)}"
    cached = _cache.get(key)
    if cached is not None:
        return cached
    resp = _client().embeddings.create(model=settings.OPENAI_EMBED_MODEL, input=query)
    emb = resp.data[0].embedding
    _cache.set(key, emb)
    return emb


def buscar(
    query: str,
    fuente: Optional[str] = None,
    k: int = 5,
    min_similarity: float = 0.0,
) -> List[Dict[str, Any]]:
    """Top-k chunks por similitud coseno desde `documents`, filtrando por
    metadata.source = fuente (o sin filtro si fuente es None).
    """
    if not query or not query.strip():
        return []
    if fuente and fuente not in FUENTES_VALIDAS:
        log.warning("fuente inválida: %s", fuente)
        return []

    cache_key = f"chunks:{_hash(query, fuente, k)}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        emb = embeber(query)
    except Exception as e:
        log.error("embed falló: %s", e)
        raise

    filtro: Dict[str, Any] = {"source": fuente} if fuente else {}
    try:
        sb = get_supabase_admin()
        resp = sb.rpc(
            "match_documents",
            {"query_embedding": emb, "match_count": k, "filter": filtro},
        ).execute()
        rows = resp.data or []
    except Exception as e:
        log.error("match_documents falló: %s", e)
        raise

    out: List[Dict[str, Any]] = []
    for r in rows:
        sim = float(r.get("similarity") or 0.0)
        if sim < min_similarity:
            continue
        meta = r.get("metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        out.append({
            "id": str(r.get("id")),
            "content": r.get("content") or "",
            "metadata": meta,
            "fuente": meta.get("source"),
            "similarity": round(sim, 4),
        })
    _cache.set(cache_key, out)
    return out


def conteo_por_fuente() -> Dict[str, int]:
    """Debug: cuántos chunks hay por fuente."""
    try:
        sb = get_supabase_admin()
        rows = sb.table("documents").select("metadata").execute().data or []
    except Exception as e:
        log.error("conteo_por_fuente falló: %s", e)
        return {}
    counts: Dict[str, int] = {}
    for r in rows:
        src = (r.get("metadata") or {}).get("source") or "(sin source)"
        counts[src] = counts.get(src, 0) + 1
    return counts
