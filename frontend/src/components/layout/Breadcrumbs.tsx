import { Link } from "react-router";

const LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  projects: "Projects",
  research: "Research Library",
  tasks: "Tasks",
  handbook: "Handbook",
  conferences: "Conferences",
  admin: "Administration",
  users: "User Management",
  audit: "Audit Logs",
  announcements: "Announcements",
  settings: "Settings",
  notifications: "Notifications",
  papers: "Papers",
  entries: "Entries",
  new: "New",
};

const UUID = /^[0-9a-f-]{36}$/i;

export function Breadcrumbs({ pathname }: { pathname: string }) {
  const parts = pathname.split("/").filter(Boolean);

  return (
    <nav aria-label="Breadcrumb" className="text-sm text-slate-500">
      <ol className="flex flex-wrap items-center gap-1">
        {parts.map((part, index) => {
          const to = "/" + parts.slice(0, index + 1).join("/");
          const label = UUID.test(part) ? "Details" : LABELS[part] ?? part;
          const last = index === parts.length - 1;
          return (
            <li key={to} className="flex items-center gap-1">
              {index > 0 && <span aria-hidden="true">/</span>}
              {last || part === "admin" || part === "settings" ? (
                <span className={last ? "font-medium text-slate-700" : undefined}>{label}</span>
              ) : (
                <Link to={to} className="hover:text-slate-700">
                  {label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
