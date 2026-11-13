import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getAlertActions,
  getCase,
  getCaseAlerts,
  getCaseConformance,
  getCaseDeviations,
  getCaseEvents,
  getCasePrediction,
  evaluateCaseAlert,
  getProcessStages,
  predictCase,
} from "../services/api";
import type { Alert, AlertAction, AlertEvaluation } from "../types/alerts";
import type { CaseConformance, CaseEvent, CommercialCase, ProcessStage } from "../types/cases";
import type { Deviation } from "../types/deviations";
import type { Prediction } from "../types/predictions";
import { AlertStatusBadge, CaseStatusBadge, RiskBadge, SeverityBadge } from "../shared/components/Badges";
import { PageHeader, SectionCard } from "../shared/components/Layout";
import { EmptyState, ErrorState, LoadingState } from "../shared/components/States";
import { ALERT_ACTION_LABELS, ALERT_EVALUATION_OUTCOME_LABELS, DEVIATION_TYPE_LABELS, EVENT_TYPE_LABELS } from "../shared/constants/labels";
import { describeApiError } from "../shared/utils/apiErrors";
import { formatDateTime, formatPercentage } from "../shared/utils/format";
import { RegisterEventForm } from "../features/cases/RegisterEventForm";

interface DetailData {
  commercialCase: CommercialCase;
  stages: ProcessStage[];
  events: CaseEvent[];
  conformance: CaseConformance;
  deviations: Deviation[];
  prediction: Prediction | null;
  alerts: Alert[];
  actions: Record<string, AlertAction[]>;
}

