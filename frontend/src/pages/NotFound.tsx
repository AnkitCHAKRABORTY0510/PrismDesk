import { Link } from "react-router";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-surface-muted text-center">
      <h1 className="text-3xl font-semibold text-fg">404 — Page not found</h1>
      <p className="text-sm text-fg-muted">The page you requested does not exist.</p>
      <Link to="/" className="text-sm text-link underline">Go to Prism Desk</Link>
    </div>
  );
}
