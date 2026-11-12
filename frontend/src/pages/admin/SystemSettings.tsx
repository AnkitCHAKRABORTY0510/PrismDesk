import { PageHeader } from "../../components/layout/PageHeader";
import { Card, ErrorMessage, Loading } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { humanize } from "../../lib/format";
import { systemSettings } from "../../services/dashboardService";

export default function SystemSettings() {
  const { data, loading, error, reload } = useAsync(systemSettings, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="System Settings"
        description="Read-only summary of the server configuration. Secrets are never shown; change values in the backend environment file and restart."
      />
      <Card>
        <ErrorMessage message={error} onRetry={reload} />
        {loading && !data ? (
          <Loading />
        ) : (
          data && (
            <dl className="divide-y divide-line text-sm">
              {Object.entries(data).map(([key, value]) => (
                <div key={key} className="flex justify-between gap-4 py-2">
                  <dt className="text-fg-muted">{humanize(key)}</dt>
                  <dd className="text-right font-medium text-fg">
                    {Array.isArray(value) ? value.join(", ") : typeof value === "boolean" ? (value ? "Yes" : "No") : String(value)}
                  </dd>
                </div>
              ))}
            </dl>
          )
        )}
      </Card>
    </div>
  );
}
