import type { Deviation } from "./deviations";

export type CaseStatus = "ACTIVE" | "CLOSED" | "CANCELLED";
export type EventType = "STAGE_CHANGE" | "INTERACTION" | "SYSTEM";

export interface CommercialCase {
  id: string;
  case_code: string;
  current_stage_id: string;
  assigned_resource: string | null;
  source: string | null;
  status: CaseStatus;
  started_at: string;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CommercialCaseList {
  items: CommercialCase[];
  page: number;
  page_size: number;
  total: number;
}

export interface ProcessStage {
  id: string;
  code: string;
  name: string;
  sequence: number;
  sla_hours: number;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CaseEvent {
  id: string;
  case_id: string;
  stage_id: string;
  activity: string;
  event_type: EventType;
  resource: string | null;
  timestamp: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface CaseConformance {
  case_id: string;
  case_code: string;
  expected_sequence: string[];
  observed_sequence: string[];
  structurally_conforming: boolean;
  structural_deviations: Deviation[];
  temporal_deviations: Deviation[];
}
