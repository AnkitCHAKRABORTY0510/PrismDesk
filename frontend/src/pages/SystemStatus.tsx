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
      ? "text-green-600"
      : "text-yellow-600";

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-6">
      <div className="w-full max-w-lg rounded-xl bg-white p-8 shadow-lg">
        <h1 className="text-2xl font-bold text-slate-800">
          Prism Desk
        </h1>

        <p className="mt-2 text-sm text-slate-500">
          System Connection Status
        </p>

        <div className="mt-8 space-y-5">
          <div className="flex justify-between border-b pb-4">
            <span className="font-medium">React Frontend</span>
            <span className="font-semibold text-green-600">
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
          <p className="mt-6 rounded-lg bg-red-50 p-3 text-sm text-red-600">
            {error}
          </p>
        )}

        <p className="mt-8 text-center text-xs text-slate-400">
          PRISM Laboratory | Prism Desk
        </p>
      </div>
    </div>
  );
}

export default SystemStatus;
