/**
 * Logo de Sonner replicando la tipografía geométrica del original.
 * Usa Audiowide como aproximación a la fuente custom del logo real.
 *
 * Props:
 *   variant: "full" (con bajada "SONIDO E ILUMINACION") | "compact" (solo SONNER) | "icon" (solo S)
 *   color: color del texto (default blanco)
 *   size: tamaño base en px
 */
export default function SonnerLogo({ variant = "full", color = "#fff", size = 32 }) {
  if (variant === "icon") {
    return (
      <div
        className="flex items-center justify-center rounded-lg"
        style={{
          width: size,
          height: size,
          background: "linear-gradient(135deg, #1e3a8a 0%, #0D1117 100%)",
          fontFamily: "Audiowide, sans-serif",
          fontSize: size * 0.55,
          color,
          letterSpacing: "-0.05em",
          fontWeight: 400,
        }}
      >
        S
      </div>
    );
  }

  return (
    <div className="flex flex-col" style={{ lineHeight: 0.95 }}>
      <span
        style={{
          fontFamily: "Audiowide, Impact, sans-serif",
          fontSize: size,
          color,
          letterSpacing: "0.02em",
          fontWeight: 400,
        }}
      >
        SONNER
      </span>
      {variant === "full" && (
        <span
          style={{
            fontFamily: "Audiowide, sans-serif",
            fontSize: size * 0.28,
            color,
            letterSpacing: "0.18em",
            opacity: 0.85,
            marginTop: size * 0.05,
          }}
        >
          SONIDO E ILUMINACION
        </span>
      )}
    </div>
  );
}
