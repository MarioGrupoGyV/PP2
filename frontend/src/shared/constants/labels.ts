export const CASE_STATUS_LABELS = {
  ACTIVE: "Activo",
  CLOSED: "Cerrado",
  CANCELLED: "Cancelado",
} as const;

export const ALERT_STATUS_LABELS = {
  ACTIVE: "Activa",
  ATTENDED: "Atendida",
  RESOLVED: "Resuelta",
  DISMISSED: "Descartada",
} as const;

export const RISK_LABELS = { LOW: "Bajo", MEDIUM: "Medio", HIGH: "Alto" } as const;
export const SEVERITY_LABELS = RISK_LABELS;

export const DEVIATION_TYPE_LABELS = {
  SLA_BREACH: "SLA excedido",
  STAGE_SKIP: "Salto de etapa",
  BACKTRACK: "Retroceso",
  REWORK: "Retrabajo",
  INACTIVITY: "Inactividad",
} as const;

export const ALERT_ACTION_LABELS: Record<string, string> = {
  CREATED: "Alerta creada",
  ATTENDED: "Alerta atendida",
  NOTE: "Nota registrada",
  RISK_REEVALUATED: "Riesgo reevaluado",
  RESOLVED: "Alerta resuelta",
  DISMISSED: "Alerta descartada",
};

export const EVENT_TYPE_LABELS = {
  STAGE_CHANGE: "Cambio de etapa",
  INTERACTION: "Interacción",
  SYSTEM: "Sistema",
} as const;
