-- 001 — Observabilidad de los agentes (Fase 1 del plan de migración a LangGraph).
--
-- Reemplaza el "no queda registro de nada" actual: hoy el _meta de cada corrida
-- (proveedor, modelo, tiempo, intentos, si degradó a handoff) se calcula y se tira.
--
-- Idempotente: se puede correr varias veces.
-- RLS habilitado sin políticas = solo service_role entra. El backend usa esa key.

-- ── Una fila por corrida del grafo ───────────────────────────────────────────
create table if not exists agent_runs (
    run_id          uuid primary key,
    creado_en       timestamptz not null default now(),
    cerrado_en      timestamptz,
    canal           text        not null,           -- whatsapp | telegram | web
    audiencia       text        not null,           -- externo | interno
    chat_id         text,
    nombre          text,
    entrada         text,
    respuesta       text,
    comando         text,
    mensaje_comando text,
    proveedor       text,                           -- claude | openai
    modelo          text,
    tokens_in       integer,
    tokens_out      integer,
    costo_usd       numeric(12, 6),
    latencia_ms     integer,
    degradado       boolean     not null default false,
    motivo_corte    text,                           -- kill_switch | blocklist | debounce | ...
    ok              boolean,
    meta            jsonb       not null default '{}'::jsonb
);

create index if not exists agent_runs_creado_idx  on agent_runs (creado_en desc);
create index if not exists agent_runs_chat_idx    on agent_runs (chat_id, creado_en desc);
create index if not exists agent_runs_fallidas_idx on agent_runs (creado_en desc) where ok is not true;

-- ── Un paso del grafo (nodo o tool) ──────────────────────────────────────────
create table if not exists agent_steps (
    id          bigserial primary key,
    run_id      uuid        not null references agent_runs (run_id) on delete cascade,
    orden       integer     not null,
    nodo        text        not null,
    tool        text,
    args        jsonb,                              -- argumentos ya redactados
    resultado   text,                               -- truncado
    duracion_ms integer,
    error       text,
    creado_en   timestamptz not null default now()
);

create index if not exists agent_steps_run_idx on agent_steps (run_id, orden);

-- ── Errores agregados por firma ──────────────────────────────────────────────
create table if not exists agent_errors (
    firma         text primary key,                 -- hash de tipo + mensaje + nodo
    tipo          text,
    mensaje       text,
    nodo          text,
    cantidad      integer     not null default 1,
    first_seen    timestamptz not null default now(),
    last_seen     timestamptz not null default now(),
    ultimo_run_id uuid,
    resuelto      boolean     not null default false
);

create index if not exists agent_errors_abiertos_idx on agent_errors (last_seen desc) where resuelto = false;

-- ── Rate-limit de alertas (para no spamear Telegram) ─────────────────────────
create table if not exists agent_alerts (
    firma        text primary key,
    ultimo_envio timestamptz not null default now(),
    enviados     integer     not null default 0
);

-- ── Casos de referencia para la suite de regresión (Fase 7) ──────────────────
create table if not exists agent_golden_cases (
    id        bigserial primary key,
    nombre    text        not null,
    canal     text        not null default 'whatsapp',
    audiencia text        not null default 'externo',
    historial jsonb       not null default '[]'::jsonb,
    mensaje   text        not null,
    esperado  jsonb       not null default '{}'::jsonb,  -- {respuesta_semantica, comando}
    asserts   jsonb       not null default '[]'::jsonb,  -- reglas duras verificables
    activo    boolean     not null default true,
    creado_en timestamptz not null default now()
);

alter table agent_runs         enable row level security;
alter table agent_steps        enable row level security;
alter table agent_errors       enable row level security;
alter table agent_alerts       enable row level security;
alter table agent_golden_cases enable row level security;

-- ── Incremento atómico de la firma de error ──────────────────────────────────
-- Evita el read-modify-write desde el backend (que pierde eventos con concurrencia).
create or replace function agent_error_registrar(
    p_firma   text,
    p_tipo    text,
    p_mensaje text,
    p_nodo    text,
    p_run_id  uuid
) returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
    v_cantidad integer;
begin
    insert into agent_errors as e (firma, tipo, mensaje, nodo, ultimo_run_id)
    values (p_firma, p_tipo, p_mensaje, p_nodo, p_run_id)
    on conflict (firma) do update
        set cantidad      = e.cantidad + 1,
            last_seen     = now(),
            ultimo_run_id = excluded.ultimo_run_id,
            resuelto      = false
    returning cantidad into v_cantidad;
    return v_cantidad;
end;
$$;
