import { useState } from "react";

import { PageHeader } from "../../components/layout/PageHeader";
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  DataTable,
  ErrorMessage,
  FilterSelect,
  Loading,
  Modal,
  Pagination,
  SearchInput,
  StatusBadge,
  useToast,
} from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useAsync, useDebounced } from "../../hooks/useAsync";
import { formatDate } from "../../lib/format";
import { getErrorMessage } from "../../services/api";
import {
  assignRole,
  getAllUsers,
  reactivateUser,
  removeRole,
  suspendUser,
  type ManagedUser,
  type RoleName,
} from "../../services/adminService";
import PendingRegistrations from "./PendingRegistrations";

const ROLES: RoleName[] = ["Administrator", "Professor", "Student", "Guest"];
const PAGE_SIZE = 20;

export default function UserManagement() {
  const { user: me } = useAuth();
  const { notify } = useToast();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [role, setRole] = useState("");
  const [page, setPage] = useState(1);
  const [confirm, setConfirm] = useState<ManagedUser | null>(null);
  const [rolesFor, setRolesFor] = useState<ManagedUser | null>(null);
  const [busy, setBusy] = useState(false);
  const debouncedSearch = useDebounced(search);

  const { data, loading, error, reload } = useAsync(
    () => getAllUsers({ search: debouncedSearch, account_status: status, role_name: role, page, page_size: PAGE_SIZE }),
    [debouncedSearch, status, role, page]
  );

  const toggleSuspension = async (target: ManagedUser) => {
    setBusy(true);
    try {
      if (target.account_status === "suspended") {
        await reactivateUser(target.id);
        notify(`${target.username} reactivated. They must log in again.`);
      } else {
        await suspendUser(target.id);
        notify(`${target.username} suspended and signed out.`, "info");
      }
      setConfirm(null);
      await reload();
    } catch (err) {
      notify(getErrorMessage(err), "error");
    } finally {
      setBusy(false);
    }
  };

  const changeRole = async (target: ManagedUser, roleName: RoleName, add: boolean) => {
    setBusy(true);
    try {
      const result = add ? await assignRole(target.id, roleName) : await removeRole(target.id, roleName);
      setRolesFor({ ...target, roles: result.roles as RoleName[] });
      notify(`${add ? "Assigned" : "Removed"} ${roleName} ${add ? "to" : "from"} ${target.username}.`);
      await reload();
    } catch (err) {
      notify(getErrorMessage(err), "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="User Management" description="Approve registrations, manage roles and account status." />

      <PendingRegistrations onChange={reload} />

      <Card title="All users">
        <div className="mb-4 flex flex-wrap gap-3">
          <SearchInput
            value={search}
            onChange={(value) => {
              setSearch(value);
              setPage(1);
            }}
            placeholder="Search username, email or name…"
          />
          <FilterSelect
            label="Account status"
            value={status}
            allLabel="All statuses"
            onChange={(value) => {
              setStatus(value);
              setPage(1);
            }}
            options={["pending", "approved", "rejected", "suspended"].map((v) => ({ value: v, label: v }))}
          />
          <FilterSelect
            label="Role"
            value={role}
            allLabel="All roles"
            onChange={(value) => {
              setRole(value);
              setPage(1);
            }}
            options={ROLES.map((r) => ({ value: r, label: r }))}
          />
        </div>

        <ErrorMessage message={error} onRetry={reload} />
        {loading && !data ? (
          <Loading />
        ) : (
          data && (
            <>
              <DataTable
                rows={data.items}
                rowKey={(row) => row.id}
                empty="No users match these filters."
                columns={[
                  {
                    header: "User",
                    cell: (row) => (
                      <div>
                        <div className="font-medium">{row.full_name}</div>
                        <div className="text-xs text-fg-muted">@{row.username}</div>
                      </div>
                    ),
                  },
                  { header: "Email", cell: (row) => row.email },
                  {
                    header: "Roles",
                    cell: (row) =>
                      row.roles.length ? (
                        <div className="flex flex-wrap gap-1">
                          {row.roles.map((r) => (
                            <Badge key={r} tone="blue">
                              {r}
                            </Badge>
                          ))}
                        </div>
                      ) : (
                        <span className="text-fg-subtle">No role</span>
                      ),
                  },
                  { header: "Status", cell: (row) => <StatusBadge status={row.account_status} /> },
                  { header: "Registered", cell: (row) => formatDate(row.created_at) },
                  {
                    header: "Actions",
                    cell: (row) => (
                      <div className="flex flex-wrap gap-2">
                        {(row.account_status === "approved" || row.account_status === "suspended") && (
                          <>
                            <Button size="sm" variant="secondary" onClick={() => setRolesFor(row)}>
                              Roles
                            </Button>
                            {row.id !== me?.id && (
                              <Button
                                size="sm"
                                variant={row.account_status === "suspended" ? "success" : "danger"}
                                onClick={() => setConfirm(row)}
                              >
                                {row.account_status === "suspended" ? "Reactivate" : "Suspend"}
                              </Button>
                            )}
                          </>
                        )}
                      </div>
                    ),
                  },
                ]}
              />
              <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onChange={setPage} />
            </>
          )
        )}
      </Card>

      <ConfirmDialog
        open={confirm !== null}
        title={confirm?.account_status === "suspended" ? "Reactivate account" : "Suspend account"}
        message={
          confirm?.account_status === "suspended"
            ? `Reactivate ${confirm?.username}? They will need to log in again.`
            : `Suspend ${confirm?.username}? All of their sessions end immediately.`
        }
        confirmLabel={confirm?.account_status === "suspended" ? "Reactivate" : "Suspend"}
        danger={confirm?.account_status !== "suspended"}
        busy={busy}
        onConfirm={() => confirm && void toggleSuspension(confirm)}
        onCancel={() => setConfirm(null)}
      />

      <Modal open={rolesFor !== null} title={`Roles for @${rolesFor?.username ?? ""}`} onClose={() => setRolesFor(null)}>
        <p className="text-sm text-fg-muted">
          A user keeps at least one role. You cannot remove your own Administrator role, and the last active
          administrator is protected.
        </p>
        <ul className="divide-y divide-line">
          {ROLES.map((roleName) => {
            const has = rolesFor?.roles.includes(roleName) ?? false;
            return (
              <li key={roleName} className="flex items-center justify-between py-2 text-sm">
                <span>{roleName}</span>
                <Button
                  size="sm"
                  variant={has ? "secondary" : "primary"}
                  disabled={busy}
                  onClick={() => rolesFor && void changeRole(rolesFor, roleName, !has)}
                >
                  {has ? "Remove" : "Assign"}
                </Button>
              </li>
            );
          })}
        </ul>
      </Modal>
    </div>
  );
}
