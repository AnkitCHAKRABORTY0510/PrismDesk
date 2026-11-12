import { Monitor, Moon, Sun } from "lucide-react";

import { useTheme, type ThemePreference } from "../../context/ThemeContext";

const ORDER: ThemePreference[] = ["light", "dark", "system"];
const LABELS: Record<ThemePreference, string> = { light: "Light", dark: "Dark", system: "System" };
const ICONS = { light: Sun, dark: Moon, system: Monitor };

// Cycles light → dark → system. Shows the current preference.
export function ThemeToggle({ className = "", tone = "default" }: { className?: string; tone?: "default" | "onDark" }) {
  const { theme, setTheme } = useTheme();
  const next = ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length];
  const Icon = ICONS[theme];
  const label = `Theme: ${LABELS[theme]}. Switch to ${LABELS[next]} theme`;

  const toneClass =
    tone === "onDark"
      ? "border-white/15 text-slate-200 hover:bg-white/10 hover:text-white"
      : "border-line bg-surface text-fg-soft hover:bg-surface-muted hover:text-fg";

  return (
    <button
      type="button"
      onClick={() => setTheme(next)}
      aria-label={label}
      title={label}
      className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border transition-colors ${toneClass} ${className}`}
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
    </button>
  );
}
