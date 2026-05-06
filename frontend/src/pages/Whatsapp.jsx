import { useState, useEffect } from "react";
import { ArrowDownLeft, ArrowUpRight, MessageCircle, RefreshCw, Users, Activity, TrendingUp } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { supabase } from "../utils/supabase";
import { format, subDays, startOfDay } from "date-fns";

function WhatsappLogo({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="#25D366">
      <path d="M17.498 14.382c-.301-.15-1.767-.867-2.04-.966-.273-.101-.473-.15-.673.15-.197.295-.771.964-.944 1.162-.175.195-.349.21-.646.075-.3-.15-1.263-.465-2.403-1.485-.888-.795-1.484-1.77-1.66-2.07-.174-.3-.019-.465.13-.615.136-.135.301-.345.451-.523.146-.181.194-.301.297-.496.1-.21.049-.375-.025-.524-.075-.15-.672-1.62-.922-2.206-.24-.584-.487-.51-.672-.51-.172-.015-.371-.015-.571-.015-.2 0-.523.074-.797.359-.273.3-1.045 1.02-1.045 2.475s1.07 2.865 1.219 3.075c.149.195 2.105 3.195 5.1 4.485.714.3 1.27.48 1.704.629.714.227 1.365.195 1.88.121.574-.091 1.767-.721 2.016-1.426.255-.705.255-1.29.18-1.425-.074-.135-.27-.21-.57-.345m-5.446 7.443h-.016c-1.77 0-3.524-.48-5.055-1.38l-.36-.214-3.75.975 1.005-3.645-.239-.375a9.869 9.869 0 0 1-1.516-5.26c.002-5.45 4.437-9.884 9.892-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413Z"/>
    </svg>
  );
}

function StatCard({ icon: Icon, label, value, color, sub }) {
  return (
    <div className="rounded-2xl p-5"
      style={{ background: "#161B22", border: "1px solid #21262D" }}>
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 rounded-lg flex items-center justify-center"
          style={{ background: `${color}22`, border: `1px solid ${color}44` }}>
          <Icon size={18} style={{ color }} />
        </div>
        <p className="text-sm font-medium" style={{ color: "#8B949E" }}>{label}</p>
      </div>
      <p className="text-3xl font-bold text-white">{value.toLocaleString("es-AR")}</p>
      {sub && <p className="text-xs mt-1" style={{ color: "#484F58" }}>{sub}</p>}
    </div>
  );
}

const TooltipBox = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg px-3 py-2 text-sm shadow-xl"
      style={{ background: "#161B22", border: "1px solid #21262D" }}>
      <p className="mb-1" style={{ color: "#8B949E" }}>{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }} className="font-medium">
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  );
};

