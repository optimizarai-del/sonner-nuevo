import { useState, useEffect } from "react";
import {
  Settings, Building2, Plug, Activity, Save, Check, AlertCircle,
  Database, Globe, FileText, Loader2, RefreshCw,
} from "lucide-react";
import { supabase } from "../utils/supabase";

const N8N_BASE       = import.meta.env.VITE_N8N_BASE       || "https://n8n.optimizar-ia.com";
const CONTRATOS_API  = import.meta.env.VITE_CONTRATOS_API  || "https://backend-sonner.optimizar-ia.com";
const SUPABASE_URL   = import.meta.env.VITE_SUPABASE_URL   || "https://wndfjicwzmsuxxcsnccl.supabase.co";

// ── Sub-componentes ───────────────────────────────────────────────────────────
function Section({ icon: Icon, title, subtitle, children, color = "#2B6BF3" }) {
  return (
    <div className="rounded-2xl p-5 mb-5"
      style={{ background: "#161B22", border: "1px solid #21262D" }}>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-lg flex items-center justify-center"
          style={{ background: `${color}22`, border: `1px solid ${color}44` }}>
          <Icon size={18} style={{ color }} />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-white">{title}</h2>
          {subtitle && <p className="text-xs mt-0.5" style={{ color: "#8B949E" }}>{subtitle}</p>}
        </div>
      </div>
      {children}
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-xs font-medium mb-1.5" style={{ color: "#8B949E" }}>{label}</label>
      {children}
    </div>
  );
}

function ServiceRow({ label, url, status }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 rounded-lg"
      style={{ background: "#0D1117", border: "1px solid #21262D" }}>
      <div className="w-2 h-2 rounded-full shrink-0"
        style={{ background: status === "ok" ? "#3FB950" : status === "error" ? "#F85149" : "#8B949E" }} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white">{label}</p>
        <p className="text-xs font-mono truncate" style={{ color: "#8B949E" }}>{url}</p>
      </div>
      <span className="text-xs font-bold px-2 py-1 rounded" style={{
        background: status === "ok" ? "#3FB95022" : status === "error" ? "#F8514922" : "#21262D",
        color:      status === "ok" ? "#3FB950"   : status === "error" ? "#F85149"   : "#8B949E",
      }}>
        {status === "ok" ? "OK" : status === "error" ? "ERROR" : status === "loading" ? "..." : "—"}
      </span>
    </div>
  );
}

