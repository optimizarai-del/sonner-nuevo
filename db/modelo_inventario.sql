-- ════════════════════════════════════════════════════════════════════════════
-- MODELO INVENTARIO + EVENTOS COORDINADOS (SONNER)
-- Permite: ver materiales asignados a cada evento, y la disponibilidad de cada
-- equipo por fecha (eventos + alquileres individuales).
-- ════════════════════════════════════════════════════════════════════════════

-- ── 1) Catálogo de materiales ───────────────────────────────────────────────
create table if not exists public.materiales (
  id                bigserial primary key,
  categoria         text not null,         -- SONIDO, ILUMINACION, ESTRUCTURAS, etc.
  producto          text not null,
  stock_total       integer not null default 0,  -- unidades que SONNER posee
  unidad            text default 'unidad',
  ubicacion         text,
  estado            text default 'ok',     -- ok | reparacion | baja
  activo            boolean default true,
  created_at        timestamptz not null default now(),
  unique (categoria, producto)
);
create index if not exists idx_materiales_cat on public.materiales (categoria);

-- ── 2) Eventos (incluye alquileres individuales) ────────────────────────────
create table if not exists public.eventos (
  id                bigserial primary key,
  tipo              text not null default 'evento',  -- 'evento' | 'alquiler'
  nombre            text,
  cliente           text,
  fecha_inicio      date not null,         -- desde cuándo el equipo queda ocupado
  fecha_fin         date not null,         -- hasta cuándo (= fecha_inicio si es un solo día)
  hora              text,                  -- horario del evento (texto libre)
  lugar             text,
  tipo_evento       text,                  -- Social, Cumpleaños 15, Corporativo, etc.
  asistentes        integer,
  estado            text default 'confirmado', -- confirmado | tentativo | finalizado | cancelado
  notas             text,
  event_id_externo  text,                  -- id de Google/Calendly si aplica
  created_at        timestamptz not null default now(),
  check (fecha_fin >= fecha_inicio)
);
create index if not exists idx_eventos_fechas on public.eventos (fecha_inicio, fecha_fin);
create index if not exists idx_eventos_estado on public.eventos (estado);

-- ── 3) Asignación material ↔ evento (el corazón del sistema) ─────────────────
create table if not exists public.evento_materiales (
  id           bigserial primary key,
  evento_id    bigint not null references public.eventos(id) on delete cascade,
  material_id  bigint not null references public.materiales(id) on delete restrict,
  cantidad     integer not null default 1,
  created_at   timestamptz not null default now(),
  unique (evento_id, material_id)
);
create index if not exists idx_em_evento   on public.evento_materiales (evento_id);
create index if not exists idx_em_material on public.evento_materiales (material_id);

-- ════════════════════════════════════════════════════════════════════════════
-- CONSULTAS CLAVE
-- ════════════════════════════════════════════════════════════════════════════

-- A) Materiales asignados a un evento (lo que ves al abrir el evento)
--    SELECT m.categoria, m.producto, em.cantidad
--    FROM evento_materiales em
--    JOIN materiales m ON m.id = em.material_id
--    WHERE em.evento_id = :evento_id;

-- B) ¿En qué fechas está ocupado un material? (qué eventos lo tienen)
--    SELECT e.nombre, e.tipo, e.fecha_inicio, e.fecha_fin, em.cantidad
--    FROM evento_materiales em
--    JOIN eventos e ON e.id = em.evento_id
--    WHERE em.material_id = :material_id
--      AND e.estado <> 'cancelado'
--    ORDER BY e.fecha_inicio;

-- C) Disponibilidad de un equipo en una FECHA puntual (para alquileres)
--    = stock_total - lo asignado a eventos que ocupan esa fecha.
create or replace function public.disponibilidad_material(p_material bigint, p_fecha date)
returns integer
language sql stable
as $$
  select m.stock_total - coalesce((
    select sum(em.cantidad)
    from evento_materiales em
    join eventos e on e.id = em.evento_id
    where em.material_id = p_material
      and e.estado <> 'cancelado'
      and p_fecha between e.fecha_inicio and e.fecha_fin
  ), 0)
  from materiales m
  where m.id = p_material;
$$;
-- Uso:  SELECT disponibilidad_material(12, '2026-07-04');  -- unidades libres ese día

-- D) Vista: disponibilidad de TODO el catálogo en una fecha
--    (cambiá la fecha en el WHERE; útil para "qué hay libre el día X")
create or replace view public.v_disponibilidad_hoy as
select
  m.id, m.categoria, m.producto, m.stock_total,
  public.disponibilidad_material(m.id, current_date) as disponible_hoy
from materiales m
where m.activo
order by m.categoria, m.producto;
