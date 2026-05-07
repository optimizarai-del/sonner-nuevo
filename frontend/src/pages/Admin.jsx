import { useState, useEffect } from "react";
import { MessageSquare, RefreshCw, ChevronDown } from "lucide-react";
import { supabase } from "../utils/supabase";

function parseMessage(row) {
  // n8n_chat_histories tiene esquema mínimo: id, session_id, message (sin created_at)
  const msg = row.message ?? {};
  const role = msg.type === "human" ? "user" : "assistant";
  let content = msg.data?.content ?? msg.content ?? "(vacío)";
  // Agente devuelve JSON anidado: {"output":{"respuesta":"..."}}
  if (typeof content === "string" && content.trim().startsWith("{")) {
    try {
      const parsed = JSON.parse(content);
      content = parsed.output?.respuesta ?? parsed.respuesta ?? (typeof parsed.output === "string" ? parsed.output : null) ?? content;
    } catch {}
  }
  return { id: row.id, session_id: row.session_id, role, content };
}

export default function Admin() {
  const [rows, setRows]         = useState([]);
  const [loading, setLoading]   = useState(false);
  const [expanded, setExpanded] = useState(null);
  const [search, setSearch]     = useState("");

  async function load() {
    setLoading(true);
    // Lee mensajes EXTERNOS (agente WhatsApp). El interno NO se muestra.
    const { data } = await supabase
      .from("external_chat_histories")
      .select("id, session_id, message")
      .order("id", { ascending: false })
      .limit(1000);
    setRows(data ?? []);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  const messages = rows.map(parseMessage);
  const sessions = messages.reduce((acc, m) => {
    if (!acc[m.session_id]) acc[m.session_id] = [];
    acc[m.session_id].push(m);
    return acc;
  }, {});

  const sessionList = Object.entries(sessions)
    .map(([key, msgs]) => ({
      key,
      mensajes: msgs.length,
      ultimoId: msgs[0]?.id,
      msgs: [...msgs].reverse(),
    }))
    .sort((a, b) => (b.ultimoId ?? 0) - (a.ultimoId ?? 0))
    .filter((s) => !search || s.key.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-white">Panel de administración</h1>
        <p className="text-sm mt-0.5" style={{ color: "#484F58" }}>Historial de conversaciones del agente externo</p>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-3 mb-5">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por session ID..."
          className="input flex-1 text-sm"
        />
        <button onClick={load} className="btn-ghost flex items-center gap-2 text-sm shrink-0">
          <RefreshCw size={14} />
          Actualizar
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        {[
          { label: "Sesiones",  value: sessionList.length },
          { label: "Mensajes",  value: messages.length },
          {
            label: "Respuestas",
            value: messages.length
              ? `${Math.round((messages.filter((m) => m.role === "assistant").length / messages.length) * 100)}%`
              : "—",
          },
        ].map((s) => (
          <div key={s.label} className="card px-4 py-3 text-center">
            <p className="text-xs" style={{ color: "#8B949E" }}>{s.label}</p>
            <p className="text-white text-xl font-bold mt-0.5">{s.value}</p>
          </div>
        ))}
      </div>

      {/* Conversaciones */}
      {loading ? (
        <div className="space-y-2">
          {[0, 1, 2, 3].map((i) => <div key={i} className="card p-4 h-14 animate-pulse" />)}
        </div>
      ) : sessionList.length === 0 ? (
        <div className="card p-10 text-center">
          <MessageSquare size={24} className="mx-auto mb-2" style={{ color: "#30363D" }} />
          <p className="text-sm" style={{ color: "#484F58" }}>No hay conversaciones aún</p>
        </div>
      ) : (
        <div className="space-y-2">
          {sessionList.map((s) => (
            <div key={s.key} className="card overflow-hidden">
              <button
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-[#1C2230] transition-colors text-left"
                onClick={() => setExpanded(expanded === s.key ? null : s.key)}
              >
                <span className="flex-1 text-xs font-mono truncate" style={{ color: "#8B949E" }}>{s.key}</span>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-xs" style={{ color: "#8B949E" }}>{s.mensajes} msgs</span>
                  <span className="text-[10px]" style={{ color: "#484F58" }}>
                    #{s.ultimoId}
                  </span>
                  <ChevronDown
                    size={14}
                    style={{ color: "#484F58" }}
                    className={`transition-transform ${expanded === s.key ? "rotate-180" : ""}`}
                  />
                </div>
              </button>
              {expanded === s.key && (
                <div className="p-4 space-y-2" style={{ borderTop: "1px solid #21262D", background: "#0D1117" }}>
                  {s.msgs.map((m) => (
                    <div
                      key={m.id}
                      className="rounded-xl px-4 py-3 text-sm"
                      style={m.role === "user"
                        ? { background: "#1C2230", border: "1px solid #30363D", marginLeft: "2rem" }
                        : { background: "#0D1B38", border: "1px solid #1e3a6e", marginRight: "2rem" }
                      }
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium"
                          style={{ color: m.role === "user" ? "#79C0FF" : "#3fb950" }}>
                          {m.role === "user" ? "Usuario" : "Agente"}
                        </span>
                        <span className="text-xs" style={{ color: "#484F58" }}>#{m.id}</span>
                      </div>
                      <p className="whitespace-pre-wrap leading-relaxed" style={{ color: "#C9D1D9" }}>
                        {m.content}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
