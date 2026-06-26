-- ════════════════════════════════════════════════════════════════════════════
-- ANALISTA IA — historial de conversación + introspección de tablas
-- Correr en el SQL Editor del proyecto plataforma (wndfjicwzmsuxxcsnccl).
-- ════════════════════════════════════════════════════════════════════════════

-- 1) Historial de mensajes del Analista, por usuario de la plataforma.
create table if not exists public.analista_historial (
  id          bigserial primary key,
  username    text not null,                 -- username del JWT de la plataforma
  role        text not null,                 -- 'user' | 'assistant'
  content     text not null,
  created_at  timestamptz not null default now()
);
create index if not exists idx_analista_hist_user
  on public.analista_historial (username, created_at);

-- Se accede solo con service_role (igual que csm_analisis / users). RLS activado:
alter table public.analista_historial enable row level security;

-- 2) Función para que el Analista descubra qué tablas existen (introspección).
--    security definer: corre con permisos del owner para poder leer el catálogo.
create or replace function public.analista_list_tables()
returns table (tabla text, filas_estimadas bigint)
language sql
stable
security definer
set search_path = public
as $$
  select c.relname::text, c.reltuples::bigint
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public'
    and c.relkind = 'r'
  order by c.relname;
$$;
