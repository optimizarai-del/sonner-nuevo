import { useState, useEffect } from "react";
import { MessageSquare, Search, RefreshCw, ChevronDown, User, Bot } from "lucide-react";
import { supabase } from "../utils/supabase";
import { format } from "date-fns";
import { es } from "date-fns/locale";

// ── Helpers ───────────────────────────────────────────────────────────────────
function parseMessage(row) {
  // n8n guarda: { type: "human"|"ai", content: "...", data: {...} }
  // El esquema mínimo de n8n NO tiene created_at, solo id (bigserial autoincremental)
  const msg = row.message ?? {};
  const role = msg.type === "human" ? "user" : "assistant";
  let content = msg.data?.content ?? msg.content ?? "(vacío)";
  // El agente devuelve JSON en string: {"output":{"respuesta":"...","comando":"..."}}
  if (typeof content === "string" && content.trim().startsWith("{")) {
    try {
      const parsed = JSON.parse(content);
      content = parsed.output?.respuesta ?? parsed.respuesta ?? (typeof parsed.output === "string" ? parsed.output : null) ?? content;
    } catch {}
  }
  return { id: row.id, session_id: row.session_id, role, content };
}

function ConvThread({ messages }) {
  return (
    <div className="space-y-2 pl-4 border-l-2 border-[#21262D] ml-2">
      {messages.map((m) => (
        <div key={m.id} className={`flex gap-2 items-start ${m.role === "user" ? "" : "flex-row-reverse"}`}>
          <div
            className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5"
            style={{
              background: m.role === "user" ? "#21262D" : "#2B6BF322",
              border: `1px solid ${m.role === "user" ? "#30363D" : "#2B6BF344"}`,
            }}
          >
            {m.role === "user"
              ? <User size={11} className="text-[#8B949E]" />
              : <Bot  size={11} style={{ color: "#2B6BF3" }} />
            }
          </div>
          <div
            className="flex-1 rounded-xl px-3 py-2 text-xs leading-relaxed max-w-[85%]"
            style={{
              background: m.role === "user" ? "#161B22" : "#0D1B38",
              border: `1px solid ${m.role === "user" ? "#21262D" : "#1e3a6e"}`,
              color: m.role === "user" ? "#C9D1D9" : "#79C0FF",
            }}
          >
            <p className="whitespace-pre-wrap">{m.content}</p>
            <p className="text-[10px] mt-1" style={{ color: "#484F58" }}>#{m.id}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Componente principal ──────────────────────────────────────────────────────
export default function Mensajes() {
  const [rows, setRows]       = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch]   = useState("");
  const [expanded, setExpanded] = useState(null);

  async function load() {
    setLoading(true);
    const { data } = await supabase
      .from("n8n_chat_histories")
      .select("id, session_id, message")
      .order("id", { ascending: false })
      .limit(500);
    setRows(data ?? []);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  // Parsear y agrupar por session_id
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
      msgs: [...msgs].reverse(), // cronológico para mostrar
    }))
    .sort((a, b) => (b.ultimoId ?? 0) - (a.ultimoId ?? 0))
    .filter((s) => !search || s.key.includes(search));

  return (
    <div className="p-6 space-y-5">

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <MessageSquare size={20} style={{ color: "#2B6BF3" }} />
            Base de mensajes
          </h1>
          <p className="text-sm mt-0.5" style={{ color: "#8B949E" }}>Conversaciones del agente interno vía n8n</p>
        </div>
        <button onClick={load} className="btn-ghost flex items-center gap-2">
          <RefreshCw size={14} />
          Actualizar
        </button>
      </div>

      {/* Búsqueda */}
      <div className="card p-4 flex items-center gap-3">
        <Search size={13} className="shrink-0" style={{ color: "#484F58" }} />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filtrar por session ID..."
          className="flex-1 bg-transparent text-sm outline-none text-white placeholder-[#484F58]"
        />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Sesiones", value: sessionList.length },
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

      {/* Lista */}
      {loading ? (
        <div className="space-y-2">
          {[0, 1, 2, 3].map((i) => <div key={i} className="card p-4 h-14 animate-pulse" />)}
        </div>
      ) : sessionList.length === 0 ? (
        <div className="card p-10 text-center text-sm" style={{ color: "#484F58" }}>
          No hay conversaciones aún
        </div>
      ) : (
        <div className="space-y-2">
          {sessionList.map((s) => (
            <div key={s.key} className="card overflow-hidden">
              <button
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-[#1C2230] transition-colors text-left"
                onClick={() => setExpanded(expanded === s.key ? null : s.key)}
              >
                <span
                  className="text-xs font-medium px-2 py-0.5 rounded-full"
                  style={{ background: "#2B6BF322", color: "#79C0FF", border: "1px solid #2B6BF344" }}
                >
                  web
                </span>
                <span className="flex-1 text-xs text-[#8B949E] font-mono truncate">{s.key}</span>
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
                <div className="px-4 pb-4 pt-2" style={{ borderTop: "1px solid #21262D", background: "#0D1117" }}>
                  <ConvThread messages={s.msgs} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
