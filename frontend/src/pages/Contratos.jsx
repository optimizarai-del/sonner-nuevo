import { useState, useEffect } from "react";
import { FileText, Download, ExternalLink, Plus, X, Check, AlertCircle, Loader2, Trash2, Send, User, Calendar, DollarSign, Wrench, FileSignature } from "lucide-react";
import { supabase } from "../utils/supabase";
import { format } from "date-fns";
import { es } from "date-fns/locale";

// Backend Python — genera Doc + PDF + guarda en Supabase
const CONTRATOS_API = import.meta.env.VITE_CONTRATOS_API
  || "https://backend-sonner.optimizar-ia.com";

const MESES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

// ── Valores vacíos del formulario ─────────────────────────────────────────────
const EMPTY = {
  nombre_prestatario:     "",
  DNI_prestatario:        "",
  domicilio_prestatario:  "",
  lugar_evento:           "",
  dia_evento:             "",
  dia_finevento:          "",
  hora_inicio:            "",
  hora_fin:               "",
  dias_para_pagar:        "30",
  valor_total_prestacion: "",
  equipamientos:          "",
  monto_total_pesos:      "",
  monto_total_reserva:    "",
  saldo_a_cancelar:       "",
  dia_firma:              "",
  mes_firma:              "",
  año_firma:              new Date().getFullYear().toString(),
};

// ── Sub-componentes ───────────────────────────────────────────────────────────
function Field({ label, children, required }) {
  return (
    <div>
      <label className="block text-xs font-medium mb-1.5" style={{ color: "#8B949E" }}>
        {label}{required && <span style={{ color: "#f85149" }}> *</span>}
      </label>
      {children}
    </div>
  );
}

function Inp(props) {
  return <input className="input w-full" {...props} />;
}

function Textarea(props) {
  return <textarea rows={4} className="input w-full resize-none" {...props} />;
}

function Section({ icon: Icon, title, children, color = "#2B6BF3" }) {
  return (
    <div className="rounded-xl p-5" style={{ background: "#0D1117", border: "1px solid #21262D" }}>
      <div className="flex items-center gap-2 mb-4">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center"
          style={{ background: `${color}22`, border: `1px solid ${color}44` }}>
          <Icon size={14} style={{ color }} />
        </div>
        <h3 className="text-sm font-semibold text-white">{title}</h3>
      </div>
      {children}
    </div>
  );
}

