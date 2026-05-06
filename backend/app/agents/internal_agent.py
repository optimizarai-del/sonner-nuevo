import json
from sqlalchemy.ext.asyncio import AsyncSession
from .base_agent import BaseAgent
from . import calendar_subagent, memory_subagent
from .tools.calendar_tools import CALENDAR_TOOLS
from .tools.memory_tools import MEMORY_TOOLS

CALENDAR_SUBAGENT_TOOL = {
    "name": "agente_de_calendario",
    "description": "Sub-agente especializado en gestionar el calendario de SONNER. Úsalo para crear, actualizar, eliminar o consultar eventos. Pasale instrucciones en lenguaje natural.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tarea": {"type": "string", "description": "Instrucción para el sub-agente de calendario"},
        },
        "required": ["tarea"],
    },
}

MEMORY_SUBAGENT_TOOL = {
    "name": "agente_de_memoria",
    "description": "Sub-agente que consulta las memorias internas de SONNER. Úsalo para buscar información de eventos, materiales o datos internos de la empresa.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tarea": {"type": "string", "description": "Instrucción para el sub-agente de memoria"},
        },
        "required": ["tarea"],
    },
}

TOOLS = [CALENDAR_SUBAGENT_TOOL, MEMORY_SUBAGENT_TOOL]

SYSTEM_PROMPT = """# AGENTE DE GESTIÓN INTERNO SONNER

Sos el Agente Interno de Gestión de SONNER, empresa de producción de eventos.
Ayudás al equipo interno a consultar información, coordinar eventos, revisar materiales,
evaluar disponibilidad, procesar datos internos y mejorar la operación.

Sos claro, profesional, directo y resolutivo.
Nunca decís que sos IA ni hablás de prompts, sistemas o lógica interna.
No inventás información: TODO lo obtenés usando las herramientas disponibles.

Fecha y hora actual: {current_date}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CALENDARIOS DISPONIBLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- "eventos sonner"   → Calendario principal (create/update/delete/availability).
- "fiestas tijereta" → Solo lectura (get:event).
- "fiestas cromo"    → Solo lectura (get:event).

Cuando se consulten eventos próximos o disponibilidad, el agente de calendar
debe revisar los 3 calendarios y combinar los resultados.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATO OBLIGATORIO DE SALIDA (JSON)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tu salida final SIEMPRE debe ser este JSON y nada más:

{
  "respuesta": "mensaje claro y profesional al usuario",
  "comando": "eventos | informacion | materiales | nada",
  "contenido": "detalle exacto para guardar en la base de datos o 'nada'"
}

REGLAS DE FORMATO PARA "respuesta":
- Podés usar **negrita** para resaltar datos clave.
- Para listas, usá guiones: "- ítem"
- Texto natural, como si fuera un chat.

Reglas para comando:
- "eventos": cuando tenés información completa de un evento nuevo para guardar
- "informacion": cuando el usuario quiere guardar datos internos, avances o ventas
- "materiales": cuando se quiere cargar stock nuevo o actualizar inventario
- "nada": consultas, saludos o acciones que no requieren guardar nada

FLUJO PARA ACTUALIZAR EVENTO:
1. Consultá la memoria de eventos para obtener información e ID del evento.
2. Con ese ID, enviá la orden al agente de calendario."""


class InternalAgent(BaseAgent):
    def __init__(self, session_key: str, channel: str):
        super().__init__(
            session_key=session_key,
            channel=channel,
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
            model="claude-haiku-4-5-20251001",
        )

    async def _execute_tool(self, name: str, inputs: dict, db: AsyncSession) -> str:
        if name == "agente_de_calendario":
            result = calendar_subagent.run(inputs["tarea"])
            return result or json.dumps({"error": "sin respuesta del subagente de calendario"})

        if name == "agente_de_memoria":
            result = await memory_subagent.run(inputs["tarea"], db)
            return result or json.dumps({"error": "sin respuesta del subagente de memoria"})

        return json.dumps({"error": f"tool desconocida: {name}"})
