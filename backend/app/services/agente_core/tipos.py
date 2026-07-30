"""Tipos compartidos por el motor de agentes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Herramienta:
    """Una tool que el LLM puede invocar.

    - nombre: identificador que ve el LLM (sin espacios ni acentos).
    - descripcion: cuándo/cómo usarla (se la mostramos al LLM).
    - parametros: JSON Schema de los argumentos.
    - ejecutar: función Python que recibe el dict de argumentos y devuelve algo
      serializable a JSON (dict/list/str). NO debe lanzar: si algo falla, devolver
      {"error": "..."} para que el LLM lo vea y siga.
    """
    nombre: str
    descripcion: str
    parametros: dict[str, Any]
    ejecutar: Callable[[dict[str, Any]], Any]

    def correr(self, args: dict[str, Any]) -> Any:
        try:
            return self.ejecutar(args or {})
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}
