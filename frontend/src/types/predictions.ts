export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

export interface RiskFactor {
  feature: string;
  value: unknown;
  influence: number | null;
  importance: number | null;
  direction: string | null;
  scope: string;
}

export interface Prediction {
  id: string | null;
  case_id: string;
  case_code: string;
  snapshot_timestamp: string;
  model_version: string;
  algorithm: string;
  risk_score: number | null;
  risk_level: RiskLevel | null;
  predicted_label: boolean | null;
  decision_threshold: number;
  prediction_applicable: boolean;
  reason: string | null;
  top_factors: RiskFactor[];
  predicted_at: string | null;
}

export interface PredictionList {
  items: Prediction[];
  page: number;
  page_size: number;
  total: number;
}

export interface MetricSet {
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  pr_auc: number;
  brier_score: number;
  confusion_matrix: number[][];
  threshold: number;
}

export interface ActiveModel {
  model_version: string;
  algorithm: string;
  target_name: string;
  feature_schema_version: string;
  dataset_hash: string;
  trained_at: string;
  decision_threshold: number;
  test_metrics: MetricSet;
  predictive_quality_warning: boolean;
}

export interface ModelEvaluation {
  model_version: string;
  selected_model: string;
  validation_metrics: Record<string, MetricSet>;
  test_metrics: MetricSet;
  confusion_matrix: number[][];
  class_distribution: Record<string, number>;
  split_summary: Record<string, number>;
  selection_reason: string;
}
