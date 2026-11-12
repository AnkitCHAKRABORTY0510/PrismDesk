import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

interface Toast {
  id: number;
  kind: "success" | "error" | "info";
  message: string;
}

interface ToastContextType {
  notify: (message: string, kind?: Toast["kind"]) => void;
}

const ToastContext = createContext<ToastContextType>({ notify: () => undefined });

// In-app feedback toasts for actions (not a messaging system).
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const notify = useCallback((message: string, kind: Toast["kind"] = "success") => {
    const id = Date.now() + Math.random();
    setToasts((current) => [...current, { id, kind, message }]);
    window.setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), 4000);
  }, []);

  const tone = {
    success: "border-success-line text-success-fg",
    error: "border-danger-line text-danger-fg",
    info: "border-info-line text-info-fg",
  };

  return (
    <ToastContext.Provider value={{ notify }}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-4 bottom-4 z-[60] flex flex-col gap-2 sm:inset-x-auto sm:right-4 sm:w-80">
        {toasts.map((toast) => (
          <div key={toast.id} role="status" className={`pointer-events-auto rounded-lg border bg-surface-raised px-4 py-3 text-sm shadow-pop animate-in fade-in-0 slide-in-from-bottom-2 ${tone[toast.kind]}`}>
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast() {
  return useContext(ToastContext);
}
