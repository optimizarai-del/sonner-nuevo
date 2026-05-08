import { NavLink, useNavigate } from "react-router-dom";
import { LayoutDashboard, MessageSquare, FileText, Brain, Send, Settings, LogOut, Users, Shield, Phone } from "lucide-react";
import SonnerLogo from "../SonnerLogo";

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

const NAV = [
  { to: "/dashboard",     icon: LayoutDashboard, label: "Dashboard" },
  { to: "/crm",           icon: Users,           label: "CRM" },
  { to: "/chat",          icon: MessageSquare,   label: "Chat interno" },
  { to: "/whatsapp",      icon: WaIcon,          label: "WhatsApp" },
  { to: "/contratos",     icon: FileText,        label: "Contratos" },
  { to: "/analista",      icon: Brain,           label: "Analista IA" },
  { to: "/telegram",      icon: TgIcon,          label: "Agente externo" },
  { to: "/configuracion", icon: Settings,        label: "Configuración" },
];

export default function Sidebar() {
  const navigate = useNavigate();

  return (
    <aside className="w-56 flex flex-col shrink-0" style={{ background: "#161B22", borderRight: "1px solid #21262D" }}>

      {/* Logo */}
      <div className="px-5 py-6 flex items-center justify-center" style={{ borderBottom: "1px solid #21262D" }}>
        <SonnerLogo variant="full" color="#fff" size={26} />
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
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
