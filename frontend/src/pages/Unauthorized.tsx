import { Link } from "react-router";

export default function Unauthorized() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-slate-50 text-center">
      <h1 className="text-3xl font-semibold text-slate-800">403 — Access denied</h1>
      <p className="text-sm text-slate-500">You do not have permission to access this page.</p>
      <Link to="/dashboard" className="text-sm text-brand underline">Return to your dashboard</Link>
    </div>
  );
}
