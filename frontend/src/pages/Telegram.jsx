import { useState, useEffect } from "react";
import { Power, Shield, Plus, Trash2, User } from "lucide-react";
import api from "../utils/api";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const TG_ICON = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
    <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L8.32 14.617l-2.96-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.828.942z" fill="#0088cc"/>
  </svg>
);

const DEMO_BLOCKLIST = [
  { id: 1, identifier: "549112345678", label: "Juan cliente molesto", created_at: "2026-04-10T14:00:00" },
  { id: 2, identifier: "7891234567",   label: "Spam repetitivo",      created_at: "2026-04-22T09:30:00" },
  { id: 3, identifier: "123456789",    label: "",                      created_at: "2026-05-01T18:15:00" },
];

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
  const [autoActiva, setAutoActiva]   = useState(true);
  const [autoLoading, setAutoLoading] = useState(false);
  const [blocklist, setBlocklist]     = useState(DEMO_BLOCKLIST);
  const [blockLoading, setBlockLoading] = useState(false);
  const [newId, setNewId]             = useState("");
  const [newLabel, setNewLabel]       = useState("");
  const [addLoading, setAddLoading]   = useState(false);
  const [addError, setAddError]       = useState("");
  const [backendOk, setBackendOk]     = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [autoRes, blockRes] = await Promise.all([
          api.get("/telegram-externo/automatizacion-estado"),
          api.get("/telegram-externo/blocklist"),
        ]);
        setAutoActiva(autoRes.data.activa);
        setBlocklist(blockRes.data);
        setBackendOk(true);
      } catch {
        // sin backend → queda con datos demo
        setBackendOk(false);
      }
    })();
  }, []);

  async function toggleAutomatizacion() {
    setAutoLoading(true);
    try {
      if (backendOk) {
        const { data } = await api.post("/telegram-externo/toggle-automatizacion");
        setAutoActiva(data.activa);
      } else {
        // demo: toggle local
        await new Promise((r) => setTimeout(r, 300));
        setAutoActiva((prev) => !prev);
      }
    } catch {
      setAutoActiva((prev) => !prev); // optimistic fallback
    }
    setAutoLoading(false);
  }

  async function addBlocked() {
    if (!newId.trim()) return;
    setAddLoading(true);
    setAddError("");
    try {
      if (backendOk) {
        const { data } = await api.post("/telegram-externo/blocklist", {
          identifier: newId.trim(),
          label: newLabel.trim(),
        });
        setBlocklist((prev) => [data, ...prev]);
      } else {
        // demo: agregar local
        await new Promise((r) => setTimeout(r, 300));
        const nuevo = {
          id: Date.now(),
          identifier: newId.trim(),
          label: newLabel.trim(),
          created_at: new Date().toISOString(),
        };
        setBlocklist((prev) => [nuevo, ...prev]);
      }
      setNewId("");
      setNewLabel("");
    } catch (err) {
      setAddError(err.response?.data?.detail || "Error al agregar");
    }
    setAddLoading(false);
  }

  async function removeBlocked(id) {
    setBlockLoading(true);
    try {
      if (backendOk) {
        await api.delete(`/telegram-externo/blocklist/${id}`);
      } else {
        await new Promise((r) => setTimeout(r, 200));
      }
      setBlocklist((prev) => prev.filter((c) => c.id !== id));
    } catch {}
    setBlockLoading(false);
  }

  return (
    <div className="p-6 space-y-5 max-w-2xl">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: "#0088cc22", border: "1px solid #0088cc44" }}>
            <TG_ICON />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Telegram</h1>
            <p className="text-sm" style={{ color: "#8B949E" }}>Gestión de bots — interno y externo</p>
          </div>
        </div>
        {!backendOk && (
          <span className="text-xs px-2.5 py-1 rounded-full font-medium" style={{ background: "#2B6BF322", color: "#79C0FF", border: "1px solid #2B6BF344" }}>
            Modo demo
          </span>
        )}
      </div>

      {/* Toggle automatización */}
      <div className="rounded-xl p-5" style={{ background: "#161B22", border: "1px solid #21262D" }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center transition-colors"
              style={{
                background: autoActiva ? "#2B6BF322" : "#21262D",
                border: `1px solid ${autoActiva ? "#2B6BF344" : "#30363D"}`,
              }}
            >
              <Power size={16} style={{ color: autoActiva ? "#2B6BF3" : "#484F58" }} />
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Automatización — bot externo</p>
              <p className="text-xs mt-0.5" style={{ color: "#8B949E" }}>
                {autoActiva
                  ? "El bot responde mensajes de clientes"
                  : "Bot pausado — no responde a nadie"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold" style={{ color: autoActiva ? "#3fb950" : "#f85149" }}>
              {autoActiva ? "ON" : "OFF"}
            </span>
            <ToggleSwitch activa={autoActiva} onChange={toggleAutomatizacion} loading={autoLoading} />
          </div>
        </div>
      </div>

      {/* Lista de bloqueo */}
      <div className="rounded-xl overflow-hidden" style={{ background: "#161B22", border: "1px solid #21262D" }}>

        {/* Header */}
        <div className="px-5 py-4 flex items-center gap-2" style={{ borderBottom: "1px solid #21262D" }}>
          <Shield size={15} style={{ color: "#2B6BF3" }} />
          <h2 className="text-sm font-semibold text-white">Lista de bloqueo</h2>
          <span
            className="ml-auto text-xs font-medium px-2 py-0.5 rounded-full"
            style={{ background: "#21262D", color: "#8B949E" }}
          >
            {blocklist.length} bloqueados
          </span>
        </div>

        {/* Formulario */}
        <div className="px-5 py-4" style={{ borderBottom: "1px solid #21262D" }}>
          <p className="text-xs mb-3" style={{ color: "#8B949E" }}>
            Ingresá el Telegram ID o número de teléfono. El bot ignorará todos sus mensajes.
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
              <Plus size={14} />
              {addLoading ? "..." : "Agregar"}
            </button>
          </div>
          {addError && (
            <p className="text-xs mt-2" style={{ color: "#f85149" }}>{addError}</p>
          )}
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
                <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0" style={{ background: "#21262D" }}>
                  <User size={14} style={{ color: "#484F58" }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-mono text-white truncate">{c.identifier}</p>
                  {c.label && (
                    <p className="text-xs truncate mt-0.5" style={{ color: "#8B949E" }}>{c.label}</p>
                  )}
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
