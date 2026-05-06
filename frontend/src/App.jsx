import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout/Layout";
import Dashboard from "./pages/Dashboard";
import Chat from "./pages/Chat";
import Mensajes from "./pages/Mensajes";
import Analista from "./pages/Analista";
import Contratos from "./pages/Contratos";
import Telegram from "./pages/Telegram";
import Admin from "./pages/Admin";
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
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="chat"      element={<Chat />} />
          <Route path="mensajes"  element={<Mensajes />} />
          <Route path="analista"  element={<Analista />} />
          <Route path="contratos" element={<Contratos />} />
          <Route path="telegram"  element={<Telegram />} />
          <Route path="admin"     element={<Admin />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
