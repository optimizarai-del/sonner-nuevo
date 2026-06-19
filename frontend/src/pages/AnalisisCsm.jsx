import { useEffect, useState } from "react";
import {
  ThumbsUp, ThumbsDown, AlertTriangle, RefreshCw, Download,
  MessageSquareText, Bot,
} from "lucide-react";
import { authFetch, hasRole } from "../utils/auth";

// ── Catálogos ─────────────────────────────────────────────────────────────────
const TAGS = ["tono", "dato_incorrecto", "incompleta", "no_entendio", "fuera_de_tema", "formato", "inventó_datos", "dio_precio"];
const STATUS_FILTERS = [
  { key: "pending", label: "Pendientes" },
  { key: "reviewed", label: "Revisadas" },
  { key: "", label: "Todas" },
];
const TIPOS = ["minorista", "mayorista"];
const TIPO_FILTERS = [{ key: "", label: "Todos" }, ...TIPOS.map((t) => ({ key: t, label: t }))];
const AGENTES = ["principal", "calendario", "salones"];
const AGENTE_FILTERS = [{ key: "", label: "Todos" }, ...AGENTES.map((a) => ({ key: a, label: a }))];

const RATING_LABEL = { good: "✅ correcta", mejorable: "⚠️ mejorable", bad: "❌ mal" };
const RATING_COLOR = { good: "#3FB950", mejorable: "#D29922", bad: "#F85149" };

