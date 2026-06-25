import { useState, useMemo } from "react";
import {
  Package, Search, Plus, Pencil, Trash2, Filter,
  Boxes, CircleCheck, Wrench, CalendarClock,
} from "lucide-react";
import { getUser } from "../utils/auth";

// ── Datos de ejemplo (TODO: reemplazar por fetch a la tabla `materiales` de Supabase) ──
const SAMPLE = [
  { id: 1, nombre: "Parlante activo 15\"",      categoria: "Sonido",       total: 8,  disponible: 5, estado: "ok",        ubicacion: "Depósito A" },
  { id: 2, nombre: "Subwoofer 18\"",            categoria: "Sonido",       total: 4,  disponible: 2, estado: "ok",        ubicacion: "Depósito A" },
  { id: 3, nombre: "Consola digital 32ch",      categoria: "Sonido",       total: 2,  disponible: 1, estado: "ok",        ubicacion: "Depósito A" },
  { id: 4, nombre: "Moving head LED",           categoria: "Iluminación",  total: 12, disponible: 6, estado: "ok",        ubicacion: "Depósito B" },
  { id: 5, nombre: "Par LED RGBW",              categoria: "Iluminación",  total: 24, disponible: 18, estado: "ok",       ubicacion: "Depósito B" },
  { id: 6, nombre: "Máquina de humo",           categoria: "Efectos",      total: 3,  disponible: 0, estado: "reparacion", ubicacion: "Taller" },
  { id: 7, nombre: "Pantalla LED P3 (módulo)",  categoria: "Video",        total: 40, disponible: 40, estado: "ok",       ubicacion: "Depósito C" },
  { id: 8, nombre: "Micrófono inalámbrico",     categoria: "Sonido",       total: 10, disponible: 7, estado: "ok",        ubicacion: "Depósito A" },
];

const CATEGORIAS = ["Todas", "Sonido", "Iluminación", "Video", "Efectos"];

const ESTADO_META = {
  ok:         { label: "Disponible",  color: "#3FB950" },
  reparacion: { label: "En reparación", color: "#D29922" },
  baja:       { label: "De baja",     color: "#F85149" },
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

export default function Materiales() {
  const role = getUser()?.role || "armador";
  const isAdmin = role === "admin";

  const [items] = useState(SAMPLE);
  const [search, setSearch] = useState("");
  const [cat, setCat] = useState("Todas");

  const filtered = useMemo(() => items.filter((m) => {
    const okCat = cat === "Todas" || m.categoria === cat;
    const okSearch = !search.trim() || m.nombre.toLowerCase().includes(search.toLowerCase());
    return okCat && okSearch;
  }), [items, search, cat]);

  const stats = useMemo(() => ({
    total: items.reduce((a, m) => a + m.total, 0),
    disponible: items.reduce((a, m) => a + m.disponible, 0),
    asignado: items.reduce((a, m) => a + (m.total - m.disponible), 0),
    reparacion: items.filter((m) => m.estado === "reparacion").length,
  }), [items]);

  return (
    <div className="p-6 space-y-5 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: "#A371F722", border: "1px solid #A371F744" }}>
            <Package size={18} style={{ color: "#A371F7" }} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Materiales</h1>
            <p className="text-sm" style={{ color: "#8B949E" }}>Inventario de sonido, iluminación y video</p>
          </div>
        </div>
        {isAdmin && (
          <button className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white"
            style={{ background: "#2B6BF3" }}>
            <Plus size={15} /> Agregar material
          </button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard icon={Boxes}        label="Total"        value={stats.total}      color="#A371F7" />
        <StatCard icon={CircleCheck}  label="Disponibles"  value={stats.disponible} color="#3FB950" />
        <StatCard icon={CalendarClock} label="Asignados"   value={stats.asignado}   color="#2B6BF3" />
        <StatCard icon={Wrench}       label="En reparación" value={stats.reparacion} color="#D29922" />
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "#484F58" }} />
          <input value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar material..." className="input pl-8 text-sm h-9 w-full" />
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <Filter size={13} style={{ color: "#6E7681" }} />
          {CATEGORIAS.map((c) => (
            <button key={c} onClick={() => setCat(c)}
              className="px-3 py-1.5 rounded-full text-[12px] font-medium transition-colors"
              style={cat === c
                ? { background: "#A371F7", color: "#fff" }
                : { background: "#161B22", color: "#8B949E", border: "1px solid #21262D" }}>
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Tabla */}
      <div className="rounded-xl overflow-hidden" style={{ background: "#161B22", border: "1px solid #21262D" }}>
        <table className="w-full text-sm">
          <thead>
            <tr style={{ borderBottom: "1px solid #21262D" }} className="text-[11px] uppercase tracking-wider" >
              <th className="text-left px-4 py-3 font-medium" style={{ color: "#6E7681" }}>Material</th>
              <th className="text-left px-4 py-3 font-medium" style={{ color: "#6E7681" }}>Categoría</th>
              <th className="text-center px-4 py-3 font-medium" style={{ color: "#6E7681" }}>Disp. / Total</th>
              <th className="text-left px-4 py-3 font-medium hidden md:table-cell" style={{ color: "#6E7681" }}>Ubicación</th>
              <th className="text-left px-4 py-3 font-medium" style={{ color: "#6E7681" }}>Estado</th>
              {isAdmin && <th className="text-right px-4 py-3 font-medium" style={{ color: "#6E7681" }}>Acciones</th>}
            </tr>
          </thead>
          <tbody>
            {filtered.map((m, i) => {
              const em = ESTADO_META[m.estado] || ESTADO_META.ok;
              const pct = m.total ? Math.round((m.disponible / m.total) * 100) : 0;
              return (
                <tr key={m.id} style={{ borderBottom: i < filtered.length - 1 ? "1px solid #21262D" : "none" }}>
                  <td className="px-4 py-3 text-white font-medium">{m.nombre}</td>
                  <td className="px-4 py-3" style={{ color: "#8B949E" }}>{m.categoria}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 justify-center">
                      <span className="tabular-nums font-medium text-white">{m.disponible}/{m.total}</span>
                      <div className="w-16 h-1.5 rounded-full overflow-hidden" style={{ background: "#0D1117" }}>
                        <div className="h-full" style={{ width: `${pct}%`, background: pct > 30 ? "#3FB950" : "#D29922" }} />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell" style={{ color: "#8B949E" }}>{m.ubicacion}</td>
                  <td className="px-4 py-3">
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-full"
                      style={{ background: `${em.color}22`, color: em.color }}>{em.label}</span>
                  </td>
                  {isAdmin && (
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 justify-end">
                        <button className="p-1.5 rounded hover:bg-[#1C2230]" style={{ color: "#8B949E" }}><Pencil size={14} /></button>
                        <button className="p-1.5 rounded hover:bg-[#1C2230]" style={{ color: "#8B949E" }}><Trash2 size={14} /></button>
                      </div>
                    </td>
                  )}
                </tr>
              );
            })}
            {!filtered.length && (
              <tr><td colSpan={isAdmin ? 6 : 5} className="px-4 py-10 text-center" style={{ color: "#6E7681" }}>Sin resultados.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="text-[11px]" style={{ color: "#484F58" }}>
        * Datos de ejemplo — pendiente conectar a la tabla `materiales` de Supabase.
      </p>
    </div>
  );
}
