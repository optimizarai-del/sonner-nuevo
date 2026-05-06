import json
import os
import anthropic
from ..core.vector_store import search
from .tools.memory_tools import MEMORY_TOOLS

_client = None


def _anthropic():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


SYSTEM_PROMPT = """Sos el Subagente de Memoria de SONNER.
Tu trabajo es buscar y devolver información EXACTA desde las memorias internas.
Nunca inventás nada. Nunca completás huecos con suposiciones.
Todo sale EXCLUSIVAMENTE de las memorias.

Memorias disponibles:
- source: "materiales" → Stock y materiales de la empresa
- source: "eventos" → Eventos programados, etapas, fechas
- source: "informacion_interna" → Datos internos, ventas, proyecciones

Respondés siempre en JSON:
{
  "consulta": "qué buscaste",
  "resultados": [{"metadata": "...", "coincidencias": [...]}]
}

PROHIBIDO: adivinar, responder en texto libre, mezclar memorias."""


async def execute_tool(name: str, inputs: dict, db) -> str:
    if name == "search_memory":
        results = await search(db, query=inputs["query"], source=inputs["source"])
        return json.dumps({"source": inputs["source"], "results": results}, ensure_ascii=False)
    return json.dumps({"error": f"unknown tool: {name}"})


async def run(task: str, db) -> str:
    """Run the memory sub-agent for a given task string."""
    messages = [{"role": "user", "content": task}]

    while True:
        response = _anthropic().messages.create(
            model="claude-haiku-4-5-20251001",
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=MEMORY_TOOLS,
            max_tokens=2048,
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
                    result = await execute_tool(block.name, block.input, db)
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
