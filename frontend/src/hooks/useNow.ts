import { useEffect, useState } from "react";

// Re-render every interval (default one minute) so countdowns stay current.
export function useNow(intervalMs = 60000) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), intervalMs);
    return () => window.clearInterval(timer);
  }, [intervalMs]);
  return now;
}
