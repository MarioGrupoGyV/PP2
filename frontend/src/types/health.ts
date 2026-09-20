export type RequestState = "loading" | "success" | "error";

export interface ServiceStatus {
  state: RequestState;
  message?: string;
}

export interface HealthResponse {
  status: "ok";
  service: "backend";
}

export interface DatabaseHealthResponse {
  status: "ok";
  database: "connected";
}
