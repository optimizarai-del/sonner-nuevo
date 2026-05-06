import { useState, useEffect } from "react";
import { Power, Shield, Plus, Trash2, User, Loader2 } from "lucide-react";
import { supabase } from "../utils/supabase";
import { format } from "date-fns";
import { es } from "date-fns/locale";

function ToggleSwitch({ activa, onChange, loading }) {
  return (
    <button
      onClick={onChange}
      disabled={loading}
      className="relative inline-flex items-center h-6 rounded-full w-11 transition-all focus:outline-none disabled:opacity-50 cursor-pointer"
      style={{ background: activa ? "#2B6BF3" : "#30363D" }}
    >
      <span
        className="inline-block w-4 h-4 bg-white rounded-full transition-transform shadow"
        style={{ transform: activa ? "translateX(24px)" : "translateX(4px)" }}
      />
    </button>
  );
}

export default function Telegram() {
  const [activa, setActiva]       = useState(true);
  const [autoLoading, setAutoLoading] = useState(false);
  const [blocklist, setBlocklist] = useState([]);
  const [blockLoading, setBlockLoading] = useState(false);
  const [newId, setNewId]         = useState("");
  const [newLabel, setNewLabel]   = useState("");
  const [addLoading, setAddLoading] = useState(false);
  const [addError, setAddError]   = useState("");

  // ── Cargar estado inicial desde Supabase ────────────────────────────────────
  useEffect(() => {
    async function load() {
      const [{ data: cfg }, { data: bl }] = await Promise.all([
        supabase.from("automatizacion_config").select("activa").eq("id", 1).single(),
        supabase.from("blocklist").select("id, identifier, label, created_at").order("created_at", { ascending: false }),
      ]);
      if (cfg) setActiva(cfg.activa);
      setBlocklist(bl ?? []);
    }
    load();
  }, []);

  // ── Toggle automatización ────────────────────────────────────────────────────
  async function toggleAutomatizacion() {
    setAutoLoading(true);
    const nuevo = !activa;
    setActiva(nuevo); // optimistic
    const { error } = await supabase
      .from("automatizacion_config")
      .update({ activa: nuevo })
      .eq("id", 1);
    if (error) setActiva(!nuevo); // revert
    setAutoLoading(false);
  }

  // ── Agregar a blocklist ──────────────────────────────────────────────────────
  async function addBlocked() {
    if (!newId.trim()) return;
    setAddLoading(true);
    setAddError("");
    const { data, error } = await supabase
      .from("blocklist")
      .insert({ identifier: newId.trim(), label: newLabel.trim() })
      .select()
      .single();
    if (error) {
      setAddError(error.code === "23505" ? "Este ID ya está bloqueado" : "Error al agregar");
    } else {
      setBlocklist((prev) => [data, ...prev]);
      setNewId("");
      setNewLabel("");
    }
    setAddLoading(false);
  }

  // ── Eliminar de blocklist ────────────────────────────────────────────────────
  async function removeBlocked(id) {
    setBlockLoading(true);
    await supabase.from("blocklist").delete().eq("id", id);
    setBlocklist((prev) => prev.filter((c) => c.id !== id));
    setBlockLoading(false);
  }

  return (
    <div className="p-6 space-y-5 max-w-2xl">

      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: "#0088cc22", border: "1px solid #0088cc44" }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L8.32 14.617l-2.96-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.828.942z" fill="#0088cc"/>
          </svg>
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">Agente externo</h1>
          <p className="text-sm" style={{ color: "#8B949E" }}>Control de automatización y lista de bloqueo</p>
        </div>
      </div>

      {/* Toggle */}
      <div className="rounded-xl p-5" style={{ background: "#161B22", border: "1px solid #21262D" }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center transition-colors"
              style={{
                background: activa ? "#2B6BF322" : "#21262D",
                border: `1px solid ${activa ? "#2B6BF344" : "#30363D"}`,
              }}
            >
              <Power size={16} style={{ color: activa ? "#2B6BF3" : "#484F58" }} />
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Automatización — agente externo</p>
              <p className="text-xs mt-0.5" style={{ color: "#8B949E" }}>
                {activa ? "El agente responde mensajes de clientes" : "Agente pausado — no responde a nadie"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {autoLoading && <Loader2 size={14} className="animate-spin" style={{ color: "#8B949E" }} />}
            <span className="text-xs font-bold" style={{ color: activa ? "#3fb950" : "#f85149" }}>
              {activa ? "ON" : "OFF"}
            </span>
            <ToggleSwitch activa={activa} onChange={toggleAutomatizacion} loading={autoLoading} />
          </div>
        </div>
      </div>

      {/* Blocklist */}
      <div className="rounded-xl overflow-hidden" style={{ background: "#161B22", border: "1px solid #21262D" }}>
        <div className="px-5 py-4 flex items-center gap-2" style={{ borderBottom: "1px solid #21262D" }}>
          <Shield size={15} style={{ color: "#2B6BF3" }} />
          <h2 className="text-sm font-semibold text-white">Lista de bloqueo</h2>
          <span className="ml-auto text-xs font-medium px-2 py-0.5 rounded-full"
            style={{ background: "#21262D", color: "#8B949E" }}>
            {blocklist.length} bloqueados
          </span>
        </div>

        {/* Formulario */}
        <div className="px-5 py-4" style={{ borderBottom: "1px solid #21262D" }}>
          <p className="text-xs mb-3" style={{ color: "#8B949E" }}>
            Ingresá el ID de Telegram o número de teléfono (WhatsApp). El agente ignorará sus mensajes.
          </p>
          <div className="flex gap-2">
            <input
              value={newId}
              onChange={(e) => setNewId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addBlocked()}
              placeholder="ID o número (ej: 123456789)"
              className="input flex-1 text-sm"
            />
            <input
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addBlocked()}
              placeholder="Etiqueta (opcional)"
              className="input text-sm"
              style={{ width: "160px" }}
            />
            <button
              onClick={addBlocked}
              disabled={!newId.trim() || addLoading}
              className="flex items-center gap-1.5 text-sm font-medium px-4 rounded-lg text-white transition-opacity disabled:opacity-40 whitespace-nowrap"
              style={{ background: "#2B6BF3" }}
            >
              {addLoading ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
              Agregar
            </button>
          </div>
          {addError && <p className="text-xs mt-2" style={{ color: "#f85149" }}>{addError}</p>}
        </div>

        {/* Lista */}
        <div>
          {blocklist.length === 0 ? (
            <div className="px-5 py-10 text-center">
              <Shield size={24} className="mx-auto mb-2" style={{ color: "#30363D" }} />
              <p className="text-sm" style={{ color: "#484F58" }}>No hay contactos bloqueados</p>
            </div>
          ) : (
            blocklist.map((c, idx) => (
              <div
                key={c.id}
                className="px-5 py-3 flex items-center gap-3"
                style={{ borderBottom: idx < blocklist.length - 1 ? "1px solid #21262D" : "none" }}
              >
                <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
                  style={{ background: "#21262D" }}>
                  <User size={14} style={{ color: "#484F58" }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-mono text-white truncate">{c.identifier}</p>
                  {c.label && <p className="text-xs truncate mt-0.5" style={{ color: "#8B949E" }}>{c.label}</p>}
                </div>
                <span className="text-xs shrink-0" style={{ color: "#484F58" }}>
                  {format(new Date(c.created_at), "dd/MM/yy", { locale: es })}
                </span>
                <button
                  onClick={() => removeBlocked(c.id)}
                  disabled={blockLoading}
                  className="shrink-0 p-1 rounded transition-colors disabled:opacity-40"
                  style={{ color: "#484F58" }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = "#f85149")}
                  onMouseLeave={(e) => (e.currentTarget.style.color = "#484F58")}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
