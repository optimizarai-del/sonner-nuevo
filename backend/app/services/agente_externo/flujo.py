"""Flujo completo del agente externo: del webhook YCloud a la respuesta enviada.

Ata todas las piezas en el mismo orden que el workflow n8n `SONNER · PRINCIPAL EXTERNO`:

  recibir(inbound):
    1. kill-switch (automatizacion_config)           → si off, corta
    2. blocklist                                      → si bloqueado, corta
    3. media → texto (audio/imagen) o texto directo   → si tipo no soportado, corta
    4. buffer/debounce por teléfono
  procesar(tel, texto, meta):   (lo dispara el buffer)
    5. tipo_cliente (mayorista/minorista)
    6. contexto de reunión
    7. orquestador (cerebro v3.5)  → {respuesta, comando, mensaje_comando}
    8. post: enviar por YCloud + (si mensaje_gabi) avisar a Gabi + CRM + CSM
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from ...config import settings
from . import buffer, media, post, supabase_ops
from . import orquestador

log = logging.getLogger("agente_externo.flujo")


def recibir(inbound: dict[str, Any]) -> None:
    """Punto de entrada desde el webhook (corre en background)."""
    tel = inbound.get("usuario")
    if not tel:
        return
    # 1. kill-switch
    if not supabase_ops.automatizacion_activa():
        log.info("automatización OFF — ignoro mensaje de %s", tel)
        return
    # 2. blocklist
    if supabase_ops.esta_bloqueado(tel):
        log.info("contacto bloqueado %s — ignoro", tel)
        return
    # 3. media → texto
    texto = media.a_texto(inbound)
    if texto is None:
        log.info("tipo de mensaje no soportado (%s) de %s — ignoro", inbound.get("tipo"), tel)
        return
    if not texto.strip():
        return
    # 4. buffer/debounce
    buffer.encolar(tel, texto, inbound, _procesar_callback, settings.WA_BUFFER_SECONDS)


def _procesar_callback(clave: str, texto: str, meta: dict[str, Any]) -> None:
    procesar(clave, texto, meta)


def procesar(tel: str, texto: str, inbound: dict[str, Any]) -> None:
    """Corre el cerebro + post-proceso para el texto ya buffizado."""
    nombre = inbound.get("nombre") or tel
    tipo = supabase_ops.tipo_cliente(tel)
    reunion = supabase_ops.contexto_reunion(tel)

    contrato = orquestador.responder(
        texto=texto, telefono=tel, nombre=nombre,
        tipo_cliente=tipo, reunion_cliente=reunion, persistir=True,
    )
    respuesta = contrato.get("respuesta") or ""
    comando = contrato.get("comando")
    mensaje_comando = contrato.get("mensaje_comando")

    # 8. post-proceso
    if respuesta:
        post.enviar_respuesta(inbound, respuesta)
    if comando == "mensaje_gabi":
        post.avisar_gabi(inbound, mensaje_comando)
    # CRM + CSM (best-effort, no bloquean la respuesta ya enviada)
    post.registrar_crm(inbound, texto, respuesta)
    post.registrar_csm(inbound, texto, respuesta, tipo)


def recibir_async(inbound: dict[str, Any]) -> None:
    """Lanza recibir() en un thread daemon para devolver el webhook al instante."""
    t = threading.Thread(target=recibir, args=(inbound,), daemon=True)
    t.start()
