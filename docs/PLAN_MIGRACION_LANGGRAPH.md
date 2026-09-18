# Plan de migración SONNER · n8n → agentes Python (LangChain + LangGraph)

**Estado:** propuesta, pendiente de aprobación
**Fecha:** 2026-09-17
**Repo:** `optimizarai-del/sonner-nuevo` · rama base `agentes-sonner`
**Objetivo final:** que toda la lógica de agentes viva en Python, que n8n quede reducido a dos workflows tontos (webhook de entrada y envío de salida) y que el sistema se pueda operar, monitorear y depurar sin abrir n8n.

---

## 0. Resumen ejecutivo

Hoy SONNER tiene **6 workflows en n8n** (~200 nodos en total) y **un agente externo ya migrado a Python** con un loop de tool-calling escrito a mano. Lo que falta es: el agente interno (Telegram + página), todo el toolbelt de calendarios y planillas, los procesos no-IA (contratos, keep-alive, error handler, ingesta vectorial) y una capa de observabilidad seria.

Este plan propone:

1. **Un solo core de agentes en LangGraph**, con dos grafos (externo / interno) construidos sobre los mismos nodos y el mismo toolbelt.
2. **Convertir los subagentes LLM en herramientas deterministas.** Hoy hay 5 LLMs anidados (principal → calendario → salones → DJs → memoria). Las reglas de esos subagentes son fijas y se pueden escribir en Python. Queda **un solo LLM en el loop**.
3. **Checkpointer en Postgres (Supabase)** como memoria de conversación y de ejecución. Esto elimina el buffer en memoria que hoy obliga a correr con `--workers 1`.
4. **Observabilidad de primera clase desde la Fase 1**, no al final: cada corrida persistida, métricas Prometheus, healthchecks reales, alertas deduplicadas y un panel dentro de la plataforma que ya existe.
5. **Cutover gradual con shadow mode y rollback de un solo switch**, no un big-bang.

**Esfuerzo estimado:** 9 fases, ~28–34 sesiones de trabajo. Las fases 0–2 son las que desbloquean todo lo demás.

---

## 1. Punto de partida (auditoría, 2026-09-17)

### 1.1 Lo que hay en n8n

| Workflow | Nodos | Trigger | Tiene IA | Complejidad de migración |
|---|---|---|---|---|
| `SONNER · PRINICPAL EXTERNO` | 66 | Webhook `/ycloude-sonner` | Sí (4 LLM) | **Alta** |
| `AGT-INTERNO-SONNER` | 63 | Telegram Trigger | Sí (4 LLM) | **Alta** |
| `AGT-INTERNO-SONNER PAGINA` | 61 | Webhook `/sonner-pagina` | Sí (4 LLM) | **Media** (clon del anterior) |
| `contratos sonner` | 8 | Webhook | No | Baja-Media |
| `error trigger sonner` | 3 | Error Trigger | No | Baja |
| `Supabase keep-alive` | 2 | Cron diario | No | Baja |

**Ninguno de los 3 workflows grandes está versionado en el repo.** `n8n/workflows-export/` está vacío y `.gitignore` ignora `*.json` global. Las únicas copias son exports sueltos en `Downloads/` con sufijos `(1)`…`(4)`. Esto es un riesgo operativo: hoy no hay forma de reconstruir producción si alguien rompe un workflow.

### 1.2 Lo que ya está en Python

- `backend/app/agente_main.py` — app standalone del agente externo, corre en EasyPanel (`n8n-nuevo-agente-sonner.3buyoj.easypanel.host`), **1 worker** porque el buffer de debounce es un `threading.Timer` en memoria.
- `services/agente_core/motor.py` — loop de tool-calling propio, driver Anthropic con fallback a OpenAI, reintentos con backoff, `max_iter=6`.
- `services/agente_externo/` — orquestador v3.5, prompt, herramientas (`memoria`, `calendario`, `salones`, `pensar`), degradación a handoff.
- `POST /api/agente/n8n` — el relay que n8n llama hoy, devuelve `{output:{respuesta,comando,mensaje_comando}}`.

**No hay LangChain ni LangGraph en el proyecto** (`requirements.txt` solo trae `anthropic` y `openai`). **No hay tests.** La observabilidad es logging de texto plano; el `_meta` de cada corrida (proveedor, modelo, tiempo, intentos, si degradó) se calcula y **se tira**.

### 1.3 Hallazgos de seguridad (bloquean el arranque)

| # | Hallazgo | Dónde | Acción |
|---|---|---|---|
| S1 | Token completo del bot de Telegram embebido en la URL de un nodo HTTP | `Downloads/SONNER · PRINICPAL EXTERNO*.json` y `AGT-INTERNO-SONNER*.json` | **Rotar el token** y pasar a credencial de n8n / env |
| S2 | Literales en líneas de `SECRET`/`KEY`/`TOKEN`/`CLIENT_ID` como defaults | `backend/app/config.py` L9, L52, L62, L63, L90, L91 | Auditar uno por uno, rotar los que sean secretos reales, dejar `os.getenv(...)` sin default |
| S3 | IDs de recursos privados en claro (plantilla de contrato, carpeta de Drive, sheets de salones y DJs) | JSONs de n8n | Parametrizar por env en la versión Python |
| S4 | Emails personales hardcodeados | `error trigger sonner`, `contratos sonner` | Parametrizar por env |

> **Nada de esto se toca en el mismo commit que la migración.** Fase 0 es su propio PR, para poder auditarlo solo.

