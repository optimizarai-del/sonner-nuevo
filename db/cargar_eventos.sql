-- Carga de eventos limpios (reuniones filtradas, fechas normalizadas, dedup por event_id).
-- tipo='evento', fecha_fin = fecha_inicio (ajustar luego los multi-día).
insert into public.eventos
  (tipo, nombre, cliente, fecha_inicio, fecha_fin, hora, lugar, tipo_evento, asistentes, estado, notas, event_id_externo) values
  ('evento', 'Cumpleaños mica', null, '2026-03-20', '2026-03-20', '20:00 - 00:00', null, null, null, 'Confirmado', null, 'c6j7a210e4hcregpd7qfa8cl78'),
  ('evento', 'Cumpleaños Federico', 'Fede Rodriguez', '2026-04-22', '2026-04-22', '21:00 hs', 'Cromo', null, 300, 'Confirmado', '7 horas', 'cjgusl7u7jmeb125vc302eug2c'),
  ('alquiler', 'Alquiler de proyector - Hotel UNIT', null, '2026-06-07', '2026-06-07', '08:00 - 15:00', 'Hotel UNIT', null, null, null, 'Entrega de proyector en el Hotel UNIT', 'k5bq0jld1dl57bkt9eq96enl2c'),
  ('alquiler', 'Gisela Anahi', null, '2026-09-07', '2026-09-07', '09:00 - 18:00 hs', 'Salon Cromo', null, null, 'Confirmado', 'Alquiler de pantalla LED con falcón de cabina | Alquiler de pantalla LED con falcón de cabina | DJ - Juany Quiess | Día completo', 'bfjchtsefnan3pfqh0h7u0bmg0'),
  ('evento', 'Evento Salon Campiña - 120 Invitados', null, '2026-09-07', '2026-09-07', '00:00-23:59 (día completo)', 'Salon Campiña', null, 120, 'Confirmado', 'Sonido Yamaha | DJ: Pepe Lapera', 'n5ruj4bl0m20p34m7t6hc7gnrk'),
  ('evento', 'Cumpleaños de 15 de Magali', 'Yanina La Torre', '2026-12-18', '2026-12-18', '21:00 hs', 'Hotel Mercure', 'Evento Social - Cumpleaños de 15', null, 'Vendido - 3 de febrero de 2026', 'Presupuesto: Premium', 's9p587180dm5bbhl0cs9kukdac');
