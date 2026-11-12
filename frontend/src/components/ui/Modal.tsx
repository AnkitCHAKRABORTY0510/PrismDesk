import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";

import { Button } from "./primitives";

export function Modal({
  open,
  title,
  onClose,
  children,
  footer,
  wide = false,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  // Escape closes; focus moves into the dialog and returns on close;
  // Tab is kept inside the dialog; the page behind does not scroll.
  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const dialog = dialogRef.current;
    if (dialog && !dialog.contains(document.activeElement)) dialog.focus();

    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab" || !dialog) return;
      const focusable = dialog.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", handler);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", handler);
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus?.();
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-stretch justify-center bg-[var(--overlay)] backdrop-blur-[2px] sm:items-start sm:overflow-y-auto sm:p-4 sm:pt-16">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={`flex h-full w-full flex-col bg-surface-raised shadow-pop outline-none animate-in fade-in-0 slide-in-from-bottom-4 duration-200 sm:h-auto sm:rounded-xl sm:border sm:border-line sm:zoom-in-95 sm:slide-in-from-bottom-0 ${wide ? "sm:max-w-3xl" : "sm:max-w-lg"}`}
      >
        <div className="flex shrink-0 items-center justify-between gap-3 border-b border-line px-4 py-3 sm:px-5 sm:py-4">
          <h2 id={titleId} className="min-w-0 text-base font-semibold text-fg">
            {title}
          </h2>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="-mr-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-fg-muted transition-colors hover:bg-surface-muted hover:text-fg"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4 sm:flex-none sm:overflow-visible sm:px-5">{children}</div>
        {footer && (
          <div className="flex shrink-0 flex-wrap justify-end gap-2 border-t border-line px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-5">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  danger = false,
  busy = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <Modal
      open={open}
      title={title}
      onClose={onCancel}
      footer={
        <>
          <Button variant="secondary" onClick={onCancel} disabled={busy}>
            Cancel
          </Button>
          <Button variant={danger ? "danger" : "primary"} onClick={onConfirm} loading={busy}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="text-sm text-fg-soft">{message}</div>
    </Modal>
  );
}
