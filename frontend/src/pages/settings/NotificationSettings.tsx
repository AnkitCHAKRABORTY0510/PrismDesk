import { useState } from "react";
import { useSearchParams } from "react-router";

import { PageHeader } from "../../components/layout/PageHeader";
import {
  Alert,
  Button,
  Card,
  DataTable,
  ErrorMessage,
  Loading,
  Pagination,
  StatusBadge,
  useToast,
} from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { formatDateTime, humanize } from "../../lib/format";
import { getErrorMessage } from "../../services/api";
import {
  discordStatus,
  getPreferences,
  myNotifications,
  savePreferences,
  startDiscordLink,
  unlinkDiscord,
  type Preference,
} from "../../services/notificationService";

const DESCRIPTIONS: Record<string, string> = {
  tasks: "Assignments, submissions, reviews and due-date reminders",
  projects: "New projects, membership changes and archival requests",
  conferences: "Upcoming conference submission deadlines",
  handbook: "Comments and replies on handbook entries",
  administrative: "Account approval and lab announcements",
};

const RESULT_MESSAGES: Record<string, { kind: "success" | "error" | "info"; text: string }> = {
  linked: { kind: "success", text: "Your Discord account is now linked." },
  conflict: { kind: "error", text: "That Discord account is already linked to another Prism Desk user." },
  error: { kind: "error", text: "Discord linking failed or expired. Please try again." },
  cancelled: { kind: "info", text: "Discord linking was cancelled." },
};

export default function NotificationSettings() {
  const { notify } = useToast();
  const [params] = useSearchParams();
  const status = useAsync(discordStatus, []);
  const prefs = useAsync(getPreferences, []);
  const [edited, setDraft] = useState<Preference[] | null>(null);
  const draft = edited ?? prefs.data ?? [];
  const [saving, setSaving] = useState(false);
  const [page, setPage] = useState(1);
  const history = useAsync(() => myNotifications({ page, page_size: 10 }), [page]);
  const result = RESULT_MESSAGES[params.get("discord") ?? ""];

  const link = async () => {
    try {
      const { authorize_url } = await startDiscordLink();
      window.location.assign(authorize_url);
    } catch (err) {
      notify(getErrorMessage(err), "error");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notification Settings"
        description="Discord is Prism Desk's only notification channel. Notifications are sent as Discord direct messages from the lab bot."
      />
      {result && <Alert kind={result.kind}>{result.text}</Alert>}

      <Card title="Discord account">
        <ErrorMessage message={status.error} onRetry={status.reload} />
        {status.loading && !status.data ? (
          <Loading />
        ) : (
          status.data && (
            <div className="space-y-3 text-sm">
              {status.data.linked ? (
                <>
                  <p>
                    Linked as <strong>{status.data.discord_username}</strong> since {formatDateTime(status.data.linked_at)}.
                  </p>
                  <Button
                    variant="secondary"
                    onClick={async () => {
                      try {
                        await unlinkDiscord();
                        notify("Discord account unlinked.", "info");
                        await status.reload();
                      } catch (err) {
                        notify(getErrorMessage(err), "error");
                      }
                    }}
                  >
                    Unlink Discord
                  </Button>
                </>
              ) : (
                <>
                  <p>No Discord account is linked, so you will not receive notifications.</p>
                  {status.data.oauth_configured ? (
                    <Button onClick={() => void link()}>Link with Discord</Button>
                  ) : (
                    <Alert kind="info">Discord linking has not been configured on this server yet. Ask an administrator.</Alert>
                  )}
                </>
              )}
              <p className="text-xs text-slate-500">
                Linking uses Discord OAuth2 with the “identify” scope only. Prism Desk stores your Discord user ID and
                username — never your Discord password or access tokens.
              </p>
            </div>
          )
        )}
      </Card>

      <Card title="Notification categories">
        <ErrorMessage message={prefs.error} onRetry={prefs.reload} />
        <ul className="divide-y divide-slate-100">
          {draft.map((pref) => (
            <li key={pref.category} className="flex items-center justify-between gap-4 py-3 text-sm">
              <div>
                <div className="font-medium">{humanize(pref.category)}</div>
                <div className="text-xs text-slate-500">{DESCRIPTIONS[pref.category]}</div>
              </div>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  aria-label={`${humanize(pref.category)} notifications`}
                  checked={pref.enabled}
                  onChange={(e) => setDraft(draft.map((p) => (p.category === pref.category ? { ...p, enabled: e.target.checked } : p)))}
                />
                {pref.enabled ? "On" : "Off"}
              </label>
            </li>
          ))}
        </ul>
        <Button
          className="mt-4"
          loading={saving}
          onClick={async () => {
            setSaving(true);
            try {
              setDraft(await savePreferences(draft));
              notify("Preferences saved.");
            } catch (err) {
              notify(getErrorMessage(err), "error");
            } finally {
              setSaving(false);
            }
          }}
        >
          Save preferences
        </Button>
      </Card>

      <Card title="Recent notifications and delivery status">
        <ErrorMessage message={history.error} />
        {history.data && (
          <>
            <DataTable
              rows={history.data.items}
              rowKey={(row) => row.id}
              empty="No notifications have been queued for you yet."
              columns={[
                { header: "Created", cell: (row) => formatDateTime(row.created_at) },
                { header: "Title", cell: (row) => row.title },
                { header: "Category", cell: (row) => humanize(row.category) },
                { header: "Status", cell: (row) => <StatusBadge status={row.status} /> },
              ]}
            />
            <Pagination page={page} pageSize={10} total={history.data.total} onChange={setPage} />
          </>
        )}
      </Card>
    </div>
  );
}
