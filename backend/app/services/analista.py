"""
Analista IA — agente Anthropic con tool use sobre Supabase.
"""
import json
import logging
from datetime import datetime
import anthropic

from ..config import settings
from . import credentials
from .analytics import TOOLS, TOOL_FNS

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None
_client_key: str | None = None  # tracking de qué key se usó al crear el cliente


def _get_client() -> anthropic.Anthropic:
    """
    Obtiene cliente Anthropic. Si la API key cambió en la base de datos,
    recrea el cliente. Esto permite editar la credencial desde la UI sin reiniciar.
    """
    global _client, _client_key
    api_key = credentials.get("ANTHROPIC_API_KEY", settings.ANTHROPIC_API_KEY)
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY no configurada — agregala en Configuración → Credenciales")
    if _client is None or _client_key != api_key:
        _client = anthropic.Anthropic(api_key=api_key)
        _client_key = api_key
    return _client


def _get_model() -> str:
    return credentials.get("ANTHROPIC_MODEL", settings.ANTHROPIC_MODEL) or "claude-haiku-4-5-20251001"


SYSTEM_PROMPT = """Sos el ANALISTA DE DATOS de SONNER Sonido e Iluminación.

Tu trabajo es responder preguntas del equipo sobre la actividad del negocio:
contratos generados, ingresos, conversaciones del agente WhatsApp, contactos
más activos, leads del CRM, lista de bloqueo, etc.

Tenés acceso a estas herramientas (todas son de SOLO LECTURA contra Supabase):
- stats_contratos        → cantidad de contratos por período + facturado del mes
- listar_contratos       → últimos contratos con detalle
- stats_whatsapp         → mensajes in/out, tasa de respuesta, contactos únicos
- top_contactos_whatsapp → quiénes son los contactos más activos
- stats_blocklist        → cuántos números están bloqueados
- stats_crm              → distribución de leads por etapa + pipeline activo
- stats_chat_externo     → tamaño total de la memoria del agente externo

REGLAS:
1. Si te preguntan algo que requiere datos, USÁ una o más herramientas. Nunca inventes números.
2. Respondé en español rioplatense, conciso, con números formateados (ej: "$ 1.234.567").
3. Si la pregunta es ambigua, usá las herramientas con valores razonables (ej: dias=30) y aclará el período en la respuesta.
4. Si la respuesta requiere combinar varias métricas, encadená múltiples tool_use en una sola respuesta.
5. Cerrá con una frase corta sobre lo que más llama la atención (insight rápido) si tiene sentido.

Fecha actual: {fecha}
"""


def consultar(question: str) -> str:
    """
    Recibe una pregunta del usuario y devuelve la respuesta del Analista IA.
    Loop estándar de tool use con Anthropic.
    """
    client = _get_client()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    system = SYSTEM_PROMPT.format(fecha=fecha)

    messages: list[dict] = [{"role": "user", "content": question}]
    max_iters = 8

    for i in range(max_iters):
        resp = client.messages.create(
            model=_get_model(),
            max_tokens=2048,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        # Caso 1: el modelo terminó con texto
        if resp.stop_reason == "end_turn":
            for block in resp.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        # Caso 2: el modelo pide ejecutar tools
        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})

            tool_results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                fn = TOOL_FNS.get(block.name)
                if fn is None:
                    output = {"error": f"tool desconocida: {block.name}"}
                else:
                    try:
                        output = fn(**(block.input or {}))
                    except Exception as e:
                        logger.exception("Error en tool %s", block.name)
                        output = {"error": str(e)}
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(output, ensure_ascii=False, default=str),
                })
            messages.append({"role": "user", "content": tool_results})
            continue

        # Otros stop_reasons: cortar
        for block in resp.content:
            if hasattr(block, "text"):
                return block.text
        return "No pude completar la consulta."

    return "Tardé demasiado en analizar. Probá con una pregunta más específica."
