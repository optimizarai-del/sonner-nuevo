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
import Login from "./pages/Login";

function RequireAuth({ children }) {
  const token = localStorage.getItem("sonner_token");
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index               element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard"    element={<Dashboard />} />
          <Route path="crm"          element={<Crm />} />
          <Route path="chat"         element={<Chat />} />
          <Route path="whatsapp"     element={<Whatsapp />} />
          <Route path="contratos"    element={<Contratos />} />
          <Route path="analista"     element={<Analista />} />
          <Route path="telegram"     element={<Telegram />} />
          <Route path="configuracion" element={<Configuracion />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
