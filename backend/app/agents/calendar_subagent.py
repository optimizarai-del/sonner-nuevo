import json
import os
from datetime import datetime
import anthropic
from ..core import google_calendar as gc
from .tools.calendar_tools import CALENDAR_TOOLS

_client = None


def _anthropic():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


SYSTEM_PROMPT = """🗓️ SUBAGENTE DE CALENDAR – SONNER
Fecha y hora actual: {current_date}

Sos el Subagente de Calendar de SONNER. Tu única función es ejecutar acciones sobre
eventos usando las herramientas del calendario. Nunca inventás información. Ejecutás
EXACTAMENTE lo que te pida el Agente Principal.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🗂 CALENDARIOS DISPONIBLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- "eventos sonner"   → Calendario principal. Todas las acciones de producción.
- "fiestas tijereta" → Solo lectura. Se consulta con encontrar_evento_sonner.
- "fiestas cromo"    → Solo lectura. Se consulta con encontrar_evento_sonner.
- "reuniones gabi"   → Calendar personal de Gabi. Bloqueos, compromisos y ausencias personales.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛠 HERRAMIENTAS Y FLUJOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── EVENTOS SONNER ──────────────────────────────────────────────────────────────

✔ encontrar_evento_sonner — Busca en los 3 calendarios (sonner + tijereta + cromo).
  → PASO 1 obligatorio antes de actualizar o eliminar.

✔ get_availability_sonner — Disponibilidad en Eventos Sonner para un rango de fechas.

✔ crear_evento_sonner — Crea en Eventos Sonner. Devolvé el ID generado.

✔ actualizar_evento_sonner — Cambia TÍTULO y/o DESCRIPCIÓN. NO para fechas.
  FLUJO: encontrar_evento_sonner → extraer ID → actualizar_evento_sonner

✔ actualizar_fechas_sonner — Cambia FECHA/HORARIO. Formato ISO 8601 con timezone.
  Ejemplo: 2026-05-10T20:00:00-03:00
  FLUJO: encontrar_evento_sonner → extraer ID → actualizar_fechas_sonner

✔ eliminar_evento_sonner — Elimina de Eventos Sonner.
  FLUJO: encontrar_evento_sonner → extraer ID → eliminar_evento_sonner

── REUNIONES GABI (uso personal) ───────────────────────────────────────────────

Usá estas herramientas SOLO cuando Gabi pida algo personal:
bloquear un día, ir al banco, compromiso propio, ausencia, indisponibilidad.

✔ encontrar_reunion — Obtiene una reunión personal por ID.
  → PASO 1 obligatorio antes de actualizar o borrar.

✔ crear_reunion — Crea en Reuniones Gabi.

✔ actualizar_reunion — Modifica reunión personal.
  FLUJO: encontrar_reunion → extraer ID → actualizar_reunion

✔ borrar_reunion — Elimina reunión personal.
  FLUJO: encontrar_reunion → extraer ID → borrar_reunion

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧾 FORMATO DE RESPUESTA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Siempre respondés con este JSON exacto:
{
  "resumen": "Qué realizaste en lenguaje natural",
  "resultados": [
    {
      "herramienta": "nombre de la herramienta usada",
      "calendario": "eventos sonner | fiestas tijereta | fiestas cromo | reuniones gabi",
      "output": "resultado devuelto por la herramienta",
      "event_id": "ID del evento o null"
    }
  ]
}"""


def execute_tool(name: str, inputs: dict) -> str:
    try:
        # ── Lectura ────────────────────────────────────────────────────────────
        if name == "encontrar_evento_sonner":
            result = gc.encontrar_evento_sonner(inputs["time_min"], inputs["time_max"])
            return json.dumps(result, ensure_ascii=False, default=str)

        if name == "get_availability_sonner":
            result = gc.get_availability_sonner(inputs["time_min"], inputs["time_max"])
            return json.dumps(result, ensure_ascii=False, default=str)

        if name == "encontrar_reunion":
            result = gc.encontrar_reunion(inputs["event_id"])
            return json.dumps(result, ensure_ascii=False, default=str)

        # ── Crear ──────────────────────────────────────────────────────────────
        if name == "crear_evento_sonner":
            result = gc.crear_evento_sonner(
                summary=inputs["summary"],
                start=inputs["start"],
                end=inputs["end"],
                description=inputs.get("description", ""),
                location=inputs.get("location", ""),
            )
            return json.dumps(result, ensure_ascii=False, default=str)

        if name == "crear_reunion":
            result = gc.crear_reunion(
                summary=inputs["summary"],
                start=inputs["start"],
                end=inputs["end"],
                description=inputs.get("description", ""),
                location=inputs.get("location", ""),
            )
            return json.dumps(result, ensure_ascii=False, default=str)

        # ── Actualizar ─────────────────────────────────────────────────────────
        if name == "actualizar_evento_sonner":
            result = gc.actualizar_evento_sonner(
                event_id=inputs["event_id"],
                summary=inputs.get("summary"),
                description=inputs.get("description"),
            )
            return json.dumps(result, ensure_ascii=False, default=str)

        if name == "actualizar_fechas_sonner":
            result = gc.actualizar_fechas_sonner(
                event_id=inputs["event_id"],
                start=inputs["start"],
                end=inputs["end"],
                summary=inputs.get("summary"),
                description=inputs.get("description"),
            )
            return json.dumps(result, ensure_ascii=False, default=str)

        if name == "actualizar_reunion":
            result = gc.actualizar_reunion(
                event_id=inputs["event_id"],
                summary=inputs.get("summary"),
                start=inputs.get("start"),
                end=inputs.get("end"),
                description=inputs.get("description"),
            )
            return json.dumps(result, ensure_ascii=False, default=str)

        # ── Eliminar ───────────────────────────────────────────────────────────
        if name == "eliminar_evento_sonner":
            gc.eliminar_evento_sonner(inputs["event_id"])
            return json.dumps({"status": "eliminado", "event_id": inputs["event_id"]})

        if name == "borrar_reunion":
            gc.borrar_reunion(inputs["event_id"])
            return json.dumps({"status": "eliminado", "event_id": inputs["event_id"]})

    except Exception as e:
        return json.dumps({"error": str(e)})

    return json.dumps({"error": f"herramienta desconocida: {name}"})


def run(task: str) -> str:
    """Run the calendar sub-agent for a given task string."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system = SYSTEM_PROMPT.replace("{current_date}", now)
    messages = [{"role": "user", "content": task}]

    while True:
        response = _anthropic().messages.create(
            model="claude-haiku-4-5-20251001",
            system=system,
            messages=messages,
            tools=CALENDAR_TOOLS,
            max_tokens=4096,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return ""
