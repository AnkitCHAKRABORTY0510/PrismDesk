import { Link } from "react-router";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-slate-50 text-center">
      <h1 className="text-3xl font-semibold text-slate-800">404 — Page not found</h1>
      <p className="text-sm text-slate-500">The page you requested does not exist.</p>
      <Link to="/" className="text-sm text-brand underline">Go to Prism Desk</Link>
    </div>
  );
}
