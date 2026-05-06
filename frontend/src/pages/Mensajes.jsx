import { useState, useEffect, useRef } from "react";
import { MessageSquare, Search, Filter, RefreshCw, ChevronDown, User, Bot } from "lucide-react";
import api from "../utils/api";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const CHANNELS = ["todos", "web", "telegram", "whatsapp"];
const CANAL_COLORS = { web: "#2B6BF3", telegram: "#0088cc", whatsapp: "#25D366" };
const CANAL_LABELS = { web: "Web", telegram: "Telegram", whatsapp: "WhatsApp" };

function CanalBadge({ canal }) {
  const color = CANAL_COLORS[canal] || "#8B949E";
  return (
    <span
      className="badge text-[10px] font-semibold uppercase tracking-wide"
      style={{ background: `${color}22`, color, border: `1px solid ${color}44` }}
    >
      {CANAL_LABELS[canal] || canal}
    </span>
  );
}

function ConvThread({ messages }) {
  return (
    <div className="space-y-2 pl-4 border-l-2 border-[#21262D] ml-2">
      {messages.map((m) => (
        <div key={m.id} className={`flex gap-2 items-start ${m.role === "user" ? "" : "flex-row-reverse"}`}>
          <div
            className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5"
            style={{ background: m.role === "user" ? "#21262D" : "#2B6BF322", border: `1px solid ${m.role === "user" ? "#30363D" : "#2B6BF344"}` }}
          >
            {m.role === "user"
              ? <User size={11} className="text-[#8B949E]" />
              : <Bot size={11} className="text-snr-400" />
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
            <p className="text-[#484F58] text-[10px] mt-1">
              {format(new Date(m.created_at), "HH:mm:ss", { locale: es })}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function Mensajes() {
  const [channel, setChannel] = useState("todos");
  const [searchKey, setSearchKey] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(null);
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 50;

  async function load(reset = false) {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: PAGE_SIZE, canal: channel === "todos" ? "web" : channel });
      if (searchKey) params.append("session_key", searchKey);
      const { data } = await api.get(`/admin/conversaciones?${params}`);
      setMessages(data);
    } catch {}
    setLoading(false);
  }

  useEffect(() => { load(); }, [channel]);

  // Agrupar mensajes por session_key
  const sessions = messages.reduce((acc, m) => {
    if (!acc[m.session_key]) acc[m.session_key] = [];
    acc[m.session_key].push(m);
    return acc;
  }, {});

  const sessionList = Object.entries(sessions).map(([key, msgs]) => ({
    key,
    canal: msgs[0].channel,
    mensajes: msgs.length,
    ultimo: msgs[msgs.length - 1]?.created_at,
    msgs,
  }));

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <MessageSquare size={20} className="text-snr-400" />
            Base de mensajes
          </h1>
          <p className="text-[#8B949E] text-sm mt-0.5">Análisis de conversaciones por canal</p>
        </div>
        <button onClick={() => load()} className="btn-ghost flex items-center gap-2">
          <RefreshCw size={14} />
          Actualizar
        </button>
      </div>

      {/* Filtros */}
      <div className="card p-4 flex flex-wrap items-center gap-3">
        <div className="flex gap-1.5">
          {CHANNELS.map((ch) => (
            <button
              key={ch}
              onClick={() => { setChannel(ch); setExpanded(null); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors capitalize ${
                channel === ch
                  ? "text-white"
                  : "text-[#8B949E] hover:text-white hover:bg-[#1C2230]"
              }`}
              style={channel === ch ? { background: ch === "todos" ? "#2B6BF3" : CANAL_COLORS[ch] } : {}}
            >
              {ch}
            </button>
          ))}
        </div>
        <div className="flex-1 min-w-[200px] relative">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#484F58]" />
          <input
            value={searchKey}
            onChange={(e) => setSearchKey(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load()}
            placeholder="Buscar por session ID..."
            className="input pl-8 text-xs h-9"
          />
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Sesiones", value: sessionList.length },
          { label: "Mensajes", value: messages.length },
          {
            label: "Tasa respuesta",
            value: messages.length
              ? `${Math.round((messages.filter((m) => m.role === "assistant").length / messages.length) * 100)}%`
              : "—",
          },
        ].map((s) => (
          <div key={s.label} className="card px-4 py-3 text-center">
            <p className="text-[#8B949E] text-xs">{s.label}</p>
            <p className="text-white text-xl font-bold mt-0.5">{s.value}</p>
          </div>
        ))}
      </div>

      {/* Lista de sesiones */}
      {loading ? (
        <div className="space-y-2">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="card p-4 h-14 animate-pulse" />
          ))}
        </div>
      ) : sessionList.length === 0 ? (
        <div className="card p-10 text-center text-[#484F58] text-sm">
          No hay conversaciones para este filtro
        </div>
      ) : (
        <div className="space-y-2">
          {sessionList.map((s) => (
            <div key={s.key} className="card overflow-hidden">
              {/* Session header */}
              <button
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-[#1C2230] transition-colors text-left"
                onClick={() => setExpanded(expanded === s.key ? null : s.key)}
              >
                <CanalBadge canal={s.canal} />
                <span className="flex-1 text-xs text-[#8B949E] font-mono truncate">{s.key}</span>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-xs text-[#8B949E]">{s.mensajes} msgs</span>
                  <span className="text-[10px] text-[#484F58]">
                    {s.ultimo ? format(new Date(s.ultimo), "dd/MM HH:mm", { locale: es }) : ""}
                  </span>
                  <ChevronDown
                    size={14}
                    className={`text-[#484F58] transition-transform ${expanded === s.key ? "rotate-180" : ""}`}
                  />
                </div>
              </button>
              {/* Thread */}
              {expanded === s.key && (
                <div className="px-4 pb-4 pt-2 border-t border-[#21262D] bg-[#0D1117]">
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
