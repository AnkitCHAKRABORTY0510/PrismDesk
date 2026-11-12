import { useEffect, useState } from "react";
import {
  getBackendHealth,
  getDatabaseHealth,
} from "../services/healthService";

function SystemStatus() {
  const [backend, setBackend] = useState("Checking...");
  const [database, setDatabase] = useState("Checking...");
  const [error, setError] = useState("");

  useEffect(() => {
    const checkConnections = async () => {
      try {
        const backendResult = await getBackendHealth();
        setBackend(backendResult.status);

        const databaseResult = await getDatabaseHealth();
        setDatabase(databaseResult.status);
      } catch (err) {
        console.error(err);
        setError("Unable to connect to the backend or database.");
      }
    };

    checkConnections();
  }, []);

  const statusStyle = (status: string) =>
    status === "healthy" || status === "connected"
      ? "text-success-fg"
      : "text-warn-fg";

  return (
    <div className="min-h-screen bg-surface-muted flex items-center justify-center p-6">
      <div className="w-full max-w-lg rounded-xl bg-surface p-8 shadow-pop">
        <h1 className="text-2xl font-bold text-fg">
          Prism Desk
        </h1>

        <p className="mt-2 text-sm text-fg-muted">
          System Connection Status
        </p>

        <div className="mt-8 space-y-5">
          <div className="flex justify-between border-b pb-4">
            <span className="font-medium">React Frontend</span>
            <span className="font-semibold text-success-fg">
              Running
            </span>
          </div>

          <div className="flex justify-between border-b pb-4">
            <span className="font-medium">FastAPI Backend</span>
            <span className={`font-semibold ${statusStyle(backend)}`}>
              {backend}
            </span>
          </div>

          <div className="flex justify-between">
            <span className="font-medium">PostgreSQL Database</span>
            <span className={`font-semibold ${statusStyle(database)}`}>
              {database}
            </span>
          </div>
        </div>

        {error && (
          <p className="mt-6 rounded-lg bg-danger-soft p-3 text-sm text-danger-fg">
            {error}
          </p>
        )}

        <p className="mt-8 text-center text-xs text-fg-subtle">
          PRISM Laboratory | Prism Desk
        </p>
      </div>
    </div>
  );
}

export default SystemStatus;
