import { useCallback, useEffect, useMemo, useState } from "react";

import { getCaseByCode, getCases, getProcessStages } from "../services/api";
import type { CommercialCase, CommercialCaseList, ProcessStage } from "../types/cases";
import { CaseStatusBadge } from "../shared/components/Badges";
import { PageHeader, SectionCard } from "../shared/components/Layout";
import { EmptyState, ErrorState, LoadingState } from "../shared/components/States";
import { formatDateTime } from "../shared/utils/format";
import { MANUAL_REGISTRATION_LABELS } from "../shared/constants/labels";
import { NewCaseForm } from "../features/cases/NewCaseForm";

export function CasesPage() {
  const [result, setResult] = useState<CommercialCaseList | null>(null);
  const [stages, setStages] = useState<ProcessStage[]>([]);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewCase, setShowNewCase] = useState(false);

  const load = useCallback(async (targetPage = page) => {
    setLoading(true); setError(null);
    try {
      const [cases, stageList] = await Promise.all([getCases(targetPage, 20), getProcessStages()]);
      setResult(cases); setStages(stageList); setPage(targetPage);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudieron cargar los casos"); }
    finally { setLoading(false); }
  }, [page]);

  useEffect(() => { void load(1); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const stageById = useMemo(() => Object.fromEntries(stages.map((stage) => [stage.id, stage])), [stages]);

  async function search(event: React.FormEvent) {
    event.preventDefault();
    if (!query.trim()) { await load(1); return; }
    setLoading(true); setError(null);
    try {
      const item = await getCaseByCode(query.trim().toUpperCase());
      setResult({ items: [item], page: 1, page_size: 20, total: 1 });
    } catch (reason) {
      setResult({ items: [], page: 1, page_size: 20, total: 0 });
      setError(reason instanceof Error ? reason.message : "No se encontró el caso");
    } finally { setLoading(false); }
  }

  return <main className="px-4 py-6 sm:px-6 lg:px-8"><div className="mx-auto max-w-[1500px] space-y-6"><PageHeader eyebrow="Operación comercial" title="Casos" description="Consulta paginada de las instancias del proceso y acceso a su trazabilidad integral." action={<button type="button" disabled={stages.length === 0} aria-expanded={showNewCase} onClick={() => setShowNewCase((current) => !current)} className="rounded-lg bg-brand-700 px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-800 disabled:opacity-50">{MANUAL_REGISTRATION_LABELS.newCase}</button>} />
    {showNewCase && stages.length > 0 && <NewCaseForm stages={stages} onCancel={() => setShowNewCase(false)} />}
    <SectionCard><form onSubmit={(event) => void search(event)} className="flex flex-col gap-2 sm:flex-row"><label className="flex-1 text-sm font-bold text-ink-950">Buscar por código exacto<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="DEMO-00141" className="mt-1 w-full rounded-lg border border-line px-3 py-2 font-normal" /></label><div className="flex items-end gap-2"><button className="rounded-lg bg-brand-700 px-4 py-2 text-sm font-bold text-white">Buscar</button><button type="button" onClick={() => { setQuery(""); void load(1); }} className="rounded-lg border border-line px-4 py-2 text-sm font-bold">Limpiar</button></div></form></SectionCard>
    {loading && <LoadingState />}{error && <ErrorState message={error} onRetry={() => void load(page)} />}
    {!loading && result && <SectionCard title={`${result.total} caso${result.total === 1 ? "" : "s"}`} description="Ordenados por fecha de registro"><div className="overflow-x-auto"><table className="min-w-full divide-y divide-line text-left text-sm"><thead className="bg-surface-muted text-xs uppercase text-muted"><tr><th className="px-3 py-3">Código</th><th className="px-3 py-3">Etapa actual</th><th className="px-3 py-3">Estado</th><th className="px-3 py-3">Fuente</th><th className="px-3 py-3">Recurso / asesor</th><th className="px-3 py-3">Inicio</th><th className="px-3 py-3"><span className="sr-only">Acción</span></th></tr></thead><tbody className="divide-y divide-line">{result.items.map((item: CommercialCase) => <tr key={item.id}><td className="px-3 py-3 font-bold text-ink-950">{item.case_code}</td><td className="px-3 py-3">{stageById[item.current_stage_id]?.name ?? "Etapa no disponible"}</td><td className="px-3 py-3"><CaseStatusBadge status={item.status} /></td><td className="px-3 py-3">{item.source || "—"}</td><td className="px-3 py-3">{item.assigned_resource || "—"}</td><td className="whitespace-nowrap px-3 py-3">{formatDateTime(item.started_at)}</td><td className="px-3 py-3 text-right"><a href={`/cases/${item.id}`} className="font-bold text-brand-700">Ver detalle</a></td></tr>)}</tbody></table></div>{result.items.length === 0 && !error && <EmptyState title="No hay casos" description="Importa un Event Log o usa «Nuevo caso» para registrar uno manualmente." actionHref="/imports" actionLabel="Ir a Importaciones" />}{result.total > result.page_size && <div className="mt-4 flex items-center justify-between border-t border-line pt-4"><button disabled={page <= 1} onClick={() => void load(page - 1)} className="rounded-lg border border-line px-3 py-2 text-sm font-bold disabled:opacity-40">Anterior</button><span className="text-sm text-muted">Página {page} de {Math.ceil(result.total / result.page_size)}</span><button disabled={page >= Math.ceil(result.total / result.page_size)} onClick={() => void load(page + 1)} className="rounded-lg border border-line px-3 py-2 text-sm font-bold disabled:opacity-40">Siguiente</button></div>}</SectionCard>}
  </div></main>;
}
