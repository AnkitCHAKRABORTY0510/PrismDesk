import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import axios from "axios";

import { registerUser } from "../../services/authService";
import { AuthBrand, AuthThemeToggle } from "./AuthBrand";
import "./auth.css";

export default function Register() {
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    full_name: "",
    password: "",
    confirmPassword: "",
  });

  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    setError("");

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (formData.password.length < 12) {
      setError("Password must contain at least 12 characters.");
      return;
    }

    setSubmitting(true);

    try {
      await registerUser({
        username: formData.username.trim(),
        email: formData.email.trim(),
        full_name: formData.full_name.trim(),
        password: formData.password,
      });

      setSuccess(true);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;

        if (typeof detail === "string") {
          setError(detail);
        } else if (Array.isArray(detail)) {
          setError(
            detail.map((item) => item.msg).join(", ")
          );
        } else {
          setError("Registration failed. Please try again.");
        }
      } else {
        setError("An unexpected error occurred.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="auth-page">
        <AuthThemeToggle />
        <div className="auth-card auth-success">
          <AuthBrand />
          <div className="auth-body">

          <div className="auth-success-icon">✓</div>

          <h1>Registration Successful</h1>

          <p>
            Your Prism Desk account has been created successfully.
          </p>

          <div className="auth-approval">
            <strong>Waiting for Administrator Approval</strong>

            <p>
              Your account is currently pending approval.
              You will be able to log in after an administrator
              approves your registration.
            </p>
          </div>

          <Link to="/login" className="auth-button">
            Return to Login
          </Link>
          </div>

        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <AuthThemeToggle />

      <div className="auth-card">

        <AuthBrand />

        <div className="auth-body">
        <div className="auth-product">
          <h1>PrismDesk</h1>
          <p>One Lab. Multiple Projects. Connected Research.</p>
        </div>

        <div className="auth-heading">
          <h2>Create your account</h2>
          <p>Join the PRISM Laboratory research workspace.</p>
        </div>

        <form onSubmit={handleSubmit}>

          <div className="auth-field">
            <label htmlFor="full_name">Full Name</label>

            <input
              id="full_name"
              name="full_name"
              type="text"
              placeholder="Enter your full name"
              value={formData.full_name}
              onChange={handleChange}
              maxLength={150}
              required
            />
          </div>

          <div className="auth-field">
            <label htmlFor="username">Username</label>

            <input
              id="username"
              name="username"
              type="text"
              placeholder="Choose a username"
              value={formData.username}
              onChange={handleChange}
              minLength={3}
              maxLength={50}
              pattern="[A-Za-z0-9_.-]+"
              title="Use letters, numbers, underscores, dots, or hyphens."
              autoComplete="username"
              required
            />
          </div>

          <div className="auth-field">
            <label htmlFor="email">Email Address</label>

            <input
              id="email"
              name="email"
              type="email"
              placeholder="Enter your email"
              value={formData.email}
              onChange={handleChange}
              maxLength={255}
              autoComplete="email"
              required
            />
          </div>

          <div className="auth-field">
            <label htmlFor="password">Password</label>

            <div className="auth-password">
              <input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                placeholder="Create a password"
                value={formData.password}
                onChange={handleChange}
                minLength={12}
                maxLength={128}
                autoComplete="new-password"
                required
              />

              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="auth-password-toggle"
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>

            <small>Minimum 12 characters.</small>
          </div>

          <div className="auth-field">
            <label htmlFor="confirmPassword">
              Confirm Password
            </label>

            <input
              id="confirmPassword"
              name="confirmPassword"
              type={showPassword ? "text" : "password"}
              placeholder="Re-enter your password"
              value={formData.confirmPassword}
              onChange={handleChange}
              autoComplete="new-password"
              required
            />
          </div>

          {error && (
            <div className="auth-error" role="alert">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="auth-button"
            disabled={submitting}
          >
            {submitting ? "Creating Account..." : "Create Account"}
          </button>

        </form>

        <div className="auth-footer">
          Already have an account?{" "}
          <Link to="/login">Sign in</Link>
        </div>

        <div className="auth-notice">
          All new accounts require administrator approval.
        </div>
        </div>

      </div>

      <div className="auth-copyright">
        PRISM Lab · PrismDesk
      </div>

    </div>
  );
}