export default function Whatsapp() {
  const [stats, setStats] = useState({ in: 0, out: 0, contacts: 0, today: 0 });
  const [chart, setChart] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);

  async function load() {
    setLoading(true);
    const now    = new Date();
    const hace30 = subDays(now, 30).toISOString();
    const hoy    = startOfDay(now).toISOString();

    const [
      { count: cIn },
      { count: cOut },
      { count: cToday },
      { data: contactRows },
      { data: chartRows },
    ] = await Promise.all([
      supabase.from("whatsapp_messages").select("*", { count: "exact", head: true }).eq("direction", "in"),
      supabase.from("whatsapp_messages").select("*", { count: "exact", head: true }).eq("direction", "out"),
      supabase.from("whatsapp_messages").select("*", { count: "exact", head: true }).gte("created_at", hoy),
      supabase.from("whatsapp_messages").select("contacto").gte("created_at", hace30),
      supabase.from("whatsapp_messages").select("direction, created_at").gte("created_at", hace30).order("created_at"),
    ]);

    const uniqueContacts = new Set((contactRows ?? []).map((r) => r.contacto)).size;

    const byDay = {};
    for (let i = 0; i < 30; i++) {
      const d = format(subDays(now, 29 - i), "dd/MM");
      byDay[d] = { dia: d, recibidos: 0, enviados: 0 };
    }
    for (const r of (chartRows ?? [])) {
      const d = format(new Date(r.created_at), "dd/MM");
      if (!byDay[d]) continue;
      if (r.direction === "in")  byDay[d].recibidos++;
      else                        byDay[d].enviados++;
    }

    setStats({
      in:       cIn ?? 0,
      out:      cOut ?? 0,
      contacts: uniqueContacts,
      today:    cToday ?? 0,
    });
    setChart(Object.values(byDay));
    setLastUpdate(new Date());
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  // Realtime: refrescar cuando llegan mensajes nuevos
  useEffect(() => {
    const channel = supabase
      .channel("whatsapp-stats")
      .on("postgres_changes",
        { event: "INSERT", schema: "public", table: "whatsapp_messages" },
        () => load()
      )
      .subscribe();
    return () => supabase.removeChannel(channel);
  }, []);

  return (
    <div className="p-6 space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center"
            style={{ background: "#25D36622", border: "1px solid #25D36644" }}>
            <WhatsappLogo size={22} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">WhatsApp</h1>
            <p className="text-sm" style={{ color: "#8B949E" }}>
              Estadísticas del agente externo
              {lastUpdate && (
                <span className="ml-2 text-xs" style={{ color: "#484F58" }}>
                  · Actualizado {format(lastUpdate, "HH:mm:ss")}
                </span>
              )}
            </p>
          </div>
        </div>
        <button onClick={load} className="btn-ghost flex items-center gap-2 text-xs">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          Actualizar
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={ArrowDownLeft} label="Mensajes recibidos" value={stats.in}       color="#79C0FF" sub="Total histórico" />
        <StatCard icon={ArrowUpRight}  label="Mensajes enviados"  value={stats.out}      color="#3FB950" sub="Respuestas del agente" />
        <StatCard icon={Activity}      label="Hoy"                value={stats.today}    color="#D29922" sub="Mensajes intercambiados" />
        <StatCard icon={Users}         label="Contactos únicos"   value={stats.contacts} color="#A371F7" sub="Últimos 30 días" />
      </div>

      {/* Stats secundarias */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-2xl p-5" style={{ background: "#161B22", border: "1px solid #21262D" }}>
          <div className="flex items-center gap-2 mb-2">
            <MessageCircle size={14} style={{ color: "#25D366" }} />
            <p className="text-sm font-medium" style={{ color: "#8B949E" }}>Total intercambios</p>
          </div>
          <p className="text-2xl font-bold text-white">{(stats.in + stats.out).toLocaleString("es-AR")}</p>
        </div>
        <div className="rounded-2xl p-5" style={{ background: "#161B22", border: "1px solid #21262D" }}>
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={14} style={{ color: "#3FB950" }} />
            <p className="text-sm font-medium" style={{ color: "#8B949E" }}>Tasa de respuesta</p>
          </div>
          <p className="text-2xl font-bold text-white">
            {stats.in > 0 ? `${Math.round((stats.out / stats.in) * 100)}%` : "—"}
          </p>
        </div>
        <div className="rounded-2xl p-5" style={{ background: "#161B22", border: "1px solid #21262D" }}>
          <div className="flex items-center gap-2 mb-2">
            <Activity size={14} style={{ color: "#D29922" }} />
            <p className="text-sm font-medium" style={{ color: "#8B949E" }}>Promedio diario</p>
          </div>
          <p className="text-2xl font-bold text-white">{Math.round((stats.in + stats.out) / 30)}</p>
        </div>
      </div>

      {/* Gráfico */}
      <div className="rounded-2xl p-5" style={{ background: "#161B22", border: "1px solid #21262D" }}>
        <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <TrendingUp size={14} style={{ color: "#25D366" }} />
          Mensajes por día (últimos 30 días)
        </h2>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={chart} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="gradIn" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#79C0FF" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#79C0FF" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradOut" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#3FB950" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3FB950" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="dia" tick={{ fill: "#484F58", fontSize: 10 }} tickLine={false} axisLine={false} interval={4} />
            <YAxis tick={{ fill: "#484F58", fontSize: 10 }} tickLine={false} axisLine={false} />
            <Tooltip content={<TooltipBox />} />
            <Area type="monotone" dataKey="recibidos" name="Recibidos" stroke="#79C0FF" strokeWidth={2} fill="url(#gradIn)" dot={false} />
            <Area type="monotone" dataKey="enviados"  name="Enviados"  stroke="#3FB950" strokeWidth={2} fill="url(#gradOut)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
        <div className="flex items-center gap-4 mt-3 justify-center text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: "#79C0FF" }} />
            <span style={{ color: "#8B949E" }}>Recibidos</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: "#3FB950" }} />
            <span style={{ color: "#8B949E" }}>Enviados</span>
          </div>
        </div>
      </div>
    </div>
  );
}
