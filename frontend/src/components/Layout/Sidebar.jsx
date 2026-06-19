import { useState, useEffect } from "react";
import { NavLink, useNavigate, useLocation } from "react-router-dom";
import {
  LayoutDashboard, MessageSquare, FileText, Brain, Settings,
  LogOut, Users, CalendarDays, Package, Menu, X, ChevronDown,
  Bot, Briefcase, ShieldCheck, Zap, Store, MessageSquareText,
} from "lucide-react";
import SonnerLogo from "../SonnerLogo";
import { getUser, logout } from "../../utils/auth";

// ── Iconos custom ────────────────────────────────────────────────────────────
const WaIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
    <path d="M17.498 14.382c-.301-.15-1.767-.867-2.04-.966-.273-.101-.473-.15-.673.15-.197.295-.771.964-.944 1.162-.175.195-.349.21-.646.075-.3-.15-1.263-.465-2.403-1.485-.888-.795-1.484-1.77-1.66-2.07-.174-.3-.019-.465.13-.615.136-.135.301-.345.451-.523.146-.181.194-.301.297-.496.1-.21.049-.375-.025-.524-.075-.15-.672-1.62-.922-2.206-.24-.584-.487-.51-.672-.51-.172-.015-.371-.015-.571-.015-.2 0-.523.074-.797.359-.273.3-1.045 1.02-1.045 2.475s1.07 2.865 1.219 3.075c.149.195 2.105 3.195 5.1 4.485.714.3 1.27.48 1.704.629.714.227 1.365.195 1.88.121.574-.091 1.767-.721 2.016-1.426.255-.705.255-1.29.18-1.425-.074-.135-.27-.21-.57-.345m-5.446 7.443h-.016c-1.77 0-3.524-.48-5.055-1.38l-.36-.214-3.75.975 1.005-3.645-.239-.375a9.869 9.869 0 0 1-1.516-5.26c.002-5.45 4.437-9.884 9.892-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413Z"/>
  </svg>
);

const TgIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L8.32 14.617l-2.96-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.828.942z"/>
  </svg>
);

// ── Estructura del menú agrupada por secciones ───────────────────────────────
const SECTIONS = [
  {
    id: "principal",
    label: null, // sin label = no muestra el header del grupo
    items: [
      { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard",    roles: ["admin"] },
      { to: "/chat",      icon: MessageSquare,   label: "Chat interno", roles: ["admin", "armador", "mayorista", "deposito"] },
    ],
  },
  {
    id: "operaciones",
    label: "Operaciones",
    icon: Briefcase,
    items: [
      { to: "/eventos",    icon: CalendarDays, label: "Eventos",    roles: ["admin", "armador", "mayorista"] },
      { to: "/materiales", icon: Package,      label: "Materiales", roles: ["admin", "armador", "mayorista"] },
      { to: "/crm",        icon: Users,        label: "CRM",        roles: ["admin"] },
      { to: "/mayoristas", icon: Store,        label: "Mayoristas", roles: ["admin"] },
      { to: "/contratos",  icon: FileText,     label: "Contratos",  roles: ["admin"] },
    ],
  },
  {
    id: "agentes",
    label: "Agentes IA",
    icon: Bot,
    items: [
      { to: "/analista",     icon: Brain,              label: "Analista IA",     roles: ["admin"] },
      { to: "/whatsapp",     icon: WaIcon,             label: "WhatsApp",        roles: ["admin"] },
      { to: "/telegram",     icon: TgIcon,             label: "Agente externo",  roles: ["admin"] },
      { to: "/analisis-csm", icon: MessageSquareText,  label: "Análisis de CSM", roles: ["admin"] },
    ],
  },
  {
    id: "equipo",
    label: "Gestión de equipo",
    icon: ShieldCheck,
    items: [
      { to: "/equipo",        icon: Users,    label: "Usuarios",      roles: ["admin"] },
      { to: "/configuracion", icon: Settings, label: "Configuración", roles: ["admin"] },
    ],
  },
  {
    id: "gestiones",
    label: "Gestiones",
    icon: Zap,
    items: [
      { to: "/gestiones", icon: Zap, label: "Accesos rápidos", roles: ["admin"] },
    ],
  },
];

const ROLE_LABELS = {
  admin:     { label: "Administrador", color: "#2B6BF3" },
  armador:   { label: "Armador",       color: "#3FB950" },
  mayorista: { label: "Mayorista",     color: "#D29922" },
  deposito:  { label: "Depósito",      color: "#A371F7" },
};

// ── Hook: persistir estado de grupos abiertos ────────────────────────────────
function useCollapsedGroups() {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      const raw = localStorage.getItem("sonner_sidebar_collapsed");
      return raw ? JSON.parse(raw) : {};
    } catch { return {}; }
  });
  useEffect(() => {
    try { localStorage.setItem("sonner_sidebar_collapsed", JSON.stringify(collapsed)); } catch {}
  }, [collapsed]);
  const toggle = (id) => setCollapsed((c) => ({ ...c, [id]: !c[id] }));
  return [collapsed, toggle];
}

