import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getActivePredictiveModel,
  getAlerts,
  getAlertSummary,
  getCases,
  getConformanceSummary,
  getDeviationSummary,
  getProcessMiningSummary,
  getProcessTransitions,
  getProcessVariants,
} from "../services/api";
import type { Alert, AlertSummary } from "../types/alerts";
import type { ConformanceSummary, DeviationSummary } from "../types/deviations";
import type { ActiveModel } from "../types/predictions";
import type { ProcessMiningSummary, TransitionStatistic, VariantStatistic } from "../types/processMining";
import { AlertStatusBadge, RiskBadge } from "../shared/components/Badges";
import { DatasetNotice, KpiCard, PageHeader, SectionCard } from "../shared/components/Layout";
import { EmptyState, ErrorState, LoadingState } from "../shared/components/States";
import { DEVIATION_TYPE_LABELS } from "../shared/constants/labels";
import { formatDateTime, formatNumber, formatPercentage } from "../shared/utils/format";
import { formatDuration } from "../utils/duration";

interface DashboardData {
  caseTotal: number;
  conformance: ConformanceSummary;
  deviations: DeviationSummary;
  process: ProcessMiningSummary;
  variants: VariantStatistic[];
  transitions: TransitionStatistic[];
  model: ActiveModel;
  alerts: AlertSummary;
  recentAlerts: Alert[];
}

