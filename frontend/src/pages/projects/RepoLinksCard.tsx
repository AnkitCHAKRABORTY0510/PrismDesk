import { useState, type FormEvent } from "react";
import { ExternalLink as ExternalIcon, Plus, Trash2 } from "lucide-react";

import { GithubMark } from "../../components/common/GithubMark";
import { Button, Card, ErrorMessage, Input, Loading, useToast } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { formatDate } from "../../lib/format";
import { isGithubRepoUrl, repoName } from "../../lib/github";
import { getErrorMessage } from "../../services/api";
import { addRepoLink, listRepoLinks, removeRepoLink, type Project } from "../../services/projectService";

/**
 * GitHub repositories linked to a project. Any active member (not guests)
 * can add one while the project is active; the adder or a supervisor can
 * remove it. The server enforces the same rules.
 */
export default function RepoLinksCard({ project }: { project: Project }) {
  const { notify } = useToast();
  const links = useAsync(() => listRepoLinks(project.id), [project.id]);
  const canAdd = project.permissions.can_contribute;
  const [adding, setAdding] = useState(false);
  const [url, setUrl] = useState("");
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const urlError = url.trim() && !isGithubRepoUrl(url) ? "Use a link like https://github.com/owner/repository" : "";

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!url.trim() || urlError) return;
    setBusy(true);
    try {
      const created = await addRepoLink(project.id, url.trim(), label.trim());
      links.setData([...(links.data ?? []), created]);
      setUrl("");
      setLabel("");
      setAdding(false);
      notify("Repository linked.");
    } catch (err) {
      notify(getErrorMessage(err), "error");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (linkId: string) => {
    const before = links.data ?? [];
    links.setData(before.filter((link) => link.id !== linkId));
    try {
      await removeRepoLink(project.id, linkId);
      notify("Repository link removed.");
    } catch (err) {
      links.setData(before);
      notify(getErrorMessage(err), "error");
    }
  };

  return (
    <Card
      title={
        <span className="inline-flex items-center gap-2">
          <GithubMark className="h-4 w-4 text-fg-soft" />
          Code
        </span>
      }
      actions={
        canAdd &&
        !adding && (
          <Button size="sm" variant="secondary" onClick={() => setAdding(true)}>
            <Plus className="h-3.5 w-3.5" aria-hidden="true" /> Add repository
          </Button>
        )
      }
    >
      <ErrorMessage message={links.error} onRetry={links.reload} />
      {links.loading && !links.data ? (
        <Loading />
      ) : (
        <ul className="space-y-2">
          {(links.data ?? []).map((link) => (
            <li key={link.id} className="group flex items-start gap-3 rounded-lg border border-line px-3 py-2">
              <GithubMark className="mt-0.5 h-4 w-4 shrink-0 text-fg-soft" />
              <div className="min-w-0 flex-1">
                <a
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex max-w-full items-center gap-1 font-mono text-sm font-medium text-link hover:underline"
                >
                  <span className="truncate">{link.label || repoName(link.url)}</span>
                  <ExternalIcon className="h-3 w-3 shrink-0" aria-hidden="true" />
                </a>
                <div className="truncate text-xs text-fg-muted">
                  {link.label ? `${repoName(link.url)} · ` : ""}
                  added {link.added_by_username ? `by @${link.added_by_username} ` : ""}on {formatDate(link.created_at)}
                </div>
              </div>
              {link.can_remove && (
                <button
                  type="button"
                  onClick={() => void remove(link.id)}
                  aria-label={`Remove ${repoName(link.url)}`}
                  className="rounded-md p-1 text-fg-muted transition-colors hover:bg-danger-soft hover:text-danger-fg"
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </button>
              )}
            </li>
          ))}
          {(links.data ?? []).length === 0 && !adding && (
            <li className="text-sm text-fg-muted">
              No repositories linked yet.{canAdd ? " Add the project's GitHub repository so everyone can find the code." : ""}
            </li>
          )}
        </ul>
      )}
      {adding && (
        <form onSubmit={(event) => void submit(event)} className="mt-3 space-y-2">
          <Input
            aria-label="GitHub repository URL"
            placeholder="https://github.com/owner/repository"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            autoFocus
            inputMode="url"
            aria-invalid={Boolean(urlError)}
          />
          {urlError && <p className="text-xs text-danger-fg">{urlError}</p>}
          <Input aria-label="Label (optional)" placeholder="Label (optional), e.g. Simulation code" maxLength={100} value={label} onChange={(event) => setLabel(event.target.value)} />
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => { setAdding(false); setUrl(""); setLabel(""); }}>
              Cancel
            </Button>
            <Button size="sm" type="submit" loading={busy} disabled={!url.trim() || Boolean(urlError)}>
              Link repository
            </Button>
          </div>
        </form>
      )}
    </Card>
  );
}
