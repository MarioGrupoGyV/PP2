import { useCallback, useEffect, useMemo, useState } from "react";

import {
  evaluateCaseAlert,
  getAlerts,
  getPredictions,
  predictCase,
} from "../services/api";
import type { Alert, AlertEvaluation } from "../types/alerts";
import type { Prediction } from "../types/predictions";
import { AlertStatusBadge, RiskBadge } from "../shared/components/Badges";
import { DatasetNotice, PageHeader, SectionCard } from "../shared/components/Layout";
import { EmptyState, ErrorState, LoadingState } from "../shared/components/States";
import { ALERT_STATUS_LABELS } from "../shared/constants/labels";
import { formatDateTime, formatPercentage } from "../shared/utils/format";

export function DemoPage() {
  const [highCandidates, setHighCandidates] = useState<Prediction[]>([]);
  const [lowCandidates, setLowCandidates] = useState<Prediction[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [highId, setHighId] = useState<string>("");
  const [lowId, setLowId] = useState<string>("");
  const [replayed, setReplayed] = useState<Prediction | null>(null);
  const [evaluation, setEvaluation] = useState<AlertEvaluation | null>(null);
  const [working, setWorking] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [high, low, alertList] = await Promise.all([
        getPredictions({ riskLevel: "HIGH", predictedLabel: true, pageSize: 100 }),
        getPredictions({ riskLevel: "LOW", pageSize: 100 }),
        getAlerts({ pageSize: 100 }),
      ]);
      const highItems = high.items.filter((item) => item.prediction_applicable && item.predicted_label);
      const lowItems = low.items.filter((item) => item.prediction_applicable);
      const caseIdsWithAlerts = new Set(alertList.items.map((item) => item.case_id));
      highItems.sort((a, b) => Number(caseIdsWithAlerts.has(a.case_id)) - Number(caseIdsWithAlerts.has(b.case_id)) || (b.risk_score ?? 0) - (a.risk_score ?? 0));
      lowItems.sort((a, b) => (a.risk_score ?? 1) - (b.risk_score ?? 1));
      setHighCandidates(highItems); setLowCandidates(lowItems); setAlerts(alertList.items);
      setHighId((current) => current || highItems[0]?.id || "");
      setLowId((current) => current || lowItems[0]?.id || "");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudieron seleccionar escenarios reales"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);
  const high = useMemo(() => highCandidates.find((item) => item.id === highId) ?? highCandidates[0] ?? null, [highCandidates, highId]);
  const low = useMemo(() => lowCandidates.find((item) => item.id === lowId) ?? lowCandidates[0] ?? null, [lowCandidates, lowId]);
  const highAlert = useMemo(() => alerts.find((item) => item.case_id === high?.case_id) ?? evaluation?.alert ?? null, [alerts, evaluation, high]);
  const lowAlert = useMemo(() => alerts.find((item) => item.case_id === low?.case_id) ?? null, [alerts, low]);

  async function replayHigh() {
    if (!high) return;
    setWorking(true); setError(null);
    try { setReplayed(await predictCase(high.case_id, high.snapshot_timestamp)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo reproducir la predicción"); }
    finally { setWorking(false); }
  }

  async function evaluateHigh() {
    if (!high) return;
    setWorking(true); setError(null);
    try {
      const result = await evaluateCaseAlert(high.case_id, high.snapshot_timestamp);
      setEvaluation(result);
      const alertList = await getAlerts({ pageSize: 100 });
      setAlerts(alertList.items);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo evaluar la alerta"); }
    finally { setWorking(false); }
  }

  return <main className="px-4 py-6 sm:px-6 lg:px-8"><div className="mx-auto max-w-[1300px] space-y-6"><PageHeader eyebrow="Recorrido académico · 3–5 minutos" title="Modo demostración" description="Escenarios seleccionados dinámicamente desde predicciones y alertas persistidas. No utiliza ground truth ni modifica el Event Log." action={<a href="/" className="rounded-lg border border-line bg-white px-4 py-2 text-sm font-bold">Volver al Dashboard</a>} /><DatasetNotice />
    {loading && <LoadingState label="Seleccionando escenarios" />}{error && <ErrorState message={error} onRetry={() => void load()} />}
    {!loading && <div className="grid gap-6 xl:grid-cols-2">
      <SectionCard title="Escenario A · Riesgo alto" description="Predicción elegible sobre el threshold operativo"><div className="space-y-5">{high ? <><label className="block text-sm font-bold">Candidato real<select value={high.id ?? ""} onChange={(event) => { setHighId(event.target.value); setReplayed(null); setEvaluation(null); }} className="mt-1 w-full rounded-lg border border-line px-3 py-2 font-normal">{highCandidates.map((item) => <option key={item.id ?? item.snapshot_timestamp} value={item.id ?? ""}>{item.case_code} · {formatPercentage(item.risk_score)}</option>)}</select></label><ol className="space-y-3" aria-label="Pasos del escenario de riesgo alto"><DemoStep number="1" title="Estado del caso" complete detail={high.case_code} /><DemoStep number="2" title="Reproducción histórica" complete={Boolean(replayed)} detail={formatDateTime(high.snapshot_timestamp)} /><DemoStep number="3" title="Predicción" complete detail={`Riesgo estimado ${formatPercentage((replayed ?? high).risk_score)}`} /><DemoStep number="4" title="Alerta predictiva" complete={Boolean(highAlert || evaluation?.alert)} detail={highAlert?.alert_code ?? evaluation?.message ?? "Pendiente de evaluación"} /><DemoStep number="5" title="Gestión operativa" complete={Boolean(highAlert && highAlert.status !== "ACTIVE")} detail={highAlert ? ALERT_STATUS_LABELS[highAlert.status] : "Pendiente"} /></ol><div className="rounded-lg border border-red-200 bg-red-50 p-4"><div className="flex items-center justify-between gap-3"><div><p className="text-xs font-bold uppercase text-red-800">Riesgo estimado</p><p className="mt-1 text-4xl font-bold text-red-950">{formatPercentage((replayed ?? high).risk_score)}</p></div>{high.risk_level && <RiskBadge level={high.risk_level} />}</div><p className="mt-2 text-xs text-red-800">Modelo {high.model_version} · etiqueta predictiva positiva</p></div><div className="flex flex-wrap gap-2"><button disabled={working} onClick={() => void replayHigh()} className="rounded-lg bg-brand-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">Reproducir predicción</button><button disabled={working} onClick={() => void evaluateHigh()} className="rounded-lg border border-brand-700 px-4 py-2 text-sm font-bold text-brand-700 disabled:opacity-50">Evaluar alerta</button><a href={`/cases/${high.case_id}`} className="rounded-lg border border-line px-4 py-2 text-sm font-bold">Ver caso</a>{highAlert && <a href={`/alerts?case=${encodeURIComponent(high.case_code)}`} className="rounded-lg border border-line px-4 py-2 text-sm font-bold">Ver alerta existente</a>}</div>{highAlert && <div className="flex items-center justify-between rounded-lg bg-surface-muted p-3"><span className="text-sm font-bold">{highAlert.alert_code}</span><AlertStatusBadge status={highAlert.status} /></div>}</> : <EmptyState title="Sin candidato HIGH" description="No existe una predicción persistida que cumpla las reglas del escenario." />}</div></SectionCard>
      <SectionCard title="Escenario B · Riesgo bajo" description="Predicción persistida que no genera alerta"><div className="space-y-5">{low ? <><label className="block text-sm font-bold">Candidato real<select value={low.id ?? ""} onChange={(event) => setLowId(event.target.value)} className="mt-1 w-full rounded-lg border border-line px-3 py-2 font-normal">{lowCandidates.map((item) => <option key={item.id ?? item.snapshot_timestamp} value={item.id ?? ""}>{item.case_code} · {formatPercentage(item.risk_score)}</option>)}</select></label><div className="rounded-lg border border-sky-200 bg-sky-50 p-5"><div className="flex items-center justify-between gap-3"><div><p className="text-xs font-bold uppercase text-sky-800">Riesgo estimado</p><p className="mt-1 text-4xl font-bold text-sky-950">{formatPercentage(low.risk_score)}</p></div>{low.risk_level && <RiskBadge level={low.risk_level} />}</div></div><dl className="divide-y divide-line rounded-lg border border-line"><DemoFact label="Caso" value={low.case_code} /><DemoFact label="Snapshot" value={formatDateTime(low.snapshot_timestamp)} /><DemoFact label="Predicción almacenada" value="Sí" /><DemoFact label="Alerta generada" value={lowAlert ? `Sí · ${lowAlert.alert_code}` : "No"} /><DemoFact label="Motivo" value={lowAlert ? "El caso tiene historial operativo de alertas." : "El riesgo no supera el umbral operativo."} /></dl><p className="rounded-lg bg-surface-muted p-3 text-sm font-semibold">Predicción ≠ alerta: un score puede persistirse sin originar una acción operativa.</p><a href={`/cases/${low.case_id}`} className="inline-flex rounded-lg border border-line px-4 py-2 text-sm font-bold">Ver caso LOW</a></> : <EmptyState title="Sin candidato LOW" description="No existe una predicción LOW persistida para la demostración." />}</div></SectionCard>
    </div>}
    <SectionCard title="Guion sugerido" description="Recorrido natural sin automatizar ni alterar resultados"><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{[["00:00–00:30","Dashboard"],["00:30–01:15","Minería de Procesos"],["01:15–02:00","Desviaciones"],["02:00–03:00","Caso + predicción"],["03:00–04:30","Alerta + escenario LOW"]].map(([time, label]) => <div key={time} className="rounded-lg border border-line p-3"><p className="text-xs font-bold text-brand-700">{time}</p><p className="mt-1 text-sm font-semibold">{label}</p></div>)}</div></SectionCard>
  </div></main>;
}

function DemoStep({ number, title, complete, detail }: { number: string; title: string; complete: boolean; detail: string }) {
  return <li className="flex items-center gap-3"><span aria-hidden="true" className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-black ${complete ? "bg-brand-700 text-white" : "border border-line bg-white text-muted"}`}>{complete ? "✓" : number}</span><div><p className="text-sm font-bold">{title}</p><p className="text-xs text-muted">{detail}</p></div></li>;
}

function DemoFact({ label, value }: { label: string; value: string }) {
  return <div className="flex items-start justify-between gap-4 px-4 py-3 text-sm"><dt className="text-muted">{label}</dt><dd className="text-right font-bold">{value}</dd></div>;
}
