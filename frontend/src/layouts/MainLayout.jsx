import { Outlet } from "react-router-dom";
import Navbar from "./Navbar";

export default function MainLayout() {
  return (
    <div className="flex flex-col h-full w-full bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.18),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(59,130,246,0.16),transparent_28%),#020617] text-white">
      <Navbar />
      <main className="flex h-full w-full">
        <Outlet />
      </main>
    </div>
  );
}
