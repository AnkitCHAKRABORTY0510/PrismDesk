import { useState, type FormEvent } from "react";

import { PageHeader } from "../../components/layout/PageHeader";
import {
  Alert,
  Button,
  Card,
  DataTable,
  ErrorMessage,
  Field,
  FilterSelect,
  Input,
  Loading,
  Pagination,
  StatusBadge,
  Textarea,
  useToast,
} from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { formatDateTime, humanize } from "../../lib/format";
import { getErrorMessage } from "../../services/api";
import { notificationQueue, retryNotification, sendAnnouncement } from "../../services/notificationService";

export default function Announcements() {
  const { notify } = useToast();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [toChannel, setToChannel] = useState(true);
  const [toAll, setToAll] = useState(false);
  const [sending, setSending] = useState(false);
  const [formError, setFormError] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const queue = useAsync(() => notificationQueue({ status, page, page_size: 20 }), [status, page]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setFormError("");
    if (!toChannel && !toAll) {
      setFormError("Choose at least one destination.");
      return;
    }
    setSending(true);
    try {
      const result = await sendAnnouncement({ title, body, post_to_channel: toChannel, direct_message_all: toAll });
      notify(`${result.queued} Discord message(s) queued.`);
      if (toChannel && !result.channel_configured) {
        notify("No announcement channel is configured on the server.", "info");
      }
      setTitle("");
      setBody("");
      await queue.reload();
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Announcements & Notification Queue"
        description="Announcements are delivered through Discord only. Prism Desk has no internal chat."
      />
      <Card title="New announcement">
        <form onSubmit={submit} className="space-y-4">
          <Field label="Title">{(id) => <Input id={id} value={title} maxLength={200} required onChange={(e) => setTitle(e.target.value)} />}</Field>
          <Field label="Message">
            {(id) => <Textarea id={id} value={body} maxLength={1800} required onChange={(e) => setBody(e.target.value)} />}
          </Field>
          <div className="flex flex-wrap gap-6 text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={toChannel} onChange={(e) => setToChannel(e.target.checked)} />
              Post to the lab announcement channel
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={toAll} onChange={(e) => setToAll(e.target.checked)} />
              Direct-message every linked user
            </label>
          </div>
          {formError && <Alert>{formError}</Alert>}
          <Button type="submit" loading={sending}>
            Queue announcement
          </Button>
        </form>
      </Card>

      <Card
        title="Delivery queue"
        actions={
          <FilterSelect
            label="Delivery status"
            value={status}
            allLabel="All statuses"
            onChange={(value) => {
              setStatus(value);
              setPage(1);
            }}
            options={["pending", "processing", "sent", "failed", "retry_scheduled"].map((v) => ({ value: v, label: humanize(v) }))}
          />
        }
      >
        <ErrorMessage message={queue.error} onRetry={queue.reload} />
        {queue.loading && !queue.data ? (
          <Loading />
        ) : (
          queue.data && (
            <>
              <DataTable
                rows={queue.data.items}
                rowKey={(row) => row.id}
                columns={[
                  { header: "Created", cell: (row) => formatDateTime(row.created_at) },
                  { header: "Event", cell: (row) => humanize(row.event_type) },
                  { header: "Title", cell: (row) => row.title },
                  { header: "Status", cell: (row) => <StatusBadge status={row.status} /> },
                  { header: "Attempts", cell: (row) => `${row.attempt_count}/${row.max_attempts}` },
                  { header: "Last error", cell: (row) => <span className="text-xs text-slate-500">{row.last_error ?? "—"}</span> },
                  {
                    header: "",
                    cell: (row) =>
                      row.status === "failed" ? (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={async () => {
                            try {
                              await retryNotification(row.id);
                              await queue.reload();
                            } catch (err) {
                              notify(getErrorMessage(err), "error");
                            }
                          }}
                        >
                          Retry
                        </Button>
                      ) : null,
                  },
                ]}
              />
              <Pagination page={page} pageSize={20} total={queue.data.total} onChange={setPage} />
            </>
          )
        )}
      </Card>
    </div>
  );
}
