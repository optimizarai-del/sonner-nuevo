# Migración de los agentes de SONNER: n8n → 100% código

> Objetivo: sacar los agentes de n8n y correrlos dentro del backend FastAPI. n8n
> desaparece. Mismo comportamiento, más rápido, versionado en git y testeable.

Basado en el análisis de los 3 workflows exportados (2026-07-29):
`SONNER · PRINCIPAL EXTERNO`, `AGT-INTERNO-SONNER PAGINA`, `AGT-INTERNO-SONNER`.

---

## 🔴 ALERTA DE SEGURIDAD (hacer YA)

Los JSON exportados traen secretos **en texto plano** que quedaron expuestos. Hay que
**rotarlos** y moverlos a variables de entorno (nunca hardcodeados):
- **YCloud** `X-API-Key`: `775726e7...` (aparece en 3 nodos).
- **Telegram bot** token: `8232086208:AAE...` (nodo "Avisar a Gabi").
- **CSM key**: `da145b70...`  · **Memoria key**: `k7Qm2pR9...`.

En código todo esto va a `settings` desde `.env`. Ninguna key literal en el repo.

---

## 1. Los 3 sistemas (qué hace cada uno)

### A) AGENTE EXTERNO — "Tomi" (cliente final, WhatsApp/YCloud)  ★ prioridad
Webhook `POST /webhook/ycloude-sonner`. Pipeline:
1. **Kill-switch**: `SELECT activa FROM automatizacion_config WHERE id=1`. Si off → nada.
2. **Parseo YCloud** (`whatsappInboundMessage`): from(+tel), to(+nuestro nº), id, nombre
   (`customerProfile.name`), tipo. Según tipo:
   - `text` → texto directo.
   - `audio` → descarga (header `X-API-Key`) → Whisper (OpenAI) → `<audio>…</audio>`.
   - `image` → descarga → visión gpt-4o-mini → `<image>…</image>`.
   - otro → ignorar.
3. **Buffer** Redis por teléfono, `wait 15s`, dedupe (solo procesa el último mensaje).
4. **Blocklist**: match por últimos 10 dígitos → si está, corta.
5. **Mayorista**: `SELECT es_mayorista(tel)` → `tipo_cliente` (minorista|mayorista).
6. **Contexto de reunión**: `reuniones` (próxima 'agendada' futura, match 10 díg.) →
   `{tiene, fecha_hora_texto, titulo}` inyectado en el prompt.
7. **LLM**: Claude **Haiku 4.5** primario, **Gemini 2.5 Pro** fallback. Prompt **v3.5**.
   Tools: `Think`, `agente_calendario` (subagente GCal: disponibilidad de una fecha),
   `AGENTE DE SALONES` (subagente Sheets: `verificar_salon`), `Memoria` (HTTP→backend ✅).
   Salida JSON: `{respuesta, comando: mensaje_gabi|nada, mensaje_comando}`.
8. **Post-respuesta (4 ramas en paralelo)**:
   - Trocear (≤4 mensajes) → enviar YCloud `sendDirectly` (from=nuestro, to=cliente), wait 2s.
   - Si `comando=mensaje_gabi` → Telegram a Gabi (chat 6124095544) con el lead formateado.
   - LLM chain → `{nota,tipo_evento,lugar_evento,fecha_evento}` → `crm_registrar_interaccion(...)`.
   - CSM → `POST /api/csm/log` ✅.

### B) AGENTE INTERNO — gestión (equipo SONNER)
Mismo cerebro, dos canales:
- **PAGINA**: webhook `/sonner-pagina` (responde por el mismo webhook; sessionId web).
- **TELEGRAM**: bot `Sonner_Interno_Bot` (sessionId = chat.id). Trocea en ≤4 y manda c/1s.
LLM: Claude **Sonnet 4.5** + Gemini fallback. Buffer Redis `wait 25s`. Memoria Postgres
(`n8n_chat_histories`). Tools:
- `Agente de Memoria` (subagente) → 3 vector stores RW sobre `documents` (eventos /
  informacion_interna / materiales), retrieve-as-tool.
- `agente de calendario` (subagente) → **CRUD completo** GCal en 5 calendarios: Eventos
  Sonner, Tijereta, Cromo (lectura), Reuniones Gabi (personal). Crear/editar/mover/borrar/
  disponibilidad/encontrar.
