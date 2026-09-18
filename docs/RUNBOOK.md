# RUNBOOK — SONNER

Qué hacer cuando algo se rompe. Se completa a medida que avanzan las fases del
[plan de migración](PLAN_MIGRACION_LANGGRAPH.md).

---

## 1. Rotación de secretos pendiente

Estos secretos estuvieron expuestos en el repo o en los exports de n8n. **Redactarlos no
los rota**: hay que darlos de baja en el proveedor.

| Secreto | Dónde estuvo | Cómo se rota |
|---|---|---|
| Token del bot de Telegram | URL del nodo `Avisar a Gabi` en los exports de n8n | BotFather → `/revoke` → `/token`. Cargar en `TELEGRAM_BOT_TOKEN` (env del backend) y en la credencial de n8n |
| `GOOGLE_AGENT_CLIENT_SECRET` | `backend/app/config.py` (default en el código) | Google Cloud Console → APIs y servicios → Credenciales → cliente OAuth del proyecto de calendarios → *Restablecer secreto*. Regenerar después `GOOGLE_AGENT_REFRESH_TOKEN` |
| `JWT_SECRET` | `backend/app/config.py` (default en el código) | Generar uno nuevo y cargarlo por env. **Invalida todas las sesiones abiertas**: los usuarios vuelven a loguearse |

Después de rotar, verificar que el historial de git ya no sea el problema: los valores
siguen en commits viejos. Si el repo alguna vez se hace público, hay que reescribir la
historia (`git filter-repo`) **además** de rotar.

### Arranque tras la rotación

`JWT_SECRET` ya no tiene default: **si falta, el backend no arranca** y tira un
`RuntimeError` explícito. Es intencional — arrancar con un secret que está publicado en
el repo es peor que no arrancar. Antes de desplegar, cargar la variable en EasyPanel.

---

## 2. Workflows de n8n: versionado y restauración

### Dónde están

`n8n/workflows-export/` — seis workflows, con los secretos reemplazados por
`{{$env.VAR}}` y sin `pinData`:

| Archivo | Workflow en n8n |
|---|---|
| `sonner-prinicpal-externo.json` | SONNER · PRINICPAL EXTERNO (WhatsApp, cliente final) |
| `agt-interno-sonner.json` | AGT-INTERNO-SONNER (Telegram, equipo) |
| `agt-interno-sonner-pagina.json` | AGT-INTERNO-SONNER PAGINA (chat web) |
| `contratos-sonner.json` | contratos sonner |
| `error-trigger-sonner.json` | error trigger sonner |
| `supabase-keep-alive-memorias-sonner.json` | Supabase keep-alive |

### Restaurar producción desde el repo

1. En n8n: *Workflows* → *Import from File* → elegir el JSON.
2. Reasignar credenciales. El import trae la **referencia** (`id` + `name`) pero no el
   secreto; si la credencial ya existe en esa instancia se reconecta sola, si no hay que
   crearla y seleccionarla nodo por nodo.
3. Definir las variables de entorno que quedaron como `{{$env.VAR}}` en *Settings →
   Variables* (al menos `TELEGRAM_BOT_TOKEN`).
4. Verificar la URL del webhook: al importar, n8n puede generar un `webhookId` nuevo. Si
   cambia, hay que actualizar el endpoint en YCloud.
5. Activar el workflow y probar con un mensaje real antes de desactivar el anterior.

### Actualizar los exports versionados

Nunca copiar el JSON crudo al repo. Siempre:

```bash
python scripts/scrub_n8n_export.py "/ruta/al/export.json" --salida n8n/workflows-export
```

El script imprime qué redactó (regla + ruta JSON, nunca el valor) y elimina `pinData`,
que suele contener payloads reales con teléfonos de clientes. Verificar la salida antes
de commitear.

---

## 3. Kill-switch: apagar el agente

El agente consulta `automatizacion_config.activa` (fila `id=1`) en cada mensaje.

```sql
update automatizacion_config set activa = false where id = 1;
```

Efecto inmediato (no hay cache). Los mensajes entrantes se registran y se ignoran; nadie
recibe respuesta automática. Para volver: `activa = true`.

## 4. Bloquear un contacto

```sql
insert into blocklist (identifier) values ('+5492954xxxxxx');
```

El match es por los **últimos 10 dígitos**, así que el formato del prefijo no importa.
Hay un cache de 60 segundos: puede tardar hasta un minuto en tomar efecto.

---

## 5. Google: cuando las tools fallan

### Síntoma

`GET /api/agente/diag` devuelve error en `calendar` o `sheets`, o el agente deriva todo
a Gabriel en vez de responder por disponibilidad.

### Causas por orden de frecuencia

1. **Falta `GOOGLE_AGENT_REFRESH_TOKEN`.** Sin él se cae al token de contratos, que no
   tiene scopes de Calendar ni Sheets. `GET /health/deps` lo dice explícitamente.
2. **El token no tiene permiso de escritura.** El agente externo solo lee, pero el
   interno crea y borra eventos y escribe en la planilla de DJs. Si el token se generó
   con los scopes `.readonly`, las lecturas andan y las escrituras devuelven 403.
   **En el flujo de refresh token los permisos son los que se otorgaron al generarlo**,
   no los que pide el código: hay que regenerarlo con `calendar` y `spreadsheets`.
3. **El token se revocó.** Pasa al cambiar la contraseña de la cuenta de Google o al
   resetear el client secret. Hay que volver a generarlo.

### Qué NO hace el agente si Google falla

Nada destructivo. Las tools degradan al valor seguro (`estado: "error"`,
`compatibilidad: "especial"`) y el agente deriva a un humano. Nunca le afirma al cliente
que una fecha está libre sin haberlo podido verificar.

## 6. Permisos de escritura del agente interno

| Calendario | Lectura | Escritura |
|---|---|---|
| `eventos_sonner` | sí | **sí** |
| `reuniones_gabi` | sí | **sí** |
| `fiestas_tijereta` | sí | no |
| `fiestas_cromo` | sí | no |

La regla vive en `ESCRIBIBLES`, en `services/agente_interno/calendario.py`, y las tools
de escritura **no reciben el calendario como argumento**: cada una tiene su destino fijo.
Para cambiar esto hay que tocar código y un test va a fallar — es a propósito.

## 7. Jobs de fondo

Arrancan con el servicio (`app/jobs/scheduler.py`):

| Job | Cada | Qué hace |
|---|---|---|
| `watchdog` | 5 min | Corridas que arrancaron y nunca cerraron; tasa de derivación > 30% |
| `digest` | 20:00 AR | Resumen del día a Telegram |

Con varios workers, un `SET NX` en Redis decide cuál corre. Si Redis no está, corre el
único worker que hay.

**El keep-alive de Supabase no está acá**: lo hace el GitHub Action
`.github/workflows/supabase-keepalive.yml`, que sigue funcionando aunque el servicio esté
caído — que es cuando hace falta. El cron equivalente de n8n se puede borrar.

### Silenciar las alertas

`SONNER_ALERT_ENABLED=false`. El rate-limit por firma ya evita el spam
(`SONNER_ALERT_WINDOW_SECONDS`, 10 min por defecto), así que apagarlas del todo debería
ser temporal.

## 8. Pendiente

- Diagnóstico de una conversación fallida desde el panel (Fase 6).
- Procedimiento de rollback del cutover (Fase 8).
