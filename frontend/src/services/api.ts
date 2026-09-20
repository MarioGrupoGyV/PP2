import type { DatabaseHealthResponse, HealthResponse } from "../types/health";

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(
  /\/$/,
  "",
);

async function get<T>(path: string): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 5000);

  try {
    const response = await fetch(`${API_URL}${path}`, {
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error("Sin conexión");
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Tiempo de espera agotado");
    }
    throw error instanceof Error ? error : new Error("Sin conexión");
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export function getBackendHealth(): Promise<HealthResponse> {
  return get<HealthResponse>("/api/v1/health");
}

export function getDatabaseHealth(): Promise<DatabaseHealthResponse> {
  return get<DatabaseHealthResponse>("/api/v1/health/database");
}
