/**
 * Cliente de auth: login contra backend, guarda JWT en localStorage,
 * helpers para obtener usuario actual y rol.
 */
const API = import.meta.env.VITE_CONTRATOS_API || "https://backend-sonner.optimizar-ia.com";

const TOKEN_KEY = "sonner_token";
const USER_KEY  = "sonner_user";

// ── Login / logout ───────────────────────────────────────────────────────────
export async function login(username, password) {
  const res = await fetch(`${API}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  const data = await res.json();
  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));
  return data.user;
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

// ── State del usuario actual ─────────────────────────────────────────────────
export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function isAuthenticated() {
  return Boolean(getToken());
}

export function hasRole(...roles) {
  const u = getUser();
  return u && roles.includes(u.role);
}

// ── Fetch con auth automática ────────────────────────────────────────────────
export async function authFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const url = path.startsWith("http") ? path : `${API}${path}`;
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    // Token expirado o inválido → forzar logout
    logout();
    window.location.href = "/login";
    throw new Error("Sesión expirada");
  }
  return res;
}

// ── Endpoints de gestión de usuarios (admin) ─────────────────────────────────
export async function listUsers() {
  const res = await authFetch("/api/auth/users");
  if (!res.ok) throw new Error("No se pudieron listar usuarios");
  return res.json();
}

export async function createUser(payload) {
  const res = await authFetch("/api/auth/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function updateUser(id, payload) {
  const res = await authFetch(`/api/auth/users/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function deactivateUser(id) {
  const res = await authFetch(`/api/auth/users/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("No se pudo desactivar");
  return res.json();
}