// ── Componente principal ──────────────────────────────────────────────────────
export default function Contratos() {
  const [form, setForm]       = useState(EMPTY);
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState(null);
  const [error, setError]     = useState("");
  const [historial, setHistorial] = useState([]);
  const [showForm, setShowForm]   = useState(false);
  const [loadingHist, setLoadingHist] = useState(true);

  async function loadHistorial() {
    setLoadingHist(true);
    const { data } = await supabase
      .from("contratos")
      .select("id, nombre_prestatario, lugar_evento, dia_evento, doc_url, pdf_url, created_at")
      .order("created_at", { ascending: false })
      .limit(50);
    setHistorial(data ?? []);
    setLoadingHist(false);
  }

  useEffect(() => { loadHistorial(); }, []);

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    const payload = {
      ...form,
      valor_total_prestacion: parseInt(form.valor_total_prestacion) || 0,
      monto_total_pesos:      parseInt(form.monto_total_pesos)      || 0,
      monto_total_reserva:    parseInt(form.monto_total_reserva)    || 0,
      saldo_a_cancelar:       parseInt(form.saldo_a_cancelar)       || 0,
    };

    try {
      const res = await fetch(`${CONTRATOS_API}/api/contratos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(`HTTP ${res.status}: ${errBody.slice(0, 200)}`);
      }
      const data = await res.json();
      setResult({ doc_url: data?.doc_url ?? null, pdf_url: data?.pdf_url ?? null });
      setForm(EMPTY);
      setShowForm(false);
      loadHistorial();
    } catch (err) {
      setError(err.message || "Error generando contrato");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-white">Contratos</h1>
          <p className="text-sm mt-0.5" style={{ color: "#484F58" }}>
            Generación automática de Google Docs + PDF
          </p>
        </div>
        <button
          onClick={() => { setShowForm(true); setResult(null); setError(""); }}
          className="flex items-center gap-2 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors"
          style={{ background: "#2B6BF3" }}
        >
          <Plus size={16} />
          Nuevo contrato
        </button>
      </div>

      {/* Resultado exitoso */}
      {result && (
        <div className="rounded-xl p-4 mb-6 flex items-start gap-3"
          style={{ background: "#0f2c1a", border: "1px solid #2ea043" }}>
          <Check size={18} className="shrink-0 mt-0.5" style={{ color: "#3fb950" }} />
          <div>
            <p className="font-medium text-sm" style={{ color: "#3fb950" }}>Contrato generado exitosamente</p>
            <div className="flex flex-wrap gap-4 mt-2">
              {result.doc_url && (
                <a href={result.doc_url} target="_blank" rel="noreferrer"
                  className="flex items-center gap-1.5 text-sm underline" style={{ color: "#79C0FF" }}>
                  <ExternalLink size={13} />
                  Abrir Google Docs
                </a>
              )}
              {result.pdf_url && (
                <a href={result.pdf_url} target="_blank" rel="noreferrer"
                  className="flex items-center gap-1.5 text-sm underline" style={{ color: "#79C0FF" }}>
                  <Download size={13} />
                  Descargar PDF
                </a>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Formulario */}
      {showForm && (
        <div className="rounded-2xl p-6 mb-6"
          style={{ background: "#161B22", border: "1px solid #21262D" }}>
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <FileSignature size={18} style={{ color: "#2B6BF3" }} />
              Nuevo contrato de prestación
            </h2>
            <button onClick={() => setShowForm(false)} style={{ color: "#484F58" }} className="hover:text-white transition-colors">
              <X size={18} />
            </button>
          </div>

          <form onSubmit={submit} className="space-y-4">

            {/* SECCIÓN: Prestatario */}
            <Section icon={User} title="Datos del prestatario" color="#2B6BF3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Field label="Nombre completo del prestatario" required>
                  <Inp value={form.nombre_prestatario} onChange={set("nombre_prestatario")} required placeholder="Juan Pérez" />
                </Field>
                <Field label="DNI del prestatario" required>
                  <Inp value={form.DNI_prestatario} onChange={set("DNI_prestatario")} required placeholder="42798702" />
                </Field>
                <Field label="Domicilio del prestatario" required>
                  <Inp value={form.domicilio_prestatario} onChange={set("domicilio_prestatario")} required placeholder="Av. Corrientes 1234" />
                </Field>
              </div>
            </Section>

            {/* SECCIÓN: Evento */}
            <Section icon={Calendar} title="Datos del evento" color="#3FB950">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Field label="Lugar del evento" required>
                  <Inp value={form.lugar_evento} onChange={set("lugar_evento")} required placeholder="Salón Sur" />
                </Field>
                <Field label="Días para pagar" required>
                  <Inp type="number" value={form.dias_para_pagar} onChange={set("dias_para_pagar")} required placeholder="30" min="1" />
                </Field>
                <Field label="Día del evento" required>
                  <Inp type="date" value={form.dia_evento} onChange={set("dia_evento")} required />
                </Field>
                <Field label="Día fin del evento">
                  <Inp type="date" value={form.dia_finevento} onChange={set("dia_finevento")} />
                </Field>
                <Field label="Hora de inicio" required>
                  <Inp type="time" value={form.hora_inicio} onChange={set("hora_inicio")} required />
                </Field>
                <Field label="Hora de fin" required>
                  <Inp type="time" value={form.hora_fin} onChange={set("hora_fin")} required />
                </Field>
              </div>
            </Section>

            {/* SECCIÓN: Valor de la prestación */}
            <Section icon={DollarSign} title="Valor de la prestación" color="#D29922">
              <Field label="Valor total de la prestación" required>
                <Inp value={form.valor_total_prestacion} onChange={set("valor_total_prestacion")} required placeholder="500000" type="number" />
              </Field>
            </Section>

            {/* SECCIÓN: Equipamientos */}
            <Section icon={Wrench} title="Equipamientos y montos" color="#A371F7">
              <div className="space-y-4">
                <Field label="Descripción del equipamiento" required>
                  <Textarea
                    value={form.equipamientos}
                    onChange={set("equipamientos")}
                    required
                    placeholder="2 parlantes JBL, consola Yamaha MG10, 4 luces LED PAR, máquina de humo, cabina DJ..."
                  />
                </Field>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Field label="Monto total en pesos ($)" required>
                    <Inp type="number" value={form.monto_total_pesos} onChange={set("monto_total_pesos")} required placeholder="500000" />
                  </Field>
                  <Field label="Monto de reserva ($)" required>
                    <Inp type="number" value={form.monto_total_reserva} onChange={set("monto_total_reserva")} required placeholder="50000" />
                  </Field>
                  <Field label="Saldo a cancelar ($)" required>
                    <Inp type="number" value={form.saldo_a_cancelar} onChange={set("saldo_a_cancelar")} required placeholder="450000" />
                  </Field>
                </div>
              </div>
            </Section>

            {/* SECCIÓN: Fecha de firma */}
            <Section icon={FileSignature} title="Fecha de firma" color="#F85149">
              <div className="grid grid-cols-3 gap-4">
                <Field label="Día" required>
                  <Inp type="number" value={form.dia_firma} onChange={set("dia_firma")} required min="1" max="31" placeholder="15" />
                </Field>
                <Field label="Mes" required>
                  <select
                    value={form.mes_firma}
                    onChange={set("mes_firma")}
                    required
                    className="input w-full"
                  >
                    <option value="">Seleccioná mes...</option>
                    {MESES.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                </Field>
                <Field label="Año" required>
                  <Inp type="number" value={form.año_firma} onChange={set("año_firma")} required placeholder="2026" />
                </Field>
              </div>
            </Section>

            {error && (
              <div className="flex items-center gap-2 text-sm rounded-lg p-3"
                style={{ color: "#f85149", background: "#2c0e0e", border: "1px solid #f8514944" }}>
                <AlertCircle size={15} />
                {error}
              </div>
            )}

            {/* Acciones */}
            <div className="flex gap-3 justify-end pt-2">
              <button
                type="button"
                onClick={() => setForm(EMPTY)}
                className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg transition-colors"
                style={{ color: "#8B949E", background: "#21262D", border: "1px solid #30363D" }}
              >
                <Trash2 size={14} />
                Limpiar
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex items-center gap-2 text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-colors disabled:opacity-50"
                style={{ background: "#2B6BF3" }}
              >
                {loading
                  ? <><Loader2 size={14} className="animate-spin" /> Generando...</>
                  : <><Send size={14} /> Enviar contrato</>}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Historial */}
      <div className="rounded-2xl overflow-hidden"
        style={{ background: "#161B22", border: "1px solid #21262D" }}>
        <div className="px-5 py-4" style={{ borderBottom: "1px solid #21262D" }}>
          <h2 className="font-semibold text-white text-sm">Historial</h2>
        </div>
        {loadingHist ? (
          <div className="px-5 py-10 text-center text-sm" style={{ color: "#484F58" }}>Cargando...</div>
        ) : historial.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm" style={{ color: "#484F58" }}>
            No hay contratos generados aún
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: "1px solid #21262D" }}>
                <th className="px-5 py-3 text-left text-xs font-medium" style={{ color: "#484F58" }}>Prestatario</th>
                <th className="px-5 py-3 text-left text-xs font-medium" style={{ color: "#484F58" }}>Lugar</th>
                <th className="px-5 py-3 text-left text-xs font-medium" style={{ color: "#484F58" }}>Fecha evento</th>
                <th className="px-5 py-3 text-left text-xs font-medium" style={{ color: "#484F58" }}>Generado</th>
                <th className="px-5 py-3 text-right text-xs font-medium" style={{ color: "#484F58" }}>Archivos</th>
              </tr>
            </thead>
            <tbody>
              {historial.map((c, i) => (
                <tr key={c.id} style={{ borderBottom: i < historial.length - 1 ? "1px solid #21262D22" : "none" }}>
                  <td className="px-5 py-3" style={{ color: "#C9D1D9" }}>{c.nombre_prestatario}</td>
                  <td className="px-5 py-3" style={{ color: "#8B949E" }}>{c.lugar_evento}</td>
                  <td className="px-5 py-3" style={{ color: "#8B949E" }}>{c.dia_evento}</td>
                  <td className="px-5 py-3 text-xs" style={{ color: "#484F58" }}>
                    {format(new Date(c.created_at), "dd MMM yyyy HH:mm", { locale: es })}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center justify-end gap-3">
                      {c.doc_url && (
                        <a href={c.doc_url} target="_blank" rel="noreferrer" title="Google Docs"
                          style={{ color: "#79C0FF" }} className="hover:opacity-80 transition-opacity">
                          <ExternalLink size={14} />
                        </a>
                      )}
                      {c.pdf_url && (
                        <a href={c.pdf_url} target="_blank" rel="noreferrer" title="PDF"
                          style={{ color: "#79C0FF" }} className="hover:opacity-80 transition-opacity">
                          <Download size={14} />
                        </a>
                      )}
                      {!c.doc_url && !c.pdf_url && <span style={{ color: "#484F58" }}>—</span>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
