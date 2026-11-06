import { useEffect, useState } from "react";

import { useDebounced } from "../../hooks/useAsync";
import { getErrorMessage } from "../../services/api";
import type { UserSummary } from "../../services/types";
import { searchDirectory } from "../../services/userService";
import { Input } from "./primitives";

// Search approved users by name (only for project managers).
export function UserPicker({
  roleName,
  onSelect,
  excludeIds = [],
  label = "Find user",
}: {
  roleName?: string;
  onSelect: (user: UserSummary) => void;
  excludeIds?: string[];
  label?: string;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<UserSummary[]>([]);
  const [error, setError] = useState("");
  const debounced = useDebounced(query);

  useEffect(() => {
    let cancelled = false;
    if (debounced.trim().length < 2) return;
    searchDirectory(debounced, roleName)
      .then((users) => !cancelled && setResults(users))
      .catch((err) => !cancelled && setError(getErrorMessage(err)));
    return () => {
      cancelled = true;
    };
  }, [debounced, roleName]);

  const visible = debounced.trim().length < 2 ? [] : results.filter((user) => !excludeIds.includes(user.id));

  return (
    <div className="space-y-2">
      <Input aria-label={label} placeholder="Type at least 2 letters of a name…" value={query} onChange={(e) => setQuery(e.target.value)} />
      {error && <p className="text-xs text-red-600">{error}</p>}
      {visible.length > 0 && (
        <ul className="max-h-56 divide-y divide-slate-100 overflow-y-auto rounded-lg border border-slate-200">
          {visible.map((user) => (
            <li key={user.id}>
              <button
                type="button"
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-slate-50"
                onClick={() => {
                  onSelect(user);
                  setQuery("");
                }}
              >
                <span>
                  <strong className="font-medium text-slate-800">{user.full_name}</strong>{" "}
                  <span className="text-slate-500">@{user.username}</span>
                </span>
                <span className="text-xs text-slate-400">{user.roles.join(", ")}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
