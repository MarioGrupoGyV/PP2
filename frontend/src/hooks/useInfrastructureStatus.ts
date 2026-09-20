import { useCallback, useEffect, useState } from "react";

import { getBackendHealth, getDatabaseHealth } from "../services/api";
import type { ServiceStatus } from "../types/health";

const loadingStatus: ServiceStatus = { state: "loading" };

function errorMessage(reason: unknown): string {
  return reason instanceof Error ? reason.message : "Sin conexión";
}

export function useInfrastructureStatus() {
  const [backend, setBackend] = useState<ServiceStatus>(loadingStatus);
  const [database, setDatabase] = useState<ServiceStatus>(loadingStatus);

  const refresh = useCallback(async () => {
    setBackend(loadingStatus);
    setDatabase(loadingStatus);

    const [backendResult, databaseResult] = await Promise.allSettled([
      getBackendHealth(),
      getDatabaseHealth(),
    ]);

    setBackend(
      backendResult.status === "fulfilled"
        ? { state: "success" }
        : { state: "error", message: errorMessage(backendResult.reason) },
    );
    setDatabase(
      databaseResult.status === "fulfilled"
        ? { state: "success" }
        : { state: "error", message: errorMessage(databaseResult.reason) },
    );
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return {
    backend,
    database,
    refresh,
    isRefreshing: backend.state === "loading" || database.state === "loading",
  };
}
