export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: T; label: string }[];
  active: T;
  onChange: (id: T) => void;
}) {
  return (
    <div role="tablist" className="-mx-1 flex gap-1 overflow-x-auto border-b border-line px-1 [scrollbar-width:none]">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          type="button"
          aria-selected={active === tab.id}
          onClick={() => onChange(tab.id)}
          className={`-mb-px shrink-0 whitespace-nowrap rounded-t-md border-b-2 px-3 py-2 text-sm font-medium transition-colors sm:px-4 ${
            active === tab.id
              ? "border-ring text-link"
              : "border-transparent text-fg-muted hover:border-line-strong hover:text-fg"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
