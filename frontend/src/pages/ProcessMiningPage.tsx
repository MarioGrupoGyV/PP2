import { useCallback, useEffect, useMemo, useState } from "react";

import { ProcessGraph } from "../components/process-mining/ProcessGraph";
import {
  getProcessDfg,
  getProcessMiningSummary,
  getProcessTransitions,
  getProcessVariants,
  getVariantCases,
} from "../services/api";
import type {
  DfgResponse,
  ProcessMiningSummary,
  TransitionStatistic,
  VariantCasesResponse,
  VariantStatistic,
} from "../types/processMining";
import { formatDuration } from "../utils/duration";

type AnalysisState = {
  summary: ProcessMiningSummary;
  dfg: DfgResponse;
  transitions: TransitionStatistic[];
  variants: VariantStatistic[];
};

function messageFrom(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "No fue posible cargar el análisis del proceso";
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.13em] text-slate-500">
        {label}
      </p>
      <p className="mt-2 text-3xl font-bold tracking-tight text-slate-950">{value}</p>
    </article>
  );
}

export function ProcessMiningPage() {
  const [analysis, setAnalysis] = useState<AnalysisState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [failure, setFailure] = useState<string | null>(null);
  const [selectedActivity, setSelectedActivity] = useState<string | null>(null);
  const [selectedTransition, setSelectedTransition] =
    useState<TransitionStatistic | null>(null);
  const [selectedVariant, setSelectedVariant] =
    useState<VariantStatistic | null>(null);
  const [variantCases, setVariantCases] =
    useState<VariantCasesResponse | null>(null);
  const [isLoadingCases, setIsLoadingCases] = useState(false);
  const [caseFailure, setCaseFailure] = useState<string | null>(null);

  const loadAnalysis = useCallback(async () => {
    setIsLoading(true);
    setFailure(null);
    try {
      const [summary, dfg, transitions, variants] = await Promise.all([
        getProcessMiningSummary(),
        getProcessDfg(),
        getProcessTransitions(),
        getProcessVariants(20),
      ]);
      setAnalysis({ summary, dfg, transitions, variants });
    } catch (requestFailure) {
      setAnalysis(null);
      setFailure(messageFrom(requestFailure));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAnalysis();
  }, [loadAnalysis]);

  const selectedNode = useMemo(
    () => analysis?.dfg.nodes.find((item) => item.activity === selectedActivity),
    [analysis, selectedActivity],
  );
  const longestTransition = useMemo(
    () =>
      analysis?.transitions.reduce<TransitionStatistic | null>(
        (longest, item) =>
          !longest || item.average_duration_seconds > longest.average_duration_seconds
            ? item
            : longest,
        null,
      ) ?? null,
    [analysis],
  );

  async function selectVariant(variant: VariantStatistic) {
    setSelectedVariant(variant);
    setVariantCases(null);
    setCaseFailure(null);
    setIsLoadingCases(true);
    try {
      setVariantCases(await getVariantCases(variant.variant_id));
    } catch (requestFailure) {
      setCaseFailure(messageFrom(requestFailure));
    } finally {
      setIsLoadingCases(false);
    }
  }

  function selectActivity(activity: string) {
    setSelectedActivity(activity);
    setSelectedTransition(null);
  }

  function selectTransition(transition: TransitionStatistic) {
    setSelectedTransition(transition);
    setSelectedActivity(null);
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-7 sm:px-8 lg:py-10">
      <section className="mx-auto max-w-[1500px]">
        <nav className="mb-7 flex flex-wrap items-center justify-between gap-3">
          <a href="/" className="text-sm font-semibold text-slate-600 hover:text-slate-950">
            ← Estado técnico
          </a>
          <a
            href="/imports"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:border-teal-500 hover:text-teal-700"
          >
            Importar Event Log
          </a>
        </nav>

        <header className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <div className="mb-3 inline-flex rounded-full bg-teal-100 px-3 py-1 text-xs font-bold uppercase tracking-[0.14em] text-teal-700">
              Sprint 3 · Proceso observado
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">
              Minería de Procesos
            </h1>
            <p className="mt-3 text-base leading-7 text-slate-600">
              Descubrimiento del flujo real desde los eventos STAGE_CHANGE almacenados en PostgreSQL.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadAnalysis()}
            disabled={isLoading}
            className="w-fit rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-wait disabled:opacity-60"
          >
            {isLoading ? "Analizando…" : "Actualizar análisis"}
          </button>
        </header>

        {isLoading && (
          <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
            <div className="h-5 w-52 animate-pulse rounded bg-slate-200" />
            <div className="mt-5 h-72 animate-pulse rounded-xl bg-slate-100" />
            <p className="mt-4 text-sm text-slate-500">Descubriendo rutas y frecuencias…</p>
          </section>
        )}

        {!isLoading && failure && (
          <section role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-6">
            <h2 className="font-bold text-rose-950">No se pudo cargar el análisis</h2>
            <p className="mt-2 text-sm text-rose-800">{failure}</p>
            <button
              type="button"
              onClick={() => void loadAnalysis()}
              className="mt-4 rounded-lg bg-rose-700 px-4 py-2 text-sm font-semibold text-white"
            >
              Reintentar
            </button>
          </section>
        )}

        {!isLoading && analysis?.summary.total_events === 0 && (
          <section className="rounded-2xl border border-amber-200 bg-amber-50 p-8 text-center">
            <h2 className="text-xl font-bold text-amber-950">
              No existen suficientes eventos para realizar minería de procesos.
            </h2>
            <p className="mt-2 text-sm text-amber-800">
              Importa un Event Log para descubrir el proceso comercial observado.
            </p>
            <a
              href="/imports"
              className="mt-5 inline-flex rounded-xl bg-amber-800 px-4 py-2.5 text-sm font-semibold text-white"
            >
              Ir a importaciones
            </a>
          </section>
        )}

        {!isLoading && analysis && analysis.summary.total_events > 0 && (
          <div className="space-y-8">
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="Casos" value={analysis.summary.total_cases.toLocaleString("es-PE")} />
              <MetricCard label="Eventos" value={analysis.summary.total_events.toLocaleString("es-PE")} />
              <MetricCard label="Actividades" value={analysis.summary.unique_activities.toLocaleString("es-PE")} />
              <MetricCard label="Variantes" value={analysis.summary.total_variants.toLocaleString("es-PE")} />
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
              <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-xl font-bold text-slate-950">Mapa del proceso</h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Selecciona una actividad o transición para consultar sus métricas.
                  </p>
                </div>
                <p className="text-xs font-semibold text-slate-500">
                  {analysis.dfg.start_activities.length} inicio(s) · {analysis.dfg.end_activities.length} fin(es)
                </p>
              </div>

              <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_310px]">
                <ProcessGraph
                  dfg={analysis.dfg}
                  transitions={analysis.transitions}
                  onSelectActivity={selectActivity}
                  onSelectTransition={selectTransition}
                />
                <aside className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                  <h3 className="text-sm font-bold uppercase tracking-wide text-slate-500">
                    Detalle seleccionado
                  </h3>
                  {selectedNode ? (
                    <dl className="mt-5 space-y-4">
                      <div><dt className="text-xs text-slate-500">Actividad</dt><dd className="mt-1 font-bold text-slate-950">{selectedNode.activity}</dd></div>
                      <div><dt className="text-xs text-slate-500">Eventos</dt><dd className="mt-1 text-2xl font-bold">{selectedNode.frequency.toLocaleString("es-PE")}</dd></div>
                      <div><dt className="text-xs text-slate-500">Casos</dt><dd className="mt-1 text-2xl font-bold">{selectedNode.case_frequency.toLocaleString("es-PE")}</dd></div>
                    </dl>
                  ) : selectedTransition ? (
                    <dl className="mt-5 space-y-4">
                      <div><dt className="text-xs text-slate-500">Transición observada</dt><dd className="mt-1 font-bold text-slate-950">{selectedTransition.source} → {selectedTransition.target}</dd></div>
                      <div className="grid grid-cols-2 gap-3">
                        <div><dt className="text-xs text-slate-500">Frecuencia</dt><dd className="mt-1 text-xl font-bold">{selectedTransition.frequency}</dd></div>
                        <div><dt className="text-xs text-slate-500">Casos</dt><dd className="mt-1 text-xl font-bold">{selectedTransition.case_frequency}</dd></div>
                      </div>
                      <div><dt className="text-xs text-slate-500">Tiempo promedio</dt><dd className="mt-1 font-bold">{formatDuration(selectedTransition.average_duration_seconds)}</dd></div>
                      <div><dt className="text-xs text-slate-500">Tiempo mediano</dt><dd className="mt-1 font-bold">{formatDuration(selectedTransition.median_duration_seconds)}</dd></div>
                    </dl>
                  ) : (
                    <p className="mt-5 text-sm leading-6 text-slate-500">
                      El mapa conserva todas las rutas observadas. Haz clic en un nodo o una conexión.
                    </p>
                  )}

                  {longestTransition && (
                    <div className="mt-6 border-t border-slate-200 pt-5">
                      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                        Mayor duración observada
                      </p>
                      <p className="mt-2 text-sm font-semibold text-slate-800">
                        {longestTransition.source} → {longestTransition.target}
                      </p>
                      <p className="mt-1 text-sm text-slate-600">
                        Promedio: {formatDuration(longestTransition.average_duration_seconds)}
                      </p>
                    </div>
                  )}
                </aside>
              </div>
            </section>

            <section className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
                <h2 className="text-xl font-bold text-slate-950">Variantes</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Principales secuencias descubiertas, ordenadas por cantidad de casos.
                </p>
                <div className="mt-5 overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                    <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                      <tr><th className="px-4 py-3">Ruta</th><th className="px-4 py-3">Casos</th><th className="px-4 py-3">Porcentaje</th></tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {analysis.variants.map((variant) => (
                        <tr
                          key={variant.variant_id}
                          onClick={() => void selectVariant(variant)}
                          className={`cursor-pointer transition hover:bg-teal-50 ${selectedVariant?.variant_id === variant.variant_id ? "bg-teal-50" : ""}`}
                        >
                          <td className="max-w-2xl px-4 py-3 font-semibold text-slate-800">{variant.activities.join(" → ")}</td>
                          <td className="px-4 py-3">{variant.case_count}</td>
                          <td className="px-4 py-3">{variant.percentage.toFixed(2)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <aside className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
                <h2 className="text-lg font-bold text-slate-950">Detalle de variante</h2>
                {!selectedVariant ? (
                  <p className="mt-4 text-sm leading-6 text-slate-500">
                    Selecciona una ruta para ver su secuencia y algunos casos asociados.
                  </p>
                ) : (
                  <div className="mt-4">
                    <div className="flex flex-wrap gap-2">
                      {selectedVariant.activities.map((activity, index) => (
                        <span key={`${activity}-${index}`} className="rounded-lg bg-teal-50 px-2.5 py-1.5 text-xs font-semibold text-teal-800">
                          {index > 0 ? "→ " : ""}{activity}
                        </span>
                      ))}
                    </div>
                    <p className="mt-4 text-sm text-slate-600">
                      <strong>{selectedVariant.case_count}</strong> casos · {selectedVariant.percentage.toFixed(2)}%
                    </p>
                    {isLoadingCases && <p className="mt-4 text-sm text-slate-500">Consultando casos…</p>}
                    {caseFailure && <p role="alert" className="mt-4 text-sm font-medium text-rose-700">{caseFailure}</p>}
                    {variantCases && (
                      <div className="mt-5 border-t border-slate-200 pt-4">
                        <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Case codes</p>
                        <ul className="mt-3 grid grid-cols-2 gap-2">
                          {variantCases.cases.map((item) => (
                            <li key={item.id} className="rounded-lg bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700">{item.case_code}</li>
                          ))}
                        </ul>
                        {variantCases.total_pages > 1 && (
                          <p className="mt-3 text-xs text-slate-500">Mostrando la primera página de {variantCases.total_pages}.</p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </aside>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div><h2 className="text-xl font-bold text-slate-950">Transiciones</h2><p className="mt-1 text-sm text-slate-500">Frecuencias y tiempos observados entre actividades consecutivas.</p></div>
                <p className="text-xs text-slate-500">Duración media del caso: <strong>{formatDuration(analysis.summary.average_case_duration_seconds)}</strong></p>
              </div>
              <div className="mt-5 overflow-x-auto rounded-xl border border-slate-200">
                <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-4 py-3">Origen</th><th className="px-4 py-3">Destino</th><th className="px-4 py-3">Frecuencia</th><th className="px-4 py-3">Casos</th><th className="px-4 py-3">Tiempo promedio</th><th className="px-4 py-3">Tiempo mediano</th></tr></thead>
                  <tbody className="divide-y divide-slate-100">
                    {analysis.transitions.map((item) => (
                      <tr key={`${item.source}-${item.target}`} onClick={() => selectTransition(item)} className="cursor-pointer hover:bg-teal-50">
                        <td className="px-4 py-3 font-semibold text-slate-800">{item.source}</td><td className="px-4 py-3 font-semibold text-slate-800">{item.target}</td><td className="px-4 py-3">{item.frequency}</td><td className="px-4 py-3">{item.case_frequency}</td><td className="whitespace-nowrap px-4 py-3">{formatDuration(item.average_duration_seconds)}</td><td className="whitespace-nowrap px-4 py-3">{formatDuration(item.median_duration_seconds)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        )}
      </section>
    </main>
  );
}