// ── Componente principal ──────────────────────────────────────────────────────
export default function Configuracion() {
  // Empresa
  const [empresa, setEmpresa] = useState({
    razon_social: "", representante: "", dni: "",
    domicilio: "", ciudad: "", email_contacto: "", telefono_contacto: "",
  });
  const [savingEmpresa, setSavingEmpresa] = useState(false);
  const [savedEmpresa, setSavedEmpresa]   = useState(false);

  // Health checks
  const [health, setHealth] = useState({
    backend: "loading", supabase: "loading", n8n_chat: "loading",
  });

  async function loadEmpresa() {
    const { data } = await supabase
      .from("empresa_config").select("*").eq("id", 1).single();
    if (data) setEmpresa({
      razon_social: data.razon_social ?? "",
      representante: data.representante ?? "",
      dni: data.dni ?? "",
      domicilio: data.domicilio ?? "",
      ciudad: data.ciudad ?? "",
      email_contacto: data.email_contacto ?? "",
      telefono_contacto: data.telefono_contacto ?? "",
    });
  }

  async function saveEmpresa() {
    setSavingEmpresa(true);
    setSavedEmpresa(false);
    const { error } = await supabase
      .from("empresa_config")
      .update({ ...empresa, updated_at: new Date().toISOString() })
      .eq("id", 1);
    if (!error) setSavedEmpresa(true);
    setSavingEmpresa(false);
    setTimeout(() => setSavedEmpresa(false), 3000);
  }

  async function checkHealth() {
    setHealth({ backend: "loading", supabase: "loading", n8n_chat: "loading" });

    // Backend
    fetch(`${CONTRATOS_API}/api/contratos/health`, { mode: "cors" })
      .then((r) => setHealth((h) => ({ ...h, backend: r.ok ? "ok" : "error" })))
      .catch(() => setHealth((h) => ({ ...h, backend: "error" })));

    // Supabase
    supabase.from("automatizacion_config").select("id").eq("id", 1).limit(1)
      .then(({ error }) => setHealth((h) => ({ ...h, supabase: error ? "error" : "ok" })));

    // n8n chat (POST simple)
    fetch(`${N8N_BASE}/webhook/sonner-pagina`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sessionId: "healthcheck", message: "ping" }),
    })
      .then((r) => setHealth((h) => ({ ...h, n8n_chat: r.ok ? "ok" : "error" })))
      .catch(() => setHealth((h) => ({ ...h, n8n_chat: "error" })));
  }

  useEffect(() => { loadEmpresa(); checkHealth(); }, []);

  function setField(field) {
    return (e) => setEmpresa((s) => ({ ...s, [field]: e.target.value }));
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">

      {/* Header */}
      <div className="mb-6 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: "#2B6BF322", border: "1px solid #2B6BF344" }}>
          <Settings size={18} style={{ color: "#2B6BF3" }} />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">Configuración</h1>
          <p className="text-sm mt-0.5" style={{ color: "#8B949E" }}>Datos del estudio · servicios · estado del sistema</p>
        </div>
      </div>

      {/* ── Datos de la empresa ────────────────────────────────────────────── */}
      <Section
        icon={Building2}
        title="Datos del estudio"
        subtitle="Información del prestador. Se usa en los contratos generados."
        color="#2B6BF3"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Razón social">
            <input className="input w-full" value={empresa.razon_social} onChange={setField("razon_social")} placeholder="SONNER Sonido e Iluminación" />
          </Field>
          <Field label="Representante">
            <input className="input w-full" value={empresa.representante} onChange={setField("representante")} placeholder="Luis Gabriel Ordoñez" />
          </Field>
          <Field label="DNI">
            <input className="input w-full" value={empresa.dni} onChange={setField("dni")} placeholder="33.835.434" />
          </Field>
          <Field label="Domicilio">
            <input className="input w-full" value={empresa.domicilio} onChange={setField("domicilio")} placeholder="Dr. José Luro N° 2.130" />
          </Field>
          <Field label="Ciudad">
            <input className="input w-full" value={empresa.ciudad} onChange={setField("ciudad")} placeholder="Santa Rosa, La Pampa" />
          </Field>
          <Field label="Email de contacto">
            <input className="input w-full" type="email" value={empresa.email_contacto} onChange={setField("email_contacto")} placeholder="contacto@sonner.com.ar" />
          </Field>
          <Field label="Teléfono de contacto">
            <input className="input w-full" value={empresa.telefono_contacto} onChange={setField("telefono_contacto")} placeholder="+54 9 2954..." />
          </Field>
        </div>
        <div className="flex items-center justify-end gap-3 mt-4">
          {savedEmpresa && (
            <span className="text-xs flex items-center gap-1.5" style={{ color: "#3FB950" }}>
              <Check size={13} /> Cambios guardados
            </span>
          )}
          <button
            onClick={saveEmpresa}
            disabled={savingEmpresa}
            className="flex items-center gap-2 text-white text-sm font-medium px-5 py-2 rounded-lg transition-colors disabled:opacity-50"
            style={{ background: "#2B6BF3" }}
          >
            {savingEmpresa
              ? <><Loader2 size={14} className="animate-spin" /> Guardando...</>
              : <><Save size={14} /> Guardar</>}
          </button>
        </div>
      </Section>

      {/* ── Servicios conectados ───────────────────────────────────────────── */}
      <Section
        icon={Plug}
        title="Servicios conectados"
        subtitle="URLs de la plataforma"
        color="#A371F7"
      >
        <div className="space-y-2">
          <ServiceRow label="Backend API"      url={CONTRATOS_API}                              status={health.backend} />
          <ServiceRow label="Supabase"          url={SUPABASE_URL}                               status={health.supabase} />
          <ServiceRow label="n8n — chat web"   url={`${N8N_BASE}/webhook/sonner-pagina`}        status={health.n8n_chat} />
          <ServiceRow label="Google Drive"      url="Plantilla + carpeta de contratos"          status="ok" />
        </div>
      </Section>

      {/* ── Estado del sistema ─────────────────────────────────────────────── */}
      <Section
        icon={Activity}
        title="Estado del sistema"
        subtitle="Verificación de conectividad"
        color="#3FB950"
      >
        <div className="flex items-center gap-3 mb-4 flex-wrap">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
            style={{ background: "#0D1117", border: "1px solid #21262D" }}>
            <Database size={13} style={{ color: "#79C0FF" }} />
            <span className="text-xs" style={{ color: "#8B949E" }}>
              Supabase: <span style={{ color: health.supabase === "ok" ? "#3FB950" : "#F85149" }}>
                {health.supabase === "loading" ? "..." : health.supabase === "ok" ? "Conectado" : "Sin conexión"}
              </span>
            </span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
            style={{ background: "#0D1117", border: "1px solid #21262D" }}>
            <Globe size={13} style={{ color: "#3FB950" }} />
            <span className="text-xs" style={{ color: "#8B949E" }}>
              Backend: <span style={{ color: health.backend === "ok" ? "#3FB950" : "#F85149" }}>
                {health.backend === "loading" ? "..." : health.backend === "ok" ? "Activo" : "Caído"}
              </span>
            </span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
            style={{ background: "#0D1117", border: "1px solid #21262D" }}>
            <FileText size={13} style={{ color: "#D29922" }} />
            <span className="text-xs" style={{ color: "#8B949E" }}>
              n8n chat: <span style={{ color: health.n8n_chat === "ok" ? "#3FB950" : "#F85149" }}>
                {health.n8n_chat === "loading" ? "..." : health.n8n_chat === "ok" ? "Respondiendo" : "Sin respuesta"}
              </span>
            </span>
          </div>
        </div>

        <button
          onClick={checkHealth}
          className="flex items-center gap-2 text-xs font-medium px-4 py-2 rounded-lg transition-colors"
          style={{ background: "#21262D", color: "#8B949E", border: "1px solid #30363D" }}
        >
          <RefreshCw size={12} />
          Reverificar
        </button>
      </Section>

      <p className="text-center text-xs mt-6" style={{ color: "#484F58" }}>
        Sonner — Panel interno · v1.0
      </p>
    </div>
  );
}
