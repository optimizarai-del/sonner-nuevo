import { useState } from "react";
import { useNavigate } from "react-router-dom";

const ADMIN_USER = import.meta.env.VITE_ADMIN_USERNAME || "admin";
const ADMIN_PASS = import.meta.env.VITE_ADMIN_PASSWORD || "sonner2026";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const navigate = useNavigate();

  function handleSubmit(e) {
    e.preventDefault();
    if (username.trim() === ADMIN_USER && password === ADMIN_PASS) {
      localStorage.setItem("sonner_token", "authenticated");
      navigate("/dashboard");
    } else {
      setError("Usuario o contraseña incorrectos");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: "#0D1117" }}>
      <div className="w-full max-w-sm">

        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5 text-white font-black text-xl tracking-wider"
            style={{
              background: "linear-gradient(135deg, #2B6BF3 0%, #1742ab 100%)",
              boxShadow: "0 0 40px #2B6BF344",
            }}
          >
            SNR
          </div>
          <h1 className="text-xl font-bold text-white">Sonner</h1>
          <p className="text-xs mt-1" style={{ color: "#484F58" }}>SONIDO E ILUMINACIÓN</p>
        </div>

        {/* Card */}
        <div className="rounded-2xl p-6 space-y-4" style={{ background: "#161B22", border: "1px solid #21262D" }}>
          <p className="text-xs font-medium text-center" style={{ color: "#8B949E" }}>Panel de gestión interno</p>

          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: "#8B949E" }}>Usuario</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input"
                placeholder="admin"
                required
                autoComplete="username"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: "#8B949E" }}>Contraseña</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder="••••••••"
                required
                autoComplete="current-password"
              />
            </div>
            {error && (
              <p className="text-xs text-red-400 text-center">{error}</p>
            )}
            <button
              type="submit"
              className="btn-primary w-full text-sm py-3 mt-2"
              style={{ boxShadow: "0 0 20px #2B6BF333" }}
            >
              Entrar
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
