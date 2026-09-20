# Staging del agente sobre LangGraph

Servicio aparte en EasyPanel para probar el grafo nuevo con el LLM, Google y Supabase
**reales**, sin tocar producción. Producción sigue en el servicio actual
(`n8n-nuevo-agente-sonner`) y n8n sigue apuntando ahí.

## Qué NO puede pasar

Staging comparte Supabase y Google con producción. Estas cuatro reglas son las que
evitan que una prueba termine en un cliente o en el calendario real:

1. **Ni YCloud ni n8n apuntan a staging.** Solo se le pega a mano o con el golden set.
2. **`SONNER_ALERT_ENABLED=false`.** Si no, el resumen diario de las 20:00 y cualquier
   error de prueba le llegan a Gabi por Telegram.
3. **El agente interno escribe en los calendarios reales.** En staging, preguntale solo
   cosas de lectura ("¿qué eventos hay en diciembre?"), o cargá en `GCAL_EVENTOS_ID` /
   `GCAL_REUNIONES_ID` / `GSHEET_DJS_ID` los IDs de un calendario y una planilla de prueba.
4. **Nunca `persistir: true` en staging.** El golden set ya manda `false`; si probás a
   mano, también.

## Crear el servicio en EasyPanel

| Campo | Valor |
|---|---|
| Tipo | App → GitHub |
| Repo / rama | `optimizarai-del/sonner-nuevo` · **`Sonner-Python-sp26`** |
| Build | Dockerfile |
| Dockerfile | `Dockerfile.agente` |
| Contexto de build | `backend` (el Dockerfile hace `COPY app` y `COPY requirements.txt`) |
| Puerto | 8000 |
| Healthcheck | `/health/ready` |
| Nombre sugerido | `sonner-agente-staging` |

**No** activar auto-deploy desde `agentes-sonner`: esa es la rama de producción.

## Variables de entorno

Copiar las del servicio de producción y **cambiar** estas:

```
SONNER_ALERT_ENABLED=false
WEB_CONCURRENCY=1                 # sin Redis en staging
JWT_SECRET=<uno nuevo>            # obligatorio: sin esto no arranca
```

Los IDs de los calendarios de tijereta y cromo y de la planilla de DJs ya vienen como
default en `config.py` (los mismos que usaba n8n); solo hace falta cargarlos si se
quieren apuntar a recursos de prueba.

Antes del primer arranque, correr `db/migrations/001_observabilidad.sql` en Supabase.
Sin esas tablas el agente funciona igual —la observabilidad es best-effort— pero no
queda registro de nada y el golden set pierde la mitad de su valor.

## Verificación, en este orden

```bash
BASE=https://sonner-agente-staging.<tu-dominio>.easypanel.host
KEY=<MEMORIA_INTERNAL_KEY>

# 1. ¿Levantó y ve sus dependencias?
curl -s $BASE/health/ready          # 200 = Supabase y LLM ok
curl -s $BASE/health/deps           # redis "sin configurar" es esperado; google tiene que decir "credenciales presentes"

# 2. ¿Google responde con el token nuevo?
curl -s -H "X-Memoria-Key: $KEY" "$BASE/api/agente/diag?fecha=2026-12-13&salon=Royal&pax=150"

# 3. Un mensaje de punta a punta, sin tocar el historial
curl -s -X POST $BASE/api/agente/probar -H "X-Memoria-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"mensaje":"hola, necesito sonido para un casamiento","telefono":"+540000000000","persistir":false}'

# 4. El agente interno, SOLO lectura
curl -s -X POST $BASE/api/agente/interno/web -H "X-Memoria-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"mensaje":"qué eventos tenemos en diciembre?","chat_id":"staging","persistir":false}'
```

Cada una de estas corridas queda en `agent_runs`. Para verlas:

```sql
select creado_en, canal, audiencia, chat_id, ok, degradado, latencia_ms, modelo, costo_usd, respuesta
from agent_runs order by creado_en desc limit 20;
```

## Golden set

Desde la raíz del repo, con el venv del backend:

```bash
export SUPABASE_URL=...  SUPABASE_SERVICE_ROLE_KEY=...  ANTHROPIC_API_KEY=...

# 1. Importar casos reales (mirá primero qué se llevaría)
backend/.venv/Scripts/python scripts/golden_set.py extraer --n 40 --dry-run
backend/.venv/Scripts/python scripts/golden_set.py extraer --n 40

# 2. Correrlos contra staging
backend/.venv/Scripts/python scripts/golden_set.py correr --url $BASE --key $KEY --juez
```

El reporte queda en `backend/.golden/` (fuera del repo: son mensajes reales de clientes).

### Cómo leer el resultado

- **Reglas duras**: tienen que dar 40/40. Una sola falla —un monto expuesto, un error
  técnico, un JSON crudo— bloquea el paso a shadow mode.
- **Juez**: es orientativo. "peor" en unos pocos casos es esperable (el juez también se
  equivoca); lo que hay que leer es el motivo. Si se repite un patrón, es un problema.
- **Casos con referencia "rechazada"**: fueron malas respuestas del agente viejo. Acá
  el grafo nuevo tiene que ganar.

### Límite conocido

Los casos son de un solo turno: se corren con un teléfono sintético, sin historial.
Conversaciones largas (el cliente ya dio la fecha tres mensajes antes) no se cubren acá;
eso lo cubre el shadow mode, que corre sobre tráfico real.