- `AGENTE DE DJS` (subagente) → Google Sheets `FECHAS DJ SONNER` (leer/crear/actualizar).
Salida `{respuesta, comando: eventos|materiales|informacion|nada, contenido}`. Cuando
`comando≠nada`, **escribe** `contenido` en `documents` con ese `source` (embeddings OpenAI).
Anti-loop: reintenta ≤2 si la respuesta contiene "json/temperatura/comando/ejecutado".

---

## 2. Dependencias externas nuevas (lo que n8n resolvía)

| Dep | Para qué | Cómo en código |
|---|---|---|
| **YCloud API** | recibir/enviar WhatsApp (agente externo) | webhook + cliente REST `sendDirectly`; verificar `ycloud-signature` |
| **Redis** | buffer/debounce de mensajes | reusar Redis, o buffer en Postgres/in-memory |
| **Google Calendar API** | disponibilidad (externo) + CRUD 5 cal. (interno) | OAuth ya existe (Docs); sumar scope Calendar |
| **Google Sheets API** | salones (externo) + DJs (interno) | OAuth Sheets; ⚠️ 2 cuentas Google distintas (salones vs DJs) |
| **Telegram Bot API** | canal interno + aviso a Gabi | 2 bots: `Sonner_Interno_Bot` y el de avisos |
| **OpenAI Whisper + visión** | audio/imagen entrantes (externo) | ya hay `openai` en deps |
| **Postgres/Supabase RPC** | `es_mayorista`, `crm_registrar_interaccion`, `automatizacion_config`, `blocklist`, `reuniones` | vía supabase client (rpc + table), sin psycopg nuevo |

---

## 3. Arquitectura en código

```
backend/app/
  services/
    agente_core/           # motor reusable
      llm.py               # loop tool-calling Claude→Gemini/OpenAI + salida JSON estructurada
      tipos.py             # Tool, contrato de mensajes
      buffer.py            # debounce (Redis o fallback)
    agente_externo/        # Tomi (cliente, YCloud)  ★ Fase 1
      prompt_v35.txt · prompt.py
      orquestador.py
      canal_ycloud.py      # parse inbound + send outbound + firma
      preproceso.py        # automatizacion_config, blocklist, mayorista, audio/imagen
      contexto_reunion.py  # reuniones (Supabase)
      tools/ (memoria.py, calendario.py, salones.py)
      post/  (trocear.py, gabi_telegram.py, crm.py, csm.py)
    agente_interno/        # gestión (página + telegram)  ← Fase 2
      prompt.py · orquestador.py
      canal_telegram.py · canal_pagina.py
      tools/ (memoria_rw.py, calendario_crud.py, djs.py)
    historial.py           # ✅ n8n_chat_histories / external_chat_histories (param tabla)
  routers/
    wa_externo.py          # POST /api/wa/webhook (YCloud)
    interno_telegram.py    # POST /api/interno/telegram
    interno_pagina.py      # POST /api/interno/pagina
```

Historial: el externo usa `external_chat_histories`; los internos `n8n_chat_histories`.
Mismo formato LangChain → un solo módulo parametrizado por tabla.

---

## 4. Decisiones tomadas
- **Alcance:** primero el **AGENTE EXTERNO** (cliente) completo end-to-end. Después el interno.
- **Historial:** reusar tablas de n8n (`external_chat_histories` / `n8n_chat_histories`).
- **Postgres:** vía supabase client (rpc/table), sin sumar psycopg.

## 5. Orden de build (externo primero)

**Fase 0 — Núcleo** `agente_core/llm.py`: loop genérico tool-calling, Claude primario +
fallback (Gemini/OpenAI), salida JSON validada. Base de los 3 agentes.

**Fase 1 — Agente externo (Tomi):**
- 1a. Canal YCloud (parse inbound + send outbound + verificación de firma).
- 1b. Preproceso: kill-switch, blocklist, mayorista, buffer, audio/imagen.
- 1c. Contexto de reunión (Supabase).
- 1d. Tools: memoria (✅), calendario (GCal lectura de fecha), salones (Sheets lectura).
- 1e. Orquestador + prompt v3.5 + salida {respuesta,comando,mensaje_comando}.
- 1f. Post: trocear+enviar, aviso Gabi (Telegram), CRM, CSM.
- 1g. Endpoint de prueba `POST /api/agente/probar` para testear sin WhatsApp.

**Fase 2 — Agente interno (página + telegram):**
- 2a. Tools: memoria RW (documents), calendario CRUD (5 cal.), DJs (Sheets).
- 2b. Orquestador + salida {respuesta,comando,contenido} + escritura a `documents`.
- 2c. Canales: webhook página + bot Telegram (trocear ≤4).

