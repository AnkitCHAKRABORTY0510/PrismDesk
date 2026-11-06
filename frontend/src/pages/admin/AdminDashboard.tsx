import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router";
import axios from "axios";

import { useAuth } from "../../context/AuthContext";

import {
  getPendingUsers,
  approveUser,
  rejectUser,
  type PendingUser,
} from "../../services/adminService";

import "./AdminDashboard.css";

type AssignableRole = "Student" | "Professor" | "Guest";

export default function AdminDashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [pendingUsers, setPendingUsers] = useState<PendingUser[]>([]);
  const [selectedRoles, setSelectedRoles] = useState<
    Record<string, AssignableRole>
  >({});
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadPendingUsers = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const users = await getPendingUsers();
      setPendingUsers(users);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(
          typeof err.response?.data?.detail === "string"
            ? err.response.data.detail
            : "Unable to load pending registrations."
        );
      } else {
        setError("Unable to load pending registrations.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadPendingUsers();
  }, [loadPendingUsers]);

  const handleRoleChange = (
    userId: string,
    role: AssignableRole
  ) => {
    setSelectedRoles((previous) => ({
      ...previous,
      [userId]: role,
    }));
  };

  const handleApprove = async (user: PendingUser) => {
    const role = selectedRoles[user.id] ?? "Student";

    const confirmed = window.confirm(
      `Approve ${user.username} as ${role}?`
    );

    if (!confirmed) return;

    setProcessingId(user.id);
    setError("");
    setSuccess("");

    try {
      const result = await approveUser(user.id, role);

      setSuccess(
        `${result.username} approved successfully as ${role}.`
      );

      await loadPendingUsers();
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(
          typeof err.response?.data?.detail === "string"
            ? err.response.data.detail
            : "Unable to approve this account."
        );
      } else {
        setError("Unable to approve this account.");
      }
    } finally {
      setProcessingId(null);
    }
  };

  const handleReject = async (user: PendingUser) => {
    const confirmed = window.confirm(
      `Are you sure you want to reject ${user.username}?`
    );

    if (!confirmed) return;

    setProcessingId(user.id);
    setError("");
    setSuccess("");

    try {
      const result = await rejectUser(user.id);

      setSuccess(`${result.username} has been rejected.`);

      await loadPendingUsers();
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(
          typeof err.response?.data?.detail === "string"
            ? err.response.data.detail
            : "Unable to reject this account."
        );
      } else {
        setError("Unable to reject this account.");
      }
    } finally {
      setProcessingId(null);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      navigate("/login", { replace: true });
    } catch {
      setError("Logout failed. Please try again.");
    }
  };

  return (
    <div className="admin-layout">

      <aside className="admin-sidebar">
        <div className="admin-brand">
          <div className="admin-brand-logo">P</div>

          <div>
            <h2>Prism Desk</h2>
            <span>PRISM Laboratory</span>
          </div>
        </div>

        <nav className="admin-navigation">

          <div className="admin-nav-label">
            ADMINISTRATION
          </div>

          <div
            className="admin-nav-item active"
            onClick={() => navigate("/admin/dashboard")}
          >
            Dashboard
          </div>

          <div
            className="admin-nav-item"
            onClick={() => navigate("/admin/users")}
          >
            User Management
          </div>

          <div className="admin-nav-item">
            Projects
          </div>

          <div className="admin-nav-item">
            Research Management
          </div>

        </nav>

        <div className="admin-sidebar-footer">
          <div className="admin-avatar">
            {user?.full_name?.charAt(0).toUpperCase() ?? "A"}
          </div>

          <div className="admin-user-info">
            <strong>{user?.full_name}</strong>
            <span>Administrator</span>
          </div>

          <button
            className="admin-logout"
            onClick={handleLogout}
          >
            Logout
          </button>
        </div>
      </aside>

      <main className="admin-main">

        <header className="admin-topbar">
          <div>
            <span className="admin-breadcrumb">
              Administration / User Management
            </span>

            <h1>Administrator Dashboard</h1>
          </div>

          <button
            className="admin-refresh-button"
            onClick={() => void loadPendingUsers()}
            disabled={loading}
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </header>

        <section className="admin-welcome">
          <div>
            <h2>Welcome, {user?.full_name}</h2>
            <p>
              Manage laboratory registrations and user access.
            </p>
          </div>
        </section>

        <section className="admin-stat-grid">

          <div className="admin-stat-card">
            <span>Pending Registrations</span>
            <strong>{pendingUsers.length}</strong>
            <small>Awaiting approval</small>
          </div>

          <div className="admin-stat-card">
            <span>Administrator</span>
            <strong>Active</strong>
            <small>Current account status</small>
          </div>

        </section>

        <section className="admin-content-card">

          <div className="admin-section-heading">
            <div>
              <h2>Pending Registrations</h2>
              <p>
                Review registrations and assign appropriate roles.
              </p>
            </div>

            <span className="pending-badge">
              {pendingUsers.length} Pending
            </span>
          </div>

          {error && (
            <div className="admin-alert error" role="alert">
              {error}
            </div>
          )}

          {success && (
            <div className="admin-alert success" role="status">
              {success}
            </div>
          )}

          {loading ? (
            <div className="admin-empty-state">
              Loading registrations...
            </div>
          ) : pendingUsers.length === 0 ? (
            <div className="admin-empty-state">
              <h3>No pending registrations</h3>
              <p>All registration requests have been processed.</p>
            </div>
          ) : (
            <div className="admin-table-wrapper">

              <table className="admin-table">

                <thead>
                  <tr>
                    <th>User</th>
                    <th>Email</th>
                    <th>Registered</th>
                    <th>Assign Role</th>
                    <th>Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {pendingUsers.map((pendingUser) => (
                    <tr key={pendingUser.id}>

                      <td>
                        <div className="admin-table-user">
                          <div className="admin-table-avatar">
                            {pendingUser.full_name
                              .charAt(0)
                              .toUpperCase()}
                          </div>

                          <div>
                            <strong>{pendingUser.full_name}</strong>
                            <span>@{pendingUser.username}</span>
                          </div>
                        </div>
                      </td>

                      <td>{pendingUser.email}</td>

                      <td>
                        {new Date(
                          pendingUser.created_at
                        ).toLocaleDateString()}
                      </td>

                      <td>
                        <select
                          value={
                            selectedRoles[pendingUser.id] ?? "Student"
                          }
                          onChange={(event) =>
                            handleRoleChange(
                              pendingUser.id,
                              event.target.value as AssignableRole
                            )
                          }
                          disabled={processingId === pendingUser.id}
                          className="admin-role-select"
                        >
                          <option value="Student">Student</option>
                          <option value="Professor">Professor</option>
                          <option value="Guest">Guest</option>
                        </select>
                      </td>

                      <td>
                        <div className="admin-action-buttons">

                          <button
                            className="approve-button"
                            onClick={() => void handleApprove(pendingUser)}
                            disabled={processingId === pendingUser.id}
                          >
                            {processingId === pendingUser.id
                              ? "Processing..."
                              : "Approve"}
                          </button>

                          <button
                            className="reject-button"
                            onClick={() => void handleReject(pendingUser)}
                            disabled={processingId === pendingUser.id}
                          >
                            Reject
                          </button>

                        </div>
                      </td>

                    </tr>
                  ))}
                </tbody>

              </table>

            </div>
          )}

        </section>

        <footer className="admin-footer">
          Prism Desk · PRISM Laboratory
        </footer>

      </main>
    </div>
  );
}
