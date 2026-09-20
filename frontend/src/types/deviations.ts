export type DeviationType = "SLA_BREACH" | "STAGE_SKIP" | "BACKTRACK" | "REWORK" | "INACTIVITY";
export type DeviationSeverity = "LOW" | "MEDIUM" | "HIGH";

export interface Deviation {
  id: string; case_id: string; case_code: string; event_id: string | null;
  stage_id: string | null; stage_code: string | null; type: DeviationType;
  severity: DeviationSeverity; description: string;
  expected_value: Record<string, unknown> | null;
  actual_value: Record<string, unknown> | null;
  details: Record<string, unknown> | null;
  fingerprint: string; detected_at: string; resolved_at: string | null; created_at: string;
}
export interface DeviationList { items: Deviation[]; page: number; page_size: number; total: number; }
export interface DeviationSummary {
  total_deviations: number; affected_cases: number; structural_deviations: number;
  temporal_deviations: number; by_type: Record<string, number>; by_severity: Record<string, number>;
}
export interface ConformanceSummary {
  total_cases: number; structurally_conforming_cases: number;
  structurally_nonconforming_cases: number; structural_conformance_percentage: number;
  cases_with_temporal_deviations: number; deviations: Record<string, number>;
}
export interface AnalyzeDeviationsResult {
  cases_analyzed: number; deviations_detected: number;
  deviations_created: number; deviations_existing: number;
}
