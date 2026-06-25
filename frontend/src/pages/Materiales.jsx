import { useState, useEffect, useMemo, useCallback } from "react";
import {
  Package, Search, Plus, Pencil, Trash2, Filter, X,
  Boxes, CircleCheck, Wrench, CalendarClock, Loader2,
} from "lucide-react";
import { supabase } from "../utils/supabase";
import { getUser } from "../utils/auth";

const ESTADO_META = {
  ok:         { label: "Disponible",    color: "#3FB950" },
  reparacion: { label: "En reparación", color: "#D29922" },
  baja:       { label: "De baja",       color: "#F85149" },
};
const ESTADOS = ["ok", "reparacion", "baja"];
const EMPTY = { categoria: "", producto: "", stock_total: 0, ubicacion: "", estado: "ok" };

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

function MaterialModal({ open, onClose, onSaved, initial }) {
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => { setForm(initial ? { ...EMPTY, ...initial } : EMPTY); setErr(""); }, [initial, open]);
  if (!open) return null;

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const save = async () => {
    if (!form.categoria.trim() || !form.producto.trim()) { setErr("Categoría y producto son obligatorios."); return; }
    setBusy(true); setErr("");
    const payload = {
      categoria: form.categoria.trim(), producto: form.producto.trim(),
      stock_total: Number(form.stock_total) || 0,
      ubicacion: form.ubicacion?.trim() || null, estado: form.estado,
    };
    const q = form.id
      ? supabase.from("materiales").update(payload).eq("id", form.id)
      : supabase.from("materiales").insert(payload);
    const { error } = await q;
    setBusy(false);
    if (error) { setErr(error.message); return; }
    onSaved();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,.6)" }}>
      <div className="w-full max-w-lg rounded-2xl p-6" style={{ background: "#0D1117", border: "1px solid #30363D" }}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">{form.id ? "Editar material" : "Nuevo material"}</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-[#1C2230]" style={{ color: "#8B949E" }}><X size={18} /></button>
        </div>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px]" style={{ color: "#8B949E" }}>Categoría *</label>
              <input className="input w-full text-sm mt-1" value={form.categoria} onChange={(e) => set("categoria", e.target.value)} />
            </div>
            <div>
              <label className="text-[11px]" style={{ color: "#8B949E" }}>Stock total</label>
              <input type="number" min="0" className="input w-full text-sm mt-1" value={form.stock_total} onChange={(e) => set("stock_total", e.target.value)} />
            </div>
          </div>
          <div>
            <label className="text-[11px]" style={{ color: "#8B949E" }}>Producto *</label>
            <input className="input w-full text-sm mt-1" value={form.producto} onChange={(e) => set("producto", e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px]" style={{ color: "#8B949E" }}>Ubicación</label>
              <input className="input w-full text-sm mt-1" value={form.ubicacion || ""} onChange={(e) => set("ubicacion", e.target.value)} />
            </div>
            <div>
              <label className="text-[11px]" style={{ color: "#8B949E" }}>Estado</label>
              <select className="input w-full text-sm mt-1" value={form.estado} onChange={(e) => set("estado", e.target.value)}>
                {ESTADOS.map((s) => <option key={s} value={s}>{ESTADO_META[s].label}</option>)}
              </select>
            </div>
          </div>
        </div>
        {err && <div className="mt-3 text-[12px]" style={{ color: "#F85149" }}>{err}</div>}
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-sm" style={{ color: "#8B949E" }}>Cancelar</button>
          <button onClick={save} disabled={busy} className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50" style={{ background: "#2B6BF3" }}>
            {busy ? <Loader2 size={14} className="animate-spin" /> : <CircleCheck size={14} />} Guardar
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Materiales() {
  const isAdmin = (getUser()?.role || "") === "admin";
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [cat, setCat] = useState("Todas");
  const [modal, setModal] = useState({ open: false, initial: null });

  const load = useCallback(async () => {
    setLoading(true);
    // La vista trae stock_total + disponible_hoy ya calculado
    const { data, error } = await supabase
      .from("v_disponibilidad_hoy")
      .select("*")
      .order("categoria").order("producto");
    if (!error && data) setItems(data);
    else {
      // fallback a la tabla si la vista no existe
      const r = await supabase.from("materiales").select("*").order("categoria").order("producto");
      setItems((r.data || []).map((m) => ({ ...m, disponible_hoy: m.stock_total })));
    }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const categorias = useMemo(() => ["Todas", ...Array.from(new Set(items.map((m) => m.categoria))).sort()], [items]);
  const filtered = useMemo(() => items.filter((m) => {
    const okCat = cat === "Todas" || m.categoria === cat;
    const okSearch = !search.trim() || m.producto.toLowerCase().includes(search.toLowerCase());
    return okCat && okSearch;
  }), [items, search, cat]);

  const stats = useMemo(() => ({
    total: items.reduce((a, m) => a + (m.stock_total || 0), 0),
    disponible: items.reduce((a, m) => a + (m.disponible_hoy ?? m.stock_total ?? 0), 0),
    asignado: items.reduce((a, m) => a + ((m.stock_total || 0) - (m.disponible_hoy ?? m.stock_total ?? 0)), 0),
    reparacion: items.filter((m) => m.estado === "reparacion").length,
  }), [items]);

  const del = async (m) => {
    if (!window.confirm(`¿Dar de baja "${m.producto}"?`)) return;
    await supabase.from("materiales").delete().eq("id", m.id);
    load();
  };

  return (
    <div className="p-6 space-y-5 max-w-6xl mx-auto">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: "#A371F722", border: "1px solid #A371F744" }}>
            <Package size={18} style={{ color: "#A371F7" }} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Materiales</h1>
            <p className="text-sm" style={{ color: "#8B949E" }}>Inventario de sonido, iluminación y video</p>
          </div>
        </div>
        {isAdmin && (
          <button onClick={() => setModal({ open: true, initial: null })} className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white" style={{ background: "#2B6BF3" }}>
            <Plus size={15} /> Agregar material
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard icon={Boxes} label="Total" value={stats.total} color="#A371F7" />
        <StatCard icon={CircleCheck} label="Disponibles hoy" value={stats.disponible} color="#3FB950" />
        <StatCard icon={CalendarClock} label="Asignados hoy" value={stats.asignado} color="#2B6BF3" />
        <StatCard icon={Wrench} label="En reparación" value={stats.reparacion} color="#D29922" />
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "#484F58" }} />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar material..." className="input pl-8 text-sm h-9 w-full" />
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <Filter size={13} style={{ color: "#6E7681" }} />
          {categorias.map((c) => (
            <button key={c} onClick={() => setCat(c)} className="px-3 py-1.5 rounded-full text-[12px] font-medium transition-colors"
              style={cat === c ? { background: "#A371F7", color: "#fff" } : { background: "#161B22", color: "#8B949E", border: "1px solid #21262D" }}>{c}</button>
          ))}
        </div>
      </div>

      <div className="rounded-xl overflow-hidden" style={{ background: "#161B22", border: "1px solid #21262D" }}>
        <table className="w-full text-sm">
          <thead>
            <tr style={{ borderBottom: "1px solid #21262D" }} className="text-[11px] uppercase tracking-wider">
              <th className="text-left px-4 py-3 font-medium" style={{ color: "#6E7681" }}>Material</th>
              <th className="text-left px-4 py-3 font-medium" style={{ color: "#6E7681" }}>Categoría</th>
              <th className="text-center px-4 py-3 font-medium" style={{ color: "#6E7681" }}>Disp. hoy / Total</th>
              <th className="text-left px-4 py-3 font-medium hidden md:table-cell" style={{ color: "#6E7681" }}>Ubicación</th>
              <th className="text-left px-4 py-3 font-medium" style={{ color: "#6E7681" }}>Estado</th>
              {isAdmin && <th className="text-right px-4 py-3 font-medium" style={{ color: "#6E7681" }}>Acciones</th>}
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={isAdmin ? 6 : 5} className="px-4 py-10 text-center"><Loader2 size={18} className="animate-spin mx-auto" style={{ color: "#484F58" }} /></td></tr>}
            {!loading && filtered.map((m, i) => {
              const em = ESTADO_META[m.estado] || ESTADO_META.ok;
              const disp = m.disponible_hoy ?? m.stock_total ?? 0;
              const pct = m.stock_total ? Math.round((disp / m.stock_total) * 100) : 0;
              return (
                <tr key={m.id} style={{ borderBottom: i < filtered.length - 1 ? "1px solid #21262D" : "none" }}>
                  <td className="px-4 py-3 text-white font-medium">{m.producto}</td>
                  <td className="px-4 py-3" style={{ color: "#8B949E" }}>{m.categoria}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 justify-center">
                      <span className="tabular-nums font-medium text-white">{disp}/{m.stock_total}</span>
                      <div className="w-16 h-1.5 rounded-full overflow-hidden" style={{ background: "#0D1117" }}>
                        <div className="h-full" style={{ width: `${pct}%`, background: pct > 30 ? "#3FB950" : "#D29922" }} />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell" style={{ color: "#8B949E" }}>{m.ubicacion || "—"}</td>
                  <td className="px-4 py-3"><span className="text-[11px] font-medium px-2 py-0.5 rounded-full" style={{ background: `${em.color}22`, color: em.color }}>{em.label}</span></td>
                  {isAdmin && (
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 justify-end">
                        <button onClick={() => setModal({ open: true, initial: m })} className="p-1.5 rounded hover:bg-[#1C2230]" style={{ color: "#8B949E" }}><Pencil size={14} /></button>
                        <button onClick={() => del(m)} className="p-1.5 rounded hover:bg-[#1C2230]" style={{ color: "#8B949E" }}><Trash2 size={14} /></button>
                      </div>
                    </td>
                  )}
                </tr>
              );
            })}
            {!loading && !filtered.length && <tr><td colSpan={isAdmin ? 6 : 5} className="px-4 py-10 text-center" style={{ color: "#6E7681" }}>Sin resultados.</td></tr>}
          </tbody>
        </table>
      </div>

      <MaterialModal open={modal.open} initial={modal.initial} onClose={() => setModal({ open: false, initial: null })} onSaved={() => { setModal({ open: false, initial: null }); load(); }} />
    </div>
  );
}
