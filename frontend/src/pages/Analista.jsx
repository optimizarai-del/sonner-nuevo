import { useState, useRef, useEffect } from "react";
import { Send, Brain, User, Sparkles, BarChart2 } from "lucide-react";
import api from "../utils/api";

const SUGGESTIONS = [
  "¿Cuántos mensajes se enviaron esta semana?",
  "¿Cuál es el canal más activo?",
  "¿Cuáles fueron las consultas más frecuentes?",
  "¿Cuántos contratos se generaron este mes?",
  "¿Hay patrones en los horarios de mayor actividad?",
  "¿Qué temas se consultan más en WhatsApp?",
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
        {isUser
          ? <User size={14} className="text-[#8B949E]" />
          : <Brain size={14} className="text-snr-400" />
        }
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
        {msg.time && (
          <p className="text-[#484F58] text-[10px] mt-2">{msg.time}</p>
        )}
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 bg-[#0D1B38] border border-[#1e3a6e]">
        <Brain size={14} className="text-snr-400" />
      </div>
      <div className="bg-[#0D1B38] border border-[#1e3a6e] rounded-2xl px-4 py-3">
        <div className="flex gap-1 items-center">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-snr-400 animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
          <span className="text-[#484F58] text-xs ml-2">Analizando datos...</span>
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
      content: "Hola, soy el Analista de Datos de SNR. Tengo acceso a las métricas de conversaciones, contratos y memoria del sistema. Podés preguntarme cualquier cosa sobre el rendimiento de los agentes.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(text) {
    const q = (text || input).trim();
    if (!q || loading) return;
    setInput("");
    setMessages((prev) => [
      ...prev,
      { id: Date.now(), role: "user", content: q },
    ]);
    setLoading(true);

    try {
      const { data } = await api.post("/analyst/query", { question: q });
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          role: "assistant",
          content: data.answer,
          time: new Date(data.context_date).toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: Date.now(), role: "assistant", content: "Error al consultar los datos. Intentá de nuevo." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-[#21262D] px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="font-semibold text-white flex items-center gap-2">
            <Brain size={18} className="text-snr-400" />
            Analista IA
          </h1>
          <p className="text-xs text-[#8B949E] mt-0.5">Análisis inteligente de la base de datos de conversaciones</p>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-[#0D1B38] border border-[#1e3a6e] rounded-full">
          <span className="w-1.5 h-1.5 rounded-full bg-snr-400 animate-pulse" />
          <span className="text-[10px] text-snr-300 font-medium">claude-sonnet-4-6</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {messages.map((m) => <Message key={m.id} msg={m} />)}
        {loading && <TypingDots />}
        <div ref={bottomRef} />
      </div>

      {/* Suggestions */}
      {messages.length <= 1 && !loading && (
        <div className="px-6 pb-2">
          <p className="text-xs text-[#484F58] mb-2 flex items-center gap-1.5">
            <Sparkles size={11} />
            Preguntas sugeridas
          </p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="text-xs px-3 py-1.5 rounded-lg bg-[#161B22] border border-[#21262D] text-[#8B949E] hover:text-white hover:border-snr-500 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-[#21262D] px-6 py-4">
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
