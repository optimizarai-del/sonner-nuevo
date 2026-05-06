import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Bot, User } from "lucide-react";

// ── Configuración ──────────────────────────────────────────────────────────────
const N8N_WEBHOOK = import.meta.env.VITE_N8N_WEBHOOK_INTERNO
  || "https://n8n.optimizar-ia.com/webhook/sonner-pagina";

const RESPONSE_TIMEOUT_MS = 90_000; // 90s máximo esperando respuesta

// ── Session ID (persiste en la pestaña) ───────────────────────────────────────
function getOrCreateSessionId() {
  const stored = sessionStorage.getItem("sonner_session");
  if (stored) return stored;
  const id = `web-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  sessionStorage.setItem("sonner_session", id);
  return id;
}

// ── Sub-componentes ────────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex items-end gap-3 mb-4">
      <div
        className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
        style={{ background: "#0D1B38", border: "1px solid #1e3a6e" }}
      >
        <Bot size={13} style={{ color: "#2B6BF3" }} />
      </div>
      <div
        className="rounded-2xl rounded-bl-sm px-4 py-3"
        style={{ background: "#0D1B38", border: "1px solid #1e3a6e" }}
      >
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 rounded-full animate-bounce"
              style={{ background: "#2B6BF3", animationDelay: `${i * 0.15}s` }}
            />
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
        style={
          isUser
            ? { background: "#21262D", border: "1px solid #30363D" }
            : { background: "#0D1B38", border: "1px solid #1e3a6e" }
        }
      >
        {isUser
          ? <User size={13} style={{ color: "#8B949E" }} />
          : <Bot  size={13} style={{ color: "#2B6BF3" }} />
        }
      </div>
      <div
        className="max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap"
        style={
          isUser
            ? { background: "#2B6BF3", color: "#fff", borderBottomRightRadius: 4 }
            : { background: "#0D1B38", color: "#79C0FF", border: "1px solid #1e3a6e", borderBottomLeftRadius: 4 }
        }
      >
        {msg.content}
      </div>
    </div>
  );
}

// ── Componente principal ───────────────────────────────────────────────────────
export default function Chat() {
  const [sessionId]             = useState(getOrCreateSessionId);
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      content: "Hola, soy el asistente interno de Sonner. ¿En qué puedo ayudarte?",
    },
  ]);
  const [input, setInput]       = useState("");
  const [loading, setLoading]   = useState(false);

  const bottomRef  = useRef(null);
  const abortRef   = useRef(null); // AbortController para cancelar fetch

  // ── Scroll automático ────────────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // ── Cleanup al desmontar ──────────────────────────────────────────────────────
  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  // ── Enviar mensaje ────────────────────────────────────────────────────────────
  const send = useCallback(async () => {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput("");

    // Agregar mensaje del usuario optimistamente
    setMessages((prev) => [
      ...prev,
      { id: `user-${Date.now()}`, role: "user", content: text },
    ]);
    setLoading(true);

    // AbortController con timeout de 90s
    const controller = new AbortController();
    abortRef.current = controller;
    const timeoutId = setTimeout(() => controller.abort(), RESPONSE_TIMEOUT_MS);

    try {
      const res = await fetch(N8N_WEBHOOK, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sessionId, message: text }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!res.ok) throw new Error(`n8n respondió ${res.status}`);

      const data = await res.json();

      // n8n puede devolver: { output: "..." } o { text: "..." } o string directo
      const reply =
        typeof data === "string"
          ? data
          : data.output ?? data.text ?? data.message ?? data.reply ?? JSON.stringify(data);

      setMessages((prev) => [
        ...prev,
        { id: `assistant-${Date.now()}`, role: "assistant", content: reply },
      ]);
    } catch (err) {
      clearTimeout(timeoutId);
      const isTimeout = err.name === "AbortError";
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: isTimeout
            ? "La respuesta tardó demasiado. Por favor intentá de nuevo."
            : "No se pudo conectar con el agente. Verificá tu conexión.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, sessionId]);

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full">

      {/* Header */}
      <div className="px-6 py-4" style={{ borderBottom: "1px solid #21262D" }}>
        <h1 className="font-semibold text-white">Chat Interno</h1>
        <p className="text-xs mt-0.5" style={{ color: "#8B949E" }}>
          Calendario · Memoria · Información interna
        </p>
      </div>

      {/* Mensajes */}
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
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
            }}
            rows={1}
            placeholder="Escribí un mensaje... (Enter para enviar)"
            className="flex-1 input resize-none text-sm"
            style={{ minHeight: "44px", maxHeight: "120px" }}
            onInput={(e) => {
              e.target.style.height = "auto";
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
            }}
            disabled={loading}
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