---

## 2. Arquitectura objetivo

### 2.1 Reparto de responsabilidades

```
┌─────────────┐   POST webhook    ┌──────────────────────────────────────┐
│   YCloud    │──────────────────▶│  n8n: SONNER-IN  (3 nodos)           │
│  WhatsApp   │                   │  Webhook → HTTP POST → Respond 200   │
└─────────────┘                   └──────────────┬───────────────────────┘
┌─────────────┐                                  │
│  Telegram   │─────────────────────────────────▶│  (mismo patrón)
└─────────────┘                                  │
┌─────────────┐                                  │
│  Página web │─────────────────────────────────▶│  (síncrono, Respond con la respuesta)
└─────────────┘                                  ▼
                              ┌─────────────────────────────────────────────┐
                              │        sonner-agentes  (FastAPI)            │
                              │                                             │
                              │  transports/  →  graphs/  →  tools/         │
                              │       ▲                          │          │
                              │       │         obs/  (runs, métricas,      │
                              │       │               alertas, health)      │
                              │       │                          │          │
                              └───────┼──────────────────────────┼──────────┘
                                      │                          │
                     ┌────────────────┴─────┐      ┌─────────────▼──────────┐
                     │ n8n: SONNER-OUT      │      │ Supabase (Postgres +   │
                     │ Webhook → send       │      │ pgvector) · Redis ·    │
                     │ (YCloud / Telegram)  │      │ Google APIs            │
                     └──────────────────────┘      └────────────────────────┘
```

**n8n conserva exactamente dos cosas**, y ninguna tiene lógica de negocio:

- **`SONNER-IN`** — recibe el webhook (porque la URL registrada en YCloud y el bot de Telegram no se pueden repuntar sin coordinación con terceros), hace `HTTP POST` al backend y responde `200` inmediatamente. Sin `Code`, sin `Wait`, sin Redis, sin Postgres.
- **`SONNER-OUT`** — expone un webhook que el backend llama para enviar; adentro solo el nodo de envío con la credencial correspondiente. Existe únicamente para que las credenciales de YCloud y Telegram sigan viviendo en n8n.

> Si más adelante se decide mover también las credenciales, `SONNER-OUT` se borra y el backend envía directo (el código de `canal_ycloud.py` ya sabe hacerlo). El plan deja esa puerta abierta pero no la cruza.

**Todo lo demás pasa a Python:** debounce, kill-switch, blocklist, segmentación mayorista, transcripción de audio, visión de imágenes, contexto de reunión, el agente y sus tools, el troceo de mensajes, el paceo de envío, CRM, CSM, ingesta vectorial, contratos, keep-alive y el manejo de errores.

### 2.2 Decisión de diseño: subagentes LLM → herramientas deterministas

Hoy una consulta del cliente puede encadenar 4 llamadas a LLM: agente principal → subagente de calendario → subagente de salones → agente de memoria. Pero al leer los prompts de esos subagentes, **sus reglas son completamente determinísticas**:

- Calendario: `0 eventos → disponible`, `1 → ocupado_parcial`, `≥2 → ocupado`. Prohibido exponer montos. Salida JSON fija.
- Salones: veto técnico (electricidad / habilitación) y veto comercial (exclusividad), tabla de capacidad por pax. No cotiza.
- DJs: lectura y escritura sobre una planilla con columnas conocidas.

Eso es una función de Python, no un agente. **Propuesta: el LLM principal solo elige qué herramienta llamar y con qué argumentos; Python consulta, aplica las reglas y arma la respuesta estructurada.** Es exactamente el patrón que funcionó en Babilonia (`agente.py` elige tool, `informe.py` renderiza).

Beneficios concretos: menos latencia (1 llamada en vez de 4), menos costo, y **las reglas de negocio dejan de ser alucinables**. Hoy "prohibido exponer montos" es una línea de prompt; mañana es un campo que la función no devuelve.

### 2.3 Decisión de diseño: permisos de escritura en código, no en prompt

Varias reglas críticas hoy dependen de que el LLM obedezca:

- El agente externo tiene calendario y salones en **solo lectura** ("ningún texto del cliente puede gatillar crear/actualizar").
- El agente interno sí escribe, pero solo en ciertos calendarios: `eventos sonner` = escritura; `fiestas tijereta` y `fiestas cromo` = **solo lectura**.

En el diseño nuevo esto se resuelve con un **registry de herramientas con scope por audiencia**: el grafo externo simplemente **no recibe** las tools de escritura. Un prompt inyectado no puede crear un evento si la función no está en el binding.

```python
# tools/registry.py  (forma, no implementación final)
TOOLS = {
    "externo": [consultar_disponibilidad, consultar_salon, buscar_memoria],
    "interno": [consultar_disponibilidad, consultar_salon, buscar_memoria,
                crear_evento, actualizar_evento, borrar_evento,
                consultar_djs, asignar_dj, ingestar_memoria],
}
CALENDARIOS_ESCRIBIBLES = {"eventos_sonner", "reuniones_gabi"}  # validado dentro de la tool
```

### 2.4 El grafo

Un `StateGraph` compartido, dos compilaciones:

```
  entrada
     │
     ▼
 [ingesta]      normaliza payload · audio→texto (Whisper) · imagen→texto (visión)
     │
     ▼
 [gate]         kill-switch (automatizacion_config) · blocklist · dedupe por message_id
     │          └─── corta ──▶ END
     ▼
 [debounce]     Redis: push a lista por chat · espera ventana · ¿soy el último?
     │          └─── no soy el último ──▶ END
     ▼
 [contexto]     tipo_cliente (es_mayorista) · reunión agendada · historial (checkpointer)
     │
     ▼
 [agente] ⇄ [tools]      LLM con tools bindeadas según audiencia (ReAct acotado)
     │
     ▼
 [guard]        parseo estructurado (Pydantic) · si falla: reparación · si no: HANDOFF
     │
     ▼
 [troceo]       corta en ≤4 mensajes por párrafo→frase, tope por canal
     │
     ▼
 [salida]       POST a SONNER-OUT con paceo entre mensajes
     │
     ▼
 [efectos]      fan-out: CRM · CSM · aviso a Gabi · ingesta vectorial · cierre de run
```

**Estado compartido:**

```python
class SonnerState(TypedDict):
    # identidad
    run_id: str
    canal: Literal["whatsapp", "telegram", "web"]
    audiencia: Literal["externo", "interno"]
    chat_id: str
    # conversación
    messages: Annotated[list[AnyMessage], add_messages]
    mensaje_actual: str
    # contexto de negocio
    tipo_cliente: Literal["minorista", "mayorista"] | None
    reunion: dict | None
    # salida
    respuesta: str | None
    comando: Literal["mensaje_gabi", "nada"] | None
    mensaje_comando: str | None
    fragmentos: list[str]
    # control
    degradado: bool
    motivo_corte: str | None
    traza: list[dict]
```

**Checkpointer:** `AsyncPostgresSaver` sobre Supabase, `thread_id = f"{canal}:{chat_id}"`. Esto reemplaza al `Postgres Chat Memory` de n8n **y** al buffer en memoria. Consecuencia directa: el servicio deja de estar atado a `--workers 1`.

> Durante la transición se mantiene escritura dual a `external_chat_histories` / `n8n_chat_histories` para no romper nada que hoy las lea. Se retiran en Fase 9.

### 2.5 Estructura de código propuesta

```
backend/app/
  agents/
    state.py              # SonnerState + reducers
    llm.py                # ChatAnthropic + fallback ChatOpenAI, retries, timeouts
    graphs/
      builder.py          # fábrica compartida de nodos
      externo.py          # compilación audiencia=externo
      interno.py          # compilación audiencia=interno
    nodes/
      ingesta.py  gate.py  debounce.py  contexto.py
      agente.py   guard.py  troceo.py   salida.py  efectos.py
    tools/
      registry.py         # scope por audiencia + permisos
      calendario.py  salones.py  djs.py  memoria.py  crm.py
    prompts/
      externo_v4.md  interno_v4.md  loader.py
  obs/
    logging.py            # structlog JSON + correlación por run_id
    runs.py               # persistencia agent_runs / agent_steps
    metrics.py            # Prometheus
    alertas.py            # dedupe por firma + Telegram
    health.py             # /health, /health/ready, /health/deps
  transports/
    ycloud.py  telegram.py  web.py
  jobs/
    scheduler.py  keepalive.py  watchdog.py  digest.py
  services/
    contratos_docs.py     # ex-workflow "contratos sonner"
```

### 2.6 Dependencias nuevas

```
langgraph                        langchain-core
langchain-anthropic              langchain-openai
langgraph-checkpoint-postgres    redis
structlog                        prometheus-fastapi-instrumentator
apscheduler                      tenacity
pytest  pytest-asyncio  respx    # tests
```

---

## 3. Sistema de monitoreo (dentro del código)

Requisito explícito: el monitoreo es parte del sistema, no una herramienta externa. Se construye en la Fase 1 y se completa en la Fase 6.

### 3.1 Tablas nuevas en Supabase

| Tabla | Para qué |
|---|---|
| `agent_runs` | una fila por corrida: `run_id`, canal, audiencia, `chat_id`, entrada, respuesta, comando, modelo, proveedor, tokens in/out, costo estimado, `latencia_ms`, `degradado`, `motivo_corte`, `ok` |
| `agent_steps` | una fila por paso del grafo: `run_id`, nodo, tool, args (redactados), resultado truncado, `duracion_ms`, error |
| `agent_errors` | errores agregados por **firma** (hash de tipo+mensaje+nodo): `count`, `first_seen`, `last_seen`, `ultimo_run_id` |
| `agent_alerts` | estado de rate-limit por firma, para no spamear Telegram |
| `agent_golden_cases` | casos de referencia para la suite de regresión (ver Fase 7) |

`agent_steps` se escribe mediante un **callback de LangGraph**, no ensuciando cada nodo con `INSERT`s.

### 3.2 Métricas Prometheus (`GET /metrics`)

```
sonner_mensajes_total{canal,audiencia}
sonner_respuestas_total{canal,resultado}        # ok | handoff | cortado
sonner_latencia_segundos{canal}                 # histograma
sonner_llm_llamadas_total{proveedor,modelo,resultado}
sonner_llm_fallback_total{de,a}
sonner_tool_llamadas_total{tool,resultado}
sonner_tokens_total{proveedor,tipo}
sonner_costo_usd_total{proveedor}
sonner_debounce_descartados_total
sonner_handoffs_total{motivo}
```

### 3.3 Healthchecks

