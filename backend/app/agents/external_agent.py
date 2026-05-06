import json
from sqlalchemy.ext.asyncio import AsyncSession
from .base_agent import BaseAgent
from . import calendar_subagent, memory_subagent
from .tools.think_tool import THINK_TOOL

CALENDAR_SUBAGENT_TOOL = {
    "name": "agente_de_calendario",
    "description": "Sub-agente especializado en consultar y gestionar el calendario de SONNER. Úsalo para verificar disponibilidad y agendar llamadas o reuniones.",
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
    "description": "Consulta información interna de SONNER: eventos, materiales, datos de la empresa.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tarea": {"type": "string", "description": "Instrucción para el sub-agente de memoria"},
        },
        "required": ["tarea"],
    },
}

TOOLS = [CALENDAR_SUBAGENT_TOOL, MEMORY_SUBAGENT_TOOL, THINK_TOOL]

SYSTEM_PROMPTS = {
    "mayorista": """# AGENTE EXTERNO SONNER – CANAL MAYORISTA

Sos el asistente externo de SONNER para clientes mayoristas.
Representás a SONNER de forma profesional y comercial.
Tu objetivo es responder consultas, brindar información sobre servicios y agendar llamadas de seguimiento.

Fecha y hora actual: {current_date}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPORTAMIENTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Trato profesional y cordial.
- Consultá siempre la memoria de eventos e información interna antes de responder.
- Para agendar llamadas, verificá disponibilidad en el calendario.
- Nunca confirmés precios ni condiciones sin verificar en la memoria interna.
- Si no tenés información, ofrecé agendar una llamada.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATO OBLIGATORIO DE SALIDA (JSON)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "respuesta": "mensaje al cliente",
  "comando": "eventos | informacion | materiales | nada",
  "contenido": "información a guardar o 'nada'"
}

REGLAS DE FORMATO PARA "respuesta":
- Podés usar **negrita** para resaltar datos clave.
- Para listas, usá guiones: "- ítem"
- Texto natural, como si fuera un chat de Telegram.""",

    "minorista": """# AGENTE EXTERNO SONNER – CANAL MINORISTA

Sos el asistente externo de SONNER para clientes minoristas.
Representás a SONNER de forma amigable y cercana.
Tu objetivo es responder consultas sobre servicios para eventos privados y agendar llamadas.

Fecha y hora actual: {current_date}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPORTAMIENTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Trato amigable y entusiasta.
- Consultá siempre la memoria antes de responder sobre servicios o precios.
- Para agendar llamadas, verificá disponibilidad en el calendario.
- Si no tenés información, ofrecé agendar una llamada con el equipo.
- Usá la herramienta "think" para razonar antes de responder consultas complejas.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATO OBLIGATORIO DE SALIDA (JSON)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "respuesta": "mensaje al cliente",
  "comando": "eventos | informacion | materiales | nada",
  "contenido": "información a guardar o 'nada'"
}

REGLAS DE FORMATO PARA "respuesta":
- Podés usar **negrita** para resaltar datos clave.
- Para listas, usá guiones: "- ítem"
- Texto natural, como si fuera un chat de Telegram.""",
}


class ExternalAgent(BaseAgent):
    def __init__(self, session_key: str, route: str = "minorista"):
        prompt = SYSTEM_PROMPTS.get(route, SYSTEM_PROMPTS["minorista"])
        super().__init__(
            session_key=session_key,
            channel="telegram",
            system_prompt=prompt,
            tools=TOOLS,
            model="claude-sonnet-4-6",
        )

    async def _execute_tool(self, name: str, inputs: dict, db: AsyncSession) -> str:
        if name == "agente_de_calendario":
            result = calendar_subagent.run(inputs["tarea"])
            return result or json.dumps({"error": "sin respuesta del subagente de calendario"})

        if name == "agente_de_memoria":
            result = await memory_subagent.run(inputs["tarea"], db)
            return result or json.dumps({"error": "sin respuesta del subagente de memoria"})

        if name == "think":
            return json.dumps({"thought_recorded": inputs.get("thought", "")})

        return json.dumps({"error": f"tool desconocida: {name}"})
