import { useState, useRef, useEffect } from "react";
import { Send, Bot, User } from "lucide-react";
import api from "../utils/api";

function generateSessionId() {
  return `web-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function TypingIndicator() {
  return (
    <div className="flex items-end gap-3 mb-4">
      <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0" style={{ background: "#0D1B38", border: "1px solid #1e3a6e" }}>
        <Bot size={13} style={{ color: "#2B6BF3" }} />
      </div>
      <div className="rounded-2xl rounded-bl-sm px-4 py-3" style={{ background: "#0D1B38", border: "1px solid #1e3a6e" }}>
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span key={i} className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: "#2B6BF3", animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
      </div>
    </div>
  );
}

function Message({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex items-end gap-3 mb-4 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
        style={isUser
          ? { background: "#21262D", border: "1px solid #30363D" }
          : { background: "#0D1B38", border: "1px solid #1e3a6e" }
        }
      >
        {isUser
          ? <User size={13} style={{ color: "#8B949E" }} />
          : <Bot size={13} style={{ color: "#2B6BF3" }} />
        }
      </div>
      <div
        className="max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap"
        style={isUser
          ? { background: "#2B6BF3", color: "#fff", borderBottomRightRadius: 4 }
          : { background: "#0D1B38", color: "#79C0FF", border: "1px solid #1e3a6e", borderBottomLeftRadius: 4 }
        }
      >
        {msg.content}
      </div>
    </div>
  );
}

export default function Chat() {
  const [messages, setMessages] = useState([
    { id: 0, role: "assistant", content: "Hola, soy el asistente interno de Sonner. ¿En qué puedo ayudarte?" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => {
    const stored = sessionStorage.getItem("sonner_session");
    if (stored) return stored;
    const id = generateSessionId();
    sessionStorage.setItem("sonner_session", id);
    return id;
  });
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send() {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { id: Date.now(), role: "user", content: text }]);
    setLoading(true);

    try {
      const { data } = await api.post("/chat/pagina/sync", { sessionId, message: text });
      const parts = data.messages || [];
      for (let i = 0; i < parts.length; i++) {
        await new Promise((r) => setTimeout(r, i === 0 ? 0 : 600));
        setMessages((prev) => [...prev, { id: Date.now() + i, role: "assistant", content: parts[i] }]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: Date.now(), role: "assistant", content: "Error al procesar el mensaje. Intentá de nuevo." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-4" style={{ borderBottom: "1px solid #21262D" }}>
        <h1 className="font-semibold text-white">Chat Interno</h1>
        <p className="text-xs mt-0.5" style={{ color: "#8B949E" }}>Calendario · Memoria · Información interna</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.map((m) => <Message key={m.id} msg={m} />)}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4" style={{ borderTop: "1px solid #21262D" }}>
        <div className="flex gap-3 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            rows={1}
            placeholder="Escribí un mensaje... (Enter para enviar)"
            className="flex-1 input resize-none text-sm"
            style={{ minHeight: "44px", maxHeight: "120px" }}
            onInput={(e) => {
              e.target.style.height = "auto";
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
            }}
          />
          <button
            onClick={send}
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
