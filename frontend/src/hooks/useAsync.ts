import { useCallback, useEffect, useRef, useState } from "react";

import { getErrorMessage } from "../services/api";

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string;
  reload: () => Promise<void>;
  setData: (value: T | null) => void;
}

// Load data for a page and expose loading/error state. ``deps`` re-run
// the loader (for example when filters change).
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const latest = useRef(0);

  // The caller passes the loader's inputs as ``deps``.
  // eslint-disable-next-line react-hooks/exhaustive-deps, react-hooks/use-memo
  const run = useCallback(loader, deps);

  const reload = useCallback(async () => {
    const requestId = ++latest.current;
    setLoading(true);
    setError("");
    try {
      const result = await run();
      if (requestId === latest.current) setData(result);
    } catch (err) {
      if (requestId === latest.current) setError(getErrorMessage(err));
    } finally {
      if (requestId === latest.current) setLoading(false);
    }
  }, [run]);

  useEffect(() => {
    // Fetching on mount/dependency change is this hook's purpose.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void reload();
  }, [reload]);

  return { data, loading, error, reload, setData };
}

// Debounce a fast-changing value such as a search box.
export function useDebounced<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
