export interface ProcessMiningSummary {
  total_cases: number;
  total_events: number;
  unique_activities: number;
  total_variants: number;
  average_case_duration_seconds: number;
  median_case_duration_seconds: number;
}

export interface ActivityBoundary {
  activity: string;
  frequency: number;
  percentage: number;
}

export interface ActivityStatistic {
  activity: string;
  frequency: number;
  case_frequency: number;
}

export interface DfgEdge {
  source: string;
  target: string;
  frequency: number;
  case_frequency: number;
  percentage: number;
}

export interface DfgResponse {
  nodes: ActivityStatistic[];
  edges: DfgEdge[];
  start_activities: ActivityBoundary[];
  end_activities: ActivityBoundary[];
}

export interface TransitionStatistic extends DfgEdge {
  average_duration_seconds: number;
  median_duration_seconds: number;
  min_duration_seconds: number;
  max_duration_seconds: number;
}

export interface VariantStatistic {
  variant_id: string;
  activities: string[];
  case_count: number;
  percentage: number;
}

export interface VariantCase {
  id: string;
  case_code: string;
}

export interface VariantCasesResponse {
  variant_id: string;
  case_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  cases: VariantCase[];
}

export interface PerformanceResponse {
  transitions: TransitionStatistic[];
}
