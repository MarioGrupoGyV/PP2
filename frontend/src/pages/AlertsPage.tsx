import { useCallback, useEffect, useState } from "react";

import {
  addAlertNote,
  evaluateAlerts,
  getAlert,
  getAlertActions,
  getAlerts,
  getAlertSummary,
  transitionAlert,
} from "../services/api";
import type {
  Alert,
  AlertAction,
  AlertBatchResult,
  AlertDetail,
  AlertStatus,
  AlertSummary,
} from "../types/alerts";
import type { RiskLevel } from "../types/predictions";
import { AlertStatusBadge, RiskBadge } from "../shared/components/Badges";
import { ALERT_ACTION_LABELS, ALERT_STATUS_LABELS, RISK_LABELS } from "../shared/constants/labels";
import { formatDateTime, formatPercentage } from "../shared/utils/format";

function Card({ label, value }: { label: string; value: string | number }) {
  return <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p><p className="mt-2 text-3xl font-bold text-slate-950">{value}</p></article>;
}

export function AlertsPage() {
  const [summary, setSummary] = useState<AlertSummary | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selected, setSelected] = useState<AlertDetail | null>(null);
  const [actions, setActions] = useState<AlertAction[]>([]);
  const [status, setStatus] = useState<AlertStatus | "">("");
  const [riskLevel, setRiskLevel] = useState<RiskLevel | "">("");
  const [caseCode, setCaseCode] = useState(() => new URLSearchParams(window.location.search).get("case") || "");
  const [asOf, setAsOf] = useState("");
  const [actor, setActor] = useState("");
  const [notes, setNotes] = useState("");
  const [batch, setBatch] = useState<AlertBatchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setFailure(null);
    try {
      const [summaryResult, listResult] = await Promise.all([
        getAlertSummary(),
        getAlerts({ status, riskLevel, caseCode: caseCode.trim() }),
      ]);
      setSummary(summaryResult); setAlerts(listResult.items);
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "No se pudieron cargar las alertas");
    } finally { setLoading(false); }
  }, [caseCode, riskLevel, status]);

  useEffect(() => { void load(); }, [load]);

  async function showDetail(id: string) {
    setFailure(null);
    try {
      const [detail, history] = await Promise.all([getAlert(id), getAlertActions(id)]);
      setSelected(detail); setActions(history);
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "No se pudo cargar el detalle");
    }
  }

  async function runEvaluation() {
    setEvaluating(true); setFailure(null);
    try {
      const result = await evaluateAlerts(asOf ? new Date(asOf).toISOString() : undefined);
      setBatch(result); await load();
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "No se pudo ejecutar la evaluación");
    } finally { setEvaluating(false); }
  }

  async function changeState(action: "attend" | "resolve" | "dismiss") {
    if (!selected || (action === "dismiss" && !notes.trim())) return;
    setSaving(true); setFailure(null);
    try {
      await transitionAlert(selected.id, action, actor.trim(), notes.trim());
      setNotes(""); await Promise.all([showDetail(selected.id), load()]);
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "No se pudo actualizar la alerta");
    } finally { setSaving(false); }
  }

  async function saveNote() {
    if (!selected || !notes.trim()) return;
    setSaving(true); setFailure(null);
    try {
      await addAlertNote(selected.id, actor.trim(), notes.trim());
      setNotes(""); await showDetail(selected.id);
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "No se pudo registrar la nota");
    } finally { setSaving(false); }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-8">
      <section className="mx-auto max-w-[1500px] space-y-7">
        <header className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
          <div><span className="rounded-full bg-rose-100 px-3 py-1 text-xs font-bold uppercase tracking-wide text-rose-800">Sprint 6 · Gestión operativa</span><h1 className="mt-4 text-4xl font-bold text-slate-950">Alertas Predictivas</h1><p className="mt-2 max-w-3xl text-slate-600">Acciones operativas creadas desde predicciones elegibles de riesgo alto. Una alerta no es una desviación ocurrida ni una certeza.</p></div>
          <div className="rounded-2xl border border-violet-200 bg-violet-50 p-4 xl:w-[430px]"><div className="flex items-center justify-between"><div><p className="text-sm font-bold text-violet-950">Evaluación explícita</p><p className="text-xs text-violet-700">Usa el último evento observable, nunca el reloj actual.</p></div><button type="button" disabled={evaluating} onClick={() => void runEvaluation()} className="rounded-xl bg-violet-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">{evaluating ? "Evaluando…" : "Evaluar casos"}</button></div><details className="mt-3"><summary className="cursor-pointer text-xs font-bold text-violet-800">Reproducción histórica</summary><input type="datetime-local" value={asOf} onChange={(event) => setAsOf(event.target.value)} className="mt-2 w-full rounded-lg border border-violet-200 bg-white px-3 py-2 text-sm" /><p className="mt-1 text-xs text-violet-700">Con fecha informada solo se consideran datos observables hasta ese instante.</p></details></div>
        </header>

        {failure && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-800">{failure}</div>}
        {summary && <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5"><Card label="Alertas abiertas" value={summary.open_alerts} /><Card label="Activas" value={summary.active} /><Card label="Atendidas" value={summary.attended} /><Card label="Resueltas" value={summary.resolved} /><Card label="Riesgo medio abierto" value={formatPercentage(summary.average_open_risk_score)} /></div>}

        {batch && <section className="rounded-2xl border border-violet-200 bg-white p-5 shadow-sm"><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="font-bold text-violet-950">Resultado de evaluación</h2><span className="text-xs font-semibold text-violet-700">{batch.evaluation_mode === "HISTORICAL_REPLAY" ? "Reproducción histórica" : "Última observación"} · threshold operativo {formatPercentage(batch.alert_risk_threshold)}</span></div><div className="mt-4 grid gap-3 sm:grid-cols-3 xl:grid-cols-6"><Card label="Casos evaluados" value={batch.cases_evaluated} /><Card label="Alertas nuevas" value={batch.alerts_created} /><Card label="Actualizadas" value={batch.alerts_updated} /><Card label="Sin alerta" value={batch.cases_without_alert} /><Card label="Bajo threshold" value={batch.below_threshold} /><Card label="No aplicables" value={batch.skipped_not_applicable} /></div></section>}

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between"><div><h2 className="text-xl font-bold">Bandeja priorizada</h2><p className="mt-1 text-sm text-slate-500">Activas primero y luego mayor riesgo estimado.</p></div><div className="grid gap-3 sm:grid-cols-3"><label className="text-xs font-bold text-slate-600">Estado<select value={status} onChange={(event) => setStatus(event.target.value as AlertStatus | "")} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-normal"><option value="">Todos</option>{Object.entries(ALERT_STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label className="text-xs font-bold text-slate-600">Nivel<select value={riskLevel} onChange={(event) => setRiskLevel(event.target.value as RiskLevel | "")} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-normal"><option value="">Todos</option>{Object.entries(RISK_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label className="text-xs font-bold text-slate-600">Caso<input value={caseCode} onChange={(event) => setCaseCode(event.target.value)} placeholder="DEMO-00141" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-normal" /></label></div></div>
          {loading ? <p className="mt-6 text-sm text-slate-500">Cargando alertas…</p> : <div className="mt-5 overflow-x-auto"><table className="min-w-full divide-y divide-slate-200 text-left text-sm"><thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-3 py-3">Código</th><th className="px-3 py-3">Caso</th><th className="px-3 py-3">Riesgo estimado</th><th className="px-3 py-3">Nivel</th><th className="px-3 py-3">Estado</th><th className="px-3 py-3">Generada</th><th className="px-3 py-3">Última evaluación</th></tr></thead><tbody className="divide-y divide-slate-100">{alerts.map((alert) => <tr key={alert.id} tabIndex={0} aria-label={`Ver alerta ${alert.alert_code}`} onClick={() => void showDetail(alert.id)} onKeyDown={(event) => { if (event.key === "Enter") void showDetail(alert.id); }} className="cursor-pointer hover:bg-slate-50"><td className="px-3 py-3 font-bold text-violet-800">{alert.alert_code}</td><td className="px-3 py-3 font-semibold"><a href={`/cases/${alert.case_id}`} onClick={(event) => event.stopPropagation()} className="text-brand-700 hover:underline">{alert.case_code}</a></td><td className="px-3 py-3 text-lg font-bold">{formatPercentage(alert.risk_score)}</td><td className="px-3 py-3"><RiskBadge level={alert.risk_level} /></td><td className="px-3 py-3"><AlertStatusBadge status={alert.status} /></td><td className="whitespace-nowrap px-3 py-3">{formatDateTime(alert.triggered_at)}</td><td className="whitespace-nowrap px-3 py-3">{formatDateTime(alert.last_evaluated_at)}</td></tr>)}</tbody></table>{alerts.length === 0 && <p className="py-8 text-center text-sm text-slate-500">No hay alertas para los filtros seleccionados.</p>}</div>}
        </section>

        {selected && <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_430px]">
          <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-bold text-violet-700">{selected.alert_code}</p><h2 className="mt-1 text-2xl font-bold">{selected.title}</h2><p className="mt-1 text-slate-600">Caso <a href={`/cases/${selected.case_id}`} className="font-bold text-brand-700 hover:underline">{selected.case_code}</a></p></div><AlertStatusBadge status={selected.status} /></div><p className="mt-5 text-sm text-slate-500">Riesgo estimado</p><p className="text-5xl font-bold">{formatPercentage(selected.risk_score)}</p><p className="mt-3 text-sm text-slate-700">{selected.description}</p><div className="mt-5 grid gap-3 sm:grid-cols-2"><div className="rounded-xl bg-slate-50 p-4"><p className="text-xs font-bold uppercase text-slate-500">Predicción</p><p className="mt-1 font-semibold">{selected.latest_prediction.predicted_label ? "Posible desviación en la próxima evolución" : "Riesgo bajo el threshold de decisión"}</p></div><div className="rounded-xl bg-slate-50 p-4"><p className="text-xs font-bold uppercase text-slate-500">Modelo y snapshot</p><p className="mt-1 break-all text-sm font-semibold">{selected.model_version}</p><p className="mt-1 text-xs text-slate-500">{formatDateTime(selected.snapshot_timestamp)}</p></div></div><h3 className="mt-6 font-bold">Factores asociados actuales</h3><div className="mt-3 grid gap-2 sm:grid-cols-2">{selected.current_factors.map((factor) => <div key={factor.feature} className="rounded-lg border border-slate-200 p-3"><p className="break-all text-xs font-semibold">{factor.feature}</p><p className="mt-1 text-sm text-slate-600">Valor: {factor.value == null ? "Sin valor" : String(factor.value)}</p><p className="mt-1 text-xs text-slate-500">{factor.direction === "INCREASES_RISK" ? "Aumenta asociación" : factor.direction === "DECREASES_RISK" ? "Disminuye asociación" : "Importancia global"}</p></div>)}</div>
            {(selected.status === "ACTIVE" || selected.status === "ATTENDED") && <div className="mt-6 border-t border-slate-200 pt-5"><h3 className="font-bold">Registrar gestión</h3><div className="mt-3 grid gap-3 sm:grid-cols-2"><label className="text-xs font-bold text-slate-600">Actor<input value={actor} onChange={(event) => setActor(event.target.value)} placeholder="Jefe Comercial" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-normal" /></label><label className="text-xs font-bold text-slate-600">Notas<textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={2} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-normal" /></label></div><div className="mt-3 flex flex-wrap gap-2">{selected.status === "ACTIVE" && <button disabled={saving} onClick={() => void changeState("attend")} className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-bold text-white">Atender</button>}{selected.status === "ATTENDED" && <button disabled={saving} onClick={() => void changeState("resolve")} className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-bold text-white">Resolver</button>}<button disabled={saving || !notes.trim()} onClick={() => void changeState("dismiss")} className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-bold text-white">Descartar</button><button disabled={saving || !notes.trim()} onClick={() => void saveNote()} className="rounded-lg border border-violet-300 px-4 py-2 text-sm font-bold text-violet-800">Agregar nota</button></div><p className="mt-2 text-xs text-slate-500">Descartar y agregar nota requieren una justificación.</p></div>}
          </article>
          <aside className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-xl font-bold">Timeline de acciones</h2><div className="mt-5 space-y-0">{actions.map((action, index) => { const details = action.details as { previous_risk_score?: number; new_risk_score?: number } | null; return <div key={action.id} className="relative pl-8 pb-6"><span className="absolute left-1 top-1 h-3 w-3 rounded-full bg-violet-600" />{index < actions.length - 1 && <span className="absolute left-[9px] top-4 h-full w-px bg-violet-200" />}<p className="font-bold">{ALERT_ACTION_LABELS[action.action_type]}</p><p className="mt-1 text-xs text-slate-500">{formatDateTime(action.created_at)} · {action.actor || "Sistema"}</p>{action.notes && <p className="mt-2 text-sm text-slate-700">{action.notes}</p>}{action.action_type === "RISK_REEVALUATED" && details?.previous_risk_score != null && details.new_risk_score != null && <p className="mt-2 rounded-lg bg-violet-50 p-2 text-sm font-bold text-violet-900">{formatPercentage(details.previous_risk_score)} → {formatPercentage(details.new_risk_score)}</p>}</div>; })}</div></aside>
        </section>}
      </section>
    </main>
  );
}
