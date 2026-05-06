import { useState, useEffect } from "react";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import {
  MessageSquare, Users, FileText, Database,
  TrendingUp, Activity, Zap, Globe,
} from "lucide-react";
import api from "../utils/api";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const CANAL_COLORS = {
  web: "#2B6BF3",
  telegram: "#0088cc",
  whatsapp: "#25D366",
};

const CANAL_LABELS = { web: "Web", telegram: "Telegram", whatsapp: "WhatsApp" };

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
        <p className="text-[#8B949E] text-xs font-medium mb-1">{label}</p>
        <p className="text-white text-2xl font-bold">{value ?? "—"}</p>
        {sub && <p className="text-[#8B949E] text-xs mt-1">{sub}</p>}
      </div>
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#161B22] border border-[#21262D] rounded-lg px-3 py-2 text-sm shadow-xl">
      <p className="text-[#8B949E] mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }} className="font-medium">
          {CANAL_LABELS[p.dataKey] || p.dataKey}: {p.value}
        </p>
      ))}
    </div>
  );
};

export default function Dashboard() {
  const [overview, setOverview] = useState(null);
  const [daily, setDaily] = useState([]);
  const [active, setActive] = useState([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const [ov, dy, ac] = await Promise.all([
        api.get("/metrics/overview"),
        api.get("/metrics/mensajes-por-dia?dias=30"),
        api.get("/metrics/sesiones-activas"),
      ]);
      setOverview(ov.data);
      // Pivot daily data por canal
      const map = {};
      for (const r of dy.data) {
        if (!map[r.dia]) map[r.dia] = { dia: r.dia };
        map[r.dia][r.canal] = r.total;
      }
      setDaily(Object.values(map).sort((a, b) => a.dia.localeCompare(b.dia)));
      setActive(ac.data);
    } catch {}
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  const kpis = overview
    ? [
        {
          icon: MessageSquare,
          label: "Mensajes totales",
          value: overview.mensajes.total.toLocaleString(),
          sub: `${overview.mensajes.semana} esta semana`,
          color: "#2B6BF3",
        },
        {
          icon: Users,
          label: "Sesiones únicas",
          value: overview.sesiones.unicas.toLocaleString(),
          sub: "Usuarios distintos",
          color: "#58A6FF",
        },
        {
          icon: FileText,
          label: "Contratos generados",
          value: overview.contratos.total.toLocaleString(),
          sub: `${overview.contratos.mes} este mes`,
          color: "#3FB950",
        },
        {
          icon: Database,
          label: "Documentos en memoria",
          value: overview.memoria.total_docs.toLocaleString(),
          sub: `${overview.memoria.por_fuente.length} fuentes`,
          color: "#D29922",
        },
      ]
    : [];

  const canalesData = overview?.por_canal.map((c) => ({
    name: CANAL_LABELS[c.canal] || c.canal,
    value: c.total,
    color: CANAL_COLORS[c.canal] || "#8B949E",
  })) || [];

  const memoriaData = overview?.memoria.por_fuente.map((f) => ({
    name: f.fuente.replace("_", " "),
    value: f.total,
  })) || [];

  const FUENTE_COLORS = ["#2B6BF3", "#58A6FF", "#3FB950"];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Activity size={20} className="text-snr-400" />
            Dashboard
          </h1>
          <p className="text-[#8B949E] text-sm mt-0.5">Métricas en tiempo real de agentes internos y externos</p>
        </div>
        <button onClick={load} className="btn-ghost flex items-center gap-2 text-xs">
          <TrendingUp size={14} />
          Actualizar
        </button>
      </div>

      {/* KPIs */}
      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="card p-5 h-24 animate-pulse bg-[#161B22]" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {kpis.map((k) => <KpiCard key={k.label} {...k} />)}
        </div>
      )}

      {/* Charts row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Mensajes por día */}
        <div className="lg:col-span-2 card p-5">
          <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Zap size={14} className="text-snr-400" />
            Mensajes por día (30 días)
          </h2>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={daily} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <defs>
                {Object.entries(CANAL_COLORS).map(([k, c]) => (
                  <linearGradient key={k} id={`grad-${k}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={c} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={c} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <XAxis
                dataKey="dia"
                tick={{ fill: "#484F58", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(d) => {
                  try { return format(new Date(d), "dd/MM"); } catch { return d; }
                }}
              />
              <YAxis tick={{ fill: "#484F58", fontSize: 10 }} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              {Object.entries(CANAL_COLORS).map(([canal, color]) => (
                <Area
                  key={canal}
                  type="monotone"
                  dataKey={canal}
                  stroke={color}
                  strokeWidth={2}
                  fill={`url(#grad-${canal})`}
                  dot={false}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Distribución por canal */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Globe size={14} className="text-snr-400" />
            Mensajes por canal
          </h2>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={canalesData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} dataKey="value" paddingAngle={3}>
                {canalesData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v, n) => [v, n]}
                contentStyle={{ background: "#161B22", border: "1px solid #21262D", borderRadius: 8 }}
                labelStyle={{ color: "#8B949E" }}
                itemStyle={{ color: "#E6EDF3" }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1.5 mt-2">
            {canalesData.map((c) => (
              <div key={c.name} className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full" style={{ background: c.color }} />
                  <span className="text-[#8B949E]">{c.name}</span>
                </span>
                <span className="text-white font-medium">{c.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Charts row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Memoria por fuente */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Database size={14} className="text-snr-400" />
            Memoria vectorial por fuente
          </h2>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={memoriaData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <XAxis dataKey="name" tick={{ fill: "#484F58", fontSize: 11 }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fill: "#484F58", fontSize: 10 }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ background: "#161B22", border: "1px solid #21262D", borderRadius: 8 }}
                itemStyle={{ color: "#E6EDF3" }}
                cursor={{ fill: "#1C2230" }}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {memoriaData.map((_, i) => (
                  <Cell key={i} fill={FUENTE_COLORS[i % FUENTE_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Sesiones activas */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Activity size={14} className="text-snr-400" />
            Sesiones activas (últimas 24h)
          </h2>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {active.length === 0 && (
              <p className="text-[#484F58] text-sm text-center py-6">Sin actividad reciente</p>
            )}
            {active.map((s, i) => (
              <div key={i} className="flex items-center justify-between bg-[#0D1117] border border-[#21262D] rounded-lg px-3 py-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ background: CANAL_COLORS[s.canal] || "#8B949E" }}
                  />
                  <span className="text-xs text-[#8B949E] truncate">{s.session_key.slice(0, 24)}</span>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-xs text-white font-medium">{s.mensajes} msgs</span>
                  <span className="badge text-[10px]" style={{ background: `${CANAL_COLORS[s.canal]}22`, color: CANAL_COLORS[s.canal] || "#8B949E" }}>
                    {CANAL_LABELS[s.canal] || s.canal}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
