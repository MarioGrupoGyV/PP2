import { useMemo, useState } from "react";

import { createCaseEvent } from "../../services/api";
import type { CommercialCase, EventType, ProcessStage } from "../../types/cases";
import { SectionCard } from "../../shared/components/Layout";
import { ErrorState } from "../../shared/components/States";
import { EVENT_TYPE_LABELS, FORM_FIELD_LABELS, MANUAL_REGISTRATION_LABELS as T } from "../../shared/constants/labels";
import { describeApiError } from "../../shared/utils/apiErrors";
import { localInputToIso, toDateTimeLocalValue } from "../../shared/utils/datetime";
import { activeStagesInOrder } from "./NewCaseForm";

const INPUT_CLASS = "mt-1 w-full rounded-lg border border-line px-3 py-2 font-normal";
const LABEL_CLASS = "text-sm font-bold text-ink-950";

/** Siguiente etapa activa tras la etapa actual del caso (o la propia etapa si es la última). */
function suggestedStage(activeStages: ProcessStage[], currentStageId: string): ProcessStage | undefined {
  const current = activeStages.find((stage) => stage.id === currentStageId);
  if (!current) return activeStages[0];
  return activeStages.find((stage) => stage.sequence > current.sequence) ?? current;
}

export function RegisterEventForm({
  commercialCase,
  stages,
  onSaved,
}: {
  commercialCase: CommercialCase;
  stages: ProcessStage[];
  onSaved: () => Promise<void>;
}) {
  const activeStages = useMemo(() => activeStagesInOrder(stages), [stages]);
  const initialStage = suggestedStage(activeStages, commercialCase.current_stage_id);

  const [stageId, setStageId] = useState(initialStage?.id ?? "");
  const [activity, setActivity] = useState(initialStage?.name ?? "");
  const [eventType, setEventType] = useState<EventType>("STAGE_CHANGE");
  const [resource, setResource] = useState(commercialCase.assigned_resource ?? "");
  const [timestamp, setTimestamp] = useState(() => toDateTimeLocalValue());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  function changeStage(nextId: string) {
    const previous = activeStages.find((stage) => stage.id === stageId);
    const next = activeStages.find((stage) => stage.id === nextId);
    setStageId(nextId);
    // Autocompleta la actividad salvo que el usuario la haya personalizado.
    if (next && (!activity.trim() || activity === previous?.name)) setActivity(next.name);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const timestampIso = localInputToIso(timestamp);
    if (!timestampIso) { setError(T.invalidDate); return; }
    setSaving(true); setError(null); setSuccess(false);
    try {
      await createCaseEvent(commercialCase.id, {
        stage_id: stageId,
        activity: activity.trim(),
        event_type: eventType,
        resource: resource.trim() || null,
        timestamp: timestampIso,
      });
      await onSaved();
      const next = suggestedStage(activeStages, eventType === "STAGE_CHANGE" ? stageId : commercialCase.current_stage_id);
      if (next) { setStageId(next.id); setActivity(next.name); }
      setTimestamp(toDateTimeLocalValue());
      setSuccess(true);
    } catch (reason) {
      setError(describeApiError(reason, "No se pudo registrar el evento"));
    } finally {
      setSaving(false);
    }
  }

  return <SectionCard title={T.registerEvent} description="Añade manualmente un evento al Event Log del caso. Un cambio de etapa actualiza la etapa actual." action={<a href={`/deviations?case=${encodeURIComponent(commercialCase.case_code)}`} className="text-sm font-bold text-brand-700">{T.analyzeDeviations}</a>}>
    <form onSubmit={(event) => void submit(event)} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <label className={LABEL_CLASS}>{FORM_FIELD_LABELS.stage_id}<select required value={stageId} onChange={(event) => changeStage(event.target.value)} className={INPUT_CLASS}>{activeStages.length === 0 && <option value="">Sin etapas activas</option>}{activeStages.map((stage) => <option key={stage.id} value={stage.id}>{stage.sequence}. {stage.name} ({stage.code})</option>)}</select></label>
        <label className={LABEL_CLASS}>{FORM_FIELD_LABELS.activity}<input required maxLength={200} value={activity} onChange={(event) => setActivity(event.target.value)} className={INPUT_CLASS} /></label>
        <label className={LABEL_CLASS}>{FORM_FIELD_LABELS.event_type}<select value={eventType} onChange={(event) => setEventType(event.target.value as EventType)} className={INPUT_CLASS}>{(Object.keys(EVENT_TYPE_LABELS) as EventType[]).map((item) => <option key={item} value={item}>{EVENT_TYPE_LABELS[item]}</option>)}</select></label>
        <label className={LABEL_CLASS}>{FORM_FIELD_LABELS.resource}<input maxLength={150} value={resource} onChange={(event) => setResource(event.target.value)} placeholder="Asesor responsable" className={INPUT_CLASS} /></label>
        <label className={LABEL_CLASS}>{FORM_FIELD_LABELS.timestamp}<input required type="datetime-local" value={timestamp} onChange={(event) => setTimestamp(event.target.value)} className={INPUT_CLASS} /></label>
      </div>
      <p className="text-xs text-muted">Puedes indicar una fecha distinta a la actual para simular plazos vencidos (SLA) y luego analizar las desviaciones.</p>
      {error && <ErrorState title="No se pudo registrar el evento" message={error} />}
      {success && <p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800">{T.eventSaved}</p>}
      <div className="flex justify-end">
        <button type="submit" disabled={saving || !stageId} className="rounded-lg bg-brand-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">{saving ? T.savingEvent : T.registerEvent}</button>
      </div>
    </form>
  </SectionCard>;
}
