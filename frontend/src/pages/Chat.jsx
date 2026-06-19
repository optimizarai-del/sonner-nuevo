import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Bot, User, Trash2, Loader2 } from "lucide-react";
import { supabase } from "../utils/supabase";
import { getUser } from "../utils/auth";

// ── Configuración ──────────────────────────────────────────────────────────────
const N8N_WEBHOOK = import.meta.env.VITE_N8N_WEBHOOK_INTERNO
  || "https://n8n.optimizar-ia.com/webhook/sonner-pagina";

const RESPONSE_TIMEOUT_MS = 90_000;

// ── Welcome message según rol ─────────────────────────────────────────────────
const WELCOME = {
  admin:     "Hola, soy el asistente interno de Sonner. Puedo consultar calendario, memoria, contratos, eventos y materiales. ¿En qué te ayudo?",
  armador:   "Hola. Como armador, te puedo decir qué eventos tenés próximos y qué materiales hay que cargar. ¿Qué consultás?",
  mayorista: "Hola. Te puedo informar disponibilidad de materiales y fechas. ¿En qué te ayudo?",
  deposito:  "Hola. Te puedo decir qué eventos hay próximos y qué materiales necesitás llevar para cada uno. ¿Qué consultás?",
};

// ── Sub-componentes ────────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex items-end gap-3 mb-4">
      <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
        style={{ background: "#0D1B38", border: "1px solid #1e3a6e" }}>
        <Bot size={13} style={{ color: "#2B6BF3" }} />
      </div>
      <div className="rounded-2xl rounded-bl-sm px-4 py-3"
        style={{ background: "#0D1B38", border: "1px solid #1e3a6e" }}>
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span key={i} className="w-1.5 h-1.5 rounded-full animate-bounce"
              style={{ background: "#2B6BF3", animationDelay: `${i * 0.15}s` }} />
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
      <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
        style={isUser
          ? { background: "#21262D", border: "1px solid #30363D" }
          : { background: "#0D1B38", border: "1px solid #1e3a6e" }}>
        {isUser ? <User size={13} style={{ color: "#8B949E" }} />
                : <Bot  size={13} style={{ color: "#2B6BF3" }} />}
      </div>
      <div className="max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap"
        style={isUser
          ? { background: "#2B6BF3", color: "#fff", borderBottomRightRadius: 4 }
          : { background: "#0D1B38", color: "#79C0FF", border: "1px solid #1e3a6e", borderBottomLeftRadius: 4 }}>
        {msg.content}
      </div>
    </div>
  );
}

// ── Parsear mensajes guardados en n8n_chat_histories ─────────────────────────
function parseStoredMessage(row) {
  const msg = row.message ?? {};
  const role = msg.type === "human" ? "user" : "assistant";
  let content = msg.data?.content ?? msg.content ?? "";
  // El agente puede devolver JSON anidado
  if (typeof content === "string" && content.trim().startsWith("{")) {
    try {
      const parsed = JSON.parse(content);
      content = parsed.output?.respuesta ?? parsed.respuesta
              ?? (typeof parsed.output === "string" ? parsed.output : null)
              ?? content;
    } catch {}
  }
  return { id: `db-${row.id}`, role, content };
}

