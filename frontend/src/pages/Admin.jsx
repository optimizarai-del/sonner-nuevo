import { useState, useEffect } from "react";
import { Plus, Trash2, MessageSquare, Database, RefreshCw } from "lucide-react";
import api from "../utils/api";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const SOURCES = ["eventos", "informacion_interna", "materiales"];
const CHANNELS = ["web", "telegram", "whatsapp"];

function TabBtn({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className="px-4 py-2 text-sm font-medium rounded-lg transition-colors"
      style={active
        ? { background: "#2B6BF322", color: "#79C0FF", border: "1px solid #2B6BF344" }
        : { color: "#8B949E" }
      }
    >
      {children}
    </button>
  );
}

function MemoryPanel() {
  const [source, setSource] = useState("eventos");
  const [docs, setDocs] = useState([]);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    try {
      const { data } = await api.get(`/admin/memoria?source=${source}`);
      setDocs(data);
    } catch {}
  }

  useEffect(() => { load(); }, [source]);

  async function add() {
    if (!content.trim()) return;
    setLoading(true);
    try {
      await api.post("/admin/memoria", { content: content.trim(), source });
      setContent("");
      await load();
    } catch {}
    setLoading(false);
  }

  async function del(id) {
    if (!confirm("¿Eliminar este documento?")) return;
    try {
      await api.delete(`/admin/memoria/${id}`);
      await load();
    } catch {}
  }

  return (
    <div className="space-y-5">
      <div className="flex gap-2 flex-wrap">
        {SOURCES.map((s) => (
          <TabBtn key={s} active={source === s} onClick={() => setSource(s)}>
            {s.replace("_", " ")}
          </TabBtn>
        ))}
      </div>

      <div className="rounded-xl p-4 space-y-3" style={{ background: "#161B22", border: "1px solid #21262D" }}>
        <label className="block text-xs font-medium" style={{ color: "#8B949E" }}>
          Agregar documento ({source})
        </label>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={4}
          className="input w-full resize-none"
          placeholder="Escribí el contenido a guardar en la memoria..."
        />
        <button
          onClick={add}
          disabled={!content.trim() || loading}
          className="flex items-center gap-2 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
          style={{ background: "#2B6BF3" }}
        >
          <Plus size={15} />
          {loading ? "Guardando..." : "Guardar en memoria"}
        </button>
      </div>

      <div className="space-y-2">
        {docs.length === 0 && (
          <p className="text-sm text-center py-6" style={{ color: "#484F58" }}>
            No hay documentos en esta sección
          </p>
        )}
        {docs.map((d) => (
          <div key={d.id} className="rounded-xl px-4 py-3 flex gap-3" style={{ background: "#161B22", border: "1px solid #21262D" }}>
            <p className="flex-1 text-sm leading-relaxed" style={{ color: "#C9D1D9" }}>{d.content}</p>
            <div className="flex flex-col items-end gap-2 shrink-0">
              <button
                onClick={() => del(d.id)}
                className="transition-colors hover:opacity-80"
                style={{ color: "#484F58" }}
                onMouseEnter={(e) => e.currentTarget.style.color = "#f85149"}
                onMouseLeave={(e) => e.currentTarget.style.color = "#484F58"}
              >
                <Trash2 size={14} />
              </button>
              <span className="text-xs" style={{ color: "#484F58" }}>
                {format(new Date(d.created_at), "dd/MM/yy", { locale: es })}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ConversationsPanel() {
  const [channel, setChannel] = useState("web");
  const [convs, setConvs] = useState([]);
  const [sessionKey, setSessionKey] = useState("");

  async function load() {
    try {
      const params = new URLSearchParams({ canal: channel, limit: 100 });
      if (sessionKey) params.append("session_key", sessionKey);
      const { data } = await api.get(`/admin/conversaciones?${params}`);
      setConvs(data);
    } catch {}
  }

  useEffect(() => { load(); }, [channel]);

  const sessions = [...new Set(convs.map((c) => c.session_key))];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex gap-2">
          {CHANNELS.map((ch) => (
            <TabBtn key={ch} active={channel === ch} onClick={() => { setChannel(ch); setSessionKey(""); }}>
              {ch}
            </TabBtn>
          ))}
        </div>
        <select
          value={sessionKey}
          onChange={(e) => setSessionKey(e.target.value)}
          className="rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none"
          style={{ background: "#161B22", border: "1px solid #21262D" }}
        >
          <option value="">Todas las sesiones</option>
          {sessions.map((s) => (
            <option key={s} value={s}>{s.slice(0, 30)}...</option>
          ))}
        </select>
        <button
          onClick={load}
          className="transition-colors hover:text-white"
          style={{ color: "#8B949E" }}
        >
          <RefreshCw size={16} />
        </button>
      </div>

      <div className="space-y-2 max-h-[60vh] overflow-y-auto">
        {convs.filter((c) => !sessionKey || c.session_key === sessionKey).map((c) => (
          <div
            key={c.id}
            className="rounded-xl px-4 py-3 text-sm"
            style={c.role === "user"
              ? { background: "#1C2230", border: "1px solid #30363D", marginLeft: "2rem" }
              : { background: "#0D1B38", border: "1px solid #1e3a6e", marginRight: "2rem" }
            }
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium" style={{ color: c.role === "user" ? "#79C0FF" : "#3fb950" }}>
                {c.role === "user" ? "Usuario" : "Agente"} · {c.session_key.slice(0, 20)}
              </span>
              <span className="text-xs" style={{ color: "#484F58" }}>
                {format(new Date(c.created_at), "dd/MM HH:mm", { locale: es })}
              </span>
            </div>
            <p className="leading-relaxed whitespace-pre-wrap" style={{ color: "#C9D1D9" }}>{c.content}</p>
          </div>
        ))}
        {convs.length === 0 && (
          <p className="text-sm text-center py-6" style={{ color: "#484F58" }}>
            No hay conversaciones en este canal
          </p>
        )}
      </div>
    </div>
  );
}

export default function Admin() {
  const [tab, setTab] = useState("memoria");

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-white">Panel de administración</h1>
        <p className="text-sm mt-0.5" style={{ color: "#484F58" }}>Memoria vectorial · Historial de conversaciones</p>
      </div>

      <div className="flex gap-2 mb-6 pb-3" style={{ borderBottom: "1px solid #21262D" }}>
        <button
          onClick={() => setTab("memoria")}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors"
          style={tab === "memoria"
            ? { background: "#2B6BF322", color: "#79C0FF", border: "1px solid #2B6BF344" }
            : { color: "#8B949E" }
          }
        >
          <Database size={15} />
          Memoria
        </button>
        <button
          onClick={() => setTab("conversaciones")}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors"
          style={tab === "conversaciones"
            ? { background: "#2B6BF322", color: "#79C0FF", border: "1px solid #2B6BF344" }
            : { color: "#8B949E" }
          }
        >
          <MessageSquare size={15} />
          Conversaciones
        </button>
      </div>

      {tab === "memoria" ? <MemoryPanel /> : <ConversationsPanel />}
    </div>
  );
}
