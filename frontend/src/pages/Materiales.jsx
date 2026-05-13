import { Package, Sparkles } from "lucide-react";
import { getUser } from "../utils/auth";

export default function Materiales() {
  const user = getUser();
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: "#A371F722", border: "1px solid #A371F744" }}>
          <Package size={18} style={{ color: "#A371F7" }} />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">Materiales</h1>
          <p className="text-sm mt-0.5" style={{ color: "#8B949E" }}>
            Inventario de equipamiento de sonido e iluminación
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
              <li>• Catálogo completo de materiales</li>
              <li>• Crear, editar, dar de baja items</li>
              <li>• Cantidades totales y disponibles</li>
              <li>• Asignación a eventos</li>
            </>
          )}
          {user?.role === "armador" && (
            <>
              <li>• Materiales del evento que estás armando</li>
              <li>• Marcar items cargados</li>
            </>
          )}
          {user?.role === "mayorista" && (
            <>
              <li>• Inventario completo: disponible / total</li>
              <li>• Consulta de disponibilidad por fecha</li>
              <li>• Reservas y devoluciones</li>
            </>
          )}
        </ul>
      </div>
    </div>
  );
}
