import { useCallback, useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router";
import {
  Bell,
  BookOpen,
  CalendarDays,
  FolderKanban,
  LayoutDashboard,
  Library,
  ListChecks,
  LogOut,
  Megaphone,
  Menu,
  NotebookPen,
  PanelLeftClose,
  PanelLeftOpen,
  ScrollText,
  Settings,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";

import { ThemeToggle } from "../ui/ThemeToggle";
import { useAuth } from "../../context/AuthContext";
import { navigationFor, primaryRole } from "../../lib/permissions";
import { Breadcrumbs } from "./Breadcrumbs";
import { ReminderWatcher } from "../../pages/handbook/ReminderWatcher";

const ICONS: Record<string, LucideIcon> = {
  "/dashboard": LayoutDashboard,
  "/projects": FolderKanban,
  "/research": BookOpen,
  "/tasks": ListChecks,
  "/handbook": NotebookPen,
  "/conferences": CalendarDays,
  "/journals": Library,
  "/admin/users": Users,
  "/admin/audit": ScrollText,
  "/admin/announcements": Megaphone,
  "/admin/settings": Settings,
  "/settings/notifications": Bell,
};

const RAIL_STORAGE_KEY = "prismdesk-rail-expanded";

function readRailExpanded(): boolean {
  try {
    return window.localStorage.getItem(RAIL_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

/*
 * Responsive shell:
 *  - < md:  top bar with a hamburger that opens an off-canvas drawer.
 *  - md–lg: a collapsible icon rail (expandable to full width).
 *  - ≥ lg:  a fixed full-width sidebar.
 * The sidebar is a single <aside> in every mode, always a dark navy brand panel.
 */
export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [railExpanded, setRailExpanded] = useState(readRailExpanded);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  const items = navigationFor(user);
  const sections = ["Workspace", "Administration", "Account"] as const;

  const closeMenu = useCallback(() => {
    setMenuOpen(false);
    menuButtonRef.current?.focus();
  }, []);

  // Close the drawer when the route changes.
  const [lastPath, setLastPath] = useState(location.pathname);
  if (lastPath !== location.pathname) {
    setLastPath(location.pathname);
    setMenuOpen(false);
  }

  // Drawer: focus the close button, close on Escape, lock page scroll.
  useEffect(() => {
    if (!menuOpen) return;
    closeButtonRef.current?.focus();
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeMenu();
    };
    window.addEventListener("keydown", handler);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", handler);
      document.body.style.overflow = previousOverflow;
    };
  }, [menuOpen, closeMenu]);

  const toggleRail = () => {
    setRailExpanded((current) => {
      const next = !current;
      try {
        window.localStorage.setItem(RAIL_STORAGE_KEY, next ? "1" : "0");
      } catch {
        // Not persisted.
      }
      return next;
    });
  };

  const handleLogout = async () => {
    await logout().catch(() => undefined);
    navigate("/login", { replace: true });
  };

  // On tablets (md–lg) the rail hides text unless expanded.
  const railText = railExpanded ? "" : "md:max-lg:sr-only";
  const railHide = railExpanded ? "" : "md:max-lg:hidden";
  const railWidth = railExpanded ? "md:w-64" : "md:w-[4.5rem]";

  return (
    <div className="flex min-h-svh bg-canvas font-sans text-fg">
      <aside
        id="app-sidebar"
        aria-label="Main navigation"
        className={`fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] flex-col border-r border-white/[0.06] bg-navy text-slate-100 shadow-2xl transition-[transform,width] duration-200 ease-out md:sticky md:top-0 md:z-30 md:h-svh md:max-w-none md:translate-x-0 md:shadow-none md:visible lg:w-64 ${railWidth} ${
          menuOpen ? "translate-x-0" : "-translate-x-full max-md:invisible max-md:transition-[transform,visibility]"
        }`}
      >
        {/* Prism glow behind the logo */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-[radial-gradient(ellipse_at_top,rgba(30,155,255,0.22),transparent_70%)]"
        />

        <div className={`relative flex items-center gap-2 px-4 pb-4 pt-5 ${railExpanded ? "" : "md:max-lg:justify-center md:max-lg:px-2"}`}>
          <Link
            to="/dashboard"
            className="flex min-w-0 flex-1 items-center rounded-lg"
            aria-label="PrismDesk home"
          >
            <img
              src="/brand/prism-logo.png"
              alt="PRISM Lab"
              width={1200}
              height={405}
              className={`h-auto w-full max-w-[200px] select-none ${railHide}`}
            />
            <img
              src="/brand/prism-mark.png"
              alt=""
              width={40}
              height={40}
              className={`hidden h-10 w-10 select-none ${railExpanded ? "" : "md:max-lg:block"}`}
            />
          </Link>
          <button
            ref={closeButtonRef}
            type="button"
            aria-label="Close navigation"
            onClick={closeMenu}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-300 hover:bg-white/10 hover:text-white md:hidden"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        <div className={`relative mx-4 mb-4 px-1 ${railHide}`}>
          <div className="text-sm font-semibold tracking-wide text-white">PrismDesk</div>
          <div className="text-[11px] leading-snug text-slate-400">Research workspace</div>
        </div>

        <nav className="relative flex-1 space-y-5 overflow-y-auto overflow-x-hidden px-3 pb-4">
          {sections.map((section) => {
            const sectionItems = items.filter((item) => item.section === section);
            if (sectionItems.length === 0) return null;
            return (
              <div key={section}>
                <div className={`mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500 ${railText}`}>
                  {section}
                </div>
                <ul className="space-y-0.5">
                  {sectionItems.map((item) => {
                    const Icon = ICONS[item.to] ?? LayoutDashboard;
                    return (
                      <li key={item.to}>
                        <NavLink
                          to={item.to}
                          title={item.label}
                          onClick={() => setMenuOpen(false)}
                          className={({ isActive }) =>
                            `group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors focus-visible:outline-sky-400 ${
                              railExpanded ? "" : "md:max-lg:justify-center md:max-lg:px-0"
                            } ${
                              isActive
                                ? "bg-white/10 font-medium text-white"
                                : "text-slate-300 hover:bg-white/5 hover:text-white"
                            }`
                          }
                        >
                          {({ isActive }) => (
                            <>
                              {isActive && (
                                <span
                                  aria-hidden="true"
                                  className="absolute inset-y-1.5 left-0 w-[2px] rounded-full bg-[#4c9bff]"
                                />
                              )}
                              <Icon
                                className={`h-[18px] w-[18px] shrink-0 ${isActive ? "text-sky-300" : "text-slate-400 group-hover:text-slate-200"}`}
                                aria-hidden="true"
                              />
                              <span className={`truncate ${railText}`}>{item.label}</span>
                            </>
                          )}
                        </NavLink>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </nav>

        <div className="relative border-t border-white/10 p-3">
          <div className={`mb-2 flex items-center gap-3 px-2 ${railExpanded ? "" : "md:max-lg:justify-center md:max-lg:px-0"}`}>
            <span
              aria-hidden="true"
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-sky-400 to-blue-700 text-xs font-semibold text-white"
            >
              {(user?.full_name || user?.username || "?").charAt(0).toUpperCase()}
            </span>
            <div className={`min-w-0 text-sm ${railHide}`}>
              <div className="truncate font-medium text-white">{user?.full_name}</div>
              <div className="truncate text-xs text-slate-400">{user?.roles.join(" · ")}</div>
            </div>
          </div>
          <button
            type="button"
            onClick={toggleRail}
            aria-label={railExpanded ? "Collapse sidebar" : "Expand sidebar"}
            aria-expanded={railExpanded}
            aria-controls="app-sidebar"
            className="hidden h-9 w-full items-center justify-center gap-2 rounded-lg text-sm text-slate-300 hover:bg-white/10 hover:text-white md:max-lg:flex"
          >
            {railExpanded ? <PanelLeftClose className="h-4 w-4" aria-hidden="true" /> : <PanelLeftOpen className="h-4 w-4" aria-hidden="true" />}
            {railExpanded && <span>Collapse</span>}
          </button>
        </div>
      </aside>

      {menuOpen && (
        <div
          aria-hidden="true"
          className="fixed inset-0 z-40 bg-[var(--overlay)] backdrop-blur-[1px] animate-in fade-in-0 md:hidden"
          onClick={closeMenu}
        />
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 border-b border-line bg-surface/85 backdrop-blur supports-[backdrop-filter]:bg-surface/75">
          <div className="flex h-14 items-center justify-between gap-3 px-4 lg:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <button
                ref={menuButtonRef}
                type="button"
                aria-label="Open navigation"
                aria-expanded={menuOpen}
                aria-controls="app-sidebar"
                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-line text-fg-soft hover:bg-surface-muted hover:text-fg md:hidden"
                onClick={() => setMenuOpen(true)}
              >
                <Menu className="h-5 w-5" aria-hidden="true" />
              </button>
              <Link to="/dashboard" className="flex shrink-0 items-center gap-2 rounded-lg md:hidden" aria-label="PrismDesk home">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-navy">
                  <img src="/brand/prism-mark.png" alt="" width={28} height={28} className="h-7 w-7" />
                </span>
                <span className="text-sm font-semibold tracking-tight text-fg">PrismDesk</span>
              </Link>
              <div className="hidden min-w-0 md:block">
                <Breadcrumbs pathname={location.pathname} />
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2 text-sm">
              <span className="hidden max-w-[16rem] truncate text-fg-muted lg:inline">
                {user?.username} · {primaryRole(user)}
              </span>
              <ThemeToggle />
              <button
                type="button"
                onClick={() => void handleLogout()}
                className="inline-flex h-9 items-center gap-2 rounded-lg border border-line bg-surface px-2.5 text-fg-soft transition-colors hover:bg-surface-muted hover:text-fg sm:px-3"
              >
                <LogOut className="h-4 w-4" aria-hidden="true" />
                <span className="max-sm:sr-only">Log out</span>
              </button>
            </div>
          </div>
          <div aria-hidden="true" className="h-0.5 bg-rainbow opacity-70" />
        </header>

        <main className="mx-auto w-full min-w-0 max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <div className="mb-4 md:hidden">
            <Breadcrumbs pathname={location.pathname} />
          </div>
          <Outlet />
          <ReminderWatcher />
        </main>

        <footer className="px-4 py-4 text-center text-xs text-fg-subtle sm:px-8">
          PrismDesk · PRISM Lab · One Lab. Multiple Projects. Connected Research.
        </footer>
      </div>
    </div>
  );
}
