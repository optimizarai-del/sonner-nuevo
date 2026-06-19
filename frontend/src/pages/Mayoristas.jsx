import { useState, useEffect } from "react";
import { Plus, X, Pencil, Trash2, Phone, Store, Loader2, Search } from "lucide-react";
import { supabase } from "../utils/supabase";

// ── Helpers ───────────────────────────────────────────────────────────────────
const EMPTY_FORM = { identifier: "", nombre: "" };

// Normaliza a solo dígitos (para mostrar / validar)
function soloDigitos(s) {
  return (s || "").toString().replace(/[^0-9]/g, "");
}

// ── Modal alta / edición ──────────────────────────────────────────────────────
function MayoristaModal({ mayorista, onClose, onSave }) {
  const [form, setForm]     = useState(mayorista ?? EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function handleSave(e) {
    e.preventDefault();
    const id = soloDigitos(form.identifier);
    if (id.length < 8) { setError("El número debe tener al menos 8 dígitos"); return; }
    setSaving(true);
    setError("");
    const payload = { identifier: form.identifier.trim(), nombre: form.nombre.trim() };
    let err;
    if (mayorista?.id) {
      ({ error: err } = await supabase.from("mayoristas").update(payload).eq("id", mayorista.id));
    } else {
      ({ error: err } = await supabase.from("mayoristas").insert(payload));
    }
    if (err) {
      setError(err.code === "23505" ? "Ese número ya está cargado como mayorista." : err.message);
      setSaving(false);
      return;
    }
    onSave();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "#00000088" }}
      onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="w-full max-w-md rounded-2xl"
        style={{ background: "#161B22", border: "1px solid #21262D" }}>

        {/* Header */}
        <div className="px-6 py-4 flex items-center justify-between"
          style={{ borderBottom: "1px solid #21262D" }}>
          <h2 className="font-semibold text-white">
            {mayorista?.id ? "Editar mayorista" : "Nuevo mayorista"}
          </h2>
          <button onClick={onClose} className="hover:text-white transition-colors" style={{ color: "#484F58" }}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSave} className="p-6 space-y-5">
          <div>
            <label className="block text-xs font-medium mb-1" style={{ color: "#8B949E" }}>
              Número de WhatsApp *
            </label>
            <input value={form.identifier} onChange={set("identifier")} className="input w-full"
              placeholder="+54 9 2954 11-1111" autoFocus />
            <p className="text-[11px] mt-1" style={{ color: "#484F58" }}>
              Se compara por los últimos 8 dígitos, no importa el formato.
            </p>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1" style={{ color: "#8B949E" }}>
              Nombre / Empresa
            </label>
            <input value={form.nombre} onChange={set("nombre")} className="input w-full"
              placeholder="Distribuidora Pérez" />
          </div>

          {error && <p className="text-sm" style={{ color: "#f85149" }}>{error}</p>}

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm transition-colors" style={{ color: "#8B949E" }}>
              Cancelar
            </button>
            <button type="submit" disabled={saving}
              className="flex items-center gap-2 px-5 py-2 rounded-lg text-white text-sm font-medium disabled:opacity-50"
              style={{ background: "#2B6BF3" }}>
              {saving ? <Loader2 size={14} className="animate-spin" /> : null}
              {saving ? "Guardando..." : (mayorista?.id ? "Guardar cambios" : "Agregar mayorista")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Componente principal ──────────────────────────────────────────────────────
export default function Mayoristas() {
  const [items, setItems]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal]     = useState(null);   // null | { mode, mayorista }
  const [deleting, setDeleting] = useState(null);
  const [search, setSearch]   = useState("");

  async function load() {
    setLoading(true);
    const { data } = await supabase
      .from("mayoristas")
      .select("*")
      .order("created_at", { ascending: false });
    setItems(data ?? []);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function confirmDelete() {
    if (!deleting) return;
    setItems((prev) => prev.filter((m) => m.id !== deleting.id));
    await supabase.from("mayoristas").delete().eq("id", deleting.id);
    setDeleting(null);
  }

  const filtered = items.filter((m) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      m.nombre?.toLowerCase().includes(q) ||
      m.identifier?.includes(q) ||
      soloDigitos(m.identifier).includes(soloDigitos(search))
    );
  });

  return (
    <div className="flex flex-col h-full overflow-hidden">

      {/* Header */}
      <div className="px-6 py-4 shrink-0" style={{ borderBottom: "1px solid #21262D" }}>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Store size={20} style={{ color: "#D29922" }} />
              Mayoristas
            </h1>
            <p className="text-sm mt-0.5" style={{ color: "#8B949E" }}>
              {items.length} {items.length === 1 ? "número" : "números"} · El agente los atiende con tarifa mayorista
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "#484F58" }} />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar número o empresa..."
                className="input text-sm h-9 pl-9"
                style={{ width: "240px" }}
              />
            </div>
            <button
              onClick={() => setModal({ mode: "new" })}
              className="flex items-center gap-2 text-white text-sm font-medium px-4 py-2 rounded-lg"
              style={{ background: "#2B6BF3" }}
            >
              <Plus size={15} />
              Nuevo mayorista
            </button>
          </div>
        </div>
      </div>

      {/* Lista */}
      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 size={24} className="animate-spin" style={{ color: "#2B6BF3" }} />
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2" style={{ color: "#484F58" }}>
          <Store size={32} />
          <p className="text-sm">
            {search ? "Sin resultados para esa búsqueda" : "Todavía no cargaste ningún mayorista"}
          </p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-4">
          <div className="max-w-3xl mx-auto rounded-xl overflow-hidden"
            style={{ border: "1px solid #21262D" }}>
            {filtered.map((m, i) => (
              <div key={m.id}
                className="flex items-center justify-between gap-3 px-4 py-3 group transition-colors hover:bg-[#1C2230]"
                style={{ background: "#161B22", borderTop: i === 0 ? "none" : "1px solid #21262D" }}>
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                    style={{ background: "#D2992218", color: "#D29922" }}>
                    <Phone size={14} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white truncate">
                      {m.nombre || "(sin nombre)"}
                    </p>
                    <p className="text-xs" style={{ color: "#8B949E" }}>{m.identifier}</p>
                  </div>
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                  <button onClick={() => setModal({ mode: "edit", mayorista: m })}
                    className="p-1.5 rounded transition-colors hover:bg-[#21262D]" style={{ color: "#8B949E" }}>
                    <Pencil size={13} />
                  </button>
                  <button onClick={() => setDeleting(m)}
                    className="p-1.5 rounded transition-colors hover:bg-[#21262D]" style={{ color: "#8B949E" }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = "#f85149")}
                    onMouseLeave={(e) => (e.currentTarget.style.color = "#8B949E")}>
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal alta/edición */}
      {modal && (
        <MayoristaModal
          mayorista={modal.mode === "edit" ? modal.mayorista : null}
          onClose={() => setModal(null)}
          onSave={() => { setModal(null); load(); }}
        />
      )}

      {/* Confirmar eliminación */}
      {deleting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "#00000088" }}>
          <div className="w-full max-w-sm rounded-2xl p-6" style={{ background: "#161B22", border: "1px solid #21262D" }}>
            <h3 className="font-semibold text-white mb-2">¿Quitar mayorista?</h3>
            <p className="text-sm mb-5" style={{ color: "#8B949E" }}>
              <strong className="text-white">{deleting.nombre || deleting.identifier}</strong> volverá a atenderse como minorista.
            </p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setDeleting(null)} className="px-4 py-2 text-sm" style={{ color: "#8B949E" }}>
                Cancelar
              </button>
              <button onClick={confirmDelete}
                className="px-4 py-2 rounded-lg text-white text-sm font-medium" style={{ background: "#F85149" }}>
                Quitar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