**Fase 3 — Corte:** shadow mode → flip webhooks (YCloud, Telegram, página) al backend →
monitoreo → apagar workflows n8n.

## 6. Riesgos
- Superficie grande: 2 cerebros, ~6 subagentes/tools, 6 integraciones externas.
- 2 cuentas Google distintas (Sheets salones vs DJs) → 2 juegos de credenciales.
- Firma YCloud (`ycloud-signature`) y reintentos: el webhook debe responder 200 rápido.
- Paridad de buffer (15s externo / 25s interno) para no cambiar el tono.

## 7. Avance
- [x] Plan y arquitectura real de las 3.
- [x] `services/agente/historial.py` (formato LangChain; verificado con datos reales; parametrizado por tabla).
- [x] `agente_core/` (motor.py + tipos.py): loop tool-calling Claude→OpenAI. Verificado offline.
- [x] **Cerebro del agente externo (Tomi)**:
      - `agente_externo/prompt.py` (+ `prompt_v35.txt`): v3.5, placeholders resueltos. Verificado.
      - `agente_externo/herramientas.py`: memoria ✅ / calendario ⏳stub / salones ⏳stub / pensar.
      - `agente_externo/orquestador.py`: historial + prompt + motor + contrato {respuesta,comando,mensaje_comando} con fallback.
      - `routers/agente_externo.py`: `POST /api/agente/probar` (auth X-Memoria-Key). Registrado en main.
- [x] **Tools reales**: `tools_google.py` — calendario (GCal, disponibilidad de fecha) + salones (Sheets, apto/capacidad).
- [x] **Canal YCloud** `canal_ycloud.py`: parseo inbound + envío outbound + verificación de firma + descarga media.
- [x] **Media** `media.py`: audio→Whisper, imagen→visión gpt-4o-mini.
- [x] **Preproceso** `supabase_ops.py`: kill-switch, blocklist (últimos 10 díg.), mayorista (RPC), contexto reunión.
- [x] **Buffer** `buffer.py`: debounce en memoria (verificado: 3 msgs → 1 proceso).
- [x] **Post** `post.py`: trocear ≤4, enviar YCloud, avisar Gabi (Telegram), CRM (RPC), CSM.
- [x] **Flujo** `flujo.py` + webhook `routers/wa_externo.py` (`POST /api/wa/webhook`, 200 rápido + background).
- [ ] Deploy + prueba end-to-end contra WhatsApp real (requiere env + verificar caveats abajo).
- [ ] Agente interno (página + telegram) — Fase 2.

## 9. Config/env a setear (reusando los valores que ya existen)
En EasyPanel (env del backend) o en `app_settings` de Supabase:
- `YCLOUD_API_KEY` = la key de YCloud (la que estaba en el nodo HTTP).
- `TELEGRAM_BOT_TOKEN` = token del bot que avisa a Gabi.
- (opcional) `YCLOUD_WEBHOOK_SECRET` para verificar la firma; si no se setea, no se verifica.
- Ya con default correcto (no hace falta tocar): `GABI_TELEGRAM_CHAT_ID`, `GCAL_EVENTOS_ID`,
  `GSHEET_SALONES_ID`, `WA_BUFFER_SECONDS=15`. `ANTHROPIC_MODEL` ya es Haiku 4.5.

Apuntar el **webhook de YCloud** a: `https://backend-sonner.optimizar-ia.com/api/wa/webhook`.

## 10. Caveats a verificar en el deploy
- **Cuenta Google**: calendario y salones usan el OAuth de contratos (mismo refresh token).
  Si el calendario "Eventos Sonner" / el sheet "BASE DE DATOS SALONES" están en OTRA cuenta
  Google, hay que darle acceso a esa cuenta o cargar credenciales propias. Si falla, la tool
  degrada a "error/especial" y el agente deriva a Gabriel (comportamiento seguro).
- **CRM**: `crm_registrar_interaccion` se llama por RPC probando nombres de parámetros comunes.
  Si la firma real usa otros nombres, hay que ajustarlos (es best-effort; no rompe el flujo).
- **Buffer en memoria**: válido para 1 worker. Con varios workers, mover a Redis.

## 8. Qué falta de tu lado
1. **Rotar** los secretos expuestos (ver alerta arriba) y pasármelos por canal seguro / .env.
2. Confirmar scopes Google (Calendar + Sheets) sobre el OAuth actual, y las 2 cuentas de Sheets.
3. Confirmar si seguimos usando **Redis** (hay uno: "Redis Sonner") o migramos el buffer.
4. Guardar los 3 JSON en `n8n/workflows-export/` como fuente de verdad.
