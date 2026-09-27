export interface AnalystHistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AnalystToolTrace {
  name: string;
  status: "success" | "not_found" | "invalid_arguments" | "error";
  duration_ms: number;
}

export interface AnalystEvidence {
  type: string;
  case_code: string | null;
  case_id: string | null;
  alert_code: string | null;
}

export interface AnalystStatus {
  enabled: boolean;
  configured: boolean;
  provider: "ollama";
  model: string;
  available: boolean;
  read_only: boolean;
  message: string;
}

export interface AnalystChatRequest {
  message: string;
  history: AnalystHistoryMessage[];
  context_case_code: string | null;
}

export interface AnalystChatResponse {
  answer: string;
  provider: "ollama";
  model: string;
  read_only: boolean;
  tool_calls: AnalystToolTrace[];
  evidence: AnalystEvidence[];
  duration_ms: number;
  tool_rounds: number;
}
