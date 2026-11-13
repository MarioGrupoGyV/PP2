import { ApiError } from "../../services/api";
import type { ApiValidationIssue } from "../../types/api";
import {
  API_ERROR_MESSAGES,
  API_STATUS_MESSAGES,
  FORM_FIELD_LABELS,
} from "../constants/labels";

function describeIssue(issue: ApiValidationIssue): string {
  const field = [...issue.loc].reverse().find((part) => typeof part === "string" && part !== "body");
  const fieldLabel = typeof field === "string" ? FORM_FIELD_LABELS[field] ?? field : "Formulario";
  const ctx = issue.ctx ?? {};
  let problem: string;
  switch (issue.type) {
    case "missing":
      problem = "es obligatorio";
      break;
    case "string_too_short":
      problem = "no puede estar vacío";
      break;
    case "string_too_long":
      problem = `admite como máximo ${String(ctx.max_length ?? "")} caracteres`;
      break;
    case "uuid_parsing":
    case "uuid_type":
      problem = "debe seleccionarse de la lista";
      break;
    case "enum":
      problem = "tiene un valor no permitido";
      break;
    default:
      if (issue.type.startsWith("datetime")) problem = "no es una fecha y hora válida";
      else if (issue.msg.includes("closed_at cannot be earlier")) problem = "no puede ser anterior a la fecha de inicio";
      else if (issue.msg.includes("time zones")) problem = "debe incluir una zona horaria compatible";
      else problem = issue.msg;
  }
  return `${fieldLabel}: ${problem}.`;
}

/** Traduce un error de la API (404, 409, 422 u otro) a un mensaje claro en español. */
export function describeApiError(error: unknown, fallback: string): string {
  if (!(error instanceof ApiError)) {
    return error instanceof Error && error.message ? error.message : fallback;
  }
  if (Array.isArray(error.detail) && error.detail.length) {
    return `Revisa los datos del formulario. ${error.detail.map(describeIssue).join(" ")}`;
  }
  if (typeof error.detail === "string" && API_ERROR_MESSAGES[error.detail]) {
    return API_ERROR_MESSAGES[error.detail];
  }
  return API_STATUS_MESSAGES[error.status] ?? (error.message || fallback);
}