// ── Componente principal ─────────────────────────────────────────────────────
export default function Chat() {
  const user = getUser() || { id: "anon", name: "Usuario", role: "admin" };
  // sessionId persistente por usuario (no por pestaña)
  const sessionId = `user-${user.id}`;

  const [messages, setMessages]   = useState([]);
  const [input, setInput]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [loadingHist, setLoadingHist] = useState(true);

  const bottomRef = useRef(null);
  const abortRef  = useRef(null);

  // ── Cargar historial al montar ─────────────────────────────────────────────
  useEffect(() => {
    async function loadHistory() {
      setLoadingHist(true);
      try {
        const { data } = await supabase
          .from("n8n_chat_histories")
          .select("id, session_id, message")
          .eq("session_id", sessionId)
          .order("id", { ascending: true })
          .limit(500);

        const parsed = (data ?? [])
          .map(parseStoredMessage)
          .filter((m) => m.content);

        if (parsed.length === 0) {
          // Sin historial → mensaje de bienvenida según rol
          setMessages([{
            id: "welcome",
            role: "assistant",
            content: WELCOME[user.role] || WELCOME.admin,
          }]);
        } else {
          setMessages(parsed);
        }
      } catch (e) {
        console.warn("[Chat] No se pudo cargar historial:", e);
        setMessages([{
          id: "welcome",
          role: "assistant",
          content: WELCOME[user.role] || WELCOME.admin,
        }]);
      } finally {
        setLoadingHist(false);
      }
    }
    loadHistory();
  }, [sessionId, user.role]);

  // ── Scroll automático ──────────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => () => abortRef.current?.abort(), []);

  // ── Enviar mensaje ─────────────────────────────────────────────────────────
  const send = useCallback(async () => {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput("");

    setMessages((prev) => [...prev, { id: `user-${Date.now()}`, role: "user", content: text }]);
    setLoading(true);

    const controller = new AbortController();
    abortRef.current = controller;
    const timeoutId = setTimeout(() => controller.abort(), RESPONSE_TIMEOUT_MS);

    try {
      const res = await fetch(N8N_WEBHOOK, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sessionId,
          message: text,
          // Datos del usuario para que el agente n8n pueda filtrar por rol
          user: {
            id:   user.id,
            name: user.name,
            role: user.role,
          },
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      if (!res.ok) throw new Error(`n8n respondió ${res.status}`);

      const raw = await res.text();
      let reply;
      try {
        const data = JSON.parse(raw);
        reply = typeof data === "string"
          ? data
          : data.output ?? data.text ?? data.message ?? data.reply ?? data.respuesta ?? JSON.stringify(data);
      } catch {
        reply = raw;
      }

      setMessages((prev) => [...prev, { id: `assistant-${Date.now()}`, role: "assistant", content: reply }]);
    } catch (err) {
      clearTimeout(timeoutId);
      const isTimeout = err.name === "AbortError";
      setMessages((prev) => [...prev, {
        id: `err-${Date.now()}`,
        role: "assistant",
        content: isTimeout
          ? "La respuesta tardó demasiado. Por favor intentá de nuevo."
          : "No se pudo conectar con el agente. Verificá tu conexión.",
      }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, sessionId, user]);

  // ── Limpiar historial ──────────────────────────────────────────────────────
  async function limpiarHistorial() {
    if (!confirm("¿Eliminar todo el historial de chat? No se puede deshacer.")) return;
    try {
      await supabase.from("n8n_chat_histories").delete().eq("session_id", sessionId);
      setMessages([{
        id: "welcome",
        role: "assistant",
        content: WELCOME[user.role] || WELCOME.admin,
      }]);
    } catch (e) {
      console.warn("[Chat] Error limpiando:", e);
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full">

      {/* Header */}
      <div className="px-6 py-4 flex items-center justify-between" style={{ borderBottom: "1px solid #21262D" }}>
        <div>
          <h1 className="font-semibold text-white">Chat Interno</h1>
          <p className="text-xs mt-0.5" style={{ color: "#8B949E" }}>
            {user.role === "admin"     && "Calendario · Memoria · Información interna"}
            {user.role === "armador"   && "Eventos próximos y materiales del armado"}
            {user.role === "mayorista" && "Disponibilidad de inventario y fechas"}
            {user.role === "deposito"  && "Eventos y materiales — solo consulta"}
          </p>
        </div>
        <button
          onClick={limpiarHistorial}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-colors"
          style={{ background: "#21262D", color: "#8B949E", border: "1px solid #30363D" }}
          title="Eliminar todo el historial"
        >
          <Trash2 size={12} />
          Limpiar
        </button>
      </div>

      {/* Mensajes */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {loadingHist ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 size={18} className="animate-spin" style={{ color: "#8B949E" }} />
          </div>
        ) : (
          <>
            {messages.map((m) => <Message key={m.id} msg={m} />)}
            {loading && <TypingIndicator />}
          </>
        )}
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
            disabled={loading || loadingHist}
          />
          <button
            onClick={send}
            disabled={!input.trim() || loading || loadingHist}
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
