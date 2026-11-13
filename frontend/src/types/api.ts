/** Elemento de error de validación devuelto por FastAPI/Pydantic (HTTP 422). */
export interface ApiValidationIssue {
  loc: (string | number)[];
  msg: string;
  type: string;
  ctx?: Record<string, unknown>;
}

export type ApiErrorDetail = string | ApiValidationIssue[] | null;