- `GET /health` — liveness, sin dependencias, responde siempre.
- `GET /health/ready` — `503` si Supabase, Redis, la key del LLM o el refresh token de Google no están sanos. Es el que apunta EasyPanel.
- `GET /health/deps` — detalle por dependencia con latencia, para debug.

### 3.4 Alertas

Reemplaza al workflow `error trigger sonner`. Regla: **hash de la firma del error → dedupe → Telegram con rate-limit por ventana** (`SONNER_ALERT_WINDOW_SECONDS`, default 600). Fail-safe: si el alertador falla, se loguea y nunca tumba la corrida.

Se alerta por: circuito abierto de LLM o Supabase, tasa de handoff sobre umbral, corridas trabadas (>90s sin cerrar), `ready` en rojo, y fallo de refresh del token de Google.

### 3.5 Panel `/admin/monitor`

Página nueva en el frontend React que ya existe. Lee `agent_runs`:

- Fila de KPIs: mensajes hoy, tasa de handoff, latencia p50/p95, costo del día, errores abiertos.
- Timeline de corridas con filtro por canal / audiencia / estado.
- Detalle de corrida: entrada, pasos del grafo, tools con argumentos, respuesta final, `_meta`.
- Toggle del kill-switch y ABM de la blocklist (hoy se editan a mano en Supabase).

### 3.6 Trazas

`structlog` en JSON con `run_id` propagado. **LangSmith queda como opcional detrás de `LANGSMITH_TRACING=0|1`** — útil para depurar el grafo en desarrollo, pero el sistema no depende de él y en producción puede quedar apagado.

---

## 4. Fases

> Cada fase es un PR. Ninguna fase se mergea sin su criterio de aceptación verificado.

### Fase 0 — Seguridad y red de contención · 2 sesiones

**Bloqueante. No se escribe código de agentes antes de esto.**

- Rotar el token del bot de Telegram (S1). Verificar que ningún flujo quedó colgado.
- Auditar `config.py` L9/52/62/63/90/91, rotar lo que sea secreto real, quitar los defaults (S2).
- Exportar los 6 workflows de n8n **en su estado actual de producción** y versionarlos en `n8n/workflows-export/`, con un `.gitignore` que deje de ignorarlos pero **con los valores scrubbeados** por un script (`scripts/scrub_n8n_export.py`).
- Documentar en `docs/RUNBOOK.md` cómo se restaura producción desde esos exports.
- Congelar el inventario funcional (este documento, §1.1) como línea base de paridad.

**Aceptación:** los 6 workflows están en el repo, sin secretos, y se pueden reimportar en una instancia limpia de n8n.

---

### Fase 1 — Fundaciones: esqueleto LangGraph + observabilidad · 4 sesiones

- Agregar dependencias; `agents/state.py`, `agents/llm.py` con `ChatAnthropic` + fallback `ChatOpenAI` (portar la lógica de reintentos que ya existe en `motor.py`).
- Migraciones SQL de las 5 tablas de §3.1 + tablas del checkpointer, en `db/migrations/` **versionadas** (hoy `db/` es SQL suelto).
- `obs/` completo: logging estructurado, `runs.py`, `metrics.py`, `alertas.py`, `health.py`.
- Grafo "hola mundo" de 3 nodos que ya escribe `agent_runs` y expone métricas, para validar la instrumentación antes de que haya lógica real.

**Aceptación:** `/health/ready` responde correctamente con y sin dependencias caídas; una corrida de prueba queda persistida en `agent_runs` con sus `agent_steps`; `/metrics` expone los contadores.

---

### Fase 2 — Agente externo sobre LangGraph · 5 sesiones

Re-plataformar lo que **ya funciona** en `agente_externo/`. No es reescribir de cero: es mover el loop propio a `StateGraph` y ganar checkpointer, trazas y multi-worker.

- Nodos `ingesta` (portar `media.py`), `gate` (kill-switch + blocklist + dedupe por `message_id`), `debounce` (Redis, reemplaza el `threading.Timer`), `contexto` (`es_mayorista` + reunión), `agente`, `guard`, `troceo`, `salida`, `efectos` (CRM + CSM + aviso a Gabi).
- Prompt v3.5 portado tal cual a `prompts/externo_v4.md` — **sin cambios de contenido en esta fase**, para que cualquier diferencia de comportamiento sea atribuible a la plataforma y no al prompt.
- Mantener el endpoint `POST /api/agente/n8n` con **el mismo contrato de salida**, ahora servido por el grafo.
- Quitar `--workers 1` de `Dockerfile.agente`.

**Aceptación:** con el mismo set de mensajes de entrada, el grafo produce respuestas equivalentes al agente actual; corre con 2+ workers sin perder mensajes; el debounce funciona entre workers distintos.

---

### Fase 3 — Toolbelt determinista · 4 sesiones

- `tools/calendario.py` — consultas de disponibilidad con los umbrales fijos; 11 operaciones, las de escritura validando contra `CALENDARIOS_ESCRIBIBLES`.
- `tools/salones.py` — lectura de la planilla + vetos técnico y comercial en Python.
- `tools/djs.py` — lectura/escritura de la planilla de DJs.
- `tools/memoria.py` — búsqueda pgvector sobre los 3 stores (Eventos, Información Interna, Materiales) con filtro por store.
- `tools/registry.py` — scope por audiencia (§2.3).
- **Retirar los 3 subagentes LLM.**

**Aceptación:** tests unitarios de las reglas de umbral y veto sin tocar la red; el grafo externo no tiene ninguna tool de escritura bindeada; la latencia media baja respecto de Fase 2.

