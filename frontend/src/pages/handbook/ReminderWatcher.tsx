import { useEffect, useRef } from "react";

import { useToast } from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { can } from "../../lib/permissions";
import { PLANNER_CHANGED, upcomingReminders, type Reminder } from "../../services/handbookPlannerService";
import { readStorage, writeStorage } from "./plannerMeta";

const CHECK_EVERY_MS = 20_000;
const REFRESH_EVERY_MS = 5 * 60_000;

function alertedKey(userId: string) {
  return `prismdesk.handbook.alerted.${userId}`;
}

// Raises handbook reminders when they fall due: an in-app toast always,
// and a browser notification when the user has allowed them. Each reminder
// is announced once per device. Renders nothing.
export function ReminderWatcher() {
  const { user } = useAuth();
  const { notify } = useToast();
  const reminders = useRef<Reminder[]>([]);
  const enabled = !!user && can(user, "handbook.view");
  const userId = user?.id ?? "";

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    const key = alertedKey(userId);
    let seen: string[];
    try {
      seen = JSON.parse(readStorage(key) ?? "[]") as string[];
    } catch {
      seen = [];
    }
    const alerted = new Set<string>(seen);

    const refresh = async () => {
      try {
        const list = await upcomingReminders(50);
        if (!cancelled) reminders.current = list;
        check();
      } catch {
        // Offline or signed out: try again on the next refresh.
      }
    };

    const check = () => {
      const now = Date.now();
      for (const reminder of reminders.current) {
        if (reminder.dismissed_at || alerted.has(reminder.id) || new Date(reminder.remind_at).getTime() > now) continue;
        alerted.add(reminder.id);
        notify(`Reminder: ${reminder.note}`, "info");
        if ("Notification" in window && Notification.permission === "granted") {
          try {
            new Notification("Prism Desk reminder", { body: reminder.note, tag: `handbook-reminder-${reminder.id}` });
          } catch {
            // Some browsers only allow notifications from a service worker.
          }
        }
      }
      writeStorage(key, JSON.stringify([...alerted].slice(-200)));
    };

    void refresh();
    const checkTimer = window.setInterval(check, CHECK_EVERY_MS);
    const refreshTimer = window.setInterval(() => void refresh(), REFRESH_EVERY_MS);
    const onChange = () => void refresh();
    window.addEventListener(PLANNER_CHANGED, onChange);
    return () => {
      cancelled = true;
      window.clearInterval(checkTimer);
      window.clearInterval(refreshTimer);
      window.removeEventListener(PLANNER_CHANGED, onChange);
    };
  }, [enabled, userId, notify]);

  return null;
}
