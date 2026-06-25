-- Sonner · Reuniones agendadas (Calendly → Supabase)
-- El agente lee esta tabla para saber si un cliente ya tiene reunión, cruzando por teléfono.

create table if not exists public.reuniones (
  id              bigserial primary key,
  nombre          text,
  telefono        text,                       -- solo dígitos (se cruza por los últimos 10)
  email           text,
  fecha_hora      timestamptz,                -- inicio de la reunión
  evento          text,                       -- nombre del tipo de evento de Calendly
  estado          text default 'agendada',    -- agendada | cancelada | reprogramada
  cancel_url      text,
  reschedule_url  text,
  created_at      timestamptz not null default now()
);

create index if not exists idx_reuniones_tel   on public.reuniones (telefono);
create index if not exists idx_reuniones_fecha on public.reuniones (fecha_hora);

-- RLS: solo el backend / n8n (service_role) accede.
alter table public.reuniones enable row level security;