---

### Fase 4 — Agente interno (Telegram + página) · 5 sesiones

Los dos workflows internos son **el mismo agente con distinto transporte**. En Python es un grafo y dos adaptadores.

- `graphs/interno.py` con el toolbelt completo.
- `transports/telegram.py` (asíncrono, respuesta por `SONNER-OUT`) y `transports/web.py` (síncrono, responde en la misma request).
- Nodo de **ingesta vectorial** para el switch de comandos `eventos` / `informacion` / `materiales` (split + embeddings + upsert).
- **El anti-loop de n8n no se porta.** Ese hack (detectar `json|temperatura|comando|ejecutado` en la salida y reintentar hasta 2 veces con estado estático) existe porque el output parser de n8n a veces filtraba JSON crudo al usuario. Con salida estructurada de Pydantic el problema no puede ocurrir; si ocurre, es el nodo `guard` el que lo atrapa.

**Aceptación:** paridad funcional con los dos workflows internos verificada caso por caso contra el inventario de Fase 0; la ingesta vectorial produce embeddings consultables.

---

### Fase 5 — Procesos no-IA · 3 sesiones

- `services/contratos_docs.py` — copia de plantilla en Drive, `replaceAll` de variables, export a PDF, subida, permiso público, respuesta con el link, mail a Gabriel. Endpoint `POST /api/contratos/generar`. Emails e IDs de Drive por env (S3, S4).
- `jobs/keepalive.py` — el cron de Supabase, vía APScheduler dentro del proceso (o se deja el GitHub Action que ya existe; elegir uno, no los dos).
- `jobs/watchdog.py` — corridas trabadas, salud del refresh token de Google, tasa de handoff.
- `jobs/digest.py` — resumen diario a Telegram: mensajes, handoffs, costo, errores nuevos.
- El error handler global ya quedó cubierto por `obs/alertas.py` en Fase 1.

**Aceptación:** un contrato generado end-to-end idéntico al de n8n; el digest diario llega.

---

### Fase 6 — Panel de monitoreo · 3 sesiones

Implementar `/admin/monitor` según §3.5, con el toggle del kill-switch y el ABM de blocklist.

**Aceptación:** se puede diagnosticar una conversación fallida de punta a punta sin abrir Supabase ni los logs de EasyPanel.

---

### Fase 7 — Tests y QA · 4 sesiones

Hoy el proyecto **no tiene un solo test**. Esto es lo que permite hacer el cutover sin miedo.

- **Offline (sin red):** troceo, umbrales de calendario, vetos de salones, blocklist por últimos 10 dígitos, parseo de la salida, scope del registry, normalización de payloads de YCloud/Telegram.
- **Con dobles:** `respx` para mockear Google, YCloud y los LLM; el grafo completo corre contra dobles.
- **Golden set:** ~40 conversaciones reales tomadas de `csm_analisis` y `external_chat_histories` en `agent_golden_cases`. Runner que las pasa por el grafo y compara contra la respuesta esperada con un juez LLM para lo semántico y asserts duros para lo estructural (comando correcto, no exponer montos, no inventar fechas).
- **Shadow mode:** flag `SONNER_SHADOW=1` — `SONNER-IN` llama al grafo nuevo **y** al camino viejo, se responde con el viejo y se registran ambas salidas en `agent_runs` para diferencia manual. Correr una semana.
- CI en GitHub Actions: tests offline + lint en cada PR.

**Aceptación:** suite verde en CI; una semana de shadow mode sin divergencias de comportamiento inaceptables.

---

### Fase 8 — Cutover a EasyPanel · 2 sesiones

**Servicios en EasyPanel:**

| Servicio | Imagen | Notas |
|---|---|---|
| `sonner-agentes` | `backend/Dockerfile.agente` | el grafo; ahora con `WEB_CONCURRENCY=2+` |
| `sonner-backend` | `backend/Dockerfile` | la plataforma (contratos, analista, CSM, memoria) |
| `sonner-frontend` | `frontend/Dockerfile` | + la página `/admin/monitor` |
| `sonner-redis` | `redis:7-alpine` | debounce y locks |

- Healthcheck de EasyPanel apuntando a `/health/ready`.
- Cargar el set completo de variables de entorno (§5).
- Borrar el `Dockerfile` huérfano de la raíz (`node:18` + `server.js` inexistente).
- Sincronizar o borrar `docker-compose.yml`, que hoy declara variables que el código no usa.

**Cutover:**

1. Desplegar con `SONNER_SHADOW=1`, verificar una semana (Fase 7).
2. **Canario:** `SONNER-IN` rutea al grafo nuevo solo para una lista de teléfonos de prueba (`SONNER_CANARY_NUMEROS`). 2–3 días.
3. **100%:** el switch pasa a todos.
4. Los workflows viejos quedan **desactivados pero intactos 2 semanas**.
5. Recién ahí se reemplazan por `SONNER-IN` / `SONNER-OUT` definitivos.

**Rollback:** una variable de entorno en n8n (`AGENTE_URL`) y reactivar el workflow viejo. Objetivo: menos de 5 minutos, sin deploy.

---

### Fase 9 — Operación y limpieza · 2 sesiones

