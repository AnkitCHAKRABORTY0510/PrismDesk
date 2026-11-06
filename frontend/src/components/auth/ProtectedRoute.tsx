import {
  Navigate,
  Outlet,
  useLocation,
} from "react-router";

import { useAuth } from "../../context/AuthContext";

interface ProtectedRouteProps {
  allowedRoles: string[];
}

export default function ProtectedRoute({
  allowedRoles,
}: ProtectedRouteProps) {
  const { user, loading, isAuthenticated } = useAuth();
  const location = useLocation();

  // Wait until the existing session is verified.
  if (loading) {
    return <p>Checking authentication...</p>;
  }

  // Redirect unauthenticated users to login.
  if (!isAuthenticated || !user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location }}
      />
    );
  }

  // Check whether the user has an allowed role.
  const hasPermission = user.roles.some((role) =>
    allowedRoles.includes(role)
  );

  // Redirect users who do not have the required role.
  if (!hasPermission) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <Outlet />;
}

