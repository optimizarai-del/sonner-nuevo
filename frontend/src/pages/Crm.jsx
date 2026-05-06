import { useState, useEffect, useRef, useCallback } from "react";
import {
  Plus, X, Pencil, Trash2, Phone, Mail, MapPin,
  Calendar, DollarSign, MessageSquare, Users, Loader2,
  ChevronDown, StickyNote,
} from "lucide-react";
import { supabase } from "../utils/supabase";
import { format } from "date-fns";
import { es } from "date-fns/locale";

// ── Etapas ────────────────────────────────────────────────────────────────────
const ETAPAS = [
  { id: "CONSULTA_WHATSAPP",  label: "CONSULTA WHATSAPP",  color: "#25D366", bg: "#25D36618" },
  { id: "NUEVO_CLIENTE",      label: "NUEVO CLIENTE",      color: "#2B6BF3", bg: "#2B6BF318" },
  { id: "FECHA_CONFIRMADA",   label: "FECHA CONFIRMADA",   color: "#58A6FF", bg: "#58A6FF18" },
  { id: "CONTRATO_FIRMADO",   label: "CONTRATO FIRMADO",   color: "#3FB950", bg: "#3FB95018" },
  { id: "EN_PREPARACION",     label: "EN PREPARACION",     color: "#D29922", bg: "#D2992218" },
  { id: "CONCLUIDO",          label: "CONCLUIDO",          color: "#A371F7", bg: "#A371F718" },
  { id: "CANCELADO",          label: "CANCELADO",          color: "#F85149", bg: "#F8514918" },
  { id: "REPROGRAMADO",       label: "REPROGRAMADO",       color: "#8B949E", bg: "#8B949E18" },
];

const ETAPA_MAP = Object.fromEntries(ETAPAS.map((e) => [e.id, e]));

const CANALES = ["whatsapp", "instagram", "referido", "web", "telefono", "otro"];
const TIPOS_EVENTO = ["Cumpleaños", "Casamiento", "Fiesta", "Corporativo", "Quinceañero", "Aniversario", "Otro"];

