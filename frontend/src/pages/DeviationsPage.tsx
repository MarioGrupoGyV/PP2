import { useCallback, useEffect, useState } from "react";

import {
  analyzeDeviations,
  getConformanceSummary,
  getDeviation,
  getDeviations,
  getDeviationSummary,
  getExpectedModel,
} from "../services/api";
import type {
  AnalyzeDeviationsResult,
  ConformanceSummary,
  Deviation,
  DeviationList,
  DeviationSeverity,
  DeviationSummary,
  DeviationType,
} from "../types/deviations";
import type { ExpectedModel } from "../types/processMining";
import { SeverityBadge } from "../shared/components/Badges";
import { DEVIATION_TYPE_LABELS } from "../shared/constants/labels";
import { formatDateTime } from "../shared/utils/format";

const TYPES: DeviationType[] = ["SLA_BREACH", "STAGE_SKIP", "BACKTRACK", "REWORK", "INACTIVITY"];

function Card({ label, value }: { label: string; value: string | number }) {
  return <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p><p className="mt-2 text-3xl font-bold text-slate-950">{value}</p></article>;
}

export function DeviationsPage() {
  const [summary, setSummary] = useState<DeviationSummary | null>(null);
  const [conformance, setConformance] = useState<ConformanceSummary | null>(null);
  const [model, setModel] = useState<ExpectedModel | null>(null);
  const [list, setList] = useState<DeviationList | null>(null);
  const [selected, setSelected] = useState<Deviation | null>(null);
  const [type, setType] = useState<DeviationType | "">("");
  const [severity, setSeverity] = useState<DeviationSeverity | "">("");
  const [caseCode, setCaseCode] = useState(() => new URLSearchParams(window.location.search).get("case") || "");
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalyzeDeviationsResult | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setFailure(null);
    try {
      const [summaryResult, conformanceResult, modelResult, listResult] = await Promise.all([
        getDeviationSummary(), getConformanceSummary(), getExpectedModel(),
        getDeviations({ type, severity, caseCode: caseCode.trim() }),
      ]);
      setSummary(summaryResult); setConformance(conformanceResult); setModel(modelResult); setList(listResult);
    } catch (error) { setFailure(error instanceof Error ? error.message : "No se pudo cargar el análisis"); }
    finally { setLoading(false); }
  }, [type, severity, caseCode]);

  useEffect(() => { void load(); }, [load]);

  async function runAnalysis() {
    setAnalyzing(true); setFailure(null);
    try { setResult(await analyzeDeviations()); await load(); }
    catch (error) { setFailure(error instanceof Error ? error.message : "No se pudo ejecutar el análisis"); }
    finally { setAnalyzing(false); }
  }

  async function showDetail(id: string) {
    try { setSelected(await getDeviation(id)); }
    catch (error) { setFailure(error instanceof Error ? error.message : "No se pudo cargar el detalle"); }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-8">
      <section className="mx-auto max-w-[1450px] space-y-7">
        <header className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div><span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold uppercase tracking-wide text-amber-800">Sprint 4 · Conformance Checking</span><h1 className="mt-4 text-4xl font-bold text-slate-950">Desviaciones del proceso</h1><p className="mt-2 text-slate-600">Compara las trazas históricas con el flujo y los SLA configurados.</p></div>
          <button type="button" onClick={() => void runAnalysis()} disabled={analyzing} className="rounded-xl bg-amber-600 px-5 py-3 font-semibold text-white hover:bg-amber-700 disabled:opacity-60">{analyzing ? "Analizando…" : "Analizar desviaciones"}</button>
        </header>

        {failure && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-800">{failure}</div>}
        {result && <div className="grid gap-3 rounded-xl border border-teal-200 bg-teal-50 p-4 text-sm text-teal-900 sm:grid-cols-4"><span><strong>{result.cases_analyzed}</strong> casos analizados</span><span><strong>{result.deviations_detected}</strong> detectadas</span><span><strong>{result.deviations_created}</strong> nuevas</span><span><strong>{result.deviations_existing}</strong> ya existentes</span></div>}

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <Card label="Desviaciones" value={summary?.total_deviations ?? "—"} />
          <Card label="Casos afectados" value={summary?.affected_cases ?? "—"} />
          <Card label="Estructurales" value={summary?.structural_deviations ?? "—"} />
          <Card label="Temporales" value={summary?.temporal_deviations ?? "—"} />
          <Card label="Conformidad" value={conformance ? `${conformance.structural_conformance_percentage.toFixed(1)}%` : "—"} />
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold">Proceso esperado</h2><div className="mt-4 flex flex-wrap items-center gap-2">{model?.stages.map((stage, index) => <div key={stage.code} className="flex items-center gap-2"><div className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3"><p className="font-bold text-slate-900">{stage.name}</p><p className="text-xs font-semibold text-teal-700">{stage.code} · SLA {stage.sla_hours} h</p></div>{index < model.stages.length - 1 && <span className="font-bold text-slate-400">→</span>}</div>)}</div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">Conformidad estructural</h2><div className="mt-4 grid gap-3 sm:grid-cols-3"><div className="rounded-xl bg-teal-50 p-4"><p className="text-xs font-semibold text-teal-700">Casos conformes</p><p className="mt-1 text-2xl font-bold">{conformance?.structurally_conforming_cases ?? "—"}</p></div><div className="rounded-xl bg-rose-50 p-4"><p className="text-xs font-semibold text-rose-700">Con desviaciones estructurales</p><p className="mt-1 text-2xl font-bold">{conformance?.structurally_nonconforming_cases ?? "—"}</p></div><div className="rounded-xl bg-slate-100 p-4"><p className="text-xs font-semibold text-slate-600">Conformidad</p><p className="mt-1 text-2xl font-bold">{conformance ? `${conformance.structural_conformance_percentage.toFixed(2)}%` : "—"}</p></div></div></section>

        <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-3 lg:flex-row"><select aria-label="Tipo" value={type} onChange={(event) => setType(event.target.value as DeviationType | "")} className="rounded-lg border border-slate-300 px-3 py-2"><option value="">Todos los tipos</option>{TYPES.map((item) => <option key={item} value={item}>{DEVIATION_TYPE_LABELS[item]}</option>)}</select><select aria-label="Severidad" value={severity} onChange={(event) => setSeverity(event.target.value as DeviationSeverity | "")} className="rounded-lg border border-slate-300 px-3 py-2"><option value="">Toda severidad</option><option>LOW</option><option>MEDIUM</option><option>HIGH</option></select><input aria-label="Código de caso" value={caseCode} onChange={(event) => setCaseCode(event.target.value)} placeholder="Buscar case code" className="rounded-lg border border-slate-300 px-3 py-2" /></div>
            <div className="mt-5 overflow-x-auto"><table className="min-w-full divide-y divide-slate-200 text-left text-sm"><thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-3 py-3">Caso</th><th className="px-3 py-3">Tipo</th><th className="px-3 py-3">Severidad</th><th className="px-3 py-3">Etapa</th><th className="px-3 py-3">Detectada</th><th className="px-3 py-3">Descripción</th></tr></thead><tbody className="divide-y divide-slate-100">{list?.items.map((item) => <tr key={item.id} tabIndex={0} aria-label={`Ver desviación de ${item.case_code}`} onClick={() => void showDetail(item.id)} onKeyDown={(event) => { if (event.key === "Enter") void showDetail(item.id); }} className="cursor-pointer hover:bg-amber-50"><td className="px-3 py-3 font-semibold"><a href={`/cases/${item.case_id}`} onClick={(event) => event.stopPropagation()} className="text-brand-700 hover:underline">{item.case_code}</a></td><td className="px-3 py-3">{DEVIATION_TYPE_LABELS[item.type]}</td><td className="px-3 py-3"><SeverityBadge severity={item.severity} /></td><td className="px-3 py-3">{item.stage_code ?? "—"}</td><td className="whitespace-nowrap px-3 py-3">{formatDateTime(item.detected_at)}</td><td className="max-w-xs px-3 py-3 text-slate-600">{item.description}</td></tr>)}</tbody></table>{!loading && list?.total === 0 && <p className="py-10 text-center text-slate-500">No hay desviaciones con estos filtros.</p>}</div>
          </div>
          <aside className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">Detalle</h2>{selected ? <div className="mt-4 space-y-4 text-sm"><div><p className="text-xs text-slate-500">Caso y tipo</p><p className="font-bold">{selected.case_code} · {DEVIATION_TYPE_LABELS[selected.type]}</p><a href={`/cases/${selected.case_id}`} className="mt-1 inline-block font-bold text-brand-700 hover:underline">Ver caso completo</a></div><div className="flex items-center gap-2"><SeverityBadge severity={selected.severity} /><span className="text-slate-500">{selected.stage_code ?? "Sin etapa"}</span></div><p>{selected.description}</p><p className="text-xs text-slate-500">Detectada: {formatDateTime(selected.detected_at)}</p><div><p className="font-semibold">Valor esperado</p><pre className="mt-1 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100">{JSON.stringify(selected.expected_value, null, 2)}</pre></div><div><p className="font-semibold">Valor real</p><pre className="mt-1 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100">{JSON.stringify(selected.actual_value, null, 2)}</pre></div></div> : <p className="mt-4 text-sm text-slate-500">Selecciona una fila para comprender la desviación.</p>}</aside>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">Distribución por tipo</h2><div className="mt-4 grid gap-3 sm:grid-cols-5">{TYPES.map((item) => <div key={item} className="rounded-xl bg-slate-50 p-3"><p className="text-xs font-semibold text-slate-500">{DEVIATION_TYPE_LABELS[item]}</p><p className="mt-1 text-2xl font-bold">{summary?.by_type[item] ?? 0}</p></div>)}</div></section>
      </section>
    </main>
  );
}
