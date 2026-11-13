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

/** Nombres en español de los campos que la API puede rechazar (HTTP 422). */
export const FORM_FIELD_LABELS: Record<string, string> = {
  case_code: "Código del caso",
  current_stage_id: "Etapa inicial",
  assigned_resource: "Asesor asignado",
  source: "Fuente",
  status: "Estado",
  started_at: "Fecha de inicio",
  closed_at: "Fecha de cierre",
  stage_id: "Etapa",
  activity: "Actividad",
  event_type: "Tipo de evento",
  resource: "Recurso",
  timestamp: "Fecha y hora del evento",
  metadata: "Metadatos",
};

/** Traducción de los mensajes de dominio que devuelve el backend. */
export const API_ERROR_MESSAGES: Record<string, string> = {
  "Commercial case not found": "El caso comercial no existe o fue eliminado.",
  "Process stage not found": "La etapa seleccionada no existe. Recarga la página para actualizar el catálogo de etapas.",
  "Process stage is inactive": "La etapa seleccionada está inactiva y no admite nuevos registros.",
  "Commercial case code already exists": "Ya existe un caso con ese código. Usa un código diferente.",
  "Unable to persist event": "No se pudo guardar el evento. Verifica que no esté duplicado e inténtalo de nuevo.",
  "Unable to persist commercial case": "No se pudo guardar el caso. Inténtalo de nuevo.",
};

export const API_STATUS_MESSAGES: Record<number, string> = {
  404: "No se encontró el recurso solicitado.",
  409: "La operación entra en conflicto con datos ya registrados.",
  422: "Los datos enviados no son válidos.",
};

export const MANUAL_REGISTRATION_LABELS = {
  newCase: "Nuevo caso",
  createCase: "Crear caso",
  creatingCase: "Creando…",
  registerEvent: "Registrar evento",
  savingEvent: "Guardando…",
  eventSaved: "Evento registrado. El timeline, la conformidad y la etapa actual se han actualizado.",
  analyzeDeviations: "Analizar desviaciones",
  cancel: "Cancelar",
  invalidDate: "La fecha y hora indicada no es válida.",
} as const;
