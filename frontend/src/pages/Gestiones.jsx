import { ExternalLink, Zap, FileSpreadsheet } from "lucide-react";

// ── Logos SVG inline ─────────────────────────────────────────────────────────
const AnthropicLogo = ({ size = 28 }) => (
  <svg width={size} height={size} viewBox="0 0 92 65" fill="currentColor">
    <path d="M66.49 0H51.83l26.7 65h14.66L66.49 0zM26.18 0L0 65h14.95l5.36-13.84h27.4L53.07 65h14.95L41.86 0H26.18zm-1.05 38.65L34.06 15.6l8.92 23.05H25.13z"/>
  </svg>
);

const OpenAILogo = ({ size = 28 }) => (
  <svg width={size} height={size} viewBox="0 0 320 320" fill="currentColor">
    <path d="M297.06 130.97a80.06 80.06 0 0 0-6.88-65.71 81 81 0 0 0-87.28-38.81A81 81 0 0 0 69.62 53.61a80.06 80.06 0 0 0-53.45 38.77 81 81 0 0 0 9.97 95.05 80.06 80.06 0 0 0 6.87 65.71 81 81 0 0 0 87.29 38.81 80.06 80.06 0 0 0 60.43 26.99 81 81 0 0 0 77.2-55.99 80.06 80.06 0 0 0 53.43-38.77 81 81 0 0 0-9.96-95.04Zm-120.28 168.1a60.05 60.05 0 0 1-38.56-13.95c.49-.27 1.34-.74 1.89-1.08l63.72-36.8a10.36 10.36 0 0 0 5.24-9.07v-89.83l26.93 15.55a.95.95 0 0 1 .52.74v74.39a60.07 60.07 0 0 1-59.74 60.05Zm-128.84-55.03a59.97 59.97 0 0 1-7.18-40.31c.48.29 1.32.81 1.92 1.15l63.72 36.8a10.39 10.39 0 0 0 10.48 0l77.79-44.92v31.1a.96.96 0 0 1-.38.83l-64.41 37.19a60.07 60.07 0 0 1-81.94-21.84Zm-16.77-139.09a59.97 59.97 0 0 1 31.39-26.4c0 .56-.03 1.55-.03 2.24v73.59a10.36 10.36 0 0 0 5.24 9.06l77.79 44.91-26.93 15.55a.96.96 0 0 1-.9.08L53.84 187a60.07 60.07 0 0 1-22.06-81.99Zm221.26 51.49-77.79-44.92 26.93-15.54a.96.96 0 0 1 .9-.08l64.41 37.19a60.04 60.04 0 0 1-9.27 108.36c0-.57 0-1.55 0-2.24v-73.59a10.35 10.35 0 0 0-5.18-9.18Zm26.8-40.34c-.48-.3-1.32-.81-1.92-1.15l-63.72-36.8a10.4 10.4 0 0 0-10.48 0l-77.79 44.92v-31.1a.96.96 0 0 1 .38-.83l64.41-37.16a60.04 60.04 0 0 1 89.12 62.12Zm-168.51 55.43-26.94-15.55a.95.95 0 0 1-.52-.74v-74.39a60.04 60.04 0 0 1 98.43-46.12c-.49.27-1.33.74-1.89 1.08l-63.72 36.8a10.36 10.36 0 0 0-5.24 9.06l-.12 89.86Zm14.63-31.54 34.65-20.01 34.65 20v40.01l-34.65 20-34.65-20Z"/>
  </svg>
);

