import { useState, useEffect } from "react";
import { FileText, Download, ExternalLink, Plus, X, Check, AlertCircle, Loader2 } from "lucide-react";
import { supabase } from "../utils/supabase";
import { format } from "date-fns";
import { es } from "date-fns/locale";

// Backend Python — genera Doc + PDF + guarda en Supabase
const CONTRATOS_API = import.meta.env.VITE_CONTRATOS_API
  || "https://contratos-sonner.optimizar-ia.com";

// ── Valores vacíos del formulario ─────────────────────────────────────────────
const EMPTY = {
  nombre_prestatario:     "",
  DNI_prestatario:        "",
  domicilio_prestatario:  "",
  lugar_evento:           "",
  dia_evento:             "",
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
function Field({ label, children }) {
  return (
    <div>
      <label className="block text-xs font-medium mb-1.5" style={{ color: "#8B949E" }}>{label}</label>
      {children}
    </div>
  );
}

function Inp(props) {
  return <input className="input w-full" {...props} />;
}

function Textarea(props) {
  return <textarea rows={3} className="input w-full resize-none" {...props} />;
}

// ── Componente principal ──────────────────────────────────────────────────────
export default function Contratos() {
  const [form, setForm]       = useState(EMPTY);
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState(null);   // { doc_url, pdf_url }
  const [error, setError]     = useState("");
  const [historial, setHistorial] = useState([]);
  const [showForm, setShowForm]   = useState(false);
  const [loadingHist, setLoadingHist] = useState(true);

  // ── Cargar historial desde Supabase ─────────────────────────────────────────
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

  // ── Enviar a n8n ─────────────────────────────────────────────────────────────
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
      // 1. Backend Python: copia template, rellena, exporta PDF, guarda en Supabase
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

      const doc_url = data?.doc_url ?? null;
      const pdf_url = data?.pdf_url ?? null;

      // 2. Guardar en Supabase para historial
      // El backend ya guardó el registro en Supabase, no duplicamos.
      setResult({ doc_url, pdf_url });
      setForm(EMPTY);
      setShowForm(false);
      loadHistorial();

    } catch (err) {
      setError(err.name === "AbortError"
        ? "Tiempo de espera agotado. Intentá de nuevo."
        : err.message || "Error generando contrato");
    } finally {
      setLoading(false);
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div className="p-6 max-w-4xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-white">Contratos</h1>
          <p className="text-sm mt-0.5" style={{ color: "#484F58" }}>
            Generación automática — Google Docs + PDF via n8n
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
        <div className="rounded-xl p-4 mb-6 flex items-start gap-3" style={{ background: "#0f2c1a", border: "1px solid #2ea043" }}>
          <Check size={18} className="shrink-0 mt-0.5" style={{ color: "#3fb950" }} />
          <div className="space-y-1">
            <p className="font-medium text-sm" style={{ color: "#3fb950" }}>Contrato generado exitosamente</p>
            <div className="flex flex-wrap gap-4 mt-2">
              {result.doc_url && (
                <a href={result.doc_url} target="_blank" rel="noreferrer"
                  className="flex items-center gap-1.5 text-sm underline"
                  style={{ color: "#79C0FF" }}>
                  <ExternalLink size={13} />
                  Abrir Google Docs
                </a>
              )}
              {result.pdf_url && (
                <a href={result.pdf_url} target="_blank" rel="noreferrer"
                  className="flex items-center gap-1.5 text-sm underline"
                  style={{ color: "#79C0FF" }}>
                  <Download size={13} />
                  Descargar PDF
                </a>
              )}
              {!result.doc_url && !result.pdf_url && (
                <span className="text-sm" style={{ color: "#8B949E" }}>
                  Contrato guardado. Revisá Google Drive.
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Formulario */}
      {showForm && (
        <div className="rounded-2xl p-6 mb-6" style={{ background: "#161B22", border: "1px solid #21262D" }}>
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-semibold text-white">Datos del contrato</h2>
            <button onClick={() => setShowForm(false)} style={{ color: "#484F58" }} className="hover:text-white transition-colors">
              <X size={18} />
            </button>
          </div>

          <form onSubmit={submit} className="space-y-5">

            {/* Datos del prestatario */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Field label="Nombre del prestatario">
                <Inp value={form.nombre_prestatario} onChange={set("nombre_prestatario")} required placeholder="Juan Pérez" />
              </Field>
              <Field label="DNI">
                <Inp value={form.DNI_prestatario} onChange={set("DNI_prestatario")} required placeholder="42798702" />
              </Field>
              <Field label="Domicilio">
                <Inp value={form.domicilio_prestatario} onChange={set("domicilio_prestatario")} required placeholder="Av. Corrientes 1234" />
              </Field>
              <Field label="Lugar del evento">
                <Inp value={form.lugar_evento} onChange={set("lugar_evento")} required placeholder="Salón Sur" />
              </Field>
              <Field label="Fecha del evento">
                <Inp type="date" value={form.dia_evento} onChange={set("dia_evento")} required />
              </Field>
              <Field label="Días para pagar">
                <Inp type="number" value={form.dias_para_pagar} onChange={set("dias_para_pagar")} required />
              </Field>
              <Field label="Hora inicio">
                <Inp type="time" value={form.hora_inicio} onChange={set("hora_inicio")} required />
              </Field>
              <Field label="Hora fin">
                <Inp type="time" value={form.hora_fin} onChange={set("hora_fin")} required />
              </Field>
            </div>

            {/* Montos */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Field label="Valor total ($)">
                <Inp type="number" value={form.valor_total_prestacion} onChange={set("valor_total_prestacion")} required placeholder="5000000" />
              </Field>
              <Field label="Total en pesos ($)">
                <Inp type="number" value={form.monto_total_pesos} onChange={set("monto_total_pesos")} required placeholder="300000" />
              </Field>
              <Field label="Reserva ($)">
                <Inp type="number" value={form.monto_total_reserva} onChange={set("monto_total_reserva")} required placeholder="5000" />
              </Field>
              <Field label="Saldo a cancelar ($)">
                <Inp type="number" value={form.saldo_a_cancelar} onChange={set("saldo_a_cancelar")} required placeholder="295000" />
              </Field>
            </div>

            {/* Fecha de firma */}
            <div className="grid grid-cols-3 gap-4">
              <Field label="Día de firma">
                <Inp type="number" value={form.dia_firma} onChange={set("dia_firma")} required placeholder="15" min="1" max="31" />
              </Field>
              <Field label="Mes de firma">
                <Inp value={form.mes_firma} onChange={set("mes_firma")} required placeholder="julio" />
              </Field>
              <Field label="Año de firma">
                <Inp type="number" value={form.año_firma} onChange={set("año_firma")} required placeholder="2026" />
              </Field>
            </div>

            {/* Equipamientos */}
            <Field label="Equipamientos">
              <Textarea value={form.equipamientos} onChange={set("equipamientos")} required placeholder="Sonido, luces, DJ..." />
            </Field>

            {error && (
              <div className="flex items-center gap-2 text-sm" style={{ color: "#f85149" }}>
                <AlertCircle size={15} />
                {error}
              </div>
            )}

            <div className="flex gap-3 justify-end">
              <button type="button" onClick={() => setShowForm(false)}
                className="px-4 py-2 text-sm transition-colors hover:text-white"
                style={{ color: "#8B949E" }}>
                Cancelar
              </button>
              <button type="submit" disabled={loading}
                className="flex items-center gap-2 text-white text-sm font-medium px-5 py-2 rounded-lg transition-colors disabled:opacity-50"
                style={{ background: "#2B6BF3" }}>
                {loading ? (
                  <><Loader2 size={14} className="animate-spin" /> Generando...</>
                ) : (
                  <><FileText size={14} /> Generar contrato</>
                )}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Historial */}
      <div className="rounded-2xl overflow-hidden" style={{ background: "#161B22", border: "1px solid #21262D" }}>
        <div className="px-5 py-4" style={{ borderBottom: "1px solid #21262D" }}>
          <h2 className="font-semibold text-white text-sm">Historial</h2>
        </div>
        {loadingHist ? (
          <div className="px-5 py-10 text-center text-sm" style={{ color: "#484F58" }}>
            Cargando...
          </div>
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
                        <a href={c.doc_url} target="_blank" rel="noreferrer"
                          title="Google Docs"
                          style={{ color: "#79C0FF" }} className="hover:opacity-80 transition-opacity">
                          <ExternalLink size={14} />
                        </a>
                      )}
                      {c.pdf_url && (
                        <a href={c.pdf_url} target="_blank" rel="noreferrer"
                          title="PDF"
                          style={{ color: "#79C0FF" }} className="hover:opacity-80 transition-opacity">
                          <Download size={14} />
                        </a>
                      )}
                      {!c.doc_url && !c.pdf_url && (
                        <span style={{ color: "#484F58" }}>—</span>
                      )}
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
