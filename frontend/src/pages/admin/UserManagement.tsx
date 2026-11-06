import { useCallback, useEffect, useState } from "react";
import axios from "axios";

import {
  getAllUsers,
  suspendUser,
  reactivateUser,
} from "../../services/adminService";

import type {
  ManagedUser,
  UserFilters,
} from "../../services/adminService";

import "./UserManagement.css";

export default function UserManagement() {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [filters, setFilters] = useState<UserFilters>({
    search: "",
    account_status: "",
    role_name: "",
  });

  const loadUsers = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const activeFilters: UserFilters = {};

      if (filters.search?.trim()) {
        activeFilters.search = filters.search.trim();
      }

      if (filters.account_status) {
        activeFilters.account_status = filters.account_status;
      }

      if (filters.role_name) {
        activeFilters.role_name = filters.role_name;
      }

      const data = await getAllUsers(activeFilters);
      setUsers(data);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(
          err.response?.data?.detail ||
          "Unable to retrieve users."
        );
      } else {
        setError("An unexpected error occurred.");
      }
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleFilterChange = (
    field: keyof UserFilters,
    value: string
  ) => {
    setFilters((previous) => ({
      ...previous,
      [field]: value,
    }));
  };

  const handleAccountAction = async (
    user: ManagedUser
  ) => {
    const isSuspended = user.account_status === "suspended";

    const confirmed = window.confirm(
      isSuspended
        ? `Reactivate ${user.username}'s account?`
        : `Suspend ${user.username}'s account?`
    );

    if (!confirmed) return;

    try {
      setProcessingId(user.id);
      setError("");
      setMessage("");

      if (isSuspended) {
        await reactivateUser(user.id);
        setMessage(`${user.username} has been reactivated.`);
      } else {
        await suspendUser(user.id);
        setMessage(`${user.username} has been suspended.`);
      }

      await loadUsers();
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(
          err.response?.data?.detail ||
          "The account action failed."
        );
      } else {
        setError("An unexpected error occurred.");
      }
    } finally {
      setProcessingId(null);
    }
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString();
  };

  return (
    <div className="user-management-page">
      <header className="user-management-header">
        <div>
          <h1>User Management</h1>
          <p>Manage registered Prism Desk accounts.</p>
        </div>

        <button
          className="refresh-users-button"
          onClick={loadUsers}
          disabled={loading}
        >
          Refresh
        </button>
      </header>

      <section className="user-management-stats">
        <div className="user-stat-card">
          <span>Total Users</span>
          <strong>{users.length}</strong>
        </div>

        <div className="user-stat-card">
          <span>Approved</span>
          <strong>
            {users.filter(
              (user) => user.account_status === "approved"
            ).length}
          </strong>
        </div>

        <div className="user-stat-card">
          <span>Pending</span>
          <strong>
            {users.filter(
              (user) => user.account_status === "pending"
            ).length}
          </strong>
        </div>

        <div className="user-stat-card">
          <span>Suspended</span>
          <strong>
            {users.filter(
              (user) => user.account_status === "suspended"
            ).length}
          </strong>
        </div>
      </section>

      <section className="user-management-panel">
        <div className="user-filter-section">
          <input
            type="text"
            placeholder="Search username, email or name..."
            value={filters.search || ""}
            onChange={(event) =>
              handleFilterChange("search", event.target.value)
            }
          />

          <select
            value={filters.account_status || ""}
            onChange={(event) =>
              handleFilterChange("account_status", event.target.value)
            }
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="suspended">Suspended</option>
          </select>

          <select
            value={filters.role_name || ""}
            onChange={(event) =>
              handleFilterChange("role_name", event.target.value)
            }
          >
            <option value="">All Roles</option>
            <option value="Administrator">Administrator</option>
            <option value="Professor">Professor</option>
            <option value="Student">Student</option>
            <option value="Guest">Guest</option>
          </select>
        </div>

        {message && (
          <div className="user-success-message">
            {message}
          </div>
        )}

        {error && (
          <div className="user-error-message">
            {error}
          </div>
        )}

        <div className="user-table-wrapper">
          <table className="user-management-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Registered</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="user-table-message">
                    Loading users...
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="user-table-message">
                    No users found.
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.id}>
                    <td>
                      <div className="user-name-cell">
                        <strong>{user.full_name}</strong>
                        <span>@{user.username}</span>
                      </div>
                    </td>

                    <td>{user.email}</td>

                    <td>
                      {user.roles.length > 0
                        ? user.roles.join(", ")
                        : "No role assigned"}
                    </td>

                    <td>
                      <span
                        className={`user-status-badge ${user.account_status}`}
                      >
                        {user.account_status}
                      </span>
                    </td>

                    <td>{formatDate(user.created_at)}</td>

                    <td>
                      {user.account_status === "approved" ||
                      user.account_status === "suspended" ? (
                        <button
                          className={
                            user.account_status === "suspended"
                              ? "user-action-button reactivate"
                              : "user-action-button suspend"
                          }
                          disabled={processingId === user.id}
                          onClick={() => handleAccountAction(user)}
                        >
                          {processingId === user.id
                            ? "Processing..."
                            : user.account_status === "suspended"
                              ? "Reactivate"
                              : "Suspend"}
                        </button>
                      ) : (
                        <span className="no-user-action">—</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="user-table-footer">
          Displaying {users.length} user(s)
        </div>
      </section>
    </div>
  );
}