const EMPTY_FORM = {
  nombre: "", telefono: "", email: "", canal_origen: "whatsapp",
  tipo_evento: "", lugar_evento: "", fecha_evento: "",
  hora_inicio: "", hora_fin: "", valor_total: "", senia: "",
  etapa: "CONSULTA_WHATSAPP", notas: "",
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmt$(n) {
  if (!n) return null;
  return `$${Number(n).toLocaleString("es-AR")}`;
}

// ── Modal alta/edición ────────────────────────────────────────────────────────
function LeadModal({ lead, onClose, onSave }) {
  const [form, setForm]     = useState(lead ?? EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function handleSave(e) {
    e.preventDefault();
    if (!form.nombre.trim()) { setError("El nombre es obligatorio"); return; }
    setSaving(true);
    setError("");
    const payload = {
      ...form,
      valor_total: form.valor_total ? parseInt(form.valor_total) : null,
      senia:       form.senia       ? parseInt(form.senia)       : null,
      fecha_evento: form.fecha_evento || null,
    };
    let err;
    if (lead?.id) {
      ({ error: err } = await supabase.from("crm_leads").update(payload).eq("id", lead.id));
    } else {
      ({ error: err } = await supabase.from("crm_leads").insert(payload));
    }
    if (err) { setError(err.message); setSaving(false); return; }
    onSave();
  }

  function Field({ label, children }) {
    return (
      <div>
        <label className="block text-xs font-medium mb-1" style={{ color: "#8B949E" }}>{label}</label>
        {children}
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "#00000088" }}
      onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl"
        style={{ background: "#161B22", border: "1px solid #21262D" }}>

        {/* Header */}
        <div className="px-6 py-4 flex items-center justify-between sticky top-0 z-10"
          style={{ background: "#161B22", borderBottom: "1px solid #21262D" }}>
          <h2 className="font-semibold text-white">
            {lead?.id ? "Editar lead" : "Nuevo lead"}
          </h2>
          <button onClick={onClose} className="hover:text-white transition-colors" style={{ color: "#484F58" }}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSave} className="p-6 space-y-5">

          {/* Datos del cliente */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "#484F58" }}>
              Cliente
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Field label="Nombre *">
                <input value={form.nombre} onChange={set("nombre")} className="input w-full" placeholder="Juan Pérez" required />
              </Field>
              <Field label="Teléfono / WhatsApp">
                <input value={form.telefono} onChange={set("telefono")} className="input w-full" placeholder="+54 9 11 1234 5678" />
              </Field>
              <Field label="Email">
                <input type="email" value={form.email} onChange={set("email")} className="input w-full" placeholder="juan@email.com" />
              </Field>
              <Field label="Canal de origen">
                <select value={form.canal_origen} onChange={set("canal_origen")} className="input w-full capitalize">
                  {CANALES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </Field>
            </div>
          </div>

          {/* Datos del evento */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "#484F58" }}>
              Evento
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Field label="Tipo de evento">
                <select value={form.tipo_evento} onChange={set("tipo_evento")} className="input w-full">
                  <option value="">Seleccionar...</option>
                  {TIPOS_EVENTO.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </Field>
              <Field label="Lugar">
                <input value={form.lugar_evento} onChange={set("lugar_evento")} className="input w-full" placeholder="Salón Sur" />
              </Field>
              <Field label="Fecha del evento">
                <input type="date" value={form.fecha_evento} onChange={set("fecha_evento")} className="input w-full" />
              </Field>
              <Field label="">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs font-medium mb-1" style={{ color: "#8B949E" }}>Hora inicio</label>
                    <input type="time" value={form.hora_inicio} onChange={set("hora_inicio")} className="input w-full" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium mb-1" style={{ color: "#8B949E" }}>Hora fin</label>
                    <input type="time" value={form.hora_fin} onChange={set("hora_fin")} className="input w-full" />
                  </div>
                </div>
              </Field>
            </div>
          </div>

          {/* Datos comerciales */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "#484F58" }}>
              Comercial
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Field label="Valor total ($)">
                <input type="number" value={form.valor_total} onChange={set("valor_total")} className="input w-full" placeholder="500000" />
              </Field>
              <Field label="Seña / Reserva ($)">
                <input type="number" value={form.senia} onChange={set("senia")} className="input w-full" placeholder="50000" />
              </Field>
              <Field label="Etapa">
                <select value={form.etapa} onChange={set("etapa")} className="input w-full text-xs">
                  {ETAPAS.map((e) => (
                    <option key={e.id} value={e.id}>{e.label}</option>
                  ))}
                </select>
              </Field>
            </div>
          </div>

          {/* Notas */}
          <Field label="Notas">
            <textarea value={form.notas} onChange={set("notas")} rows={3}
              className="input w-full resize-none" placeholder="Observaciones, requerimientos especiales..." />
          </Field>

          {error && (
            <p className="text-sm" style={{ color: "#f85149" }}>{error}</p>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm transition-colors" style={{ color: "#8B949E" }}>
              Cancelar
            </button>
            <button type="submit" disabled={saving}
              className="flex items-center gap-2 px-5 py-2 rounded-lg text-white text-sm font-medium disabled:opacity-50"
              style={{ background: "#2B6BF3" }}>
              {saving ? <Loader2 size={14} className="animate-spin" /> : null}
              {saving ? "Guardando..." : (lead?.id ? "Guardar cambios" : "Crear lead")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Tarjeta de lead ───────────────────────────────────────────────────────────
function LeadCard({ lead, onEdit, onDelete, onDragStart }) {
  const etapa = ETAPA_MAP[lead.etapa];

  return (
    <div
      draggable
      onDragStart={(e) => { e.dataTransfer.effectAllowed = "move"; onDragStart(lead); }}
      className="rounded-xl p-3 cursor-grab active:cursor-grabbing group transition-all hover:scale-[1.01]"
      style={{ background: "#0D1117", border: "1px solid #21262D" }}
    >
      {/* Nombre + acciones */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-sm font-semibold text-white leading-tight flex-1">{lead.nombre}</p>
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          <button onClick={() => onEdit(lead)}
            className="p-1 rounded transition-colors hover:bg-[#21262D]"
            style={{ color: "#8B949E" }}>
            <Pencil size={11} />
          </button>
          <button onClick={() => onDelete(lead)}
            className="p-1 rounded transition-colors hover:bg-[#21262D]"
            style={{ color: "#8B949E" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#f85149")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#8B949E")}
          >
            <Trash2 size={11} />
          </button>
        </div>
      </div>

      {/* Info */}
      <div className="space-y-1">
        {lead.telefono && (
          <div className="flex items-center gap-1.5">
            <Phone size={10} style={{ color: "#484F58" }} />
            <span className="text-xs" style={{ color: "#8B949E" }}>{lead.telefono}</span>
          </div>
        )}
        {lead.tipo_evento && (
          <div className="flex items-center gap-1.5">
            <Users size={10} style={{ color: "#484F58" }} />
            <span className="text-xs" style={{ color: "#8B949E" }}>{lead.tipo_evento}</span>
          </div>
        )}
        {lead.fecha_evento && (
          <div className="flex items-center gap-1.5">
            <Calendar size={10} style={{ color: "#484F58" }} />
            <span className="text-xs" style={{ color: "#8B949E" }}>
              {format(new Date(lead.fecha_evento + "T12:00:00"), "dd MMM yyyy", { locale: es })}
            </span>
          </div>
        )}
        {lead.lugar_evento && (
          <div className="flex items-center gap-1.5">
            <MapPin size={10} style={{ color: "#484F58" }} />
            <span className="text-xs truncate" style={{ color: "#8B949E" }}>{lead.lugar_evento}</span>
          </div>
        )}
        {lead.notas && (
          <div className="flex items-start gap-1.5 mt-1">
            <StickyNote size={10} style={{ color: "#484F58" }} className="shrink-0 mt-0.5" />
            <span className="text-xs line-clamp-2" style={{ color: "#484F58" }}>{lead.notas}</span>
          </div>
        )}
      </div>

      {/* Footer: canal + monto */}
      {(lead.canal_origen || lead.valor_total) && (
        <div className="flex items-center justify-between mt-2 pt-2" style={{ borderTop: "1px solid #21262D" }}>
          {lead.canal_origen && (
            <span className="text-[10px] px-1.5 py-0.5 rounded font-medium capitalize"
              style={{ background: "#21262D", color: "#8B949E" }}>
              {lead.canal_origen}
            </span>
          )}
          {lead.valor_total && (
            <span className="text-xs font-semibold" style={{ color: "#3FB950" }}>
              {fmt$(lead.valor_total)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ── Columna del Kanban ────────────────────────────────────────────────────────
function KanbanColumn({ etapa, leads, onAdd, onEdit, onDelete, onDragStart, onDrop }) {
  const [over, setOver] = useState(false);

  return (
    <div
      className="flex flex-col rounded-xl shrink-0 transition-all"
      style={{
        width: "240px",
        background: over ? etapa.bg : "#161B22",
        border: `1px solid ${over ? etapa.color + "66" : "#21262D"}`,
        transition: "background 0.15s, border-color 0.15s",
      }}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); onDrop(etapa.id); }}
    >
      {/* Header */}
      <div className="px-3 py-3 flex items-center justify-between"
        style={{ borderBottom: `2px solid ${etapa.color}` }}>
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold tracking-wide" style={{ color: etapa.color }}>
            {etapa.label}
          </span>
          <span className="text-xs font-semibold px-1.5 py-0.5 rounded-full"
            style={{ background: etapa.bg, color: etapa.color }}>
            {leads.length}
          </span>
        </div>
        <button
          onClick={() => onAdd(etapa.id)}
          className="w-6 h-6 rounded-lg flex items-center justify-center transition-colors hover:opacity-80"
          style={{ background: etapa.bg, color: etapa.color }}
          title={`Agregar en ${etapa.label}`}
        >
          <Plus size={13} />
        </button>
      </div>

      {/* Cards */}
      <div className="flex-1 p-2 space-y-2 overflow-y-auto" style={{ minHeight: "120px", maxHeight: "calc(100vh - 220px)" }}>
        {leads.length === 0 ? (
          <div className="flex items-center justify-center h-16 rounded-lg"
            style={{ border: `1px dashed ${etapa.color}33`, color: etapa.color + "66" }}>
            <span className="text-xs">Arrastrá aquí</span>
          </div>
        ) : (
          leads.map((lead) => (
            <LeadCard
              key={lead.id}
              lead={lead}
              onEdit={onEdit}
              onDelete={onDelete}
              onDragStart={onDragStart}
            />
          ))
        )}
      </div>
    </div>
  );
}

// ── Componente principal ──────────────────────────────────────────────────────
export default function Crm() {
  const [leads, setLeads]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [modal, setModal]       = useState(null);   // null | { mode, lead }
  const [dragging, setDragging] = useState(null);   // lead being dragged
  const [deleting, setDeleting] = useState(null);   // lead to confirm delete
  const [search, setSearch]     = useState("");

  async function load() {
    setLoading(true);
    const { data } = await supabase
      .from("crm_leads")
      .select("*")
      .order("created_at", { ascending: false });
    setLeads(data ?? []);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  // ── Drag & drop: mover etapa ────────────────────────────────────────────────
  async function handleDrop(targetEtapaId) {
    if (!dragging || dragging.etapa === targetEtapaId) { setDragging(null); return; }
    // Optimistic update
    setLeads((prev) => prev.map((l) => l.id === dragging.id ? { ...l, etapa: targetEtapaId } : l));
    await supabase.from("crm_leads").update({ etapa: targetEtapaId }).eq("id", dragging.id);
    setDragging(null);
  }

  // ── Eliminar ────────────────────────────────────────────────────────────────
  async function confirmDelete() {
    if (!deleting) return;
    setLeads((prev) => prev.filter((l) => l.id !== deleting.id));
    await supabase.from("crm_leads").delete().eq("id", deleting.id);
    setDeleting(null);
  }

  // ── Filtro por búsqueda ──────────────────────────────────────────────────────
  const filtered = leads.filter((l) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      l.nombre?.toLowerCase().includes(q) ||
      l.telefono?.includes(q) ||
      l.lugar_evento?.toLowerCase().includes(q) ||
      l.tipo_evento?.toLowerCase().includes(q)
    );
  });

  // Agrupar por etapa
  const byEtapa = Object.fromEntries(ETAPAS.map((e) => [e.id, []]));
  for (const lead of filtered) {
    if (byEtapa[lead.etapa]) byEtapa[lead.etapa].push(lead);
  }

  // Stats rápidas
  const totalValor = leads
    .filter((l) => !["CANCELADO"].includes(l.etapa) && l.valor_total)
    .reduce((sum, l) => sum + (l.valor_total || 0), 0);

  return (
    <div className="flex flex-col h-full overflow-hidden">

      {/* Header fijo */}
      <div className="px-6 py-4 shrink-0" style={{ borderBottom: "1px solid #21262D" }}>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Users size={20} style={{ color: "#2B6BF3" }} />
              CRM
            </h1>
            <p className="text-sm mt-0.5" style={{ color: "#8B949E" }}>
              {leads.length} leads · Pipeline activo: {fmt$(totalValor) ?? "$0"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar cliente, lugar..."
              className="input text-sm h-9"
              style={{ width: "220px" }}
            />
            <button
              onClick={() => setModal({ mode: "new", lead: { ...EMPTY_FORM } })}
              className="flex items-center gap-2 text-white text-sm font-medium px-4 py-2 rounded-lg"
              style={{ background: "#2B6BF3" }}
            >
              <Plus size={15} />
              Nuevo lead
            </button>
          </div>
        </div>
      </div>

      {/* Board */}
      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 size={24} className="animate-spin" style={{ color: "#2B6BF3" }} />
        </div>
      ) : (
        <div className="flex-1 overflow-x-auto overflow-y-hidden p-4">
          <div className="flex gap-3 h-full" style={{ minWidth: "max-content" }}>
            {ETAPAS.map((etapa) => (
              <KanbanColumn
                key={etapa.id}
                etapa={etapa}
                leads={byEtapa[etapa.id]}
                onAdd={(etapaId) => setModal({ mode: "new", lead: { ...EMPTY_FORM, etapa: etapaId } })}
                onEdit={(lead) => setModal({ mode: "edit", lead })}
                onDelete={(lead) => setDeleting(lead)}
                onDragStart={(lead) => setDragging(lead)}
                onDrop={handleDrop}
              />
            ))}
          </div>
        </div>
      )}

      {/* Modal alta/edición */}
      {modal && (
        <LeadModal
          lead={modal.mode === "edit" ? modal.lead : null}
          onClose={() => setModal(null)}
          onSave={() => { setModal(null); load(); }}
        />
      )}

      {/* Confirmar eliminación */}
      {deleting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: "#00000088" }}>
          <div className="w-full max-w-sm rounded-2xl p-6"
            style={{ background: "#161B22", border: "1px solid #21262D" }}>
            <h3 className="font-semibold text-white mb-2">¿Eliminar lead?</h3>
            <p className="text-sm mb-5" style={{ color: "#8B949E" }}>
              Se eliminará <strong className="text-white">{deleting.nombre}</strong> permanentemente.
            </p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setDeleting(null)}
                className="px-4 py-2 text-sm" style={{ color: "#8B949E" }}>
                Cancelar
              </button>
              <button onClick={confirmDelete}
                className="px-4 py-2 rounded-lg text-white text-sm font-medium"
                style={{ background: "#F85149" }}>
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
