import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function Layout() {
  return (
    <div className="flex flex-col md:flex-row min-h-screen" style={{ background: "#0D1117" }}>
      <Sidebar />
      <main className="flex-1 min-w-0 md:h-screen md:overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
