import { NavLink, useNavigate } from "react-router-dom";
import { LayoutDashboard, MessageSquare, FileText, Brain, Send, Settings, LogOut } from "lucide-react";

const TgIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L8.32 14.617l-2.96-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.828.942z"/>
  </svg>
);

const NAV = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/chat",      icon: MessageSquare,   label: "Chat interno" },
  { to: "/mensajes",  icon: Send,            label: "Mensajes" },
  { to: "/analista",  icon: Brain,           label: "Analista IA" },
  { to: "/contratos", icon: FileText,        label: "Contratos" },
  { to: "/telegram",  icon: TgIcon,          label: "Telegram" },
  { to: "/admin",     icon: Settings,        label: "Admin" },
];

export default function Sidebar() {
  const navigate = useNavigate();

  return (
    <aside className="w-56 flex flex-col shrink-0" style={{ background: "#161B22", borderRight: "1px solid #21262D" }}>
      {/* Logo */}
      <div className="p-5 flex items-center gap-3" style={{ borderBottom: "1px solid #21262D" }}>
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm"
          style={{ background: "linear-gradient(135deg, #2B6BF3, #1742ab)" }}
        >
          SNR
        </div>
        <div>
          <p className="text-white font-bold text-sm leading-none">Sonner</p>
          <p className="text-[10px] leading-none mt-0.5" style={{ color: "#484F58" }}>Sonido e Iluminación</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-0.5">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? "text-white"
                  : "text-[#8B949E] hover:text-white hover:bg-[#1C2230]"
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
        ))}
      </nav>

      {/* Footer */}
      <div className="p-3" style={{ borderTop: "1px solid #21262D" }}>
        <button
          onClick={() => { localStorage.removeItem("sonner_token"); navigate("/login"); }}
          className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm font-medium text-[#8B949E] hover:text-white hover:bg-[#1C2230] transition-colors"
        >
          <LogOut size={15} />
          Salir
        </button>
      </div>
    </aside>
  );
}
