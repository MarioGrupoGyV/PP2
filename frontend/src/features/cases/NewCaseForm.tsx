import { useMemo, useState } from "react";

import { createCase } from "../../services/api";
import type { CaseStatus, ProcessStage } from "../../types/cases";
import { SectionCard } from "../../shared/components/Layout";
import { ErrorState } from "../../shared/components/States";
import { CASE_STATUS_LABELS, FORM_FIELD_LABELS, MANUAL_REGISTRATION_LABELS as T } from "../../shared/constants/labels";
import { describeApiError } from "../../shared/utils/apiErrors";
import { localInputToIso, toDateTimeLocalValue } from "../../shared/utils/datetime";

const INPUT_CLASS = "mt-1 w-full rounded-lg border border-line px-3 py-2 font-normal";
const LABEL_CLASS = "text-sm font-bold text-ink-950";

export function activeStagesInOrder(stages: ProcessStage[]): ProcessStage[] {
  return stages.filter((stage) => stage.active).sort((a, b) => a.sequence - b.sequence);
}

export function NewCaseForm({ stages, onCancel }: { stages: ProcessStage[]; onCancel: () => void }) {
  const activeStages = useMemo(() => activeStagesInOrder(stages), [stages]);
  const defaultStageId = activeStages.find((stage) => stage.code === "LEAD")?.id ?? activeStages[0]?.id ?? "";

  const [caseCode, setCaseCode] = useState("");
  const [stageId, setStageId] = useState(defaultStageId);
  const [resource, setResource] = useState("");
  const [source, setSource] = useState("");
  const [status, setStatus] = useState<CaseStatus>("ACTIVE");
  const [startedAt, setStartedAt] = useState(() => toDateTimeLocalValue());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const startedAtIso = localInputToIso(startedAt);
    if (!startedAtIso) { setError(T.invalidDate); return; }
    setSaving(true); setError(null);
    try {
      const created = await createCase({
        case_code: caseCode.trim().toUpperCase(),
        current_stage_id: stageId,
        assigned_resource: resource.trim() || null,
        source: source.trim() || null,
        status,
        started_at: startedAtIso,
      });
      window.location.assign(`/cases/${created.id}`);
    } catch (reason) {
      setError(describeApiError(reason, "No se pudo crear el caso"));
      setSaving(false);
    }
  }

  return <SectionCard title={T.newCase} description="Registra manualmente una nueva instancia del proceso comercial. Después podrás añadir sus eventos desde el detalle del caso." action={<a href="/deviations" className="text-sm font-bold text-brand-700">{T.analyzeDeviations}</a>}>
    <form onSubmit={(event) => void submit(event)} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <label className={LABEL_CLASS}>{FORM_FIELD_LABELS.case_code}<input required maxLength={100} value={caseCode} onChange={(event) => setCaseCode(event.target.value)} placeholder="MAN-00001" className={`${INPUT_CLASS} uppercase`} /></label>
        <label className={LABEL_CLASS}>{FORM_FIELD_LABELS.current_stage_id}<select required value={stageId} onChange={(event) => setStageId(event.target.value)} className={INPUT_CLASS}>{activeStages.length === 0 && <option value="">Sin etapas activas</option>}{activeStages.map((stage) => <option key={stage.id} value={stage.id}>{stage.sequence}. {stage.name} ({stage.code})</option>)}</select></label>
        <label className={LABEL_CLASS}>{FORM_FIELD_LABELS.status}<select value={status} onChange={(event) => setStatus(event.target.value as CaseStatus)} className={INPUT_CLASS}>{(Object.keys(CASE_STATUS_LABELS) as CaseStatus[]).map((item) => <option key={item} value={item}>{CASE_STATUS_LABELS[item]}</option>)}</select></label>
        <label className={LABEL_CLASS}>{FORM_FIELD_LABELS.assigned_resource}<input maxLength={150} value={resource} onChange={(event) => setResource(event.target.value)} placeholder="Nombre del asesor" className={INPUT_CLASS} /></label>
        <label className={LABEL_CLASS}>{FORM_FIELD_LABELS.source}<input maxLength={100} value={source} onChange={(event) => setSource(event.target.value)} placeholder="Web, Referido, Feria…" className={INPUT_CLASS} /></label>
        <label className={LABEL_CLASS}>{FORM_FIELD_LABELS.started_at}<input required type="datetime-local" value={startedAt} onChange={(event) => setStartedAt(event.target.value)} className={INPUT_CLASS} /></label>
      </div>
      {error && <ErrorState title="No se pudo crear el caso" message={error} />}
      <div className="flex flex-wrap justify-end gap-2">
        <button type="button" onClick={onCancel} className="rounded-lg border border-line px-4 py-2 text-sm font-bold">{T.cancel}</button>
        <button type="submit" disabled={saving || !stageId} className="rounded-lg bg-brand-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">{saving ? T.creatingCase : T.createCase}</button>
      </div>
    </form>
  </SectionCard>;
}
