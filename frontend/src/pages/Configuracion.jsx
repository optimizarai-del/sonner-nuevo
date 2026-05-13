import { useState, useEffect } from "react";
import {
  Settings, Building2, Plug, Activity, Save, Check, AlertCircle,
  Database, Globe, FileText, Loader2, RefreshCw,
  Key, Eye, EyeOff, Edit3, X, Users as UsersIcon, UserPlus, Trash2, Power,
} from "lucide-react";
import { supabase } from "../utils/supabase";
import { listUsers, createUser, updateUser, deactivateUser } from "../utils/auth";

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

// ── Tarjeta de credencial editable ────────────────────────────────────────────
function CredentialRow({ item, onSave }) {
  const [editing, setEditing] = useState(false);
  const [show, setShow] = useState(false);
  const [val, setVal] = useState(item.value ?? "");
  const [saving, setSaving] = useState(false);
  const [savedFlash, setSavedFlash] = useState(false);

  useEffect(() => { setVal(item.value ?? ""); }, [item.value, item.is_set]);

  async function save() {
    setSaving(true);
    try {
      await onSave(item.key, val);
      setSavedFlash(true);
      setEditing(false);
      setTimeout(() => setSavedFlash(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-lg px-4 py-3"
      style={{ background: "#0D1117", border: "1px solid #21262D" }}>
      <div className="flex items-center gap-3 mb-2">
        <div className="w-2 h-2 rounded-full shrink-0"
          style={{ background: item.is_set ? "#3FB950" : "#F85149" }} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-mono text-white">{item.key}</p>
          {item.description && (
            <p className="text-xs mt-0.5" style={{ color: "#8B949E" }}>{item.description}</p>
          )}
        </div>
        <span className="text-[10px] font-bold px-2 py-0.5 rounded shrink-0" style={{
          background: item.is_set ? "#3FB95022" : "#F8514922",
          color:      item.is_set ? "#3FB950"   : "#F85149",
        }}>
          {item.is_set ? "CONFIGURADO" : "FALTA"}
        </span>
        {savedFlash && <Check size={14} style={{ color: "#3FB950" }} />}
      </div>

      {editing ? (
        <div className="flex items-center gap-2">
          <div className="flex-1 relative">
            <input
              type={item.is_secret && !show ? "password" : "text"}
              value={val}
              onChange={(e) => setVal(e.target.value)}
              placeholder={item.is_secret ? "•••••••••" : "Valor..."}
              className="input w-full text-sm pr-9"
            />
            {item.is_secret && (
              <button
                type="button"
                onClick={() => setShow((s) => !s)}
                className="absolute right-2 top-1/2 -translate-y-1/2"
                style={{ color: "#8B949E" }}
              >
                {show ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            )}
          </div>
          <button
            onClick={save}
            disabled={saving || !val.trim()}
            className="text-white text-xs font-medium px-3 py-2 rounded-lg disabled:opacity-50"
            style={{ background: "#2B6BF3" }}
          >
            {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
          </button>
          <button
            onClick={() => { setEditing(false); setVal(item.value ?? ""); }}
            className="text-xs font-medium px-3 py-2 rounded-lg"
            style={{ background: "#21262D", color: "#8B949E" }}
          >
            <X size={12} />
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <div className="flex-1 px-3 py-2 rounded-lg text-xs font-mono truncate"
            style={{ background: "#161B22", border: "1px solid #21262D", color: "#8B949E" }}>
            {item.is_secret
              ? (item.is_set ? "•••••••••••••••••" : <span style={{ color: "#484F58" }}>(sin valor)</span>)
              : (item.value || <span style={{ color: "#484F58" }}>(sin valor)</span>)}
          </div>
          <button
            onClick={() => setEditing(true)}
            className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-lg transition-colors"
            style={{ background: "#21262D", color: "#8B949E", border: "1px solid #30363D" }}
          >
            <Edit3 size={12} />
            Editar
          </button>
        </div>
      )}
    </div>
  );
}

// ── Gestor de usuarios ────────────────────────────────────────────────────────
const ROLE_META = {
  admin:     { label: "Admin",     color: "#2B6BF3" },
  armador:   { label: "Armador",   color: "#3FB950" },
  mayorista: { label: "Mayorista", color: "#D29922" },
};

function UserRow({ user, onEdit, onDeactivate }) {
  const meta = ROLE_META[user.role] || { label: user.role, color: "#8B949E" };
  return (
    <div className="rounded-lg px-4 py-3 flex items-center gap-3"
      style={{ background: "#0D1117", border: "1px solid #21262D" }}>
      <div className="w-2 h-2 rounded-full shrink-0"
        style={{ background: user.active ? "#3FB950" : "#484F58" }} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white">{user.name}</p>
        <p className="text-xs font-mono mt-0.5" style={{ color: "#8B949E" }}>@{user.username}</p>
      </div>
      <span className="text-[10px] font-semibold px-2 py-1 rounded shrink-0"
        style={{ background: `${meta.color}22`, color: meta.color, border: `1px solid ${meta.color}44` }}>
        {meta.label}
      </span>
      <button
        onClick={() => onEdit(user)}
        className="p-2 rounded-lg transition-colors hover:bg-[#1C2230]"
        style={{ color: "#8B949E" }}
        title="Editar"
      >
        <Edit3 size={13} />
      </button>
      {user.active && (
        <button
          onClick={() => onDeactivate(user)}
          className="p-2 rounded-lg transition-colors hover:bg-[#1C2230]"
          style={{ color: "#F85149" }}
          title="Desactivar"
        >
          <Power size={13} />
        </button>
      )}
    </div>
  );
}

function UserForm({ initial, onSubmit, onCancel }) {
  const isNew = !initial?.id;
  const [form, setForm] = useState({
    username: initial?.username ?? "",
    name:     initial?.name ?? "",
    role:     initial?.role ?? "armador",
    password: "",
    active:   initial?.active ?? true,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState("");

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = { name: form.name, role: form.role, active: form.active };
      if (isNew) {
        payload.username = form.username.toLowerCase().trim();
        payload.password = form.password;
      } else if (form.password) {
        payload.password = form.password;
      }
      await onSubmit(payload);
    } catch (e) {
      setError(e.message || "Error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="rounded-lg p-4 space-y-3"
      style={{ background: "#0D1117", border: "1px solid #2B6BF344" }}>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "#8B949E" }}>Usuario *</label>
          <input className="input w-full text-sm" required disabled={!isNew}
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            placeholder="armador1" />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "#8B949E" }}>Nombre *</label>
          <input className="input w-full text-sm" required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Juan Pérez" />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "#8B949E" }}>Rol *</label>
          <select className="input w-full text-sm" value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="admin">Admin</option>
            <option value="armador">Armador</option>
            <option value="mayorista">Mayorista</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "#8B949E" }}>
            {isNew ? "Contraseña *" : "Nueva contraseña (opcional)"}
          </label>
          <input type="password" className="input w-full text-sm"
            required={isNew} minLength={4}
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            placeholder="••••••••" />
        </div>
      </div>
      {error && (
        <div className="text-xs flex items-center gap-1.5" style={{ color: "#F85149" }}>
          <AlertCircle size={12} /> {error}
        </div>
      )}
      <div className="flex justify-end gap-2 pt-1">
        <button type="button" onClick={onCancel}
          className="text-xs px-3 py-1.5 rounded-lg"
          style={{ background: "#21262D", color: "#8B949E", border: "1px solid #30363D" }}>
          Cancelar
        </button>
        <button type="submit" disabled={saving}
          className="text-xs text-white font-medium px-3 py-1.5 rounded-lg flex items-center gap-1.5 disabled:opacity-50"
          style={{ background: "#2B6BF3" }}>
          {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
          {isNew ? "Crear" : "Guardar"}
        </button>
      </div>
    </form>
  );
}

const CATEGORY_LABELS = {
  anthropic: { label: "Anthropic (Claude)", color: "#D29922", icon: "🧠" },
  google:    { label: "Google (Drive + Docs)", color: "#3FB950", icon: "📄" },
  whatsapp:  { label: "WhatsApp Cloud API", color: "#25D366", icon: "💬" },
  telegram:  { label: "Telegram", color: "#0088cc", icon: "✈️" },
  n8n:       { label: "n8n", color: "#A371F7", icon: "🔗" },
  general:   { label: "General", color: "#2B6BF3", icon: "⚙️" },
};

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

  // Credenciales
  const [credentials, setCredentials] = useState([]);
  const [loadingCreds, setLoadingCreds] = useState(false);
  const [credsError, setCredsError]     = useState("");

  // Usuarios
  const [users, setUsers]           = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [usersError, setUsersError] = useState("");
  const [editingUser, setEditingUser] = useState(null);  // null | "new" | user obj

  async function loadUsersList() {
    setLoadingUsers(true);
    setUsersError("");
    try {
      const data = await listUsers();
      setUsers(data ?? []);
    } catch (e) {
      setUsersError(e.message || "Error cargando usuarios");
    } finally {
      setLoadingUsers(false);
    }
  }

  async function handleSaveUser(payload) {
    if (editingUser === "new") {
      await createUser(payload);
    } else if (editingUser?.id) {
      await updateUser(editingUser.id, payload);
    }
    await loadUsersList();
    setEditingUser(null);
  }

  async function handleDeactivate(user) {
    if (!confirm(`¿Desactivar a ${user.name}? Después podés reactivarlo editándolo.`)) return;
    await deactivateUser(user.id);
    await loadUsersList();
  }

  async function loadCredentials() {
    setLoadingCreds(true);
    setCredsError("");
    try {
      const res = await fetch(`${CONTRATOS_API}/api/settings`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setCredentials(data.items ?? []);
    } catch (e) {
      setCredsError("No se pudieron cargar las credenciales: " + e.message);
    } finally {
      setLoadingCreds(false);
    }
  }

  async function saveCredential(key, value) {
    const res = await fetch(`${CONTRATOS_API}/api/settings/${encodeURIComponent(key)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value }),
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`HTTP ${res.status}: ${t.slice(0, 200)}`);
    }
    await loadCredentials();
  }

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

  useEffect(() => { loadEmpresa(); checkHealth(); loadCredentials(); loadUsersList(); }, []);

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

      {/* ── Usuarios ───────────────────────────────────────────────────────── */}
      <Section
        icon={UsersIcon}
        title="Usuarios del panel"
        subtitle="Gestión de cuentas. Roles: admin, armador, mayorista."
        color="#3FB950"
      >
        {usersError && (
          <div className="text-xs px-3 py-2 rounded-lg mb-3 flex items-center gap-2"
            style={{ background: "#2c0e0e", color: "#f85149", border: "1px solid #f8514944" }}>
            <AlertCircle size={13} /> {usersError}
          </div>
        )}

        <div className="space-y-2">
          {loadingUsers && users.length === 0 ? (
            <div className="text-center py-4">
              <Loader2 size={18} className="animate-spin mx-auto" style={{ color: "#8B949E" }} />
            </div>
          ) : (
            users.map((u) => (
              <UserRow key={u.id} user={u}
                onEdit={(usr) => setEditingUser(usr)}
                onDeactivate={handleDeactivate} />
            ))
          )}
        </div>

        {/* Edición / creación */}
        {editingUser && (
          <div className="mt-3">
            <UserForm
              initial={editingUser === "new" ? null : editingUser}
              onSubmit={handleSaveUser}
              onCancel={() => setEditingUser(null)}
            />
          </div>
        )}

        {!editingUser && (
          <div className="flex justify-end mt-4">
            <button
              onClick={() => setEditingUser("new")}
              className="flex items-center gap-2 text-white text-sm font-medium px-4 py-2 rounded-lg"
              style={{ background: "#2B6BF3" }}
            >
              <UserPlus size={14} />
              Nuevo usuario
            </button>
          </div>
        )}
      </Section>

      {/* ── Credenciales ───────────────────────────────────────────────────── */}
      <Section
        icon={Key}
        title="Credenciales y API keys"
        subtitle="Configurá las claves de Google, Anthropic, WhatsApp, etc. Se guardan encriptadas en Supabase."
        color="#D29922"
      >
        {credsError && (
          <div className="text-xs px-3 py-2 rounded-lg mb-3 flex items-center gap-2"
            style={{ background: "#2c0e0e", color: "#f85149", border: "1px solid #f8514944" }}>
            <AlertCircle size={13} /> {credsError}
          </div>
        )}
        {loadingCreds && credentials.length === 0 ? (
          <div className="text-center py-6">
            <Loader2 size={18} className="animate-spin mx-auto" style={{ color: "#8B949E" }} />
          </div>
        ) : credentials.length === 0 ? (
          <p className="text-xs text-center py-4" style={{ color: "#484F58" }}>
            Sin credenciales configuradas. Verificá que el backend tenga la SUPABASE_SERVICE_ROLE_KEY.
          </p>
        ) : (
          (() => {
            // Agrupar por categoría
            const byCat = {};
            for (const c of credentials) {
              const cat = c.category || "general";
              if (!byCat[cat]) byCat[cat] = [];
              byCat[cat].push(c);
            }
            const order = ["anthropic", "google", "whatsapp", "telegram", "n8n", "general"];
            return (
              <div className="space-y-5">
                {order.filter((k) => byCat[k]).map((cat) => {
                  const meta = CATEGORY_LABELS[cat] || CATEGORY_LABELS.general;
                  return (
                    <div key={cat}>
                      <div className="flex items-center gap-2 mb-2">
                        <span style={{ color: meta.color }}>{meta.icon}</span>
                        <p className="text-xs font-semibold uppercase tracking-wide"
                          style={{ color: meta.color }}>{meta.label}</p>
                      </div>
                      <div className="space-y-2">
                        {byCat[cat].map((item) => (
                          <CredentialRow key={item.key} item={item} onSave={saveCredential} />
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })()
        )}
        <div className="flex justify-end mt-4">
          <button
            onClick={loadCredentials}
            className="flex items-center gap-2 text-xs font-medium px-4 py-2 rounded-lg transition-colors"
            style={{ background: "#21262D", color: "#8B949E", border: "1px solid #30363D" }}
          >
            <RefreshCw size={12} className={loadingCreds ? "animate-spin" : ""} />
            Recargar
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
