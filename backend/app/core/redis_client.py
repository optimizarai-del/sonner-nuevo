import os
import asyncio
from typing import Optional
import redis.asyncio as aioredis

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        if url == "memory://":
            try:
                import fakeredis.aioredis as fake_aioredis
                _redis = fake_aioredis.FakeRedis(decode_responses=True)
            except ImportError:
                raise RuntimeError("Install fakeredis: pip install fakeredis")
        else:
            _redis = aioredis.from_url(url, decode_responses=True)
    return _redis


async def push_message(key: str, message: str) -> None:
    r = await get_redis()
    await r.rpush(key, message)


async def get_all_messages(key: str) -> list[str]:
    r = await get_redis()
    return await r.lrange(key, 0, -1)


async def get_last_message(key: str) -> Optional[str]:
    r = await get_redis()
    msgs = await r.lrange(key, -1, -1)
    return msgs[0] if msgs else None


async def delete_key(key: str) -> None:
    r = await get_redis()
    await r.delete(key)


AUTOMATION_KEY = "sonner:auto_externo"


async def get_automation_state() -> bool:
    """True = ON (activa), False = OFF (pausada). Default ON."""
    r = await get_redis()
    val = await r.get(AUTOMATION_KEY)
    return val != "OFF"


async def toggle_automation() -> str:
    """Invierte el estado y devuelve el nuevo ('ON' | 'OFF')."""
    r = await get_redis()
    current = await get_automation_state()
    new_state = "OFF" if current else "ON"
    await r.set(AUTOMATION_KEY, new_state)
    return new_state


async def debounce_process(key: str, message: str, delay_seconds: int) -> Optional[list[str]]:
    """
    n8n pattern: push → wait → get last → if still ours → delete → return all
    Returns combined messages if this was the last one, None if superseded.
    """
    await push_message(key, message)
    await asyncio.sleep(delay_seconds)

    last = await get_last_message(key)
    if last != message:
        return None

    all_messages = await get_all_messages(key)
    await delete_key(key)
    return all_messages
