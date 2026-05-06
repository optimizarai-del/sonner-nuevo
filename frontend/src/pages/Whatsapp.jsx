import { useState, useEffect, useRef } from "react";
import { Search, RefreshCw, Phone, Image as ImageIcon, ArrowDown } from "lucide-react";
import { supabase } from "../utils/supabase";
import { format, isToday, isYesterday } from "date-fns";
import { es } from "date-fns/locale";

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatDateLabel(date) {
  if (isToday(date))     return "Hoy";
  if (isYesterday(date)) return "Ayer";
  return format(date, "EEEE d MMMM", { locale: es });
}

function WhatsappLogo() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="#25D366">
      <path d="M17.498 14.382c-.301-.15-1.767-.867-2.04-.966-.273-.101-.473-.15-.673.15-.197.295-.771.964-.944 1.162-.175.195-.349.21-.646.075-.3-.15-1.263-.465-2.403-1.485-.888-.795-1.484-1.77-1.66-2.07-.174-.3-.019-.465.13-.615.136-.135.301-.345.451-.523.146-.181.194-.301.297-.496.1-.21.049-.375-.025-.524-.075-.15-.672-1.62-.922-2.206-.24-.584-.487-.51-.672-.51-.172-.015-.371-.015-.571-.015-.2 0-.523.074-.797.359-.273.3-1.045 1.02-1.045 2.475s1.07 2.865 1.219 3.075c.149.195 2.105 3.195 5.1 4.485.714.3 1.27.48 1.704.629.714.227 1.365.195 1.88.121.574-.091 1.767-.721 2.016-1.426.255-.705.255-1.29.18-1.425-.074-.135-.27-.21-.57-.345m-5.446 7.443h-.016c-1.77 0-3.524-.48-5.055-1.38l-.36-.214-3.75.975 1.005-3.645-.239-.375a9.869 9.869 0 0 1-1.516-5.26c.002-5.45 4.437-9.884 9.892-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413Z"/>
    </svg>
  );
}

// ── Burbuja de mensaje ────────────────────────────────────────────────────────
function MessageBubble({ msg }) {
  const isOut = msg.direction === "out";
  return (
    <div className={`flex ${isOut ? "justify-end" : "justify-start"} mb-1.5`}>
      <div
        className="max-w-[75%] px-3 py-2 rounded-lg text-sm shadow-sm"
        style={{
          background: isOut ? "#005c4b" : "#1f2c33",
          color: "#e9edef",
          borderRadius: isOut ? "8px 8px 2px 8px" : "8px 8px 8px 2px",
        }}
      >
        {msg.media_url && (
          <div className="mb-1 rounded overflow-hidden" style={{ maxHeight: "200px" }}>
            <img src={msg.media_url} alt="media" className="w-full" />
          </div>
        )}
        <p className="whitespace-pre-wrap leading-snug">{msg.content}</p>
        <p className="text-[10px] mt-1 text-right opacity-70">
          {format(new Date(msg.created_at), "HH:mm")}
        </p>
      </div>
    </div>
  );
}

// ── Item de la lista de contactos ─────────────────────────────────────────────
function ContactItem({ contact, active, onClick }) {
  const last = contact.last_message;
  return (
    <button
      onClick={onClick}
      className="w-full px-4 py-3 flex items-center gap-3 transition-colors text-left"
      style={{
        background: active ? "#2A3942" : "transparent",
        borderBottom: "1px solid #21262D",
      }}
      onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = "#1C2230"; }}
      onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = "transparent"; }}
    >
      <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
        style={{ background: "#25D36622", border: "1px solid #25D36644" }}>
        <Phone size={14} style={{ color: "#25D366" }} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-medium text-white truncate">
            {contact.contacto_nombre || contact.contacto}
          </p>
          {last && (
            <span className="text-[10px] shrink-0" style={{ color: "#8B949E" }}>
              {format(new Date(last.created_at), "HH:mm")}
            </span>
          )}
        </div>
        {last && (
          <p className="text-xs truncate mt-0.5" style={{ color: "#8B949E" }}>
            {last.direction === "out" ? "✓ " : ""}{last.content}
          </p>
        )}
      </div>
      {contact.unread > 0 && (
        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full shrink-0"
          style={{ background: "#25D366", color: "#0D1117" }}>
          {contact.unread}
        </span>
      )}
    </button>
  );
}

