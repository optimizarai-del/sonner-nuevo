/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // SNR brand — azul eléctrico sobre negro naval
        snr: {
          50:  "#e8eeff",
          100: "#c5d4ff",
          200: "#9ab6ff",
          300: "#6b92ff",
          400: "#4a76f5",
          500: "#2B6BF3",   // azul principal del logo
          600: "#1e56d4",
          700: "#1742ab",
          800: "#112f82",
          900: "#0c2060",
        },
        surface: {
          DEFAULT: "#0D1117",   // fondo negro naval
          card:    "#161B22",   // tarjetas
          hover:   "#1C2230",
          border:  "#21262D",
          muted:   "#30363D",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
