import { useState, useEffect } from "react";
import { Users, UserPlus, Mail, Shield, Loader2, X, Check, Trash2, Edit2 } from "lucide-react";
import { listUsers, createUser, updateUser, deactivateUser } from "../utils/auth";

// ── Metadata de roles ────────────────────────────────────────────────────────
const ROLE_META = {
  admin:     { label: "Admin",     color: "#2B6BF3", desc: "Acceso total al sistema" },
  armador:   { label: "Armador",   color: "#3FB950", desc: "Eventos y materiales operativos" },
  mayorista: { label: "Mayorista", color: "#D29922", desc: "Disponibilidad de inventario" },
  deposito:  { label: "Depósito",  color: "#A371F7", desc: "Solo eventos y materiales vía chat" },
};

// ── Fila de usuario ──────────────────────────────────────────────────────────
function UserRow({ user, onEdit, onDeactivate }) {
  const meta = ROLE_META[user.role] || { label: user.role, color: "#8B949E", desc: "" };
  return (
    <div className="rounded-xl px-4 py-3 flex items-center gap-3 group hover:border-[#30363D] transition-colors"
      style={{ background: "#161B22", border: "1px solid #21262D" }}>
      <div className="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
        style={{ background: `${meta.color}22`, color: meta.color, border: `1px solid ${meta.color}44` }}>
        <Users size={16} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="font-semibold text-white truncate">{user.name || user.username}</p>
          <span className="text-[10px] px-1.5 py-0.5 rounded font-medium"
            style={{ background: `${meta.color}22`, color: meta.color, border: `1px solid ${meta.color}44` }}>
            {meta.label}
          </span>
          {!user.active && (
            <span className="text-[10px] px-1.5 py-0.5 rounded font-medium"
              style={{ background: "#f8514922", color: "#F85149", border: "1px solid #F8514944" }}>
              Inactivo
            </span>
          )}
        </div>
        <p className="text-xs mt-0.5 truncate" style={{ color: "#8B949E" }}>
          @{user.username} {user.last_login && `· último ingreso: ${new Date(user.last_login).toLocaleDateString("es-AR")}`}
        </p>
      </div>
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={() => onEdit(user)} className="p-2 rounded-lg hover:bg-[#1C2230] text-[#8B949E] hover:text-white">
          <Edit2 size={14} />
        </button>
        {user.active && (
          <button onClick={() => onDeactivate(user)} className="p-2 rounded-lg hover:bg-[#1C2230] text-[#8B949E] hover:text-[#F85149]">
            <Trash2 size={14} />
          </button>
        )}
      </div>
    </div>
  );
}

// ── Form de alta/edición ─────────────────────────────────────────────────────
function UserForm({ initial, onSave, onCancel }) {
  const [form, setForm] = useState({
    username: initial?.username ?? "",
    name:     initial?.name ?? "",
    role:     initial?.role ?? "armador",
    password: "",
    active:   initial?.active ?? true,
  });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const isEdit = Boolean(initial?.id);

  async function handleSubmit(e) {
    e.preventDefault();
    setErr("");
    if (!form.username.trim() || !form.name.trim()) {
      setErr("Username y nombre son obligatorios");
      return;
    }
    if (!isEdit && !form.password) {
      setErr("La contraseña es obligatoria al crear");
      return;
    }
    setSaving(true);
    try {
      await onSave(form);
    } catch (e) {
      setErr(e.message || "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-xl p-5 space-y-4" style={{ background: "#0D1117", border: "1px solid #21262D" }}>
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-white">
          {isEdit ? "Editar usuario" : "Nuevo usuario"}
        </h3>
        <button type="button" onClick={onCancel} className="p-1.5 rounded-lg hover:bg-[#1C2230] text-[#8B949E]">
          <X size={16} />
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "#8B949E" }}>Username *</label>
          <input
            className="input w-full text-sm"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            disabled={isEdit}
            placeholder="ej: armador1"
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "#8B949E" }}>Nombre completo *</label>
          <input
            className="input w-full text-sm"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="ej: Juan Pérez"
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "#8B949E" }}>Rol *</label>
          <select className="input w-full text-sm" value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="admin">Admin</option>
            <option value="armador">Armador</option>
            <option value="mayorista">Mayorista</option>
            <option value="deposito">Depósito</option>
          </select>
          <p className="text-[11px] mt-1" style={{ color: "#8B949E" }}>
            {ROLE_META[form.role]?.desc}
          </p>
        </div>
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "#8B949E" }}>
            {isEdit ? "Nueva contraseña (vacío = sin cambio)" : "Contraseña *"}
          </label>
          <input
            type="password"
            className="input w-full text-sm"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            placeholder="••••••••"
          />
        </div>
      </div>

      {isEdit && (
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={form.active}
            onChange={(e) => setForm({ ...form, active: e.target.checked })}
            className="accent-[#2B6BF3]"
          />
          <span style={{ color: "#C9D1D9" }}>Usuario activo</span>
        </label>
      )}

      {err && (
        <p className="text-xs px-3 py-2 rounded-lg"
          style={{ background: "#F8514922", color: "#F85149", border: "1px solid #F8514944" }}>
          {err}
        </p>
      )}

      <div className="flex items-center justify-end gap-2 pt-2">
        <button type="button" onClick={onCancel}
          className="px-4 py-2 text-sm rounded-lg" style={{ color: "#8B949E" }}>
          Cancelar
        </button>
        <button type="submit" disabled={saving}
          className="px-4 py-2 text-sm rounded-lg flex items-center gap-2 text-white disabled:opacity-50"
          style={{ background: "#2B6BF3" }}>
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
          {isEdit ? "Guardar" : "Crear usuario"}
        </button>
      </div>
    </form>
  );
}

