import { useState, useEffect } from "react";
import { FileText, Download, Plus, X, Check, AlertCircle } from "lucide-react";
import api from "../utils/api";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const EMPTY = {
  nombre_prestatario: "",
  DNI_prestatario: "",
  domicilio_prestatario: "",
  lugar_evento: "",
  dia_evento: "",
  hora_inicio: "",
  hora_fin: "",
  dias_para_pagar: "30",
  valor_total_prestacion: "",
  equipamientos: "",
  monto_total_pesos: "",
  monto_total_reserva: "",
  saldo_a_cancelar: "",
  dia_firma: "",
  mes_firma: "",
  año_firma: new Date().getFullYear().toString(),
};

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-xs font-medium mb-1.5" style={{ color: "#8B949E" }}>{label}</label>
      {children}
    </div>
  );
}

function Input({ ...props }) {
  return (
    <input
      className="input w-full"
      {...props}
    />
  );
}

function Textarea({ ...props }) {
  return (
    <textarea
      rows={3}
      className="input w-full resize-none"
      {...props}
    />
  );
}

export default function Contratos() {
  const [form, setForm] = useState(EMPTY);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [historial, setHistorial] = useState([]);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    api.get("/contratos").then(({ data }) => setHistorial(data)).catch(() => {});
  }, [result]);

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    const montos = {
      valor_total_prestacion: parseInt(form.valor_total_prestacion) || 0,
      monto_total_pesos:      parseInt(form.monto_total_pesos)      || 0,
      monto_total_reserva:    parseInt(form.monto_total_reserva)    || 0,
      saldo_a_cancelar:       parseInt(form.saldo_a_cancelar)       || 0,
    };

    // Validar que ningún monto sea negativo antes de enviar
    if (Object.values(montos).some((m) => m < 0)) {
      setError("Los montos no pueden ser negativos.");
      setLoading(false);
      return;
    }

    const payload = { ...form, ...montos };

    try {
      // api (axios) ya agrega el header Authorization: Bearer <token>
      const { data } = await api.post("/contratos", payload);
      setResult(data);
      setForm(EMPTY);
      setShowForm(false);
    } catch (err) {
      // Detalle solo en consola; mensaje genérico al usuario
      console.error("Error generando contrato:", err.response?.data?.detail || err.message);
      setError("No se pudo generar el contrato. Intentá de nuevo.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-white">Contratos</h1>
          <p className="text-sm mt-0.5" style={{ color: "#484F58" }}>Generación automática de PDF desde template</p>
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

      {result && (
        <div className="rounded-xl p-4 mb-6 flex items-start gap-3" style={{ background: "#0f2c1a", border: "1px solid #2ea043" }}>
          <Check size={18} className="shrink-0 mt-0.5" style={{ color: "#3fb950" }} />
          <div>
            <p className="font-medium text-sm" style={{ color: "#3fb950" }}>Contrato generado exitosamente</p>
            <a
              href={result.pdf_url}
              target="_blank"
              rel="noreferrer"
              className="text-sm underline mt-1 inline-block"
              style={{ color: "#79C0FF" }}
            >
              Descargar PDF
            </a>
          </div>
        </div>
      )}

      {showForm && (
        <div className="rounded-2xl p-6 mb-6" style={{ background: "#161B22", border: "1px solid #21262D" }}>
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-semibold text-white">Datos del contrato</h2>
            <button onClick={() => setShowForm(false)} style={{ color: "#484F58" }} className="hover:text-white transition-colors">
              <X size={18} />
            </button>
          </div>

          <form onSubmit={submit} className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Field label="Nombre del prestatario">
                <Input value={form.nombre_prestatario} onChange={set("nombre_prestatario")} required placeholder="Juan Pérez" />
              </Field>
              <Field label="DNI">
                <Input value={form.DNI_prestatario} onChange={set("DNI_prestatario")} required placeholder="42798702" />
              </Field>
              <Field label="Domicilio">
                <Input value={form.domicilio_prestatario} onChange={set("domicilio_prestatario")} required placeholder="Av. Corrientes 1234" />
              </Field>
              <Field label="Lugar del evento">
                <Input value={form.lugar_evento} onChange={set("lugar_evento")} required placeholder="Salón Sur" />
              </Field>
              <Field label="Fecha del evento">
                <Input type="date" value={form.dia_evento} onChange={set("dia_evento")} required />
              </Field>
              <Field label="Días para pagar">
                <Input type="number" value={form.dias_para_pagar} onChange={set("dias_para_pagar")} required />
              </Field>
              <Field label="Hora inicio">
                <Input type="time" value={form.hora_inicio} onChange={set("hora_inicio")} required />
              </Field>
              <Field label="Hora fin">
                <Input type="time" value={form.hora_fin} onChange={set("hora_fin")} required />
              </Field>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Field label="Valor total ($)">
                <Input type="number" value={form.valor_total_prestacion} onChange={set("valor_total_prestacion")} required placeholder="5000000" />
              </Field>
              <Field label="Total en pesos ($)">
                <Input type="number" value={form.monto_total_pesos} onChange={set("monto_total_pesos")} required placeholder="300000" />
              </Field>
              <Field label="Reserva ($)">
                <Input type="number" value={form.monto_total_reserva} onChange={set("monto_total_reserva")} required placeholder="5000" />
              </Field>
              <Field label="Saldo a cancelar ($)">
                <Input type="number" value={form.saldo_a_cancelar} onChange={set("saldo_a_cancelar")} required placeholder="295000" />
              </Field>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <Field label="Día de firma">
                <Input type="number" value={form.dia_firma} onChange={set("dia_firma")} required placeholder="15" min="1" max="31" />
              </Field>
              <Field label="Mes de firma">
                <Input value={form.mes_firma} onChange={set("mes_firma")} required placeholder="julio" />
              </Field>
              <Field label="Año de firma">
                <Input type="number" value={form.año_firma} onChange={set("año_firma")} required placeholder="2026" />
              </Field>
            </div>

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
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2 text-sm transition-colors hover:text-white"
                style={{ color: "#8B949E" }}
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex items-center gap-2 text-white text-sm font-medium px-5 py-2 rounded-lg transition-colors disabled:opacity-50"
                style={{ background: "#2B6BF3" }}
              >
                {loading ? "Generando..." : "Generar contrato"}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="rounded-2xl overflow-hidden" style={{ background: "#161B22", border: "1px solid #21262D" }}>
        <div className="px-5 py-4" style={{ borderBottom: "1px solid #21262D" }}>
          <h2 className="font-semibold text-white text-sm">Historial</h2>
        </div>
        {historial.length === 0 ? (
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
                <th className="px-5 py-3 text-right text-xs font-medium" style={{ color: "#484F58" }}>PDF</th>
              </tr>
            </thead>
            <tbody>
              {historial.map((c) => (
                <tr key={c.id} className="transition-colors" style={{ borderBottom: "1px solid #21262D22" }}>
                  <td className="px-5 py-3" style={{ color: "#C9D1D9" }}>{c.nombre_prestatario}</td>
                  <td className="px-5 py-3" style={{ color: "#8B949E" }}>{c.lugar_evento}</td>
                  <td className="px-5 py-3" style={{ color: "#8B949E" }}>{c.dia_evento}</td>
                  <td className="px-5 py-3 text-xs" style={{ color: "#484F58" }}>
                    {format(new Date(c.created_at), "dd MMM yyyy HH:mm", { locale: es })}
                  </td>
                  <td className="px-5 py-3 text-right">
                    {c.pdf_url ? (
                      <a href={c.pdf_url} target="_blank" rel="noreferrer" style={{ color: "#79C0FF" }} className="hover:opacity-80 transition-opacity">
                        <Download size={15} />
                      </a>
                    ) : (
                      <span style={{ color: "#484F58" }}>—</span>
                    )}
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