// ── Componente principal ──────────────────────────────────────────────────────
export default function Whatsapp() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [search, setSearch]     = useState("");
  const [activeContact, setActiveContact] = useState(null);
  const messagesEndRef = useRef(null);

  async function load() {
    setLoading(true);
    const { data } = await supabase
      .from("whatsapp_messages")
      .select("*")
      .order("created_at", { ascending: true })
      .limit(2000);
    setMessages(data ?? []);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  // Realtime: suscripción a nuevos mensajes
  useEffect(() => {
    const channel = supabase
      .channel("whatsapp-realtime")
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "whatsapp_messages" },
        (payload) => setMessages((prev) => [...prev, payload.new])
      )
      .subscribe();
    return () => supabase.removeChannel(channel);
  }, []);

  // Auto-scroll al final cuando cambia el contacto o llegan mensajes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeContact, messages]);

  // Agrupar por contacto
  const contacts = (() => {
    const map = {};
    for (const m of messages) {
      if (!map[m.contacto]) {
        map[m.contacto] = {
          contacto: m.contacto,
          contacto_nombre: m.contacto_nombre,
          msgs: [],
          last_message: null,
        };
      }
      map[m.contacto].msgs.push(m);
      map[m.contacto].last_message = m;
      if (m.contacto_nombre) map[m.contacto].contacto_nombre = m.contacto_nombre;
    }
    return Object.values(map).sort((a, b) =>
      new Date(b.last_message.created_at) - new Date(a.last_message.created_at)
    );
  })();

  const filteredContacts = contacts.filter((c) =>
    !search ||
    c.contacto.includes(search) ||
    c.contacto_nombre?.toLowerCase().includes(search.toLowerCase())
  );

  const activeMessages = activeContact
    ? contacts.find((c) => c.contacto === activeContact)?.msgs ?? []
    : [];

  // Stats
  const totalIn  = messages.filter((m) => m.direction === "in").length;
  const totalOut = messages.filter((m) => m.direction === "out").length;

  // Agrupar mensajes activos por día
  const messagesByDay = {};
  for (const m of activeMessages) {
    const day = format(new Date(m.created_at), "yyyy-MM-dd");
    if (!messagesByDay[day]) messagesByDay[day] = [];
    messagesByDay[day].push(m);
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">

      {/* Header */}
      <div className="px-6 py-4 flex items-center justify-between flex-wrap gap-3 shrink-0"
        style={{ borderBottom: "1px solid #21262D" }}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: "#25D36622", border: "1px solid #25D36644" }}>
            <WhatsappLogo />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">WhatsApp</h1>
            <p className="text-sm" style={{ color: "#8B949E" }}>
              Mensajería del agente externo · {contacts.length} contactos
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-xs font-medium px-3 py-1.5 rounded-full"
            style={{ background: "#1C2230", color: "#8B949E" }}>
            <span style={{ color: "#79C0FF" }}>{totalIn}</span> recibidos · <span style={{ color: "#3FB950" }}>{totalOut}</span> enviados
          </div>
          <button onClick={load} className="btn-ghost flex items-center gap-2 text-xs">
            <RefreshCw size={13} />
            Actualizar
          </button>
        </div>
      </div>

      {/* Body: lista contactos + chat */}
      <div className="flex-1 flex overflow-hidden">

        {/* Sidebar contactos */}
        <div className="w-80 flex flex-col shrink-0" style={{ borderRight: "1px solid #21262D", background: "#0D1117" }}>
          <div className="p-3 shrink-0" style={{ borderBottom: "1px solid #21262D" }}>
            <div className="relative">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2"
                style={{ color: "#484F58" }} />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar contacto..."
                className="input pl-8 text-sm h-9 w-full"
              />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="p-6 text-center text-sm" style={{ color: "#484F58" }}>Cargando...</div>
            ) : filteredContacts.length === 0 ? (
              <div className="p-6 text-center text-sm" style={{ color: "#484F58" }}>
                {messages.length === 0 ? "Sin mensajes aún" : "No hay coincidencias"}
              </div>
            ) : (
              filteredContacts.map((c) => (
                <ContactItem
                  key={c.contacto}
                  contact={c}
                  active={activeContact === c.contacto}
                  onClick={() => setActiveContact(c.contacto)}
                />
              ))
            )}
          </div>
        </div>

        {/* Panel del chat */}
        <div className="flex-1 flex flex-col overflow-hidden"
          style={{
            background: `#0a121a url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='40' height='40' viewBox='0 0 40 40'%3E%3Cpath d='M0 0h40v40H0z' fill='%230a121a'/%3E%3Cpath d='M0 20h40M20 0v40' stroke='%23ffffff03'/%3E%3C/svg%3E")`
          }}>

          {!activeContact ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <WhatsappLogo />
                <p className="text-sm mt-3" style={{ color: "#8B949E" }}>
                  Seleccioná un contacto para ver la conversación
                </p>
              </div>
            </div>
          ) : (
            <>
              {/* Header del chat */}
              <div className="px-4 py-3 flex items-center gap-3 shrink-0"
                style={{ background: "#202c33", borderBottom: "1px solid #21262D" }}>
                <div className="w-9 h-9 rounded-full flex items-center justify-center"
                  style={{ background: "#25D36622" }}>
                  <Phone size={13} style={{ color: "#25D366" }} />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">
                    {contacts.find((c) => c.contacto === activeContact)?.contacto_nombre || activeContact}
                  </p>
                  <p className="text-xs" style={{ color: "#8B949E" }}>{activeContact}</p>
                </div>
              </div>

              {/* Mensajes */}
              <div className="flex-1 overflow-y-auto px-4 py-4">
                {Object.entries(messagesByDay).map(([day, msgs]) => (
                  <div key={day}>
                    <div className="text-center my-3">
                      <span className="text-[10px] font-medium px-3 py-1 rounded-full"
                        style={{ background: "#1f2c33", color: "#8B949E" }}>
                        {formatDateLabel(new Date(day + "T12:00:00"))}
                      </span>
                    </div>
                    {msgs.map((m) => <MessageBubble key={m.id} msg={m} />)}
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
