import json
import os
import re
from datetime import datetime
from typing import Optional
import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import ConversationMessage
from ..core import vector_store

PROHIBITED_WORDS = ["json", "temperatura", "comando", "ejecutado"]

_client = None


def _anthropic():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def _contains_internal_leak(text: str) -> bool:
    """Replica el filtro JS de n8n: detecta si la respuesta filtró datos internos."""
    lower = text.lower()
    return any(word in lower for word in PROHIBITED_WORDS)


def _md_to_html(text: str) -> str:
    """Convierte markdown básico a HTML para Telegram (parse_mode='HTML')."""
    import html as _html
    # Escapar caracteres HTML primero
    text = _html.escape(text)
    # **negrita** → <b>negrita</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text, flags=re.DOTALL)
    # *itálica* o _itálica_ → <i>itálica</i>
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text, flags=re.DOTALL)
    text = re.sub(r"_(.+?)_", r"<i>\1</i>", text, flags=re.DOTALL)
    # `código` → <code>código</code>
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def _split_into_messages(text: str, max_parts: int = 4) -> list[str]:
    """
    Divide el texto en máximo max_parts mensajes por oraciones.
    Convierte markdown a HTML para renderizado en Telegram.
    """
    text = _md_to_html(text.strip())
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s for s in sentences if s]
    if len(sentences) <= max_parts:
        return sentences
    # Agrupar en exactamente max_parts
    chunk_size = len(sentences) // max_parts
    remainder = len(sentences) % max_parts
    groups = []
    i = 0
    for g in range(max_parts):
        end = i + chunk_size + (1 if g < remainder else 0)
        groups.append(" ".join(sentences[i:end]))
        i = end
    return groups


class BaseAgent:
    def __init__(
        self,
        session_key: str,
        channel: str,
        system_prompt: str,
        tools: list,
        model: str = "claude-haiku-4-5-20251001",
        max_history: int = 20,
    ):
        self.session_key = session_key
        self.channel = channel
        self.system_prompt = system_prompt
        self.tools = tools
        self.model = model
        self.max_history = max_history

    async def _load_history(self, db: AsyncSession) -> list[dict]:
        stmt = (
            select(ConversationMessage)
            .where(
                ConversationMessage.session_key == self.session_key,
                ConversationMessage.channel == self.channel,
            )
            .order_by(ConversationMessage.created_at.desc())
            .limit(self.max_history)
        )
        result = await db.execute(stmt)
        msgs = list(reversed(result.scalars().all()))
        return [{"role": m.role, "content": m.content} for m in msgs]

    async def _save_message(self, db: AsyncSession, role: str, content: str) -> None:
        msg = ConversationMessage(
            session_key=self.session_key,
            channel=self.channel,
            role=role,
            content=content,
        )
        db.add(msg)
        await db.commit()

    async def _execute_tool(self, name: str, inputs: dict, db: AsyncSession) -> str:
        raise NotImplementedError

    async def run(self, user_message: str, db: AsyncSession) -> dict:
        history = await self._load_history(db)
        await self._save_message(db, "user", user_message)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        system = self.system_prompt.replace("{current_date}", now)

        messages = history + [{"role": "user", "content": user_message}]
        output = None
        attempts = 0

        while attempts < 3:
            attempts += 1
            while True:
                response = _anthropic().messages.create(
                    model=self.model,
                    system=system,
                    messages=messages,
                    tools=self.tools,
                    max_tokens=4096,
                )

                if response.stop_reason == "end_turn":
                    for block in response.content:
                        if hasattr(block, "text"):
                            try:
                                output = json.loads(block.text)
                            except json.JSONDecodeError:
                                output = {"respuesta": block.text, "comando": "nada", "contenido": "nada"}
                    break

                if response.stop_reason == "tool_use":
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            result = await self._execute_tool(block.name, block.input, db)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            })
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})
                else:
                    break

            if output and not _contains_internal_leak(output.get("respuesta", "")):
                break
            if output:
                messages.append({
                    "role": "user",
                    "content": "Tu respuesta anterior tiene palabras internas. Reformulá sin mencionar: json, temperatura, comando ni ejecutado.",
                })

        if not output:
            output = {"respuesta": "Lo siento, no pude procesar tu consulta en este momento.", "comando": "nada", "contenido": "nada"}

        respuesta = output.get("respuesta", "")
        comando = output.get("comando", "nada")
        contenido = output.get("contenido", "nada")

        # Guardar en vector store si el agente decide almacenar algo
        if comando and comando != "nada" and contenido and contenido != "nada":
            await vector_store.insert(db, content=str(contenido), source=comando)

        await self._save_message(db, "assistant", respuesta)

        return {
            "respuesta": respuesta,
            "messages": _split_into_messages(respuesta) if respuesta else ["Lo siento, no pude procesar tu consulta."],
            "comando": comando,
            "contenido": contenido,
        }