// ── Componente: grupo de items con label ─────────────────────────────────────
function NavGroup({ section, isCollapsed, onToggle, onItemClick }) {
  if (section.items.length === 0) return null;
  const HeaderIcon = section.icon;

  // Grupo sin label: items planos
  if (!section.label) {
    return (
      <div className="space-y-0.5">
        {section.items.map((item) => (
          <NavItem key={item.to} item={item} onClick={onItemClick} />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between gap-2 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider hover:text-white transition-colors"
        style={{ color: "#6E7681" }}
      >
        <span className="flex items-center gap-2">
          {HeaderIcon && <HeaderIcon size={11} />}
          {section.label}
        </span>
        <ChevronDown
          size={12}
          className="transition-transform"
          style={{ transform: isCollapsed ? "rotate(-90deg)" : "rotate(0)" }}
        />
      </button>
      {!isCollapsed && (
        <div className="space-y-0.5">
          {section.items.map((item) => (
            <NavItem key={item.to} item={item} onClick={onItemClick} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Item individual ──────────────────────────────────────────────────────────
function NavItem({ item, onClick }) {
  const { to, icon: Icon, label } = item;
  return (
    <NavLink
      to={to}
      onClick={onClick}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
          isActive ? "text-white" : "text-[#8B949E] hover:text-white hover:bg-[#1C2230]"
        }`
      }
      style={({ isActive }) =>
        isActive
          ? { background: "#2B6BF322", color: "#79C0FF", borderLeft: "2px solid #2B6BF3", paddingLeft: "10px" }
          : {}
      }
    >
      <Icon size={15} />
      <span>{label}</span>
    </NavLink>
  );
}

// ── Contenido del sidebar (compartido entre desktop y mobile drawer) ─────────
function SidebarContent({ user, role, NAV, collapsed, toggle, roleMeta, onLogout, onItemClick }) {
  return (
    <>
      {/* Logo */}
      <div className="px-5 py-5 flex items-center justify-center" style={{ borderBottom: "1px solid #21262D" }}>
        <SonnerLogo variant="full" color="#fff" size={26} />
      </div>

      {/* Nav agrupada */}
      <nav className="flex-1 p-3 space-y-4 overflow-y-auto">
        {NAV.map((section) => (
          <NavGroup
            key={section.id}
            section={section}
            isCollapsed={collapsed[section.id]}
            onToggle={() => toggle(section.id)}
            onItemClick={onItemClick}
          />
        ))}
      </nav>

      {/* Footer */}
      <div className="p-3 space-y-2" style={{ borderTop: "1px solid #21262D" }}>
        {user && (
          <div className="px-3 py-2 rounded-lg" style={{ background: "#0D1117", border: "1px solid #21262D" }}>
            <p className="text-xs font-semibold text-white truncate">{user.name}</p>
            <p className="text-[10px] mt-0.5 inline-block px-1.5 py-0.5 rounded"
              style={{ background: `${roleMeta.color}22`, color: roleMeta.color, border: `1px solid ${roleMeta.color}44` }}>
              {roleMeta.label}
            </p>
          </div>
        )}
        <button
          onClick={onLogout}
          className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm font-medium text-[#8B949E] hover:text-white hover:bg-[#1C2230] transition-colors"
        >
          <LogOut size={15} />
          Salir
        </button>
      </div>
    </>
  );
}

// ── Sidebar principal ────────────────────────────────────────────────────────
export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = getUser();
  const role = user?.role || "armador";
  const [collapsed, toggle] = useCollapsedGroups();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Filtrar items por rol, y secciones vacías
  const NAV = SECTIONS
    .map((s) => ({ ...s, items: s.items.filter((it) => it.roles.includes(role)) }))
    .filter((s) => s.items.length > 0);

  const roleMeta = ROLE_LABELS[role] || { label: role, color: "#8B949E" };

  // Cerrar drawer al cambiar de ruta
  useEffect(() => { setMobileOpen(false); }, [location.pathname]);

  // Bloquear scroll del body cuando el drawer móvil está abierto
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [mobileOpen]);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <>
      {/* ── Topbar móvil con hamburguesa ─────────────────────────────────── */}
      <header
        className="md:hidden sticky top-0 z-30 flex items-center justify-between px-4 py-3"
        style={{ background: "#0D1117", borderBottom: "1px solid #21262D" }}
      >
        <button
          onClick={() => setMobileOpen(true)}
          aria-label="Abrir menú"
          className="p-2 rounded-lg hover:bg-[#1C2230] text-white"
        >
          <Menu size={20} />
        </button>
        <SonnerLogo variant="full" color="#fff" size={22} />
        <div className="w-9" /> {/* spacer para centrar logo */}
      </header>

      {/* ── Sidebar desktop ──────────────────────────────────────────────── */}
      <aside
        className="hidden md:flex w-60 flex-col shrink-0 h-screen sticky top-0"
        style={{ background: "#161B22", borderRight: "1px solid #21262D" }}
      >
        <SidebarContent
          user={user} role={role} NAV={NAV}
          collapsed={collapsed} toggle={toggle}
          roleMeta={roleMeta} onLogout={handleLogout}
        />
      </aside>

      {/* ── Drawer móvil ─────────────────────────────────────────────────── */}
      {mobileOpen && (
        <>
          {/* Backdrop */}
          <div
            onClick={() => setMobileOpen(false)}
            className="md:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            aria-hidden="true"
          />
          {/* Panel */}
          <aside
            className="md:hidden fixed top-0 left-0 bottom-0 z-50 w-72 flex flex-col"
            style={{ background: "#161B22", borderRight: "1px solid #21262D" }}
          >
            <button
              onClick={() => setMobileOpen(false)}
              aria-label="Cerrar menú"
              className="absolute top-3 right-3 p-2 rounded-lg hover:bg-[#1C2230] text-white z-10"
            >
              <X size={18} />
            </button>
            <SidebarContent
              user={user} role={role} NAV={NAV}
              collapsed={collapsed} toggle={toggle}
              roleMeta={roleMeta} onLogout={handleLogout}
              onItemClick={() => setMobileOpen(false)}
            />
          </aside>
        </>
      )}
    </>
  );
}
