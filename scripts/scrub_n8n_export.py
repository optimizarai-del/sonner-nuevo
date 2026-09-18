"""Limpia secretos de un export de workflow de n8n para poder versionarlo.

Los exports de n8n traen tokens embebidos en URLs y headers (el caso real: el token del
bot de Telegram dentro de la URL de `api.telegram.org/bot<TOKEN>/sendMessage`). Este
script los reemplaza por expresiones `{{$env.VAR}}` que n8n resuelve al importar, y
elimina `pinData` (que suele guardar payloads reales con teléfonos de clientes).

Uso:
    python scripts/scrub_n8n_export.py ORIGEN [ORIGEN...] --salida n8n/workflows-export

El reporte nombra la ruta JSON y la regla que disparó, nunca el valor encontrado.
Salida distinta de 0 si algún archivo no se pudo procesar.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# (nombre_regla, patrón, reemplazo). El orden importa: lo más específico primero.
REGLAS: list[tuple[str, re.Pattern[str], str]] = [
    ("telegram_token_en_url",
     re.compile(r"/bot\d{6,12}:[A-Za-z0-9_-]{30,}"),
     "/bot{{$env.TELEGRAM_BOT_TOKEN}}"),
    ("telegram_token_suelto",
     re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b"),
     "{{$env.TELEGRAM_BOT_TOKEN}}"),
    ("anthropic_api_key",
     re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
     "{{$env.ANTHROPIC_API_KEY}}"),
    ("openai_api_key",
     re.compile(r"\bsk-(?!ant-)[A-Za-z0-9_-]{20,}"),
     "{{$env.OPENAI_API_KEY}}"),
    ("google_oauth_secret",
     re.compile(r"\bGOCSPX-[A-Za-z0-9_-]{15,}"),
     "{{$env.GOOGLE_CLIENT_SECRET}}"),
    ("jwt_o_supabase_key",
     re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
     "{{$env.SUPABASE_SERVICE_ROLE_KEY}}"),
    ("bearer_header",
     re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{20,}"),
     r"\1{{$env.API_TOKEN}}"),
]

# Se reportan pero no se reemplazan: no son secretos, pero conviene parametrizarlos
# en la reimplementación Python (ver PLAN_MIGRACION_LANGGRAPH.md §1.3 S3/S4).
AVISOS: list[tuple[str, re.Pattern[str]]] = [
    ("email_personal", re.compile(r"[A-Za-z0-9._%+-]+@(?:gmail|hotmail|outlook|yahoo)\.com")),
]

# Claves que se eliminan enteras del export.
CLAVES_A_ELIMINAR = ("pinData",)


class Reporte:
    def __init__(self) -> None:
        self.redacciones: list[tuple[str, str]] = []
        self.avisos: list[tuple[str, str]] = []
        self.eliminados: list[str] = []


def _limpiar_texto(valor: str, ruta: str, rep: Reporte) -> str:
    for nombre, patron, reemplazo in REGLAS:
        if patron.search(valor):
            valor = patron.sub(reemplazo, valor)
            rep.redacciones.append((ruta, nombre))
    for nombre, patron in AVISOS:
        if patron.search(valor):
            rep.avisos.append((ruta, nombre))
    return valor


def _limpiar(nodo: Any, ruta: str, rep: Reporte) -> Any:
    if isinstance(nodo, dict):
        out: dict[str, Any] = {}
        for k, v in nodo.items():
            if k in CLAVES_A_ELIMINAR:
                rep.eliminados.append(f"{ruta}.{k}")
                continue
            out[k] = _limpiar(v, f"{ruta}.{k}", rep)
        return out
    if isinstance(nodo, list):
        return [_limpiar(v, f"{ruta}[{i}]", rep) for i, v in enumerate(nodo)]
    if isinstance(nodo, str):
        return _limpiar_texto(nodo, ruta, rep)
    return nodo


def procesar(origen: Path, destino: Path) -> Reporte:
    datos = json.loads(origen.read_text(encoding="utf-8"))
    rep = Reporte()
    limpio = _limpiar(datos, "$", rep)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(limpio, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return rep


def _nombre_destino(origen: Path) -> str:
    """Normaliza el nombre: sin sufijos (1)…(4), sin acentos raros, kebab-case."""
    base = re.sub(r"\s*\(\d+\)\s*$", "", origen.stem)
    base = base.replace("·", "-").replace("_", "-")
    base = re.sub(r"[^A-Za-z0-9-]+", "-", base).strip("-").lower()
    base = re.sub(r"-{2,}", "-", base)
    return f"{base}.json"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Limpia secretos de exports de n8n.")
    ap.add_argument("origenes", nargs="+", type=Path)
    ap.add_argument("--salida", type=Path, required=True)
    args = ap.parse_args(argv)

    fallos = 0
    total_red = 0
    for origen in args.origenes:
        if not origen.is_file():
            print(f"!! no existe: {origen}", file=sys.stderr)
            fallos += 1
            continue
        destino = args.salida / _nombre_destino(origen)
        try:
            rep = procesar(origen, destino)
        except Exception as e:  # noqa: BLE001
            print(f"!! {origen.name}: {e}", file=sys.stderr)
            fallos += 1
            continue

        total_red += len(rep.redacciones)
        print(f"\n{origen.name}  ->  {destino}")
        for ruta, regla in rep.redacciones:
            print(f"   REDACTADO  {regla:24s} {ruta}")
        for ruta in rep.eliminados:
            print(f"   ELIMINADO  {'pinData':24s} {ruta}")
        for ruta, regla in rep.avisos:
            print(f"   AVISO      {regla:24s} {ruta}")
        if not (rep.redacciones or rep.eliminados or rep.avisos):
            print("   (sin hallazgos)")

    print(f"\n{total_red} valor(es) redactado(s).")
    if total_red:
        print("RECORDATORIO: redactar el export NO rota el secreto. "
              "Rotá el token en su proveedor.")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