- `docs/RUNBOOK.md`: qué hacer si el agente no responde, si Google expira, si Supabase se pausa, cómo leer una corrida, cómo activar el kill-switch.
- Retirar la escritura dual a `external_chat_histories` / `n8n_chat_histories`.
- Borrar `services/agente_core/` y `services/agente_externo/` una vez que el grafo es la única ruta.
- Borrar del repo los fragmentos de `n8n/` que ya no aplican.
- Actualizar `docs/migracion-agente-a-codigo.md` marcándolo como histórico y apuntando acá.

---

## 5. Variables de entorno

**Ya existentes** (se conservan): `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `OPENAI_API_KEY`, `OPENAI_EMBED_MODEL`, `OPENAI_CHAT_MODEL`, `YCLOUD_API_KEY`, `YCLOUD_WEBHOOK_SECRET`, `YCLOUD_SEND_URL`, `TELEGRAM_BOT_TOKEN`, `GABI_TELEGRAM_CHAT_ID`, `GOOGLE_AGENT_CLIENT_ID`, `GOOGLE_AGENT_CLIENT_SECRET`, `GOOGLE_AGENT_REFRESH_TOKEN`, `GCAL_EVENTOS_ID`, `GCAL_REUNIONES_ID`, `GSHEET_SALONES_ID`, `MEMORIA_INTERNAL_KEY`, `MEMORIA_TOPK`, `MEMORIA_MIN_SIMILARITY`, `CSM_INTERNAL_KEY`, `WA_BUFFER_SECONDS`, `JWT_SECRET`, `CORS_ORIGINS`.

**Nuevas:**

```
# infraestructura
REDIS_URL                      DATABASE_URL            WEB_CONCURRENCY

# grafo
SONNER_DEBOUNCE_EXTERNO        SONNER_DEBOUNCE_INTERNO
SONNER_MAX_ITER                SONNER_MAX_TOOL_CALLS
SONNER_LLM_TIMEOUT             SONNER_LLM_MAX_RETRIES

# transporte
N8N_OUT_URL                    N8N_OUT_TOKEN
SONNER_INTERNAL_KEY

# calendarios y planillas adicionales
GCAL_TIJERETA_ID               GCAL_CROMO_ID           GSHEET_DJS_ID

# contratos
GDOC_PLANTILLA_CONTRATO_ID     GDRIVE_CONTRATOS_FOLDER_ID
CONTRATOS_EMAIL_DESTINO

# observabilidad
SONNER_ALERT_ENABLED           SONNER_ALERT_WINDOW_SECONDS
ALERT_TELEGRAM_CHAT_ID         LANGSMITH_TRACING       LANGSMITH_API_KEY

# cutover
SONNER_SHADOW                  SONNER_CANARY_NUMEROS
```

---

## 6. Riesgos

| # | Riesgo | Impacto | Mitigación |
|---|---|---|---|
| R1 | Los workflows reales no están versionados; una diferencia con los exports de `Downloads` genera pérdida de comportamiento | Alto | Fase 0 exporta de producción, no de `Downloads`, y congela el inventario |
| R2 | Regresión de calidad al reemplazar subagentes LLM por reglas | Medio | Golden set (Fase 7) + shadow mode antes del canario |
| R3 | El refresh token de Google sigue sin cubrir Calendar + Sheets a la vez (pendiente conocido) | Medio | Resolverlo en Fase 3; hasta entonces la tool degrada a handoff, como hoy |
| R4 | Debounce distribuido mal implementado ⇒ mensajes duplicados o perdidos al escalar a N workers | Alto | Redis con lock atómico + dedupe por `message_id` en `gate`; test de concurrencia explícito |
| R5 | El prompt v3.5 depende de comportamientos específicos del output parser de n8n | Medio | Fase 2 porta el prompt sin cambios; el nodo `guard` absorbe las diferencias |
| R6 | Costo de LLM por corrida sube si el grafo cicla | Medio | `SONNER_MAX_ITER` + `SONNER_MAX_TOOL_CALLS` + métrica de costo con alerta por umbral |
| R7 | Saturación de n8n durante el shadow mode (doble llamada) | Bajo | Shadow es fire-and-forget sobre el camino nuevo, con timeout corto |

---

## 7. Orden de ejecución y dependencias

```
F0 seguridad ──▶ F1 fundaciones ──▶ F2 externo ──┬──▶ F3 toolbelt ──▶ F4 interno ──┐
                                                  └──▶ F5 no-IA ────────────────────┤
                                                                                    ▼
                                                            F6 panel ──▶ F7 tests ──▶ F8 cutover ──▶ F9 limpieza