export function CaseDetailPage({ caseId }: { caseId: string }) {
  const [data, setData] = useState<DetailData | null>(null);
  const [selectedDeviation, setSelectedDeviation] = useState<Deviation | null>(null);
  const [loading, setLoading] = useState(true);
  const [predicting, setPredicting] = useState(false);
  const [evaluatingAlert, setEvaluatingAlert] = useState(false);
  const [alertEvaluation, setAlertEvaluation] = useState<AlertEvaluation | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [commercialCase, stages, events, conformance, deviations, prediction, alerts] = await Promise.all([
        getCase(caseId), getProcessStages(), getCaseEvents(caseId), getCaseConformance(caseId),
        getCaseDeviations(caseId), getCasePrediction(caseId), getCaseAlerts(caseId),
      ]);
      const actionEntries = await Promise.all(alerts.map(async (alert) => [alert.id, await getAlertActions(alert.id)] as const));
      setData({ commercialCase, stages, events, conformance, deviations, prediction, alerts, actions: Object.fromEntries(actionEntries) });
    } catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo cargar el detalle del caso"); }
    finally { setLoading(false); }
  }, [caseId]);

  useEffect(() => { void load(); }, [load]);
  const stageById = useMemo(() => Object.fromEntries((data?.stages ?? []).map((stage) => [stage.id, stage])), [data]);

  // Tras registrar un evento se recargan el caso (etapa actual), el timeline y la conformidad
  // sin desmontar la página, para conservar el formulario y su mensaje de confirmación.
  const refreshAfterEvent = useCallback(async () => {
    try {
      const [commercialCase, events, conformance] = await Promise.all([
        getCase(caseId), getCaseEvents(caseId), getCaseConformance(caseId),
      ]);
      setData((current) => current ? { ...current, commercialCase, events, conformance } : current);
    } catch (reason) {
      setError(reason instanceof Error ? `El evento se registró, pero no se pudo actualizar la vista: ${reason.message}` : "El evento se registró, pero no se pudo actualizar la vista");
    }
  }, [caseId]);

  async function evaluateAlert() {
    setEvaluatingAlert(true); setError(null); setAlertEvaluation(null);
    try {
      const evaluation = await evaluateCaseAlert(caseId);
      setAlertEvaluation(evaluation);
      // La evaluación puede crear o actualizar alertas y persistir una predicción nueva.
      const alerts = await getCaseAlerts(caseId);
      const actionEntries = await Promise.all(alerts.map(async (alert) => [alert.id, await getAlertActions(alert.id)] as const));
      setData((current) => current ? {
        ...current,
        alerts,
        actions: Object.fromEntries(actionEntries),
        prediction: evaluation.prediction ?? current.prediction,
      } : current);
    } catch (reason) { setError(describeApiError(reason, "No se pudo evaluar la alerta")); }
    finally { setEvaluatingAlert(false); }
  }

  async function calculateRisk() {
    setPredicting(true); setError(null);
    try {
      const prediction = await predictCase(caseId);
      setData((current) => current ? { ...current, prediction } : current);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo calcular el riesgo"); }
    finally { setPredicting(false); }
  }

  if (loading) return <main className="px-4 py-6 sm:px-6 lg:px-8"><LoadingState label="Cargando caso" /></main>;
  if (error && !data) return <main className="px-4 py-6 sm:px-6 lg:px-8"><ErrorState message={error} onRetry={() => void load()} /></main>;
  if (!data) return null;

  const currentStage = stageById[data.commercialCase.current_stage_id];
  return <main className="px-4 py-6 sm:px-6 lg:px-8"><div className="mx-auto max-w-[1500px] space-y-6"><nav aria-label="Breadcrumb" className="text-sm text-muted"><a href="/cases" className="font-bold text-brand-700">Casos</a><span className="mx-2">›</span><span aria-current="page">{data.commercialCase.case_code}</span></nav><PageHeader eyebrow="Detalle integral" title={data.commercialCase.case_code} description="Trazabilidad del caso desde el Event Log hasta la gestión predictiva." action={<div className="flex flex-wrap gap-2"><a href={`/analyst?case=${encodeURIComponent(data.commercialCase.case_code)}`} className="rounded-lg border border-line bg-white px-4 py-2 text-sm font-bold text-brand-700">Preguntar al Analista</a><a href="/process-mining" className="rounded-lg border border-line bg-white px-4 py-2 text-sm font-bold">Ver minería de procesos</a></div>} />
    {error && <ErrorState message={error} onRetry={() => void load()} />}
    <SectionCard><dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-6"><div><dt className="text-xs font-bold uppercase text-muted">Etapa actual</dt><dd className="mt-1 font-bold">{currentStage?.name ?? "—"}</dd></div><div><dt className="text-xs font-bold uppercase text-muted">Estado</dt><dd className="mt-1"><CaseStatusBadge status={data.commercialCase.status} /></dd></div><div><dt className="text-xs font-bold uppercase text-muted">Fuente</dt><dd className="mt-1 font-semibold">{data.commercialCase.source || "—"}</dd></div><div><dt className="text-xs font-bold uppercase text-muted">Asesor</dt><dd className="mt-1 font-semibold">{data.commercialCase.assigned_resource || "—"}</dd></div><div><dt className="text-xs font-bold uppercase text-muted">Inicio</dt><dd className="mt-1 text-sm">{formatDateTime(data.commercialCase.started_at)}</dd></div><div><dt className="text-xs font-bold uppercase text-muted">Cierre</dt><dd className="mt-1 text-sm">{formatDateTime(data.commercialCase.closed_at)}</dd></div></dl></SectionCard>
    <RegisterEventForm commercialCase={data.commercialCase} stages={data.stages} onSaved={refreshAfterEvent} />
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(360px,0.7fr)]">
      <SectionCard title="Timeline del caso" description={`${data.events.length} eventos ordenados cronológicamente`}><div className="space-y-0">{data.events.map((event, index) => <div key={event.id} className="relative pb-5 pl-8"><span className={`absolute left-1 top-1 h-3 w-3 rounded-full ${event.event_type === "STAGE_CHANGE" ? "bg-brand-700" : "bg-blue-500"}`} />{index < data.events.length - 1 && <span className="absolute left-[9px] top-4 h-full w-px bg-line" />}<div className="flex flex-wrap items-baseline justify-between gap-2"><p className="font-bold">{stageById[event.stage_id]?.name ?? "Etapa no disponible"}</p><time className="text-xs text-muted">{formatDateTime(event.timestamp)}</time></div><p className="mt-1 text-sm text-ink-950">{event.activity}</p><p className="mt-1 text-xs text-muted">{EVENT_TYPE_LABELS[event.event_type]} · {event.resource || "Sin recurso"}</p></div>)}</div>{!data.events.length && <EmptyState title="Sin eventos" description="Este caso no dispone de un timeline observable." />}</SectionCard>
      <SectionCard title="Conformidad" description="Comparación estructural con el proceso esperado"><div className={`rounded-lg border p-4 ${data.conformance.structurally_conforming ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50"}`}><p className="font-bold">{data.conformance.structurally_conforming ? "Conforme" : "Con desviaciones estructurales"}</p><p className="mt-1 text-xs text-muted">Un recorrido incompleto no se considera incorrecto por sí mismo.</p></div><div className="mt-4"><p className="text-xs font-bold uppercase text-muted">Secuencia observada</p><div className="mt-2 flex flex-wrap gap-2">{data.conformance.observed_sequence.map((stage, index) => <span key={`${stage}-${index}`} className="rounded-md border border-line bg-surface-muted px-2 py-1 text-xs font-semibold">{stage}</span>)}</div></div><div className="mt-4"><p className="text-xs font-bold uppercase text-muted">Secuencia esperada</p><p className="mt-2 text-sm text-muted">{data.conformance.expected_sequence.join(" → ")}</p></div></SectionCard>
    </div>
    <div className="grid gap-6 xl:grid-cols-2">
      <SectionCard title="Desviaciones" description={`${data.deviations.length} detecciones asociadas`} action={<a href={`/deviations?case=${encodeURIComponent(data.commercialCase.case_code)}`} className="text-sm font-bold text-brand-700">Abrir módulo</a>}>{data.deviations.length ? <div className="overflow-x-auto"><table className="min-w-full divide-y divide-line text-left text-sm"><thead className="text-xs uppercase text-muted"><tr><th className="py-2 pr-3">Tipo</th><th className="py-2 pr-3">Severidad</th><th className="py-2 pr-3">Etapa</th><th className="py-2">Fecha</th></tr></thead><tbody className="divide-y divide-line">{data.deviations.map((item) => <tr key={item.id} tabIndex={0} aria-label={`Ver ${DEVIATION_TYPE_LABELS[item.type]}`} onClick={() => setSelectedDeviation(item)} onKeyDown={(event) => { if (event.key === "Enter") setSelectedDeviation(item); }} className="cursor-pointer hover:bg-surface-muted"><td className="py-3 pr-3 font-semibold">{DEVIATION_TYPE_LABELS[item.type]}</td><td className="py-3 pr-3"><SeverityBadge severity={item.severity} /></td><td className="py-3 pr-3">{item.stage_code || "—"}</td><td className="whitespace-nowrap py-3">{formatDateTime(item.detected_at)}</td></tr>)}</tbody></table></div> : <EmptyState title="Sin desviaciones" description="No existen desviaciones persistidas para este caso." />}{selectedDeviation && <div className="mt-4 rounded-lg border border-line bg-surface-muted p-4"><div className="flex justify-between gap-3"><p className="font-bold">{DEVIATION_TYPE_LABELS[selectedDeviation.type]}</p><button aria-label="Cerrar detalle de desviación" onClick={() => setSelectedDeviation(null)} className="text-sm font-bold text-muted">Cerrar</button></div><p className="mt-2 text-sm">{selectedDeviation.description}</p></div>}</SectionCard>
      <SectionCard title="Predicción más reciente" description="Riesgo estimado, no probabilidad real" action={<div className="flex flex-wrap gap-2"><button type="button" disabled={evaluatingAlert || predicting} onClick={() => void evaluateAlert()} className="rounded-lg border border-line bg-white px-4 py-2 text-sm font-bold text-brand-700 disabled:opacity-50">{evaluatingAlert ? "Evaluando…" : "Evaluar alerta"}</button><button type="button" disabled={predicting || evaluatingAlert} onClick={() => void calculateRisk()} className="rounded-lg bg-brand-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">{predicting ? "Calculando…" : "Calcular riesgo"}</button></div>}>{alertEvaluation && <AlertEvaluationNotice evaluation={alertEvaluation} onClose={() => setAlertEvaluation(null)} />}{data.prediction ? data.prediction.prediction_applicable && data.prediction.risk_level ? <div><div className="flex items-end justify-between gap-3"><div><p className="text-xs font-bold uppercase text-muted">Riesgo estimado</p><p className="mt-1 text-4xl font-bold">{formatPercentage(data.prediction.risk_score)}</p></div><RiskBadge level={data.prediction.risk_level} /></div><p className="mt-3 text-sm font-semibold">{data.prediction.predicted_label ? "Posible desviación en la próxima evolución" : "Riesgo bajo el threshold de decisión"}</p><p className="mt-1 break-all text-xs text-muted">{data.prediction.model_version} · snapshot {formatDateTime(data.prediction.snapshot_timestamp)}</p><div className="mt-4 grid gap-2 sm:grid-cols-2">{data.prediction.top_factors.map((factor) => <div key={factor.feature} className="rounded-lg border border-line p-3"><p className="break-all text-xs font-bold">{factor.feature}</p><p className="mt-1 text-xs text-muted">Valor: {factor.value == null ? "Sin valor" : String(factor.value)}</p></div>)}</div></div> : <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm">La predicción temprana ya no es aplicable en el último estado observable.</div> : <EmptyState title="Sin predicción persistida" description="Este caso aún no tiene una predicción persistida. Puedes calcularla explícitamente." />}</SectionCard>
    </div>
    <SectionCard title="Historial de alertas" description="Incluye ciclos abiertos y cerrados" action={<a href={`/alerts?case=${encodeURIComponent(data.commercialCase.case_code)}`} className="text-sm font-bold text-brand-700">Ver en Alertas</a>}>{data.alerts.length ? <div className="grid gap-3 lg:grid-cols-2">{data.alerts.map((alert) => <article key={alert.id} className="rounded-lg border border-line p-4"><div className="flex flex-wrap items-start justify-between gap-2"><div><p className="font-bold text-brand-700">{alert.alert_code}</p><p className="mt-1 text-2xl font-bold">{formatPercentage(alert.risk_score)}</p></div><div className="flex gap-2"><RiskBadge level={alert.risk_level} /><AlertStatusBadge status={alert.status} /></div></div><p className="mt-2 text-xs text-muted">Generada {formatDateTime(alert.triggered_at)}</p><div className="mt-3 border-t border-line pt-3"><p className="text-xs font-bold uppercase text-muted">Acciones relacionadas</p><ul className="mt-2 space-y-1 text-sm">{(data.actions[alert.id] ?? []).map((action) => <li key={action.id}>{ALERT_ACTION_LABELS[action.action_type]} · <span className="text-muted">{action.actor || "Sistema"}</span></li>)}</ul></div></article>)}</div> : <EmptyState title="Sin alertas" description="Ninguna predicción de este caso ha originado una alerta operativa." />}</SectionCard>
  </div></main>;
}

