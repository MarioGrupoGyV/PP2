import type { DatabaseHealthResponse, HealthResponse } from "../types/health";
import type {
  EventLogImport,
  ImportPreview,
  ImportResult,
} from "../types/imports";

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(
  /\/$/,
  "",
);

async function requestJson<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs = 5000,
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        Accept: "application/json",
        ...options.headers,
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      let message = "No fue posible completar la solicitud";
      try {
        const body = (await response.json()) as { detail?: string };
        if (body.detail) message = body.detail;
      } catch {
        // La respuesta puede no contener JSON en errores de red o proxy.
      }
      throw new Error(message);
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

function uploadCsv<T>(path: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append("file", file);
  return requestJson<T>(path, { method: "POST", body: formData }, 60_000);
}

export function getBackendHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/api/v1/health");
}

export function getDatabaseHealth(): Promise<DatabaseHealthResponse> {
  return requestJson<DatabaseHealthResponse>("/api/v1/health/database");
}

export function previewEventLog(file: File): Promise<ImportPreview> {
  return uploadCsv<ImportPreview>("/api/v1/imports/preview", file);
}

export function commitEventLog(file: File): Promise<ImportResult> {
  return uploadCsv<ImportResult>("/api/v1/imports/commit", file);
}

export function getImportHistory(): Promise<EventLogImport[]> {
  return requestJson<EventLogImport[]>("/api/v1/imports?limit=20");
}

export function getImportTemplateUrl(): string {
  return `${API_URL}/api/v1/imports/template`;
}
