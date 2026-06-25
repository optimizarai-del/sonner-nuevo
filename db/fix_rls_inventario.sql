-- Acceso del frontend a inventario/eventos.
-- La plataforma usa el ANON key (no Supabase Auth), igual que blocklist/automatizacion_config.
-- Con RLS activado y sin políticas, el anon recibe [] (no puede leer/escribir).
-- Desactivamos RLS en estas tablas para que el frontend pueda operarlas.
-- (Es el mismo modelo de acceso que ya usa blocklist en esta app.)

alter table public.materiales        disable row level security;
alter table public.eventos           disable row level security;
alter table public.evento_materiales disable row level security;

-- Verificación: estas consultas deberían devolver filas con el anon key.
-- select count(*) from materiales;   -- 133
-- select count(*) from eventos;      -- 6
