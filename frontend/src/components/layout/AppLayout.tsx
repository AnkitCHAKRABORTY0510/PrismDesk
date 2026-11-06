import { useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router";

import { useAuth } from "../../context/AuthContext";
import { navigationFor, primaryRole } from "../../lib/permissions";
import { Breadcrumbs } from "./Breadcrumbs";

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  const items = navigationFor(user);
  const sections = ["Workspace", "Administration", "Account"] as const;

  const handleLogout = async () => {
    await logout().catch(() => undefined);
    navigate("/login", { replace: true });
  };

  return (
    <div className="flex min-h-screen bg-slate-50 font-sans text-slate-800">
      <aside
        aria-label="Main navigation"
        className={`${menuOpen ? "flex" : "hidden"} fixed inset-y-0 left-0 z-40 w-64 flex-col bg-navy px-4 py-6 text-white lg:static lg:flex`}
      >
        <Link to="/dashboard" className="mb-8 flex items-center gap-3 px-2" onClick={() => setMenuOpen(false)}>
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-white text-xl font-extrabold text-navy">P</span>
          <span>
            <span className="block text-base font-semibold">Prism Desk</span>
            <span className="block text-xs text-slate-300">PRISM Laboratory</span>
          </span>
        </Link>

        <nav className="flex-1 space-y-6 overflow-y-auto">
          {sections.map((section) => {
            const sectionItems = items.filter((item) => item.section === section);
            if (sectionItems.length === 0) return null;
            return (
              <div key={section}>
                <div className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">{section}</div>
                <ul className="space-y-1">
                  {sectionItems.map((item) => (
                    <li key={item.to}>
                      <NavLink
                        to={item.to}
                        onClick={() => setMenuOpen(false)}
                        className={({ isActive }) =>
                          `block rounded-lg px-3 py-2 text-sm ${
                            isActive ? "bg-white/15 font-medium text-white" : "text-slate-300 hover:bg-white/10 hover:text-white"
                          }`
                        }
                      >
                        {item.label}
                      </NavLink>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </nav>

        <div className="mt-6 border-t border-white/10 pt-4 text-sm">
          <div className="font-medium">{user?.full_name}</div>
          <div className="text-xs text-slate-400">{user?.roles.join(" · ")}</div>
        </div>
      </aside>

      {menuOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-30 bg-slate-900/30 lg:hidden"
          onClick={() => setMenuOpen(false)}
        />
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-slate-200 bg-white px-4 py-3 lg:px-8">
          <div className="flex items-center gap-3">
            <button
              type="button"
              aria-label="Open navigation"
              className="rounded-md border border-slate-300 px-2 py-1 text-sm lg:hidden"
              onClick={() => setMenuOpen(true)}
            >
              ☰
            </button>
            <Breadcrumbs pathname={location.pathname} />
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="hidden text-slate-500 sm:inline">
              {user?.username} · {primaryRole(user)}
            </span>
            <button
              type="button"
              onClick={() => void handleLogout()}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-slate-700 hover:bg-slate-50"
            >
              Log out
            </button>
          </div>
        </header>

        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 lg:px-8">
          <Outlet />
        </main>

        <footer className="px-8 py-4 text-center text-xs text-slate-400">
          Prism Desk · One Lab. Multiple Projects. Connected Research.
        </footer>
      </div>
    </div>
  );
}
