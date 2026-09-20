import { useEffect, useState, type ReactNode } from "react";

import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function AppShell({ pathname, children }: { pathname: string; children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => {
    if (!menuOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape") setMenuOpen(false); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [menuOpen]);
  return <div className="min-h-screen bg-app"><Sidebar pathname={pathname} open={menuOpen} onClose={() => setMenuOpen(false)} /><div className="min-h-screen lg:pl-64"><Topbar menuOpen={menuOpen} onMenu={() => setMenuOpen(true)} /><div>{children}</div></div></div>;
}
