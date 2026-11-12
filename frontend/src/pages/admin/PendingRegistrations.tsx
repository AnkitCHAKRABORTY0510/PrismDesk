import { useState } from "react";

import { Button, Card, DataTable, EmptyState, ErrorMessage, Loading, Select, useToast } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { formatDate } from "../../lib/format";
import { getErrorMessage } from "../../services/api";
import { approveUser, getPendingUsers, rejectUser, type PendingUser } from "../../services/adminService";
import { ConfirmDialog } from "../../components/ui";

type AssignableRole = "Student" | "Professor" | "Guest";

// Approve or reject pending registrations (moved from the original
// administrator dashboard).
export default function PendingRegistrations({ onChange }: { onChange?: () => void }) {
  const { data, loading, error, reload } = useAsync(getPendingUsers, []);
  const [roles, setRoles] = useState<Record<string, AssignableRole>>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [rejecting, setRejecting] = useState<PendingUser | null>(null);
  const { notify } = useToast();

  const act = async (user: PendingUser, action: "approve" | "reject") => {
    setBusyId(user.id);
    try {
      if (action === "approve") {
        const role = roles[user.id] ?? "Student";
        await approveUser(user.id, role);
        notify(`${user.username} approved as ${role}.`);
      } else {
        await rejectUser(user.id);
        notify(`${user.username} was rejected.`, "info");
      }
      setRejecting(null);
      await reload();
      onChange?.();
    } catch (err) {
      notify(getErrorMessage(err), "error");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <Card title={`Pending registrations${data ? ` (${data.length})` : ""}`}>
      {loading && !data ? (
        <Loading />
      ) : error ? (
        <ErrorMessage message={error} onRetry={reload} />
      ) : !data || data.length === 0 ? (
        <EmptyState title="No pending registrations" description="All registration requests have been processed." />
      ) : (
        <DataTable
          rows={data}
          rowKey={(row) => row.id}
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
            { header: "Registered", cell: (row) => formatDate(row.created_at) },
            {
              header: "Assign role",
              cell: (row) => (
                <Select
                  aria-label={`Role for ${row.username}`}
                  value={roles[row.id] ?? "Student"}
                  onChange={(event) => setRoles({ ...roles, [row.id]: event.target.value as AssignableRole })}
                  disabled={busyId === row.id}
                >
                  <option value="Student">Student</option>
                  <option value="Professor">Professor</option>
                  <option value="Guest">Guest</option>
                </Select>
              ),
            },
            {
              header: "Actions",
              cell: (row) => (
                <div className="flex gap-2">
                  <Button size="sm" variant="success" loading={busyId === row.id} onClick={() => void act(row, "approve")}>
                    Approve
                  </Button>
                  <Button size="sm" variant="danger" disabled={busyId === row.id} onClick={() => setRejecting(row)}>
                    Reject
                  </Button>
                </div>
              ),
            },
          ]}
        />
      )}
      <ConfirmDialog
        open={rejecting !== null}
        title="Reject registration"
        message={`Reject ${rejecting?.full_name} (@${rejecting?.username})? They will not be able to log in.`}
        confirmLabel="Reject"
        danger
        busy={busyId !== null}
        onConfirm={() => rejecting && void act(rejecting, "reject")}
        onCancel={() => setRejecting(null)}
      />
    </Card>
  );
}
