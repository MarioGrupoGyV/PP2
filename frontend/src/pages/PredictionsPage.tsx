import { useCallback, useEffect, useState } from "react";

import {
  getActivePredictiveModel,
  getAlerts,
  getCaseByCode,
  getModelEvaluation,
  getRecentPredictions,
  predictCase,
} from "../services/api";
import type {
  ActiveModel,
  ModelEvaluation,
  Prediction,
  PredictionList,
  RiskLevel,
} from "../types/predictions";
import type { Alert } from "../types/alerts";

const LEVEL_LABEL: Record<RiskLevel, string> = { LOW: "Bajo", MEDIUM: "Medio", HIGH: "Alto" };
const LEVEL_STYLE: Record<RiskLevel, string> = {
  LOW: "bg-sky-100 text-sky-800", MEDIUM: "bg-amber-100 text-amber-800", HIGH: "bg-rose-100 text-rose-800",
};

function percentage(value: number | null | undefined): string {
  return value == null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl bg-slate-50 p-4"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p><p className="mt-1 text-2xl font-bold text-slate-950">{value}</p></div>;
}

export function PredictionsPage() {
  const [model, setModel] = useState<ActiveModel | null>(null);
  const [evaluation, setEvaluation] = useState<ModelEvaluation | null>(null);
  const [recent, setRecent] = useState<PredictionList | null>(null);
  const [openAlerts, setOpenAlerts] = useState<Record<string, Alert>>({});
  const [caseCode, setCaseCode] = useState("");
  const [asOf, setAsOf] = useState("");
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [loading, setLoading] = useState(true);
  const [predicting, setPredicting] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setFailure(null);
    try {
      const [active, metrics, predictions, alerts] = await Promise.all([
        getActivePredictiveModel(), getModelEvaluation(), getRecentPredictions(), getAlerts({ pageSize: 100 }),
      ]);
      setModel(active); setEvaluation(metrics); setRecent(predictions);
      setOpenAlerts(Object.fromEntries(alerts.items.filter((alert) => alert.status === "ACTIVE" || alert.status === "ATTENDED").map((alert) => [alert.case_id, alert])));
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "No se pudo cargar el modelo predictivo");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function calculateRisk(event: React.FormEvent) {
    event.preventDefault();
    if (!caseCode.trim()) return;
    setPredicting(true); setFailure(null); setPrediction(null);
    try {
      const commercialCase = await getCaseByCode(caseCode.trim().toUpperCase());
      const result = await predictCase(
        commercialCase.id,
        asOf ? new Date(asOf).toISOString() : undefined,
      );
      setPrediction(result);
      const [predictions, alerts] = await Promise.all([getRecentPredictions(), getAlerts({ pageSize: 100 })]);
      setRecent(predictions);
      setOpenAlerts(Object.fromEntries(alerts.items.filter((alert) => alert.status === "ACTIVE" || alert.status === "ATTENDED").map((alert) => [alert.case_id, alert])));
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "No se pudo calcular el riesgo");
    } finally { setPredicting(false); }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-8">
      <section className="mx-auto max-w-[1450px] space-y-7">
        <nav className="flex flex-wrap gap-4 text-sm font-semibold"><a href="/" className="text-slate-600 hover:text-slate-950">← Inicio</a><a href="/alerts" className="text-rose-700">Alertas</a><a href="/process-mining" className="text-teal-700">Proceso observado</a><a href="/deviations" className="text-amber-700">Desviaciones</a></nav>
        <header><span className="rounded-full bg-violet-100 px-3 py-1 text-xs font-bold uppercase tracking-wide text-violet-800">Sprint 5 · NEXT_DEVIATION</span><h1 className="mt-4 text-4xl font-bold text-slate-950">Predicción de Riesgo</h1><p className="mt-2 max-w-3xl text-slate-600">Estima el riesgo asociado a una desviación futura antes de la próxima transición. El score no es una probabilidad perfectamente calibrada ni una alerta.</p></header>

        {failure && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-800">{failure}</div>}
        {loading && <div className="rounded-2xl border border-slate-200 bg-white p-8 text-slate-500">Cargando modelo activo…</div>}

        {model && <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between"><div><h2 className="text-xl font-bold">Modelo activo</h2><p className="mt-1 text-sm text-slate-500">{model.algorithm} · {model.model_version}</p><p className="mt-1 text-xs text-slate-500">Entrenado {new Date(model.trained_at).toLocaleString("es-PE")}</p></div>{model.predictive_quality_warning && <span className="rounded-lg bg-amber-100 px-3 py-2 text-xs font-bold text-amber-800">Calidad predictiva bajo revisión</span>}</div><div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5"><Metric label="PR-AUC" value={model.test_metrics.pr_auc.toFixed(3)} /><Metric label="F1" value={model.test_metrics.f1.toFixed(3)} /><Metric label="Recall" value={model.test_metrics.recall.toFixed(3)} /><Metric label="Precision" value={model.test_metrics.precision.toFixed(3)} /><Metric label="Threshold" value={model.decision_threshold.toFixed(3)} /></div></section>}

        <section className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
          <form onSubmit={(event) => void calculateRisk(event)} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">Buscar caso</h2><label className="mt-4 block text-sm font-semibold text-slate-700">Case code<input value={caseCode} onChange={(event) => setCaseCode(event.target.value)} placeholder="DEMO-00153" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" /></label><details className="mt-4"><summary className="cursor-pointer text-sm font-semibold text-violet-700">Reproducir momento histórico</summary><label className="mt-3 block text-xs text-slate-600">Fecha de snapshot<input type="datetime-local" value={asOf} onChange={(event) => setAsOf(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></label><p className="mt-2 text-xs text-slate-500">Herramienta de demostración: ignora toda información posterior.</p></details><button disabled={predicting || !caseCode.trim()} className="mt-5 w-full rounded-xl bg-violet-700 px-4 py-3 font-semibold text-white hover:bg-violet-800 disabled:opacity-50">{predicting ? "Calculando…" : "Calcular riesgo"}</button></form>

          <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">Resultado</h2>{!prediction && <p className="mt-4 text-sm text-slate-500">Selecciona un caso para estimar su riesgo en el último evento disponible.</p>}{prediction && !prediction.prediction_applicable && <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-5"><p className="font-bold text-amber-900">Predicción temprana no aplicable</p><p className="mt-2 text-sm text-amber-800">El snapshot ya superó un umbral determinístico de SLA o inactividad.</p></div>}{prediction?.prediction_applicable && prediction.risk_level && <div className="mt-4"><div className="flex flex-wrap items-center gap-3"><h3 className="text-2xl font-bold">{prediction.case_code}</h3><span className={`rounded-full px-3 py-1 text-sm font-bold ${LEVEL_STYLE[prediction.risk_level]}`}>{LEVEL_LABEL[prediction.risk_level]}</span></div><p className="mt-5 text-sm text-slate-500">Riesgo estimado</p><p className="text-5xl font-bold tracking-tight text-slate-950">{percentage(prediction.risk_score)}</p><p className="mt-3 text-sm font-semibold text-violet-800">{prediction.predicted_label ? "Posible desviación en la próxima evolución" : "Riesgo bajo el threshold de decisión"}</p><p className="mt-1 text-xs text-slate-500">Modelo {prediction.model_version} · snapshot {new Date(prediction.snapshot_timestamp).toLocaleString("es-PE")}</p><h3 className="mt-6 font-bold">Factores asociados al riesgo</h3><div className="mt-3 grid gap-2 sm:grid-cols-2">{prediction.top_factors.map((factor) => <div key={factor.feature} className="rounded-lg bg-slate-50 p-3"><p className="break-all text-xs font-semibold text-slate-700">{factor.feature}</p><p className="mt-1 text-sm font-bold text-slate-900">{factor.value == null ? "Sin valor" : String(factor.value)}</p><p className="mt-1 text-xs text-slate-500">{factor.direction === "INCREASES_RISK" ? "Aumenta asociación" : factor.direction === "DECREASES_RISK" ? "Disminuye asociación" : "Importancia global"}</p></div>)}</div></div>}</article>
        </section>

        {recent && <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-xl font-bold">Predicciones recientes</h2><div className="mt-4 overflow-x-auto"><table className="min-w-full divide-y divide-slate-200 text-left text-sm"><thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-3 py-3">Caso</th><th className="px-3 py-3">Riesgo</th><th className="px-3 py-3">Nivel</th><th className="px-3 py-3">Modelo</th><th className="px-3 py-3">Fecha</th><th className="px-3 py-3">Alerta</th></tr></thead><tbody className="divide-y divide-slate-100">{recent.items.map((item) => <tr key={item.id}><td className="px-3 py-3 font-semibold">{item.case_code}</td><td className="px-3 py-3">{percentage(item.risk_score)}</td><td className="px-3 py-3">{item.risk_level ? LEVEL_LABEL[item.risk_level] : "—"}</td><td className="max-w-xs truncate px-3 py-3 text-xs">{item.model_version}</td><td className="whitespace-nowrap px-3 py-3">{item.predicted_at ? new Date(item.predicted_at).toLocaleString("es-PE") : "—"}</td><td className="px-3 py-3">{openAlerts[item.case_id] ? <a href={`/alerts?case=${encodeURIComponent(item.case_code)}`} className="font-bold text-rose-700">Ver alerta</a> : "—"}</td></tr>)}</tbody></table></div></section>}

        {evaluation && <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-xl font-bold">Evaluación del modelo</h2><p className="mt-1 text-sm text-slate-500">Test reservado, utilizado una vez después de seleccionar algoritmo y threshold.</p><div className="mt-4 grid gap-3 sm:grid-cols-5"><Metric label="Precision" value={evaluation.test_metrics.precision.toFixed(3)} /><Metric label="Recall" value={evaluation.test_metrics.recall.toFixed(3)} /><Metric label="F1" value={evaluation.test_metrics.f1.toFixed(3)} /><Metric label="ROC-AUC" value={evaluation.test_metrics.roc_auc.toFixed(3)} /><Metric label="PR-AUC" value={evaluation.test_metrics.pr_auc.toFixed(3)} /></div><div className="mt-5"><h3 className="font-bold">Matriz de confusión</h3><div className="mt-2 grid w-fit grid-cols-2 gap-2">{evaluation.confusion_matrix.flat().map((value, index) => <div key={index} className="flex h-16 w-24 items-center justify-center rounded-lg bg-violet-50 text-xl font-bold text-violet-900">{value}</div>)}</div></div></section>}
      </section>
    </main>
  );
}
