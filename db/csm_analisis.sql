-- Sonner · Análisis de CSM — registro y evaluación de respuestas del agente
-- Ejecutar en el SQL editor de Supabase del proyecto de Sonner.
--
-- Flujo:
--   1. n8n / el agente registra cada interacción       -> POST /api/csm/log
--   2. Un admin la puntúa y/o corrige                   -> POST /api/csm/{id}/review
--   3. Métricas y export del dataset Q/A                -> GET  /api/csm/stats · /export
-- La tabla se accede solo con la SERVICE_ROLE_KEY desde el backend (RLS activado).

create table if not exists public.csm_analisis (
  id                   bigserial primary key,
  mensaje_cliente      text not null,
  respuesta_agente     text,
  respuesta_corregida  text,
  rating               text,                      -- good | mejorable | bad | null
  status               text default 'pending',    -- pending | reviewed
  canal                text,                      -- whatsapp | telegram | sandbox | mail
  tipo_cliente         text,                      -- minorista | mayorista
  agente               text,                      -- principal | calendario | salones
  tags                 jsonb,
  nota                 text,                      -- comentario interno del revisor
  wa_id                text,                      -- id de WhatsApp / contacto, si aplica
  cliente_nombre       text,                      -- nombre del usuario (viene del input)
  reviewed_by          text,
  created_at           timestamptz not null default now(),
  reviewed_at          timestamptz
);

create index if not exists idx_csm_status       on public.csm_analisis (status, created_at desc);
create index if not exists idx_csm_rating        on public.csm_analisis (rating);
create index if not exists idx_csm_tipo_cliente  on public.csm_analisis (tipo_cliente);
create index if not exists idx_csm_agente        on public.csm_analisis (agente);

-- RLS: solo el backend (service_role) accede. El front pasa siempre por la API.
alter table public.csm_analisis enable row level security;
