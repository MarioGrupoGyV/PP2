import type { DatabaseHealthResponse, HealthResponse } from "../types/health";
import type {
  EventLogImport,
  ImportPreview,
  ImportResult,
} from "../types/imports";
import type {
  ActivityStatistic,
  DfgResponse,
  PerformanceResponse,
  ProcessMiningSummary,
  TransitionStatistic,
  VariantCasesResponse,
  VariantStatistic,
  ExpectedModel,
} from "../types/processMining";
import type {
  AnalyzeDeviationsResult,
  ConformanceSummary,
  Deviation,
  DeviationList,
  DeviationSeverity,
  DeviationSummary,
  DeviationType,
} from "../types/deviations";
import type {
  ActiveModel,
  CommercialCaseLookup,
  ModelEvaluation,
  Prediction,
  PredictionList,
} from "../types/predictions";
import type {
  Alert,
  AlertAction,
  AlertBatchResult,
  AlertDetail,
  AlertList,
  AlertStatus,
  AlertSummary,
} from "../types/alerts";
import type { RiskLevel } from "../types/predictions";

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

export function getProcessMiningSummary(): Promise<ProcessMiningSummary> {
  return requestJson<ProcessMiningSummary>("/api/v1/process-mining/summary", {}, 30_000);
}

export function getProcessDfg(): Promise<DfgResponse> {
  return requestJson<DfgResponse>("/api/v1/process-mining/dfg", {}, 30_000);
}

export function getProcessPerformance(): Promise<PerformanceResponse> {
  return requestJson<PerformanceResponse>(
    "/api/v1/process-mining/performance",
    {},
    30_000,
  );
}

export function getProcessVariants(limit = 20): Promise<VariantStatistic[]> {
  return requestJson<VariantStatistic[]>(
    `/api/v1/process-mining/variants?limit=${limit}`,
    {},
    30_000,
  );
}

export function getProcessActivities(): Promise<ActivityStatistic[]> {
  return requestJson<ActivityStatistic[]>(
    "/api/v1/process-mining/activities",
    {},
    30_000,
  );
}

export function getProcessTransitions(): Promise<TransitionStatistic[]> {
  return requestJson<TransitionStatistic[]>(
    "/api/v1/process-mining/transitions",
    {},
    30_000,
  );
}

export function getVariantCases(
  variantId: string,
  page = 1,
  pageSize = 20,
): Promise<VariantCasesResponse> {
  return requestJson<VariantCasesResponse>(
    `/api/v1/process-mining/variants/${variantId}/cases?page=${page}&page_size=${pageSize}`,
    {},
    30_000,
  );
}

export function getExpectedModel(): Promise<ExpectedModel> {
  return requestJson<ExpectedModel>("/api/v1/process-mining/expected-model");
}

export function getConformanceSummary(): Promise<ConformanceSummary> {
  return requestJson<ConformanceSummary>("/api/v1/process-mining/conformance");
}

export function analyzeDeviations(): Promise<AnalyzeDeviationsResult> {
  return requestJson<AnalyzeDeviationsResult>(
    "/api/v1/deviations/analyze",
    { method: "POST" },
    60_000,
  );
}

export function getDeviationSummary(): Promise<DeviationSummary> {
  return requestJson<DeviationSummary>("/api/v1/deviations/summary");
}

export function getDeviations(filters: {
  type?: DeviationType | "";
  severity?: DeviationSeverity | "";
  caseCode?: string;
} = {}): Promise<DeviationList> {
  const parameters = new URLSearchParams({ page: "1", page_size: "100" });
  if (filters.type) parameters.set("type", filters.type);
  if (filters.severity) parameters.set("severity", filters.severity);
  if (filters.caseCode) parameters.set("case_code", filters.caseCode);
  return requestJson<DeviationList>(`/api/v1/deviations?${parameters}`);
}

export function getDeviation(id: string): Promise<Deviation> {
  return requestJson<Deviation>(`/api/v1/deviations/${id}`);
}

export function getActivePredictiveModel(): Promise<ActiveModel> {
  return requestJson<ActiveModel>("/api/v1/ml/model");
}

export function getModelEvaluation(): Promise<ModelEvaluation> {
  return requestJson<ModelEvaluation>("/api/v1/ml/evaluation");
}

export function getRecentPredictions(): Promise<PredictionList> {
  return requestJson<PredictionList>("/api/v1/predictions?page=1&page_size=20");
}

export function getCaseByCode(caseCode: string): Promise<CommercialCaseLookup> {
  return requestJson<CommercialCaseLookup>(
    `/api/v1/cases/code/${encodeURIComponent(caseCode)}`,
  );
}

export function predictCase(caseId: string, asOf?: string): Promise<Prediction> {
  return requestJson<Prediction>(
    `/api/v1/cases/${caseId}/predict`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(asOf ? { as_of: asOf } : {}),
    },
    30_000,
  );
}

export function getAlerts(filters: {
  status?: AlertStatus | "";
  riskLevel?: RiskLevel | "";
  caseCode?: string;
  pageSize?: number;
} = {}): Promise<AlertList> {
  const parameters = new URLSearchParams({
    page: "1",
    page_size: String(filters.pageSize ?? 100),
  });
  if (filters.status) parameters.set("status", filters.status);
  if (filters.riskLevel) parameters.set("risk_level", filters.riskLevel);
  if (filters.caseCode) parameters.set("case_code", filters.caseCode);
  return requestJson<AlertList>(`/api/v1/alerts?${parameters}`);
}

export function getAlertSummary(): Promise<AlertSummary> {
  return requestJson<AlertSummary>("/api/v1/alerts/summary");
}

export function getAlert(id: string): Promise<AlertDetail> {
  return requestJson<AlertDetail>(`/api/v1/alerts/${id}`);
}

export function getAlertActions(id: string): Promise<AlertAction[]> {
  return requestJson<AlertAction[]>(`/api/v1/alerts/${id}/actions`);
}

export function evaluateAlerts(asOf?: string): Promise<AlertBatchResult> {
  return requestJson<AlertBatchResult>(
    "/api/v1/alerts/evaluate",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ as_of: asOf, limit: 100 }),
    },
    120_000,
  );
}

export function transitionAlert(
  id: string,
  action: "attend" | "resolve" | "dismiss",
  actor: string,
  notes: string,
): Promise<AlertDetail> {
  return requestJson<AlertDetail>(`/api/v1/alerts/${id}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor: actor || null, notes: notes || null }),
  });
}

export function addAlertNote(id: string, actor: string, notes: string): Promise<AlertAction> {
  return requestJson<AlertAction>(`/api/v1/alerts/${id}/actions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor: actor || null, notes }),
  });
}

export function getCaseAlerts(caseId: string): Promise<Alert[]> {
  return requestJson<Alert[]>(`/api/v1/cases/${caseId}/alerts`);
}
