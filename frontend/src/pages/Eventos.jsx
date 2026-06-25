import { useState, useMemo } from "react";
import {
  CalendarDays, Search, Plus, MapPin, Clock, Package,
  CalendarClock, Hammer, CircleCheck, Filter, Pencil,
} from "lucide-react";
import { getUser } from "../utils/auth";

// ── Datos de ejemplo (TODO: reemplazar por fetch a la tabla `eventos` de Supabase) ──
const SAMPLE = [
  { id: 1, titulo: "Casamiento Rodríguez", salon: "Salón Cromo",    fecha: "2026-07-04", hora: "21:00", estado: "proximo",   pax: 120, materiales: 14, cliente: "Ana Rodríguez" },
  { id: 2, titulo: "15 años Martina",      salon: "Salón Tijereta", fecha: "2026-07-05", hora: "22:00", estado: "armado",    pax: 200, materiales: 22, cliente: "Flia. Gómez" },
  { id: 3, titulo: "Corporativo Tech SA",  salon: "Quincho El Roble", fecha: "2026-07-11", hora: "13:00", estado: "proximo", pax: 80,  materiales: 9,  cliente: "Tech SA" },
  { id: 4, titulo: "Cumple 50 Jorge",      salon: "Salón Monet",    fecha: "2026-06-20", hora: "21:30", estado: "finalizado", pax: 90,  materiales: 11, cliente: "Jorge P." },
];

const ESTADOS = [
  { key: "todos",      label: "Todos" },
  { key: "proximo",    label: "Próximos" },
  { key: "armado",     label: "En armado" },
  { key: "finalizado", label: "Finalizados" },
];

const ESTADO_META = {
  proximo:    { label: "Próximo",    color: "#2B6BF3" },
  armado:     { label: "Armado",     color: "#3FB950" },
  finalizado: { label: "Finalizado", color: "#6E7681" },
};

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="rounded-xl p-4 flex items-center gap-3" style={{ background: "#161B22", border: "1px solid #21262D" }}>
      <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
        style={{ background: `${color}22`, border: `1px solid ${color}44` }}>
        <Icon size={16} style={{ color }} />
      </div>
      <div>
        <div className="text-[10px] uppercase tracking-wider" style={{ color: "#6E7681" }}>{label}</div>
        <div className="text-xl font-semibold text-white">{value}</div>
      </div>
    </div>
  );
}

function fechaTxt(iso) {
  try { return new Date(iso + "T00:00:00").toLocaleDateString("es-AR", { weekday: "short", day: "2-digit", month: "short" }); }
  catch { return iso; }
}

export default function Eventos() {
  const role = getUser()?.role || "armador";
  const isAdmin = role === "admin";
  const esMayorista = role === "mayorista"; // mayorista: vista de disponibilidad, sin datos del cliente

  const [items] = useState(SAMPLE);
  const [search, setSearch] = useState("");
  const [estado, setEstado] = useState("todos");

  const filtered = useMemo(() => items.filter((e) => {
    const okEstado = estado === "todos" || e.estado === estado;
    const okSearch = !search.trim() ||
      (e.titulo + " " + e.salon).toLowerCase().includes(search.toLowerCase());
    return okEstado && okSearch;
  }), [items, search, estado]);

  const stats = useMemo(() => ({
    proximos: items.filter((e) => e.estado === "proximo").length,
    armado:   items.filter((e) => e.estado === "armado").length,
    mes:      items.length,
  }), [items]);

  return (
    <div className="p-6 space-y-5 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: "#2B6BF322", border: "1px solid #2B6BF344" }}>
            <CalendarDays size={18} style={{ color: "#2B6BF3" }} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Eventos</h1>
            <p className="text-sm" style={{ color: "#8B949E" }}>
              {esMayorista ? "Disponibilidad de fechas" : "Gestión y armado de eventos"}
            </p>
          </div>
        </div>
        {isAdmin && (
          <button className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white"
            style={{ background: "#2B6BF3" }}>
            <Plus size={15} /> Nuevo evento
          </button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <StatCard icon={CalendarClock} label="Próximos"   value={stats.proximos} color="#2B6BF3" />
        <StatCard icon={Hammer}        label="En armado"  value={stats.armado}   color="#3FB950" />
        <StatCard icon={CircleCheck}   label="Total"      value={stats.mes}      color="#A371F7" />
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "#484F58" }} />
          <input value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar evento o salón..." className="input pl-8 text-sm h-9 w-full" />
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <Filter size={13} style={{ color: "#6E7681" }} />
          {ESTADOS.map((s) => (
            <button key={s.key} onClick={() => setEstado(s.key)}
              className="px-3 py-1.5 rounded-full text-[12px] font-medium transition-colors"
              style={estado === s.key
                ? { background: "#2B6BF3", color: "#fff" }
                : { background: "#161B22", color: "#8B949E", border: "1px solid #21262D" }}>
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Cards de eventos */}
      <div className="grid gap-3 md:grid-cols-2">
        {filtered.map((e) => {
          const em = ESTADO_META[e.estado] || ESTADO_META.proximo;
          return (
            <div key={e.id} className="rounded-xl p-4" style={{ background: "#161B22", border: "1px solid #21262D" }}>
              <div className="flex items-start justify-between gap-2 mb-3">
                <div>
                  <h3 className="font-semibold text-white">
                    {esMayorista ? "Reservado" : e.titulo}
                  </h3>
                  {!esMayorista && <p className="text-xs mt-0.5" style={{ color: "#6E7681" }}>{e.cliente}</p>}
                </div>
                <span className="text-[11px] font-medium px-2 py-0.5 rounded-full shrink-0"
                  style={{ background: `${em.color}22`, color: em.color }}>{em.label}</span>
              </div>
              <div className="space-y-1.5 text-[13px]" style={{ color: "#C9D1D9" }}>
                <div className="flex items-center gap-2"><CalendarDays size={13} style={{ color: "#6E7681" }} /> {fechaTxt(e.fecha)} · {e.hora}</div>
                <div className="flex items-center gap-2"><MapPin size={13} style={{ color: "#6E7681" }} /> {e.salon}</div>
                {!esMayorista && (
                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-2"><Clock size={13} style={{ color: "#6E7681" }} /> {e.pax} pax</span>
                    <span className="flex items-center gap-2"><Package size={13} style={{ color: "#6E7681" }} /> {e.materiales} ítems</span>
                  </div>
                )}
              </div>
              {!esMayorista && (
                <div className="flex items-center gap-2 mt-3 pt-3" style={{ borderTop: "1px solid #21262D" }}>
                  <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium"
                    style={{ background: "#0D1117", color: "#8B949E", border: "1px solid #30363D" }}>
                    <Package size={13} /> Ver materiales
                  </button>
                  {(isAdmin || role === "armador") && (
                    <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium"
                      style={{ background: "#0D1117", color: "#8B949E", border: "1px solid #30363D" }}>
                      <Pencil size={13} /> {role === "armador" ? "Marcar armado" : "Editar"}
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
        {!filtered.length && (
          <div className="md:col-span-2 rounded-xl p-10 text-center" style={{ background: "#161B22", border: "1px solid #21262D", color: "#6E7681" }}>
            No hay eventos en este estado.
          </div>
        )}
      </div>

      <p className="text-[11px]" style={{ color: "#484F58" }}>
        * Datos de ejemplo — pendiente conectar a la tabla `eventos` de Supabase.
      </p>
    </div>
  );
}
