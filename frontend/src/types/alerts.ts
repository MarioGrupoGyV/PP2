import type { Prediction, RiskFactor, RiskLevel } from "./predictions";

export type AlertStatus = "ACTIVE" | "ATTENDED" | "RESOLVED" | "DISMISSED";
export type AlertEvaluationMode = "LATEST_OBSERVATION" | "HISTORICAL_REPLAY";
export type AlertActionType = "CREATED" | "ATTENDED" | "NOTE" | "RISK_REEVALUATED" | "RESOLVED" | "DISMISSED";

export interface Alert {
  id: string;
  alert_code: string;
  case_id: string;
  case_code: string;
  status: AlertStatus;
  risk_score: number;
  risk_level: RiskLevel;
  title: string;
  description: string;
  evaluation_mode: AlertEvaluationMode;
  triggered_at: string;
  last_evaluated_at: string;
  attended_at: string | null;
  resolved_at: string | null;
  dismissed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AlertPrediction {
  id: string;
  model_version: string;
  snapshot_timestamp: string;
  risk_score: number;
  risk_level: RiskLevel;
  predicted_label: boolean;
}

export interface AlertDetail extends Alert {
  origin_prediction: AlertPrediction;
  latest_prediction: AlertPrediction;
  model_version: string;
  snapshot_timestamp: string;
  current_factors: RiskFactor[];
}

export interface AlertList {
  items: Alert[];
  page: number;
  page_size: number;
  total: number;
}

export interface AlertAction {
  id: string;
  alert_id: string;
  action_type: AlertActionType;
  actor: string | null;
  notes: string | null;
  previous_status: AlertStatus | null;
  new_status: AlertStatus | null;
  prediction_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface AlertSummary {
  total_alerts: number;
  active: number;
  attended: number;
  resolved: number;
  dismissed: number;
  open_alerts: number;
  average_open_risk_score: number | null;
  by_risk_level: Record<RiskLevel, number>;
}

export interface AlertEvaluation {
  case_id: string;
  case_code: string;
  evaluation_mode: AlertEvaluationMode;
  outcome: string;
  prediction: Prediction | null;
  alert: Alert | null;
  alert_risk_threshold: number;
  message: string;
}

export interface AlertBatchResult {
  evaluation_mode: AlertEvaluationMode;
  alert_risk_threshold: number;
  cases_evaluated: number;
  predictions_created: number;
  predictions_reused: number;
  alerts_created: number;
  alerts_updated: number;
  below_threshold: number;
  skipped_not_applicable: number;
  skipped_no_observable_state: number;
  skipped_ineligible: number;
  unchanged: number;
  cases_without_alert: number;
  results: AlertEvaluation[];
}
