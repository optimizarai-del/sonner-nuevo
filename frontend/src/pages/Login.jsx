import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import SonnerLogo from "../components/SonnerLogo";
import { login } from "../utils/auth";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username.trim(), password);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message || "Error de conexión");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: "#0D1117" }}>
      <div className="w-full max-w-sm">

        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <SonnerLogo variant="full" color="#fff" size={48} />
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
                disabled={loading}
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
                disabled={loading}
              />
            </div>
            {error && (
              <p className="text-xs text-red-400 text-center">{error}</p>
            )}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full text-sm py-3 mt-2 flex items-center justify-center gap-2 disabled:opacity-60"
              style={{ boxShadow: "0 0 20px #2B6BF333" }}
            >
              {loading ? <><Loader2 size={14} className="animate-spin" /> Entrando...</> : "Entrar"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
