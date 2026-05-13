import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout/Layout";
import Dashboard from "./pages/Dashboard";
import Chat from "./pages/Chat";
import Crm from "./pages/Crm";
import Whatsapp from "./pages/Whatsapp";
import Analista from "./pages/Analista";
import Contratos from "./pages/Contratos";
import Telegram from "./pages/Telegram";
import Configuracion from "./pages/Configuracion";
import Eventos from "./pages/Eventos";
import Materiales from "./pages/Materiales";
import Login from "./pages/Login";
import { isAuthenticated, hasRole } from "./utils/auth";

function RequireAuth({ children }) {
  return isAuthenticated() ? children : <Navigate to="/login" replace />;
}

function RequireRole({ roles, children }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  if (!hasRole(...roles))  return <Navigate to="/chat" replace />;  // fallback razonable
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>

          {/* Default según rol */}
          <Route index element={<DefaultRoute />} />

          {/* Solo admin */}
          <Route path="dashboard"     element={<RequireRole roles={["admin"]}><Dashboard /></RequireRole>} />
          <Route path="crm"           element={<RequireRole roles={["admin"]}><Crm /></RequireRole>} />
          <Route path="whatsapp"      element={<RequireRole roles={["admin"]}><Whatsapp /></RequireRole>} />
          <Route path="contratos"     element={<RequireRole roles={["admin"]}><Contratos /></RequireRole>} />
          <Route path="analista"      element={<RequireRole roles={["admin"]}><Analista /></RequireRole>} />
          <Route path="telegram"      element={<RequireRole roles={["admin"]}><Telegram /></RequireRole>} />
          <Route path="configuracion" element={<RequireRole roles={["admin"]}><Configuracion /></RequireRole>} />

          {/* Todos los roles */}
          <Route path="chat"          element={<Chat />} />
          <Route path="eventos"       element={<Eventos />} />
          <Route path="materiales"    element={<Materiales />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

function DefaultRoute() {
  // Admin → dashboard, otros → chat
  return hasRole("admin")
    ? <Navigate to="/dashboard" replace />
    : <Navigate to="/chat" replace />;
}
