import { Link } from "react-router";

export default function Unauthorized() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-surface-muted text-center">
      <h1 className="text-3xl font-semibold text-fg">403 — Access denied</h1>
      <p className="text-sm text-fg-muted">You do not have permission to access this page.</p>
      <Link to="/dashboard" className="text-sm text-link underline">Return to your dashboard</Link>
    </div>
  );
}