// ── Helpers de fetch ──────────────────────────────────────────────────────────
async function getJSON(path) {
  const res = await authFetch(path);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
async function postJSON(path, body) {
  const res = await authFetch(path, { method: "POST", body: JSON.stringify(body) });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Stat card ─────────────────────────────────────────────────────────────────
function StatCard({ label, value, color }) {
  return (
    <div className="rounded-xl p-4" style={{ background: "#161B22", border: "1px solid #21262D" }}>
      <div className="text-[10px] uppercase tracking-wider" style={{ color: "#6E7681" }}>{label}</div>
      <div className="text-2xl font-semibold mt-1" style={{ color: color || "#fff" }}>{value}</div>
    </div>
  );
}

// ── Chip ──────────────────────────────────────────────────────────────────────
function Chip({ children, color = "#79C0FF", bg = "#0D1B38", border = "#1e3a6e" }) {
  return (
    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium"
      style={{ background: bg, color, border: `1px solid ${border}` }}>
      {children}
    </span>
  );
}

// ── Tarjeta de interacción ────────────────────────────────────────────────────
function CsmCard({ item, onChanged }) {
  const [corregida, setCorregida] = useState(item.respuesta_corregida || "");
  const [tags, setTags] = useState(Array.isArray(item.tags) ? item.tags : []);
  const [tipo, setTipo] = useState(item.tipo_cliente || "");
  const [nota, setNota] = useState(item.nota || "");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const toggleTag = (t) => setTags((c) => (c.includes(t) ? c.filter((x) => x !== t) : [...c, t]));

  const review = async (rating) => {
    setBusy(true); setErr("");
    try {
      await postJSON(`/api/csm/${item.id}/review`, {
        rating,
        respuesta_corregida: corregida.trim() || null,
        tags,
        tipo_cliente: tipo || null,
        nota: nota.trim() || null,
      });
      onChanged();
    } catch (e) { setErr(e.message || "Error"); }
    finally { setBusy(false); }
  };

  return (
    <div className="rounded-xl p-5" style={{ background: "#161B22", border: "1px solid #21262D" }}>
      {/* Meta */}
      <div className="flex items-center gap-2 mb-3 flex-wrap text-[10px]">
        <Chip color={item.status === "pending" ? "#D29922" : "#3FB950"}
          bg="#0D1117" border="#30363D">{item.status}</Chip>
        {item.agente && <Chip>🤖 {item.agente}</Chip>}
        {item.canal && <Chip>{item.canal}</Chip>}
        {item.tipo_cliente && <Chip>👥 {item.tipo_cliente}</Chip>}
        {item.rating && (
          <span className="font-semibold" style={{ color: RATING_COLOR[item.rating] }}>
            {RATING_LABEL[item.rating] || item.rating}
          </span>
        )}
        <span className="ml-auto" style={{ color: "#6E7681" }}>
          {item.created_at ? new Date(item.created_at).toLocaleString("es-AR") : ""}
        </span>
      </div>

      {/* Mensaje del cliente */}
      <div className="mb-3">
        <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "#6E7681" }}>
          Mensaje del cliente {item.cliente_nombre ? `· ${item.cliente_nombre}` : ""}
        </div>
        <div className="text-sm font-medium text-white whitespace-pre-wrap">{item.mensaje_cliente}</div>
      </div>

      {/* Respuesta del agente */}
      <div className="mb-4">
        <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "#6E7681" }}>Respuesta del agente</div>
        <div className="text-[13px] whitespace-pre-wrap" style={{ color: "#8B949E" }}>
          {item.respuesta_agente || <em>(sin respuesta)</em>}
        </div>
      </div>

      {/* Corrección */}
      <div className="mb-4">
        <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "#6E7681" }}>
          Respuesta corregida (opcional)
        </div>
        <textarea
          className="input w-full text-sm" style={{ minHeight: "70px" }}
          placeholder="Cómo debería haber respondido el agente…"
          value={corregida} onChange={(e) => setCorregida(e.target.value)}
        />
      </div>

      {/* Tipo de cliente */}
      <div className="mb-3">
        <div className="text-[10px] uppercase tracking-wider mb-1.5" style={{ color: "#6E7681" }}>Tipo de cliente</div>
        <div className="flex flex-wrap gap-2">
          {TIPOS.map((t) => (
            <button key={t} type="button" onClick={() => setTipo((c) => (c === t ? "" : t))}
              className="px-2.5 py-1 rounded-full text-[11px] font-medium capitalize transition-colors"
              style={tipo === t
                ? { background: "#2B6BF3", color: "#fff" }
                : { background: "#0D1117", color: "#8B949E", border: "1px solid #30363D" }}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Etiquetas */}
      <div className="mb-3">
        <div className="text-[10px] uppercase tracking-wider mb-1.5" style={{ color: "#6E7681" }}>Etiquetas del problema</div>
        <div className="flex flex-wrap gap-2">
          {TAGS.map((t) => (
            <button key={t} type="button" onClick={() => toggleTag(t)}
              className="px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors"
              style={tags.includes(t)
                ? { background: "#21262D", color: "#fff", border: "1px solid #6E7681" }
                : { background: "#0D1117", color: "#8B949E", border: "1px solid #30363D" }}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Nota */}
      <div className="mb-4">
        <input className="input w-full text-sm" placeholder="Nota interna (opcional)"
          value={nota} onChange={(e) => setNota(e.target.value)} />
      </div>

      {err && <div className="mb-3 text-[12px]" style={{ color: "#F85149" }}>{err}</div>}

      {/* Acciones de puntuación */}
      <div className="flex flex-wrap gap-2">
        <button disabled={busy} onClick={() => review("good")}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-colors disabled:opacity-40"
          style={{ background: "#0D1117", color: "#3FB950", border: "1px solid #2ea04326" }}>
          <ThumbsUp size={13} /> Correcta
        </button>
        <button disabled={busy} onClick={() => review("mejorable")}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-colors disabled:opacity-40"
          style={{ background: "#0D1117", color: "#D29922", border: "1px solid #d2992226" }}>
          <AlertTriangle size={13} /> Mejorable
        </button>
        <button disabled={busy} onClick={() => review("bad")}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-colors disabled:opacity-40"
          style={{ background: "#0D1117", color: "#F85149", border: "1px solid #f8514926" }}>
          <ThumbsDown size={13} /> Mal
        </button>
      </div>
    </div>
  );
}

// ── Página ────────────────────────────────────────────────────────────────────
export default function AnalisisCsm() {
  const isAdmin = hasRole("admin");
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [status, setStatus] = useState("pending");
  const [tipo, setTipo] = useState("");
  const [agente, setAgente] = useState("");
  const [loading, setLoading] = useState(false);

  const load = () => {
    setLoading(true);
    const qs = new URLSearchParams();
    if (status) qs.set("status", status);
    if (tipo) qs.set("tipo_cliente", tipo);
    if (agente) qs.set("agente", agente);
    Promise.all([
      getJSON(`/api/csm?${qs.toString()}`).then(setItems).catch(() => setItems([])),
      getJSON("/api/csm/stats").then(setStats).catch(() => {}),
    ]).finally(() => setLoading(false));
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [status, tipo, agente]);

  const exportar = async () => {
    try {
      const data = await getJSON("/api/csm/export");
      const blob = new Blob([JSON.stringify(data.dataset, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "sonner_csm_dataset.json"; a.click();
      URL.revokeObjectURL(url);
    } catch { /* noop */ }
  };

  const FilterRow = ({ label, filters, value, onChange }) => (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-[10px] uppercase tracking-wider mr-1" style={{ color: "#6E7681" }}>{label}</span>
      {filters.map((f) => (
        <button key={f.key} onClick={() => onChange(f.key)}
          className="px-3 py-1.5 rounded-full text-[12px] font-medium capitalize transition-colors"
          style={value === f.key
            ? { background: "#2B6BF3", color: "#fff" }
            : { background: "#161B22", color: "#8B949E", border: "1px solid #21262D" }}>
          {f.label}
        </button>
      ))}
    </div>
  );

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="px-6 py-4 flex items-center justify-between" style={{ borderBottom: "1px solid #21262D" }}>
        <div>
          <h1 className="font-semibold text-white flex items-center gap-2">
            <MessageSquareText size={18} style={{ color: "#2B6BF3" }} />
            Análisis de CSM
          </h1>
          <p className="text-xs mt-0.5" style={{ color: "#8B949E" }}>
            Revisá, puntuá y corregí las respuestas del agente para mejorarlo
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={load}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium"
            style={{ background: "#161B22", color: "#8B949E", border: "1px solid #21262D" }}>
            <RefreshCw size={13} /> Refrescar
          </button>
          {isAdmin && (
            <button onClick={exportar}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium"
              style={{ background: "#161B22", color: "#8B949E", border: "1px solid #21262D" }}>
              <Download size={13} /> Exportar
            </button>
          )}
        </div>
      </div>

      <div className="px-6 py-5 space-y-6 max-w-5xl w-full mx-auto">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Pendientes" value={stats.pendientes} color="#D29922" />
            <StatCard label="Tasa de aprobación" value={`${Math.round((stats.tasa_aprobacion || 0) * 100)}%`} color="#3FB950" />
            <StatCard label="Revisadas" value={stats.revisadas} color="#79C0FF" />
            <StatCard label="Total" value={stats.total} />
          </div>
        )}

        {/* Desglose por tipo de cliente */}
        {stats?.por_tipo?.length > 0 && (
          <div className="rounded-xl p-5" style={{ background: "#161B22", border: "1px solid #21262D" }}>
            <div className="text-[10px] uppercase tracking-wider mb-3" style={{ color: "#6E7681" }}>
              Aciertos a la primera por tipo de cliente
            </div>
            <div className="space-y-2">
              {stats.por_tipo.map((p) => (
                <div key={p.tipo_cliente} className="flex items-center gap-3 text-[13px]">
                  <span className="w-28 capitalize text-white font-medium">{p.tipo_cliente}</span>
                  <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: "#0D1117" }}>
                    <div className="h-full" style={{ width: `${Math.round(p.tasa * 100)}%`, background: "#3FB950" }} />
                  </div>
                  <span className="w-12 text-right tabular-nums font-semibold" style={{ color: "#3FB950" }}>
                    {Math.round(p.tasa * 100)}%
                  </span>
                  <span className="w-28 text-right text-[11px]" style={{ color: "#6E7681" }}>
                    ✅{p.good} ⚠️{p.mejorable} ❌{p.bad}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Top etiquetas problemáticas */}
        {stats?.top_tags_malos?.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] uppercase tracking-wider mr-1" style={{ color: "#6E7681" }}>Problemas frecuentes</span>
            {stats.top_tags_malos.map((t) => (
              <Chip key={t.tag} color="#F85149" bg="#0D1117" border="#f8514926">{t.tag} · {t.count}</Chip>
            ))}
          </div>
        )}

        {/* Filtros */}
        <div className="space-y-3">
          <FilterRow label="Estado" filters={STATUS_FILTERS} value={status} onChange={setStatus} />
          <FilterRow label="Cliente" filters={TIPO_FILTERS} value={tipo} onChange={setTipo} />
          <FilterRow label="Agente" filters={AGENTE_FILTERS} value={agente} onChange={setAgente} />
        </div>

        {/* Lista */}
        <div className="space-y-4">
          {loading && <div className="text-center py-12" style={{ color: "#6E7681" }}>Cargando…</div>}
          {!loading && items.map((item) => (
            <CsmCard key={item.id} item={item} onChanged={load} />
          ))}
          {!loading && !items.length && (
            <div className="rounded-xl p-12 text-center" style={{ background: "#161B22", border: "1px solid #21262D", color: "#6E7681" }}>
              <Bot size={28} className="mx-auto mb-3 opacity-50" />
              No hay interacciones en este estado.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