const TelegramLogo = ({ size = 28 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L8.32 14.617l-2.96-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.828.942z"/>
  </svg>
);

const CloudflareLogo = ({ size = 28 }) => (
  <svg width={size} height={size} viewBox="0 0 256 116" fill="currentColor">
    <path d="M202.357 51.198c-1.246-.382-2.493-.382-3.864-.382-.5 0-.873.382-.998.764l-2.244 7.728c-.998 3.371-.624 6.49 1.122 8.84 1.62 2.097 4.114 3.371 7.105 3.626l9.475.572c.249 0 .498.127.623.382.124.255.249.51.124.764-.374 1.34-1.371 1.97-2.866 2.225l-9.85.572c-5.36.255-11.094 4.59-13.088 9.86l-.748 1.97c-.125.255 0 .51.374.51h33.91c.5 0 .874-.382.998-.764 1.745-5.952 2.494-12.34 1.495-19.18-.748-5.207-3.49-9.733-7.354-13.104-3.864-3.371-8.851-5.207-14.214-5.207m-37.275 38.66c1.621-2.097 1.62-5.594-.125-7.945-1.62-2.097-4.114-3.371-7.105-3.626l-58.71-.892c-.374 0-.873-.255-1.122-.51-.249-.255-.249-.764-.124-1.146.249-.51.748-.892 1.495-.892l59.21-.892c7.105-.382 14.71-5.952 17.45-12.952l3.49-9.097c.125-.51.249-.892.125-1.527-3.989-17.677-19.823-30.882-38.898-30.882-17.7 0-32.661 11.296-37.9 26.881-3.366-2.479-7.853-3.626-12.713-3.116-8.602.892-15.458 7.728-16.456 16.249-.249 2.225-.124 4.46.374 6.49-13.96.382-25.054 11.677-25.054 25.643 0 1.273.125 2.479.249 3.625.125.51.624.892 1.122.892h109.86c.498 0 1.122-.382 1.122-.892zm44.66-12.34c-.5 0-.998.382-1.122.892l-2.494 8.493c-.998 3.371-.625 6.49 1.122 8.84 1.62 2.098 4.113 3.372 7.105 3.626l13.589.892c.249 0 .499.127.623.382.124.255.249.51.124.764-.374 1.34-1.37 1.97-2.866 2.225l-13.96.762c-5.36.255-11.094 4.59-13.088 9.86l-.748 1.97c-.124.255 0 .51.374.51h47.747c.374 0 .748-.255.873-.638a47.4 47.4 0 0 0 1.745-13.104c0-13.34-7.354-25.262-18.197-31.595-.124 0-.249-.127-.498-.127z"/>
  </svg>
);

const SupabaseLogo = ({ size = 28 }) => (
  <svg width={size} height={size} viewBox="0 0 109 113" fill="none">
    <path d="M63.708 110.284c-2.86 3.601-8.658 1.628-8.727-2.97l-1.007-67.251h45.22c8.19 0 12.758 9.46 7.665 15.874l-43.151 54.347Z" fill="currentColor"/>
    <path d="M45.317 2.071c2.86-3.601 8.657-1.628 8.726 2.97l.442 67.251H9.83c-8.19 0-12.759-9.46-7.665-15.875L45.317 2.072Z" fill="currentColor" opacity="0.6"/>
  </svg>
);

const SheetsLogo = ({ size = 28 }) => <FileSpreadsheet size={size} strokeWidth={2.2} />;

// ── Configuración de cards ───────────────────────────────────────────────────
const GROUPS = [
  {
    title: "APIs",
    items: [
      {
        id: "anthropic",
        url: "https://console.anthropic.com/",
        name: "Anthropic Console",
        description: "Claude API · uso, billing, API keys",
        badge: "API",
        Logo: AnthropicLogo,
        brand: "#CC785C",
        bg: "linear-gradient(135deg, #2A1A14 0%, #1A100C 100%)",
      },
      {
        id: "openai",
        url: "https://platform.openai.com/",
        name: "OpenAI Platform",
        description: "GPT · embeddings · uso y API keys",
        badge: "API",
        Logo: OpenAILogo,
        brand: "#10A37F",
        bg: "linear-gradient(135deg, #0B2620 0%, #081915 100%)",
      },
    ],
  },
  {
    title: "Infraestructura",
    items: [
      {
        id: "supabase",
        url: "https://supabase.com/dashboard/project/wndfjicwzmsuxxcsnccl",
        name: "Supabase",
        description: "Base de datos · auth · storage · logs",
        badge: "DB",
        Logo: SupabaseLogo,
        brand: "#3ECF8E",
        bg: "linear-gradient(135deg, #0C2519 0%, #081A11 100%)",
      },
      {
        id: "cloudflare",
        url: "https://dash.cloudflare.com/",
        name: "Cloudflare",
        description: "DNS · proxy · subdominios optimizar-ia.com",
        badge: "DNS",
        Logo: CloudflareLogo,
        brand: "#F38020",
        bg: "linear-gradient(135deg, #2A1A0C 0%, #1A1008 100%)",
      },
    ],
  },
  {
    title: "Bots y agentes",
    items: [
      {
        id: "telegram",
        url: "https://t.me/sonner_INT_BOT",
        name: "Agente interno (Telegram)",
        description: "Chatear directo con el bot de Sonner",
        badge: "Bot",
        Logo: TelegramLogo,
        brand: "#229ED9",
        bg: "linear-gradient(135deg, #0B1F2B 0%, #08151D 100%)",
      },
    ],
  },
  {
    title: "Documentos",
    items: [
      {
        id: "salones",
        url: "https://docs.google.com/spreadsheets/d/1UC2rPEx0YNvaE3rrSVpZ-tgSTcQKEj9GF5yyJIx13VU/edit?gid=0#gid=0",
        name: "Salones",
        description: "Listado y datos de salones · Google Sheets",
        badge: "Sheet",
        Logo: SheetsLogo,
        brand: "#0F9D58",
        bg: "linear-gradient(135deg, #0C2519 0%, #081A11 100%)",
      },
    ],
  },
];

// ── Card individual ──────────────────────────────────────────────────────────
function LinkCard({ link }) {
  const { url, name, description, badge, Logo, brand, bg } = link;
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="group relative block rounded-2xl p-5 overflow-hidden transition-all duration-300 hover:scale-[1.02]"
      style={{
        background: bg,
        border: "1px solid #21262D",
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = `${brand}66`; e.currentTarget.style.boxShadow = `0 8px 32px ${brand}22`; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = "#21262D"; e.currentTarget.style.boxShadow = "none"; }}
    >
      {/* Glow decorativo */}
      <div
        className="absolute -top-12 -right-12 w-32 h-32 rounded-full opacity-20 blur-2xl pointer-events-none transition-opacity group-hover:opacity-40"
        style={{ background: brand }}
      />

      {/* Header: logo + badge + external icon */}
      <div className="flex items-start justify-between mb-4 relative">
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center"
          style={{ background: `${brand}22`, color: brand, border: `1px solid ${brand}44` }}
        >
          <Logo size={24} />
        </div>
        <div className="flex items-center gap-2">
          <span
            className="text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider"
            style={{ background: `${brand}22`, color: brand, border: `1px solid ${brand}44` }}
          >
            {badge}
          </span>
          <ExternalLink size={14} className="opacity-40 group-hover:opacity-100 transition-opacity" style={{ color: brand }} />
        </div>
      </div>

      {/* Texto */}
      <h3 className="font-semibold text-white text-base mb-1 relative">{name}</h3>
      <p className="text-xs leading-relaxed relative" style={{ color: "#8B949E" }}>
        {description}
      </p>

      {/* CTA bar */}
      <div
        className="mt-4 pt-3 flex items-center justify-between text-xs font-medium relative"
        style={{ borderTop: "1px solid #21262D", color: brand }}
      >
        <span>Abrir</span>
        <span className="opacity-0 group-hover:opacity-100 transition-opacity">→</span>
      </div>
    </a>
  );
}

// ── Página principal ─────────────────────────────────────────────────────────
export default function Gestiones() {
  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: "#D2992222", border: "1px solid #D2992244" }}
        >
          <Zap size={18} style={{ color: "#D29922" }} />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">Gestiones</h1>
          <p className="text-sm mt-0.5" style={{ color: "#8B949E" }}>
            Accesos directos a consolas externas y herramientas
          </p>
        </div>
      </div>

      {/* Grupos */}
      <div className="space-y-8">
        {GROUPS.map((group) => (
          <section key={group.title}>
            <h2 className="text-xs font-semibold uppercase tracking-wider mb-3 px-1" style={{ color: "#6E7681" }}>
              {group.title}
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {group.items.map((link) => (
                <LinkCard key={link.id} link={link} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