const EVALUATION_TONE_STYLE = {
  warning: "border-amber-200 bg-amber-50 text-amber-900",
  success: "border-emerald-200 bg-emerald-50 text-emerald-900",
  neutral: "border-line bg-surface-muted text-ink-950",
} as const;

function AlertEvaluationNotice({ evaluation, onClose }: { evaluation: AlertEvaluation; onClose: () => void }) {
  const label = ALERT_EVALUATION_OUTCOME_LABELS[evaluation.outcome] ?? { title: "Evaluación completada.", tone: "neutral" as const };
  return <div role="status" className={`mb-4 rounded-lg border p-4 text-sm ${EVALUATION_TONE_STYLE[label.tone]}`}><div className="flex items-start justify-between gap-3"><p className="font-bold">{label.title}</p><button type="button" aria-label="Cerrar resultado de la evaluación" onClick={onClose} className="text-xs font-bold opacity-70">Cerrar</button></div><p className="mt-1">{evaluation.message}</p><p className="mt-2 text-xs opacity-80">Umbral de alerta: {formatPercentage(evaluation.alert_risk_threshold)}{evaluation.prediction?.risk_score != null ? ` · Riesgo estimado: ${formatPercentage(evaluation.prediction.risk_score)}` : ""}{evaluation.alert ? ` · ${evaluation.alert.alert_code}` : ""}</p></div>;
}
