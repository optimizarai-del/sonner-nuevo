import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL  = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!SUPABASE_URL || !SUPABASE_ANON) {
  console.warn("[Supabase] Faltan VITE_SUPABASE_URL o VITE_SUPABASE_ANON_KEY en .env");
}

// Defensivo: si faltan las env NO tiramos excepción a nivel de módulo (eso tumbaría
// toda la app en pantalla blanca). Usamos un placeholder para que la app arranque; solo
// fallarán en runtime las pantallas que realmente usen Supabase.
export const supabase = createClient(
  SUPABASE_URL || "https://placeholder.supabase.co",
  SUPABASE_ANON || "placeholder-anon-key"
);
