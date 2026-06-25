import { useState, useEffect, useMemo, useCallback } from "react";
import {
  CalendarDays, Search, Plus, MapPin, Clock, Package, X, Trash2,
  CalendarClock, History, CircleCheck, Filter, Pencil, Loader2,
} from "lucide-react";
import { supabase } from "../utils/supabase";
import { getUser } from "../utils/auth";

const TIPOS = ["evento", "alquiler"];
const EMPTY = { tipo: "evento", nombre: "", cliente: "", fecha_inicio: "", fecha_fin: "", hora: "", lugar: "", asistentes: "", estado: "confirmado" };

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="rounded-xl p-4 flex items-center gap-3" style={{ background: "#161B22", border: "1px solid #21262D" }}>
      <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" style={{ background: `${color}22`, border: `1px solid ${color}44` }}>
        <Icon size={16} style={{ color }} />
      </div>
      <div>
        <div className="text-[10px] uppercase tracking-wider" style={{ color: "#6E7681" }}>{label}</div>
        <div className="text-xl font-semibold text-white">{value}</div>
      </div>
    </div>
  );
}

const hoyISO = () => new Date().toISOString().slice(0, 10);
function fechaTxt(iso) {
  if (!iso) return "—";
  try { return new Date(iso + "T00:00:00").toLocaleDateString("es-AR", { weekday: "short", day: "2-digit", month: "short" }); }
  catch { return iso; }
}

