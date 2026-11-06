import { Navigate, Outlet, useLocation } from "react-router";

import { useAuth } from "../../context/AuthContext";
import { can } from "../../lib/permissions";
import { Loading } from "../ui";

interface ProtectedRouteProps {
  allowedRoles?: string[];
  capability?: string;
}

// Client-side route guard. It improves navigation only; the API
// enforces every permission independently.
export default function ProtectedRoute({ allowedRoles, capability }: ProtectedRouteProps) {
  const { user, loading, isAuthenticated } = useAuth();
  const location = useLocation();

  // Wait until the existing session is verified.
  if (loading) {
    return <Loading label="Checking authentication…" />;
  }

  // Redirect unauthenticated users to login, remembering the target.
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  const roleAllowed = !allowedRoles || user.roles.some((role) => allowedRoles.includes(role));
  const capabilityAllowed = !capability || can(user, capability);

  if (!roleAllowed || !capabilityAllowed) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <Outlet />;
}