```

F3 y F5 pueden ir en paralelo si hay dos manos. F7 puede empezar a escribirse durante F3 (los tests offline no dependen del grafo interno).

---

## 8. Definición de terminado

El proyecto está cerrado cuando:

1. n8n tiene **exactamente dos workflows activos**, `SONNER-IN` y `SONNER-OUT`, sin nodos `Code`, `Wait`, `Redis`, `Postgres` ni `AI Agent`.
2. Los tres agentes (externo, interno Telegram, interno web) corren sobre el mismo core de LangGraph.
3. `/health/ready`, `/metrics` y `/admin/monitor` están operativos y los usa alguien de verdad.
4. Una conversación fallida se diagnostica de punta a punta sin abrir n8n.
5. La suite de tests corre en CI y el golden set pasa.
6. `docs/RUNBOOK.md` existe y alguien que no escribió el código pudo seguirlo.
7. Los secretos de §1.3 están rotados y fuera del repo.

---

## 9. Lo que este plan deliberadamente NO hace

- **No cambia el prompt del agente.** Portar plataforma y cambiar comportamiento a la vez hace imposible atribuir una regresión. Mejoras de prompt van después de Fase 8, con el golden set ya como red.
- **No saca las credenciales de n8n.** Se podría enviar directo desde Python, pero eso agrega una variable al cutover. Queda como mejora posterior.
- **No migra la plataforma web** (contratos, analista, CSM, inventario). Solo la parte de agentes y los procesos que hoy viven en n8n.
- **No introduce LangSmith como dependencia.** El monitoreo es propio, dentro del código, como se pidió.

---

## 10. Bitácora de ejecución

### Fases 0–2 — hechas (2026-09-17)

**Fase 0 — Seguridad y red de contención**

- `scripts/scrub_n8n_export.py` — limpia exports de n8n: reemplaza tokens por `{{$env.VAR}}`, elimina `pinData` (traía teléfonos reales de clientes) y reporta regla + ruta JSON sin mostrar el valor.
- `n8n/workflows-export/` — los **6 workflows versionados**. El token de Telegram apareció exactamente donde decía el inventario (`$.nodes[54].parameters.url` del principal externo). Verificación posterior: ningún archivo matchea patrones de secreto.
- `.gitignore` — excepción para `n8n/workflows-export/*.json`.
- `backend/app/config.py` — **fuera los defaults hardcodeados** de `JWT_SECRET`, `GOOGLE_AGENT_CLIENT_ID` y `GOOGLE_AGENT_CLIENT_SECRET`. Sin `JWT_SECRET` el proceso ya no arranca.
- `backend/.env.example` — completado (26 variables nuevas, ninguna perdida).
- `docs/RUNBOOK.md` — rotación de secretos, restauración de workflows, kill-switch y blocklist.

**Fase 1 — Fundaciones y observabilidad**

- `db/migrations/001_observabilidad.sql` — `agent_runs`, `agent_steps`, `agent_errors`, `agent_alerts`, `agent_golden_cases` + RPC `agent_error_registrar` (incremento atómico) + RLS.
- `backend/app/obs/` — `logs.py` (JSON con `run_id` por contextvar), `runs.py` (fila al ARRANCAR, para detectar corridas trabadas; pasos en batch al cerrar; redacción de secretos), `metrics.py` (11 series Prometheus), `alertas.py` (firma → dedupe → Telegram con ventana), `health.py` (`/health`, `/health/ready`, `/health/deps`).
- `backend/app/agents/` — `state.py` y `llm.py` (Claude → OpenAI con `with_fallbacks`, uso y costo por corrida).

**Fase 2 — Agente externo sobre LangGraph**

- 11 nodos en `agents/nodes/`, grafo en `agents/graphs/externo.py` con dos recorridos (`directo` / `relay`).
- `agents/tools/registry.py` con alcance por audiencia.
- `POST /api/agente/n8n` y `/api/agente/probar` ahora corren sobre el grafo, **mismo contrato de salida**. `/api/wa/webhook` usa el recorrido directo.
- Debounce y dedupe con Redis (con caída a memoria si no hay `REDIS_URL`); `Dockerfile.agente` pasó de `--workers 1` fijo a `WEB_CONCURRENCY`.
- **27 tests offline en verde** (`cd backend && .venv/Scripts/python -m pytest`), sin red: contrato, degradación a handoff, loop de tools, topes, alcance del toolbelt, camino directo completo, dedupe, kill-switch y observabilidad.

### Desvíos respecto del plan original

| Desvío | Por qué |
|---|---|
| El checkpointer de Postgres **no** se conectó en Fase 2 | El historial sigue saliendo de `external_chat_histories` vía REST, que es lo que n8n todavía puede leer. Conectar el checkpointer ahora crearía dos fuentes de verdad durante el corte. Pasa a Fase 3+. Se quitaron `DATABASE_URL` y las dependencias del checkpointer para no dejar config muerta |
| El prompt v3.5 se **reusa** desde `services/agente_externo/prompt.py` en vez de copiarse a `agents/prompts/` | Duplicar 25k caracteres de prompt garantiza que las dos copias diverjan. El objetivo de la fase (portar sin cambiar comportamiento) se cumple mejor reusando el archivo |
| Se escribieron tests en Fase 2, no en Fase 7 | Sin tests no había forma de verificar que el grafo se comporta como el agente viejo. Estos 27 son la base sobre la que sigue la Fase 7 (golden set y shadow mode) |
| `anthropic` subió de 0.40.0 a 0.42.0 | `langchain-anthropic` lo exige. La API de Messages que usa `motor.py` no cambió |
| `services/agente_externo/{flujo,orquestador,buffer,herramientas}.py` siguen en el repo | Son la ruta de rollback mientras dure el corte. Se borran en Fase 9, como estaba previsto |

### Fases 3–5 — hechas (2026-09-17)

**Fase 3 — Toolbelt determinista**

Las tools de Google ya eran Python determinista; lo que faltaba era otra cosa:

- **Argumentos tipados en vez de strings mágicos.** El modelo pasaba `"verificar disponibilidad evento 2026-12-13"` y un regex lo parseaba: si lo armaba mal, la tool devolvía "no pude interpretar la fecha" y nadie se enteraba. Ahora son `calendario(fecha)`, `salones(salon, pax)` y `memoria(consulta, fuente)`.
- **Se sacó el LLM anidado de memoria.** Era el más caro: el agente principal mandaba un comando, un segundo LLM elegía la fuente, llamaba a pgvector y **volvía a redactar** chunks que debía devolver verbatim. Ahora el agente elige la fuente como argumento y `memoria.consultar` resuelve. Dos llamadas a modelo menos por búsqueda.
- **Las reglas se separaron del I/O** en `tools_google.py`: `estado_por_eventos`, `titulos_sin_montos`, `evaluar_salon` y `buscar_fila` son funciones puras y ahora tienen tests.
- **Bug encontrado por los tests:** los nombres de salón con acento no matcheaban. `"Los Álamos"` se normalizaba a `"loslamos"` (se borraban los caracteres no ASCII en vez de transliterarlos) y no coincidía con `"Los Alamos"` como lo escribe el cliente. Corregido con `unicodedata`.

**Fase 4 — Agente interno (Telegram + página)**

Los dos workflows internos (63 y 61 nodos) eran el mismo agente duplicado: cambiaba el trigger y cómo se devolvía la respuesta. Ahora es **un grafo y dos canales**.

- `agents/graphs/interno.py` — contexto → agente ⇄ herramientas → guard → persistencia → ingesta_vectorial → troceo. Sin `gate` ni `debounce` (del otro lado está el equipo) y sin `salida` (envía n8n).
- **13 tools**, y ninguna de escritura recibe el calendario como argumento: el destino está fijo en el código. `ESCRIBIBLES = {eventos_sonner, reuniones_gabi}`; tijereta y cromo se leen y no hay forma de escribirles.
- `guard` pasó a ser **por audiencia**: el contrato interno es `{respuesta, comando ∈ (eventos|informacion|materiales|nada), contenido}`.
- **La degradación es distinta según quién escucha**: al cliente nunca le llega un error técnico (se deriva a Gabriel); al equipo sí se le dice que falló **y que no se ejecutó ningún cambio**, porque son quienes pueden actuar y porque si no asumen que la acción salió.
- `nodes/ingesta_vectorial.py` reemplaza el Switch y las 3 ramas de ingesta. Si el guardado falla, se lo dice en la misma respuesta: un guardado que falla en silencio es peor que uno que falla, porque nadie lo va a buscar.
- Endpoints `POST /api/agente/interno` y `/api/agente/interno/web`.
- **El hack anti-loop no se portó**: existía porque el output parser de n8n filtraba JSON crudo al chat. Con el contrato de Pydantic eso no puede pasar.

**Fase 5 — Procesos no-IA**

- **Contratos**: ya estaban en Python (`POST /api/contratos`). Faltaban dos pasos del workflow: compartir el PDF por link (sin eso el link que devolvemos no le abre al cliente) y avisar a Gabriel.
- `jobs/watchdog.py` — cada 5 min: corridas que arrancaron y nunca cerraron, y tasa de derivación por encima del 30%. Son fallas silenciosas: el servicio responde 200 y las métricas suben.
- `jobs/digest.py` — resumen diario 20:00 AR: atendidas, derivaciones, latencia p50/p95, costo y errores abiertos.
- `jobs/scheduler.py` — con varios workers todos despiertan a la misma hora; un `SET NX` en Redis por tick evita que el resumen llegue N veces.
- El error handler global ya estaba cubierto por `obs/alertas.py`.

**103 tests offline en verde.**

### Desvíos de las fases 3–5

| Desvío | Por qué |
|---|---|
| El keep-alive **no** se migró a código | El GitHub Action que ya existe funciona aunque el servicio esté caído, que es justo cuando hace falta. Además, mientras el agente corre ya golpea Supabase constantemente. Migrarlo habría sido peor por simetría. Solo hay que borrar el cron de n8n |
| El aviso de contrato va por **Telegram y no por mail** | Mandar el mail exige sumarle el scope de Gmail al cliente OAuth de contratos; el canal de Telegram ya existe, ya recibe los leads y se pudo probar |
| `tools/permisos.py` no existe como archivo | El control de escritura quedó donde es imposible de esquivar: el registry por audiencia y `ESCRIBIBLES` en el servicio de calendario. Un módulo aparte habría sido una capa más sin más garantía |

### Pendiente antes de desplegar estas tres fases

1. **Rotar** el token del bot de Telegram y el `GOOGLE_AGENT_CLIENT_SECRET` (ver RUNBOOK §1). Redactarlos del repo no los rota.
2. Cargar `JWT_SECRET` en EasyPanel — **sin esa variable el servicio no levanta**, a propósito.
3. Correr `db/migrations/001_observabilidad.sql` en Supabase.
4. Levantar el servicio Redis y cargar `REDIS_URL` si se quiere más de un worker.
5. Apuntar el healthcheck de EasyPanel a `/health/ready`.
6. **Regenerar `GOOGLE_AGENT_REFRESH_TOKEN` con permisos de escritura** (`calendar` y `spreadsheets`, no las variantes `.readonly`). El agente interno crea y borra eventos y escribe en la planilla de DJs; con el token actual eso devuelve 403. En el flujo de refresh token los permisos son los que se otorgaron al generarlo, no los que pide el código.
7. ~~Cargar `GCAL_TIJERETA_ID`, `GCAL_CROMO_ID` y `GSHEET_DJS_ID`~~ — ya vienen como default en `config.py`, tomados del workflow de n8n.
8. Apuntar los workflows internos de n8n a `/api/agente/interno` y `/api/agente/interno/web`, igual que se hizo con el externo.