// ── Modal alta/edición de evento ──────────────────────────────────────────────
function EventoModal({ open, onClose, onSaved, initial }) {
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => { setForm(initial ? { ...EMPTY, ...initial } : EMPTY); setErr(""); }, [initial, open]);
  if (!open) return null;
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const save = async () => {
    if (!form.fecha_inicio) { setErr("La fecha de inicio es obligatoria."); return; }
    setBusy(true); setErr("");
    const payload = {
      tipo: form.tipo, nombre: form.nombre?.trim() || null, cliente: form.cliente?.trim() || null,
      fecha_inicio: form.fecha_inicio, fecha_fin: form.fecha_fin || form.fecha_inicio,
      hora: form.hora?.trim() || null, lugar: form.lugar?.trim() || null,
      asistentes: form.asistentes ? Number(form.asistentes) : null, estado: form.estado,
    };
    const q = form.id ? supabase.from("eventos").update(payload).eq("id", form.id) : supabase.from("eventos").insert(payload);
    const { error } = await q;
    setBusy(false);
    if (error) { setErr(error.message); return; }
    onSaved();
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,.6)" }}>
      <div className="w-full max-w-lg rounded-2xl p-6" style={{ background: "#0D1117", border: "1px solid #30363D" }}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">{form.id ? "Editar evento" : "Nuevo evento"}</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-[#1C2230]" style={{ color: "#8B949E" }}><X size={18} /></button>
        </div>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px]" style={{ color: "#8B949E" }}>Tipo</label>
              <select className="input w-full text-sm mt-1" value={form.tipo} onChange={(e) => set("tipo", e.target.value)}>
                {TIPOS.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[11px]" style={{ color: "#8B949E" }}>Estado</label>
              <input className="input w-full text-sm mt-1" value={form.estado} onChange={(e) => set("estado", e.target.value)} />
            </div>
          </div>
          <div>
            <label className="text-[11px]" style={{ color: "#8B949E" }}>Nombre</label>
            <input className="input w-full text-sm mt-1" value={form.nombre} onChange={(e) => set("nombre", e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px]" style={{ color: "#8B949E" }}>Cliente</label>
              <input className="input w-full text-sm mt-1" value={form.cliente || ""} onChange={(e) => set("cliente", e.target.value)} />
            </div>
            <div>
              <label className="text-[11px]" style={{ color: "#8B949E" }}>Invitados</label>
              <input type="number" min="0" className="input w-full text-sm mt-1" value={form.asistentes || ""} onChange={(e) => set("asistentes", e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px]" style={{ color: "#8B949E" }}>Fecha inicio *</label>
              <input type="date" className="input w-full text-sm mt-1" value={form.fecha_inicio} onChange={(e) => set("fecha_inicio", e.target.value)} />
            </div>
            <div>
              <label className="text-[11px]" style={{ color: "#8B949E" }}>Fecha fin</label>
              <input type="date" className="input w-full text-sm mt-1" value={form.fecha_fin || ""} onChange={(e) => set("fecha_fin", e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px]" style={{ color: "#8B949E" }}>Hora</label>
              <input className="input w-full text-sm mt-1" value={form.hora || ""} onChange={(e) => set("hora", e.target.value)} />
            </div>
            <div>
              <label className="text-[11px]" style={{ color: "#8B949E" }}>Lugar / salón</label>
              <input className="input w-full text-sm mt-1" value={form.lugar || ""} onChange={(e) => set("lugar", e.target.value)} />
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

// ── Modal de materiales asignados + asignar con disponibilidad por fecha ───────
function MaterialesModal({ open, onClose, evento, onChanged }) {
  const [asignados, setAsignados] = useState([]);
  const [catalogo, setCatalogo] = useState([]);
  const [matSel, setMatSel] = useState("");
  const [cant, setCant] = useState(1);
  const [dispo, setDispo] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const cargar = useCallback(async () => {
    if (!evento) return;
    const { data } = await supabase.from("evento_materiales")
      .select("id, cantidad, material_id, materiales(producto, categoria)").eq("evento_id", evento.id);
    setAsignados(data || []);
    if (!catalogo.length) {
      const r = await supabase.from("materiales").select("id, producto, categoria, stock_total").order("categoria").order("producto");
      setCatalogo(r.data || []);
    }
  }, [evento]); // eslint-disable-line
  useEffect(() => { if (open) { setMatSel(""); setCant(1); setDispo(null); setErr(""); cargar(); } }, [open, cargar]);

  // Al elegir un material, consultar disponibilidad en la fecha del evento
  useEffect(() => {
    (async () => {
      if (!matSel || !evento) { setDispo(null); return; }
      const { data, error } = await supabase.rpc("disponibilidad_material", { p_material: Number(matSel), p_fecha: evento.fecha_inicio });
      setDispo(error ? null : data);
    })();
  }, [matSel, evento]);

  if (!open || !evento) return null;

  const asignar = async () => {
    if (!matSel) { setErr("Elegí un material."); return; }
    setBusy(true); setErr("");
    const { error } = await supabase.from("evento_materiales")
      .upsert({ evento_id: evento.id, material_id: Number(matSel), cantidad: Number(cant) || 1 }, { onConflict: "evento_id,material_id" });
    setBusy(false);
    if (error) { setErr(error.message); return; }
    setMatSel(""); setCant(1); cargar(); onChanged?.();
  };
  const quitar = async (id) => { await supabase.from("evento_materiales").delete().eq("id", id); cargar(); onChanged?.(); };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,.6)" }}>
      <div className="w-full max-w-xl rounded-2xl p-6" style={{ background: "#0D1117", border: "1px solid #30363D" }}>
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-lg font-semibold text-white">Materiales del evento</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-[#1C2230]" style={{ color: "#8B949E" }}><X size={18} /></button>
        </div>
        <p className="text-xs mb-4" style={{ color: "#6E7681" }}>{evento.nombre} · {fechaTxt(evento.fecha_inicio)}</p>

        {/* Asignados */}
        <div className="space-y-1.5 mb-4">
          {asignados.length === 0 && <div className="text-sm py-3 text-center" style={{ color: "#6E7681" }}>Sin materiales asignados.</div>}
          {asignados.map((a) => (
            <div key={a.id} className="flex items-center gap-3 px-3 py-2 rounded-lg" style={{ background: "#161B22", border: "1px solid #21262D" }}>
              <span className="text-sm text-white flex-1">{a.materiales?.producto || `#${a.material_id}`}</span>
              <span className="text-xs" style={{ color: "#8B949E" }}>{a.materiales?.categoria}</span>
              <span className="text-sm font-semibold tabular-nums text-white">×{a.cantidad}</span>
              <button onClick={() => quitar(a.id)} className="p-1 rounded hover:bg-[#1C2230]" style={{ color: "#8B949E" }}><Trash2 size={13} /></button>
            </div>
          ))}
        </div>

        {/* Asignar nuevo */}
        <div className="rounded-lg p-3" style={{ background: "#161B22", border: "1px solid #21262D" }}>
          <div className="text-[11px] uppercase tracking-wider mb-2" style={{ color: "#6E7681" }}>Asignar material</div>
          <div className="flex gap-2 items-end">
            <div className="flex-1">
              <select className="input w-full text-sm" value={matSel} onChange={(e) => setMatSel(e.target.value)}>
                <option value="">Elegir material…</option>
                {catalogo.map((m) => <option key={m.id} value={m.id}>{m.categoria} · {m.producto}</option>)}
              </select>
            </div>
            <input type="number" min="1" className="input text-sm w-20" value={cant} onChange={(e) => setCant(e.target.value)} />
            <button onClick={asignar} disabled={busy || !matSel} className="flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50" style={{ background: "#2B6BF3" }}>
              {busy ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
            </button>
          </div>
          {matSel && dispo !== null && (
            <div className="text-[12px] mt-2" style={{ color: dispo >= Number(cant) ? "#3FB950" : "#F85149" }}>
              {dispo} disponible(s) el {fechaTxt(evento.fecha_inicio)}{dispo < Number(cant) ? " — ¡no alcanza!" : ""}
            </div>
          )}
          {err && <div className="text-[12px] mt-2" style={{ color: "#F85149" }}>{err}</div>}
        </div>
      </div>
    </div>
  );
}

// ── Página ────────────────────────────────────────────────────────────────────
export default function Eventos() {
  const role = getUser()?.role || "armador";
  const isAdmin = role === "admin";
  const esMayorista = role === "mayorista";
  const [items, setItems] = useState([]);
  const [counts, setCounts] = useState({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [periodo, setPeriodo] = useState("todos");
  const [modal, setModal] = useState({ open: false, initial: null });
  const [matModal, setMatModal] = useState({ open: false, evento: null });

  const load = useCallback(async () => {
    setLoading(true);
    const { data } = await supabase.from("eventos").select("*").order("fecha_inicio");
    setItems(data || []);
    const em = await supabase.from("evento_materiales").select("evento_id");
    const map = {};
    (em.data || []).forEach((r) => { map[r.evento_id] = (map[r.evento_id] || 0) + 1; });
    setCounts(map);
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => items.filter((e) => {
    const hoy = hoyISO();
    const okPer = periodo === "todos" || (periodo === "proximos" ? e.fecha_inicio >= hoy : e.fecha_inicio < hoy);
    const okSearch = !search.trim() || `${e.nombre || ""} ${e.lugar || ""}`.toLowerCase().includes(search.toLowerCase());
    return okPer && okSearch;
  }), [items, search, periodo]);

  const stats = useMemo(() => {
    const hoy = hoyISO();
    return {
      proximos: items.filter((e) => e.fecha_inicio >= hoy).length,
      alquileres: items.filter((e) => e.tipo === "alquiler").length,
      total: items.length,
    };
  }, [items]);

  const del = async (e) => { if (!window.confirm(`¿Eliminar "${e.nombre}"?`)) return; await supabase.from("eventos").delete().eq("id", e.id); load(); };

  return (
    <div className="p-6 space-y-5 max-w-6xl mx-auto">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: "#2B6BF322", border: "1px solid #2B6BF344" }}>
            <CalendarDays size={18} style={{ color: "#2B6BF3" }} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Eventos</h1>
            <p className="text-sm" style={{ color: "#8B949E" }}>{esMayorista ? "Disponibilidad de fechas" : "Gestión y armado de eventos"}</p>
          </div>
        </div>
        {isAdmin && (
          <button onClick={() => setModal({ open: true, initial: null })} className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white" style={{ background: "#2B6BF3" }}>
            <Plus size={15} /> Nuevo evento
          </button>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <StatCard icon={CalendarClock} label="Próximos" value={stats.proximos} color="#2B6BF3" />
        <StatCard icon={Package} label="Alquileres" value={stats.alquileres} color="#3FB950" />
        <StatCard icon={CircleCheck} label="Total" value={stats.total} color="#A371F7" />
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "#484F58" }} />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar evento o salón..." className="input pl-8 text-sm h-9 w-full" />
        </div>
        <div className="flex items-center gap-1.5">
          <Filter size={13} style={{ color: "#6E7681" }} />
          {[["todos", "Todos"], ["proximos", "Próximos"], ["pasados", "Pasados"]].map(([k, l]) => (
            <button key={k} onClick={() => setPeriodo(k)} className="px-3 py-1.5 rounded-full text-[12px] font-medium transition-colors"
              style={periodo === k ? { background: "#2B6BF3", color: "#fff" } : { background: "#161B22", color: "#8B949E", border: "1px solid #21262D" }}>{l}</button>
          ))}
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {loading && <div className="md:col-span-2 py-12 text-center"><Loader2 size={20} className="animate-spin mx-auto" style={{ color: "#484F58" }} /></div>}
        {!loading && filtered.map((e) => {
          const futuro = e.fecha_inicio >= hoyISO();
          const badge = futuro ? { label: "Próximo", color: "#2B6BF3" } : { label: "Pasado", color: "#6E7681" };
          return (
            <div key={e.id} className="rounded-xl p-4" style={{ background: "#161B22", border: "1px solid #21262D" }}>
              <div className="flex items-start justify-between gap-2 mb-3">
                <div>
                  <h3 className="font-semibold text-white">{esMayorista ? "Reservado" : (e.nombre || "(sin nombre)")}</h3>
                  {!esMayorista && (e.cliente || e.tipo === "alquiler") && (
                    <p className="text-xs mt-0.5" style={{ color: "#6E7681" }}>{e.cliente || ""}{e.tipo === "alquiler" ? " · alquiler" : ""}</p>
                  )}
                </div>
                <span className="text-[11px] font-medium px-2 py-0.5 rounded-full shrink-0" style={{ background: `${badge.color}22`, color: badge.color }}>{badge.label}</span>
              </div>
              <div className="space-y-1.5 text-[13px]" style={{ color: "#C9D1D9" }}>
                <div className="flex items-center gap-2"><CalendarDays size={13} style={{ color: "#6E7681" }} /> {fechaTxt(e.fecha_inicio)}{e.hora ? " · " + e.hora : ""}</div>
                {e.lugar && <div className="flex items-center gap-2"><MapPin size={13} style={{ color: "#6E7681" }} /> {e.lugar}</div>}
                {!esMayorista && (
                  <div className="flex items-center gap-4">
                    {e.asistentes ? <span className="flex items-center gap-2"><Clock size={13} style={{ color: "#6E7681" }} /> {e.asistentes} pax</span> : null}
                    <span className="flex items-center gap-2"><Package size={13} style={{ color: "#6E7681" }} /> {counts[e.id] || 0} ítems</span>
                  </div>
                )}
              </div>
              {!esMayorista && (
                <div className="flex items-center gap-2 mt-3 pt-3" style={{ borderTop: "1px solid #21262D" }}>
                  <button onClick={() => setMatModal({ open: true, evento: e })} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium" style={{ background: "#0D1117", color: "#8B949E", border: "1px solid #30363D" }}>
                    <Package size={13} /> Ver materiales
                  </button>
                  {isAdmin && (
                    <>
                      <button onClick={() => setModal({ open: true, initial: e })} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium" style={{ background: "#0D1117", color: "#8B949E", border: "1px solid #30363D" }}>
                        <Pencil size={13} /> Editar
                      </button>
                      <button onClick={() => del(e)} className="p-1.5 rounded-lg" style={{ color: "#8B949E" }}><Trash2 size={13} /></button>
                    </>
                  )}
                </div>
              )}
            </div>
          );
        })}
        {!loading && !filtered.length && (
          <div className="md:col-span-2 rounded-xl p-10 text-center" style={{ background: "#161B22", border: "1px solid #21262D", color: "#6E7681" }}>No hay eventos en este filtro.</div>
        )}
      </div>

      <EventoModal open={modal.open} initial={modal.initial} onClose={() => setModal({ open: false, initial: null })} onSaved={() => { setModal({ open: false, initial: null }); load(); }} />
      <MaterialesModal open={matModal.open} evento={matModal.evento} onClose={() => setMatModal({ open: false, evento: null })} onChanged={load} />
    </div>
  );
}