// ── Página principal ─────────────────────────────────────────────────────────
export default function Equipo() {
  const [users, setUsers]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);
  const [err, setErr] = useState("");

  async function reload() {
    setLoading(true);
    try {
      const data = await listUsers();
      setUsers(Array.isArray(data) ? data : []);
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { reload(); }, []);

  async function handleCreate(form) {
    await createUser(form);
    setCreating(false);
    await reload();
  }

  async function handleUpdate(form) {
    const payload = { name: form.name, role: form.role, active: form.active };
    if (form.password) payload.password = form.password;
    await updateUser(editing.id, payload);
    setEditing(null);
    await reload();
  }

  async function handleDeactivate(user) {
    if (!confirm(`¿Desactivar a ${user.name}? Podrá reactivarse después.`)) return;
    await deactivateUser(user.id);
    await reload();
  }

  // Agrupar por rol para visualización
  const byRole = users.reduce((acc, u) => {
    (acc[u.role] = acc[u.role] || []).push(u);
    return acc;
  }, {});

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: "#2B6BF322", border: "1px solid #2B6BF344" }}>
            <Users size={18} style={{ color: "#2B6BF3" }} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Gestión de equipo</h1>
            <p className="text-sm mt-0.5" style={{ color: "#8B949E" }}>
              {users.length} usuario{users.length !== 1 ? "s" : ""} · {users.filter(u => u.active).length} activo{users.filter(u => u.active).length !== 1 ? "s" : ""}
            </p>
          </div>
        </div>
        {!creating && !editing && (
          <button
            onClick={() => setCreating(true)}
            className="px-4 py-2 text-sm rounded-lg flex items-center gap-2 text-white"
            style={{ background: "#2B6BF3" }}>
            <UserPlus size={14} />
            Nuevo usuario
          </button>
        )}
      </div>

      {/* Form alta */}
      {creating && (
        <div className="mb-6">
          <UserForm onSave={handleCreate} onCancel={() => setCreating(false)} />
        </div>
      )}

      {/* Form edición */}
      {editing && (
        <div className="mb-6">
          <UserForm initial={editing} onSave={handleUpdate} onCancel={() => setEditing(null)} />
        </div>
      )}

      {/* Estado de carga / error */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={20} className="animate-spin" style={{ color: "#8B949E" }} />
        </div>
      ) : err ? (
        <div className="rounded-xl px-4 py-3 text-sm"
          style={{ background: "#F8514922", color: "#F85149", border: "1px solid #F8514944" }}>
          {err}
        </div>
      ) : (
        // Lista agrupada por rol
        <div className="space-y-6">
          {Object.entries(ROLE_META).map(([roleKey, meta]) => {
            const list = byRole[roleKey] || [];
            if (list.length === 0) return null;
            return (
              <div key={roleKey}>
                <div className="flex items-center gap-2 mb-2 px-1">
                  <Shield size={12} style={{ color: meta.color }} />
                  <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: meta.color }}>
                    {meta.label}
                  </h2>
                  <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "#21262D", color: "#8B949E" }}>
                    {list.length}
                  </span>
                </div>
                <div className="space-y-2">
                  {list.map((u) => (
                    <UserRow key={u.id} user={u} onEdit={setEditing} onDeactivate={handleDeactivate} />
                  ))}
                </div>
              </div>
            );
          })}

          {users.length === 0 && (
            <div className="rounded-xl p-8 text-center" style={{ background: "#0D1117", border: "1px dashed #21262D" }}>
              <Mail size={24} className="mx-auto mb-2" style={{ color: "#8B949E" }} />
              <p className="text-sm" style={{ color: "#8B949E" }}>No hay usuarios todavía. Creá el primero.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