export function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [cases, conformance, deviations, process, variants, transitions, model, alerts, alertList] = await Promise.all([
        getCases(1, 1), getConformanceSummary(), getDeviationSummary(), getProcessMiningSummary(),
        getProcessVariants(5), getProcessTransitions(), getActivePredictiveModel(), getAlertSummary(),
        getAlerts({ pageSize: 10 }),
      ]);
      setData({
        caseTotal: cases.total,
        conformance,
        deviations,
        process,
        variants,
        transitions,
        model,
        alerts,
        recentAlerts: alertList.items.filter((item) => item.status === "ACTIVE" || item.status === "ATTENDED").slice(0, 5),
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo cargar el resumen ejecutivo");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const frequentTransition = useMemo(() => data?.transitions.reduce<TransitionStatistic | null>((best, item) => !best || item.frequency > best.frequency ? item : best, null) ?? null, [data]);
  const slowestTransition = useMemo(() => data?.transitions.reduce<TransitionStatistic | null>((best, item) => !best || item.max_duration_seconds > best.max_duration_seconds ? item : best, null) ?? null, [data]);

  return <main className="px-4 py-6 sm:px-6 lg:px-8"><div className="mx-auto max-w-[1500px] space-y-6"><PageHeader eyebrow="Visión ejecutiva" title="Dashboard" description="Estado consolidado del proceso comercial, su conformidad, riesgo predictivo y gestión de alertas." action={<a href="/demo" className="inline-flex rounded-lg bg-brand-700 px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-800">Iniciar demostración</a>} /><DatasetNotice />
    {loading && <LoadingState label="Cargando dashboard" />}
    {error && <ErrorState message={error} onRetry={() => void load()} />}
    {data && <>
      <section aria-label="Indicadores principales" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><KpiCard label="Casos" value={formatNumber(data.caseTotal)} detail="Instancias del proceso" /><KpiCard label="Conformidad estructural" value={formatPercentage(data.conformance.structural_conformance_percentage / 100)} detail={`${formatNumber(data.conformance.structurally_conforming_cases)} casos conformes`} /><KpiCard label="Desviaciones" value={formatNumber(data.deviations.total_deviations)} detail={`${formatNumber(data.deviations.affected_cases)} casos afectados`} /><KpiCard label="Alertas abiertas" value={formatNumber(data.alerts.open_alerts)} detail={`${data.alerts.active} activas · ${data.alerts.attended} atendidas`} /></section>
      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Desviaciones detectadas" description="Distribución observada por tipo" action={<a href="/deviations" className="text-sm font-bold text-brand-700">Ver desviaciones</a>}><div className="space-y-3">{Object.entries(data.deviations.by_type).sort((a, b) => b[1] - a[1]).map(([type, count]) => { const width = data.deviations.total_deviations ? count / data.deviations.total_deviations * 100 : 0; return <div key={type}><div className="mb-1 flex justify-between gap-4 text-sm"><span>{DEVIATION_TYPE_LABELS[type as keyof typeof DEVIATION_TYPE_LABELS] ?? type}</span><strong>{formatNumber(count)}</strong></div><div className="h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-warning" style={{ width: `${Math.max(width, 1)}%` }} /></div></div>; })}</div></SectionCard>
        <SectionCard title="Minería de procesos" description={`${data.process.total_variants} variantes en ${data.process.total_events} eventos`} action={<a href="/process-mining" className="text-sm font-bold text-brand-700">Ver minería de procesos</a>}><dl className="grid gap-4 sm:grid-cols-2"><div><dt className="text-xs font-bold uppercase text-muted">Variante más frecuente</dt><dd className="mt-1 text-sm font-semibold text-ink-950">{data.variants[0]?.activities.join(" → ") || "Sin variantes"}</dd><dd className="text-xs text-muted">{data.variants[0] ? formatPercentage(data.variants[0].percentage / 100) : "—"}</dd></div><div><dt className="text-xs font-bold uppercase text-muted">Transición más frecuente</dt><dd className="mt-1 font-semibold">{frequentTransition ? `${frequentTransition.source} → ${frequentTransition.target}` : "—"}</dd><dd className="text-xs text-muted">{frequentTransition ? `${frequentTransition.frequency} ocurrencias` : ""}</dd></div><div className="sm:col-span-2"><dt className="text-xs font-bold uppercase text-muted">Mayor duración observada</dt><dd className="mt-1 font-semibold">{slowestTransition ? `${slowestTransition.source} → ${slowestTransition.target}` : "—"}</dd><dd className="text-xs text-muted">{slowestTransition ? formatDuration(slowestTransition.max_duration_seconds) : ""}</dd></div></dl></SectionCard>
        <SectionCard title="Modelo predictivo activo" description={data.model.model_version} action={<a href="/predictions" className="text-sm font-bold text-brand-700">Ver predicciones</a>}><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><div><p className="text-xs uppercase text-muted">Algoritmo</p><p className="mt-1 font-bold">{data.model.algorithm}</p></div><div><p className="text-xs uppercase text-muted">PR-AUC</p><p className="mt-1 text-xl font-bold">{data.model.test_metrics.pr_auc.toFixed(3)}</p></div><div><p className="text-xs uppercase text-muted">F1 / Recall</p><p className="mt-1 text-xl font-bold">{data.model.test_metrics.f1.toFixed(3)} / {data.model.test_metrics.recall.toFixed(3)}</p></div><div><p className="text-xs uppercase text-muted">Precision</p><p className="mt-1 text-xl font-bold">{data.model.test_metrics.precision.toFixed(3)}</p></div></div><p className="mt-4 border-t border-line pt-3 text-xs text-muted">Threshold del modelo: {data.model.decision_threshold.toFixed(3)}. El threshold operativo se administra por separado en el backend.</p></SectionCard>
        <SectionCard title="Alertas pendientes" description={`${data.alerts.active} activas y ${data.alerts.attended} atendidas`} action={<a href="/alerts" className="text-sm font-bold text-brand-700">Ver alertas</a>}>{data.recentAlerts.length ? <div className="divide-y divide-line">{data.recentAlerts.map((alert) => <a key={alert.id} href={`/alerts?case=${encodeURIComponent(alert.case_code)}`} className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"><div><p className="font-bold text-ink-950">{alert.alert_code} · {alert.case_code}</p><p className="text-xs text-muted">{formatDateTime(alert.last_evaluated_at)}</p></div><div className="flex items-center gap-2"><RiskBadge level={alert.risk_level} /><AlertStatusBadge status={alert.status} /></div></a>)}</div> : <EmptyState title="Sin alertas abiertas" description="Las alertas resueltas o descartadas permanecen disponibles en su historial." />}</SectionCard>
      </div>
      <section className="flex flex-wrap gap-3 border-t border-line pt-5"><a href="/process-mining" className="rounded-lg border border-line bg-white px-4 py-2 text-sm font-bold">Ver minería de procesos</a><a href="/deviations" className="rounded-lg border border-line bg-white px-4 py-2 text-sm font-bold">Ver desviaciones</a><a href="/alerts" className="rounded-lg border border-line bg-white px-4 py-2 text-sm font-bold">Ver alertas</a></section>
    </>}</div></main>;
}
