import { useState, useRef, useEffect } from "react";
import { Send, Brain, User, Sparkles } from "lucide-react";

const ANALISTA_API = import.meta.env.VITE_CONTRATOS_API
  || "https://backend-sonner.optimizar-ia.com";

const SUGGESTIONS = [
  "¿Cuántos contratos se generaron este mes?",
  "¿Cuánto facturé en contratos este mes?",
  "¿Cuáles son los contactos más activos en WhatsApp?",
  "Resumí la actividad de la última semana",
  "¿Cómo está mi pipeline de CRM?",
  "¿Cuál es la tasa de respuesta del agente externo?",
];

function Message({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-0.5"
        style={{
          background: isUser ? "#21262D" : "#0D1B38",
          border: `1px solid ${isUser ? "#30363D" : "#1e3a6e"}`,
        }}
      >
        {isUser ? <User size={14} className="text-[#8B949E]" /> : <Brain size={14} style={{ color: "#2B6BF3" }} />}
      </div>
      <div
        className="flex-1 rounded-2xl px-4 py-3 text-sm leading-relaxed max-w-[85%]"
        style={{
          background: isUser ? "#161B22" : "#0D1B38",
          border: `1px solid ${isUser ? "#21262D" : "#1e3a6e"}`,
          color: isUser ? "#C9D1D9" : "#79C0FF",
        }}
      >
        <p className="whitespace-pre-wrap">{msg.content}</p>
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 bg-[#0D1B38] border border-[#1e3a6e]">
        <Brain size={14} style={{ color: "#2B6BF3" }} />
      </div>
      <div className="bg-[#0D1B38] border border-[#1e3a6e] rounded-2xl px-4 py-3">
        <div className="flex gap-1 items-center">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 rounded-full animate-bounce"
              style={{ background: "#2B6BF3", animationDelay: `${i * 0.15}s` }}
            />
          ))}
          <span className="text-xs ml-2" style={{ color: "#484F58" }}>Analizando datos...</span>
        </div>
      </div>
    </div>
  );
}

export default function Analista() {
  const [messages, setMessages] = useState([
    {
      id: 0,
      role: "assistant",
      content: "Hola, soy el Analista de Datos de SNR. Puedo analizar las métricas de conversaciones, contratos y actividad del sistema. ¿Qué querés saber?",
    },
  ]);
  const [input, setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(text) {
    const q = (text ?? input).trim();
    if (!q || loading) return;
    setInput("");

    setMessages((prev) => [...prev, { id: Date.now(), role: "user", content: q }]);
    setLoading(true);

    try {
      const ctrl = new AbortController();
      const tid = setTimeout(() => ctrl.abort(), 90_000);
      const res = await fetch(`${ANALISTA_API}/api/analista`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
        signal: ctrl.signal,
      });
      clearTimeout(tid);
      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(`HTTP ${res.status}: ${errBody.slice(0, 300)}`);
      }
      const data = await res.json();
      setMessages((prev) => [...prev, {
        id: Date.now(),
        role: "assistant",
        content: data?.output ?? "Sin respuesta",
      }]);
    } catch (err) {
      setMessages((prev) => [...prev, {
        id: Date.now(),
        role: "assistant",
        content: err.name === "AbortError"
          ? "La consulta tardó demasiado. Intentá de nuevo."
          : `Error al consultar el analista: ${err.message || ""}`,
      }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full">

      {/* Header */}
      <div className="px-6 py-4 flex items-center justify-between" style={{ borderBottom: "1px solid #21262D" }}>
        <div>
          <h1 className="font-semibold text-white flex items-center gap-2">
            <Brain size={18} style={{ color: "#2B6BF3" }} />
            Analista IA
          </h1>
          <p className="text-xs mt-0.5" style={{ color: "#8B949E" }}>
            Análisis inteligente vía n8n
          </p>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full"
          style={{ background: "#0D1B38", border: "1px solid #1e3a6e" }}>
          <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: "#2B6BF3" }} />
          <span className="text-[10px] font-medium" style={{ color: "#79C0FF" }}>Claude · Supabase tools</span>
        </div>
      </div>

      {/* Mensajes */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {messages.map((m) => <Message key={m.id} msg={m} />)}
        {loading && <TypingDots />}
        <div ref={bottomRef} />
      </div>

      {/* Sugerencias */}
      {messages.length <= 1 && !loading && (
        <div className="px-6 pb-2">
          <p className="text-xs mb-2 flex items-center gap-1.5" style={{ color: "#484F58" }}>
            <Sparkles size={11} />
            Preguntas sugeridas
          </p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="text-xs px-3 py-1.5 rounded-lg transition-colors"
                style={{ background: "#161B22", border: "1px solid #21262D", color: "#8B949E" }}
                onMouseEnter={(e) => { e.currentTarget.style.color = "#fff"; e.currentTarget.style.borderColor = "#2B6BF3"; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = "#8B949E"; e.currentTarget.style.borderColor = "#21262D"; }}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="px-6 py-4" style={{ borderTop: "1px solid #21262D" }}>
        <div className="flex gap-3 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            rows={1}
            placeholder="Preguntá sobre métricas, conversaciones, contratos..."
            className="flex-1 input resize-none text-sm"
            style={{ minHeight: "44px", maxHeight: "120px" }}
            onInput={(e) => {
              e.target.style.height = "auto";
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
            }}
            disabled={loading}
          />
          <button
            onClick={() => send()}
            disabled={!input.trim() || loading}
            className="w-11 h-11 rounded-xl flex items-center justify-center transition-all disabled:opacity-40 shrink-0"
            style={{ background: "#2B6BF3" }}
          >
            <Send size={15} className="text-white" />
          </button>
        </div>
      </div>
    </div>
  );
}
