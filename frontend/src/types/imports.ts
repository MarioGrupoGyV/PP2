export interface ImportValidationError {
  row: number;
  field: string;
  message: string;
}

export interface ImportPreviewRow {
  row: number;
  case_code: string;
  stage_code: string;
  activity: string;
  timestamp: string;
  resource: string | null;
  event_type: "STAGE_CHANGE" | "INTERACTION" | "SYSTEM";
  source: string | null;
}

export interface ImportPreview {
  filename: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  can_import: boolean;
  preview: ImportPreviewRow[];
  errors: ImportValidationError[];
}

export interface ImportResult {
  import_id: string;
  filename: string;
  total_rows: number;
  cases_created: number;
  cases_existing: number;
  events_imported: number;
  duplicates_skipped: number;
}

export interface EventLogImport {
  id: string;
  filename: string;
  file_sha256: string;
  total_rows: number;
  imported_cases: number;
  imported_events: number;
  skipped_duplicates: number;
  created_at: string;
}
