import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router";
import axios from "axios";

import { useAuth } from "../../context/AuthContext";
import "./Login.css";

// Users without any role cannot use the application.
function getDashboardPath(roles: string[]): string | null {
  return roles.length > 0 ? "/dashboard" : null;
}

interface LocationState {
  from?: { pathname: string; search?: string };
}

// Return to the page that required login, but never to the auth pages.
function redirectTarget(state: unknown, fallback: string): string {
  const from = (state as LocationState | null)?.from;
  if (!from || ["/login", "/register", "/"].includes(from.pathname)) {
    return fallback;
  }
  return from.pathname + (from.search ?? "");
}

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, user, loading, isAuthenticated } = useAuth();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    setError("");
    setSubmitting(true);

    try {
      const authenticatedUser = await login({
        identifier: identifier.trim(),
        password,
      });

      const dashboard = getDashboardPath(authenticatedUser.roles);

      if (!dashboard) {
        setError("Your account does not have an assigned application role.");
        return;
      }

      navigate(redirectTarget(location.state, dashboard), { replace: true });
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;

        setError(
          typeof detail === "string"
            ? detail
            : "Unable to log in. Please try again."
        );
      } else {
        setError("An unexpected error occurred.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="login-loading">Checking your session...</div>;
  }

  // Redirect users who already have an active session (declaratively,
  // not by navigating during render).
  if (isAuthenticated && user && getDashboardPath(user.roles)) {
    return <Navigate to={redirectTarget(location.state, "/dashboard")} replace />;
  }

  return (
    <div className="login-page">
      <div className="login-card">

        <div className="login-brand">
          <div className="login-logo">P</div>
          <h1>Prism Desk</h1>
          <p>One Lab. Multiple Projects. Connected Research.</p>
        </div>

        <div className="login-heading">
          <h2>Welcome back</h2>
          <p>Sign in to access your research workspace.</p>
        </div>

        <form onSubmit={handleSubmit}>

          <div className="login-field">
            <label htmlFor="identifier">
              Username or Email
            </label>

            <input
              id="identifier"
              type="text"
              placeholder="Enter username or email"
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              autoComplete="username"
              required
            />
          </div>

          <div className="login-field">
            <label htmlFor="password">
              Password
            </label>

            <div className="password-wrapper">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
              />

              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          {error && (
            <div className="login-error" role="alert">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="login-button"
            disabled={submitting}
          >
            {submitting ? "Signing in..." : "Sign In"}
          </button>

        </form>

        <div className="login-footer">
          <p>
            Don't have an account?{" "}
            <Link to="/register">Create an account</Link>
          </p>
        </div>

      </div>

      <div className="login-copyright">
        PRISM Laboratory | Prism Desk
      </div>
    </div>
  );
}