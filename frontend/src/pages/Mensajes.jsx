import { useState, useEffect } from "react";
import { MessageSquare, RefreshCw, ArrowDownLeft, ArrowUpRight, Users, Activity, TrendingUp } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from "recharts";
import { supabase } from "../utils/supabase";
import { format, subDays } from "date-fns";

// ── Card de estadística ────────────────────────────────────────────────────────
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

// ── Componente principal ──────────────────────────────────────────────────────
export default function Mensajes() {
  const [stats, setStats]   = useState({ total: 0, recibidos: 0, enviados: 0, sesiones: 0 });
  const [chart, setChart]   = useState([]);
  const [topContactos, setTopContactos] = useState([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    const now    = new Date();
    const hace30 = subDays(now, 30).toISOString();

    // 1. Total de mensajes externos (memoria del agente WhatsApp)
    const { count: totalExt } = await supabase
      .from("external_chat_histories")
      .select("*", { count: "exact", head: true });

    // 2. Sesiones únicas (cuántos contactos distintos)
    const { data: sessRows } = await supabase
      .from("external_chat_histories")
      .select("session_id");
    const sesiones = new Set((sessRows ?? []).map((r) => r.session_id)).size;

    // 3. Conteos in/out desde whatsapp_messages (más fiable)
    const [{ count: cIn }, { count: cOut }] = await Promise.all([
      supabase.from("whatsapp_messages").select("*", { count: "exact", head: true }).eq("direction", "in"),
      supabase.from("whatsapp_messages").select("*", { count: "exact", head: true }).eq("direction", "out"),
    ]);

    // 4. Gráfico por día (últimos 30 días)
    const { data: chartRows } = await supabase
      .from("whatsapp_messages")
      .select("direction, created_at")
      .gte("created_at", hace30)
      .order("created_at");

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

    // 5. Top contactos (los que más mensajes intercambiaron)
    const { data: allMsgs } = await supabase
      .from("whatsapp_messages")
      .select("contacto, contacto_nombre")
      .gte("created_at", hace30);

    const counts = {};
    for (const m of (allMsgs ?? [])) {
      const k = m.contacto;
      counts[k] = counts[k] || { contacto: k, nombre: m.contacto_nombre, total: 0 };
      counts[k].total++;
      if (m.contacto_nombre) counts[k].nombre = m.contacto_nombre;
    }
    const top = Object.values(counts).sort((a, b) => b.total - a.total).slice(0, 8);

    setStats({
      total:     totalExt ?? 0,
      recibidos: cIn ?? 0,
      enviados:  cOut ?? 0,
      sesiones,
    });
    setChart(Object.values(byDay));
    setTopContactos(top);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  // Realtime: refrescar cuando hay cambios
  useEffect(() => {
    const ch1 = supabase.channel("ext-msgs-stats")
      .on("postgres_changes",
        { event: "INSERT", schema: "public", table: "whatsapp_messages" },
        () => load())
      .on("postgres_changes",
        { event: "INSERT", schema: "public", table: "external_chat_histories" },
        () => load())
      .subscribe();
    return () => supabase.removeChannel(ch1);
  }, []);

  const TOP_COLORS = ["#25D366", "#79C0FF", "#A371F7", "#D29922", "#3FB950", "#F85149", "#58A6FF", "#FF7B72"];

  return (
    <div className="p-6 space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <MessageSquare size={20} style={{ color: "#25D366" }} />
            Mensajes externos
          </h1>
          <p className="text-sm mt-0.5" style={{ color: "#8B949E" }}>
            Estadísticas del agente WhatsApp · solo mensajes externos
          </p>
        </div>
        <button onClick={load} className="btn-ghost flex items-center gap-2 text-xs">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          Actualizar
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={MessageSquare} label="Total intercambios"   value={stats.total}     color="#25D366" sub="Memoria del agente externo" />
        <StatCard icon={ArrowDownLeft} label="Mensajes recibidos"   value={stats.recibidos} color="#79C0FF" sub="De clientes" />
        <StatCard icon={ArrowUpRight}  label="Mensajes enviados"    value={stats.enviados}  color="#3FB950" sub="Respuestas del agente" />
        <StatCard icon={Users}         label="Conversaciones"        value={stats.sesiones}  color="#A371F7" sub="Contactos únicos" />
      </div>

      {/* Gráfico mensajes por día */}
      <div className="rounded-2xl p-5" style={{ background: "#161B22", border: "1px solid #21262D" }}>
        <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <TrendingUp size={14} style={{ color: "#25D366" }} />
          Volumen por día (últimos 30 días)
        </h2>
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={chart} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="msgIn" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#79C0FF" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#79C0FF" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="msgOut" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#3FB950" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3FB950" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="dia" tick={{ fill: "#484F58", fontSize: 10 }} tickLine={false} axisLine={false} interval={4} />
            <YAxis tick={{ fill: "#484F58", fontSize: 10 }} tickLine={false} axisLine={false} />
            <Tooltip content={<TooltipBox />} />
            <Area type="monotone" dataKey="recibidos" name="Recibidos" stroke="#79C0FF" strokeWidth={2} fill="url(#msgIn)" dot={false} />
            <Area type="monotone" dataKey="enviados"  name="Enviados"  stroke="#3FB950" strokeWidth={2} fill="url(#msgOut)" dot={false} />
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

      {/* Top contactos */}
      <div className="rounded-2xl p-5" style={{ background: "#161B22", border: "1px solid #21262D" }}>
        <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <Activity size={14} style={{ color: "#A371F7" }} />
          Top contactos (últimos 30 días)
        </h2>
        {topContactos.length === 0 ? (
          <p className="text-xs text-center py-6" style={{ color: "#484F58" }}>
            Sin actividad de contactos aún
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(200, topContactos.length * 32)}>
            <BarChart data={topContactos} layout="vertical" margin={{ top: 0, right: 16, left: 80, bottom: 0 }}>
              <XAxis type="number" tick={{ fill: "#484F58", fontSize: 10 }} tickLine={false} axisLine={false} />
              <YAxis
                type="category"
                dataKey={(d) => d.nombre || d.contacto}
                tick={{ fill: "#8B949E", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                width={140}
              />
              <Tooltip cursor={{ fill: "#1C2230" }} content={<TooltipBox />} />
              <Bar dataKey="total" name="Mensajes" radius={[0, 4, 4, 0]}>
                {topContactos.map((_, i) => <Cell key={i} fill={TOP_COLORS[i % TOP_COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
