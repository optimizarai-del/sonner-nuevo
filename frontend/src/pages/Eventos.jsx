import { CalendarDays, Sparkles } from "lucide-react";
import { getUser } from "../utils/auth";

export default function Eventos() {
  const user = getUser();
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: "#2B6BF322", border: "1px solid #2B6BF344" }}>
          <CalendarDays size={18} style={{ color: "#2B6BF3" }} />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">Eventos</h1>
          <p className="text-sm mt-0.5" style={{ color: "#8B949E" }}>
            Gestión de eventos y armado
          </p>
        </div>
      </div>

      <div className="rounded-2xl p-8 text-center"
        style={{ background: "#161B22", border: "1px solid #21262D" }}>
        <Sparkles size={32} className="mx-auto mb-3" style={{ color: "#D29922" }} />
        <h2 className="text-lg font-semibold text-white mb-2">Módulo en construcción</h2>
        <p className="text-sm mb-4" style={{ color: "#8B949E" }}>
          Acá vas a ver:
        </p>
        <ul className="text-xs text-left max-w-md mx-auto space-y-1.5" style={{ color: "#C9D1D9" }}>
          {user?.role === "admin" && (
            <>
              <li>• Lista completa de eventos con filtros</li>
              <li>• Crear, editar, eliminar eventos</li>
              <li>• Asignar materiales a cada evento</li>
              <li>• Vincular contratos del CRM</li>
            </>
          )}
          {user?.role === "armador" && (
            <>
              <li>• Eventos próximos (fecha, lugar, hora)</li>
              <li>• Lista de materiales a armar por evento</li>
              <li>• Marcar como armado / listo para entrega</li>
            </>
          )}
          {user?.role === "mayorista" && (
            <>
              <li>• Calendario de disponibilidad</li>
              <li>• Consultar fechas ocupadas / libres</li>
              <li>• Sin acceso a datos del cliente</li>
            </>
          )}
        </ul>
      </div>
    </div>
  );
}
