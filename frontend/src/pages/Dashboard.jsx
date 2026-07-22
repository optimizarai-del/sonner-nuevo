import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { MessageSquare, FileText, Shield, Activity, Users, RefreshCw } from "lucide-react";
import { supabase } from "../utils/supabase";
import { format } from "date-fns";
import { es } from "date-fns/locale";

// Sesiones que NO son contactos reales (estados de WhatsApp, keep-alive, tests web)
function esContactoReal(sid) {
  if (!sid) return false;
  const s = String(sid).trim().toLowerCase();
  if (["+status", "status", "healthcheck", "test"].includes(s) || s.startsWith("web-") || s.startsWith("test")) return false;
  return (s.match(/\d/g) || []).length >= 8; // parece un teléfono
}
// Muestra el teléfono un poco acortado para la etiqueta del gráfico
const shortTel = (s) => (String(s).length > 8 ? "…" + String(s).slice(-8) : String(s));

function KpiCard({ icon: Icon, label, value, sub, color = "#2B6BF3" }) {
  return (
    <div className="card p-5 flex items-start gap-4">
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
        style={{ backgroundColor: `${color}22`, border: `1px solid ${color}44` }}
      >
        <Icon size={18} style={{ color }} />
      </div>
      <div>
        <p className="text-xs font-medium mb-1" style={{ color: "#8B949E" }}>{label}</p>
        <p className="text-white text-2xl font-bold">{value ?? "—"}</p>
        {sub && <p className="text-xs mt-1" style={{ color: "#8B949E" }}>{sub}</p>}
      </div>
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }) => {
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

export default function Dashboard() {
  const [stats, setStats]   = useState(null);
  const [chart, setChart]   = useState([]);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const now = new Date();
      const mesInicio = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();

      const [
        { count: totalContratos },
        { count: mesContratos },
        { count: totalBloqueados },
        { data: chatSesiones },
        { data: contratosRecientes },
      ] = await Promise.all([
        supabase.from("contratos").select("*", { count: "exact", head: true }),
        supabase.from("contratos").select("*", { count: "exact", head: true }).gte("created_at", mesInicio),
        supabase.from("blocklist").select("*", { count: "exact", head: true }),
        // Conversaciones del agente principal (Tomi). La tabla no tiene fecha, así que
        // no hay serie temporal: agrupamos por contacto (session_id).
        supabase.from("n8n_chat_histories").select("session_id"),
        supabase.from("contratos").select("nombre_prestatario, lugar_evento, dia_evento, created_at").order("created_at", { ascending: false }).limit(5),
      ]);

      // Tally por contacto real (filtrando estados/keep-alive/tests)
      const porContacto = {};
      let mensajesReales = 0;
      for (const row of (chatSesiones ?? [])) {
        if (!esContactoReal(row.session_id)) continue;
        porContacto[row.session_id] = (porContacto[row.session_id] || 0) + 1;
        mensajesReales++;
      }
      const top = Object.entries(porContacto)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8)
        .map(([contacto, mensajes]) => ({ contacto: shortTel(contacto), mensajes }));

      setStats({
        contratos: { total: totalContratos ?? 0, mes: mesContratos ?? 0 },
        mensajes:  mensajesReales,
        contactos: Object.keys(porContacto).length,
        bloqueados: totalBloqueados ?? 0,
      });
      setChart(top);
      setRecent(contratosRecientes ?? []);

    } catch (e) {
      console.warn("[Dashboard]", e);
    }
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  const kpis = stats ? [
    { icon: FileText,      label: "Contratos generados",  value: stats.contratos.total, sub: `${stats.contratos.mes} este mes`,       color: "#3FB950" },
    { icon: MessageSquare, label: "Mensajes del agente",   value: stats.mensajes,        sub: "Conversaciones WhatsApp (Tomi)",         color: "#25D366" },
    { icon: Users,         label: "Contactos únicos",      value: stats.contactos,       sub: "Personas que escribieron al agente",     color: "#2B6BF3" },
    { icon: Shield,        label: "Contactos bloqueados",  value: stats.bloqueados,      sub: "Lista de bloqueo agente externo",         color: "#F85149" },
  ] : [];

  return (
    <div className="p-6 space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Activity size={20} style={{ color: "#2B6BF3" }} />
            Dashboard
          </h1>
          <p className="text-sm mt-0.5" style={{ color: "#8B949E" }}>Resumen de actividad</p>
        </div>
        <button onClick={load} className="btn-ghost flex items-center gap-2 text-xs">
          <RefreshCw size={14} />
          Actualizar
        </button>
      </div>

      {/* KPIs */}
      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="card p-5 h-24 animate-pulse" style={{ background: "#161B22" }} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {kpis.map((k) => <KpiCard key={k.label} {...k} />)}
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Contactos más activos */}
        <div className="lg:col-span-2 card p-5">
          <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Users size={14} style={{ color: "#2B6BF3" }} />
            Contactos más activos (agente WhatsApp)
          </h2>
          {chart.length === 0 ? (
            <p className="text-xs text-center py-16" style={{ color: "#484F58" }}>Sin conversaciones registradas.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chart} layout="vertical" margin={{ top: 0, right: 12, left: 8, bottom: 0 }}>
                <XAxis type="number" tick={{ fill: "#484F58", fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="contacto" width={78} tick={{ fill: "#8B949E", fontSize: 11 }} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: "#ffffff08" }} />
                <Bar dataKey="mensajes" name="Mensajes" radius={[0, 4, 4, 0]}>
                  {chart.map((_, i) => <Cell key={i} fill="#2B6BF3" />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Últimos contratos */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <FileText size={14} style={{ color: "#3FB950" }} />
            Últimos contratos
          </h2>
          <div className="space-y-3">
            {recent.length === 0 ? (
              <p className="text-xs text-center py-4" style={{ color: "#484F58" }}>Sin contratos aún</p>
            ) : (
              recent.map((c) => (
                <div key={c.created_at + c.nombre_prestatario} className="flex flex-col gap-0.5">
                  <p className="text-sm font-medium text-white truncate">{c.nombre_prestatario}</p>
                  <div className="flex items-center justify-between">
                    <p className="text-xs truncate" style={{ color: "#8B949E" }}>{c.lugar_evento}</p>
                    <p className="text-xs shrink-0 ml-2" style={{ color: "#484F58" }}>
                      {format(new Date(c.created_at), "dd/MM", { locale: es })}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
