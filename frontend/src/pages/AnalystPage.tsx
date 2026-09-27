import { useCallback, useEffect, useMemo, useState } from "react";

import { askAnalyst, getAnalystStatus, getCases } from "../services/api";
import type {
  AnalystChatResponse,
  AnalystEvidence,
  AnalystHistoryMessage,
  AnalystStatus,
} from "../types/analyst";
import { PageHeader, SectionCard } from "../shared/components/Layout";
import { ErrorState, LoadingState } from "../shared/components/States";

interface ConversationMessage extends AnalystHistoryMessage {
  response?: AnalystChatResponse;
}

const GENERAL_SUGGESTIONS = [
  "¿Cuál es la variante más frecuente?",
  "¿Qué transición tiene mayor duración?",
  "¿Cuántos casos tienen retrabajo?",
  "Resume las desviaciones detectadas.",
];

const TOOL_LABELS: Record<string, string> = {
  get_case: "Caso",
  get_case_timeline: "Timeline",
  get_case_conformance: "Conformidad",
  get_case_deviations: "Desviaciones del caso",
  get_case_prediction: "Riesgo estimado",
  get_case_alerts: "Alertas del caso",
  get_process_summary: "Resumen del proceso",
  get_process_variants: "Variantes",
  get_process_transitions: "Transiciones",
  get_deviation_summary: "Resumen de desviaciones",
  get_alert_summary: "Resumen de alertas",
};

const EVIDENCE_LABELS: Record<string, string> = {
  case: "Caso",
  timeline: "Timeline",
  conformance: "Conformidad",
  deviations: "Desviaciones",
  prediction: "Predicción",
  alerts: "Alertas",
  process_summary: "Proceso",
  process_variants: "Variantes",
  process_transitions: "Transiciones",
  deviation_summary: "Resumen de desviaciones",
  alert_summary: "Resumen de alertas",
};

function AnswerText({ content }: { content: string }) {
  return <div className="mt-2 space-y-1 text-sm leading-6">{content.split("\n").map((line, lineIndex) => {
    if (!line.trim()) return <div key={lineIndex} className="h-2" />;
    const parts = line.split(/(\*\*[^*]+\*\*)/g);
    return <p key={lineIndex} className={/^\s*(?:\d+\.|[-*])\s/.test(line) ? "pl-4" : ""}>{parts.map((part, partIndex) => part.startsWith("**") && part.endsWith("**") ? <strong key={partIndex}>{part.slice(2, -2)}</strong> : <span key={partIndex}>{part}</span>)}</p>;
  })}</div>;
}

function EvidenceLink({ item }: { item: AnalystEvidence }) {
  const label = [EVIDENCE_LABELS[item.type] ?? "Fuente", item.alert_code || item.case_code].filter(Boolean).join(" · ");
  if (item.alert_code && item.case_code) {
    return <a className="rounded-md border border-line bg-white px-2 py-1 text-xs font-bold text-brand-700" href={`/alerts?case=${encodeURIComponent(item.case_code)}`}>{label}</a>;
  }
  if (item.case_id) {
    return <a className="rounded-md border border-line bg-white px-2 py-1 text-xs font-bold text-brand-700" href={`/cases/${encodeURIComponent(item.case_id)}`}>{label}</a>;
  }
  return <span className="rounded-md border border-line bg-white px-2 py-1 text-xs font-semibold">{label}</span>;
}

export function AnalystPage() {
  const [status, setStatus] = useState<AnalystStatus | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [suggestedCase, setSuggestedCase] = useState<string | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const contextCase = useMemo(() => new URLSearchParams(window.location.search).get("case")?.trim().toUpperCase() || null, []);

  const loadStatus = useCallback(async () => {
    setLoadingStatus(true);
    setError(null);
    try {
      const [nextStatus, cases] = await Promise.all([
        getAnalystStatus(),
        getCases(1, 1).catch(() => null),
      ]);
      setStatus(nextStatus);
      setSuggestedCase(cases?.items[0]?.case_code ?? null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo consultar el estado del Analista IA");
    } finally {
      setLoadingStatus(false);
    }
  }, []);

  useEffect(() => { void loadStatus(); }, [loadStatus]);

  const suggestions = useMemo(() => {
    const code = contextCase || suggestedCase;
    return [
      ...GENERAL_SUGGESTIONS,
      ...(code ? [
        `¿Qué desviaciones tiene ${code}?`,
        `¿Cuál es el riesgo estimado y el estado de las alertas de ${code}?`,
      ] : []),
    ].slice(0, 6);
  }, [contextCase, suggestedCase]);

  async function submit() {
    const message = question.trim();
    if (!message || sending || !status?.available) return;
    const history = messages.slice(-10).map(({ role, content }) => ({ role, content }));
    setMessages((current) => [...current, { role: "user", content: message }]);
    setQuestion("");
    setSending(true);
    setError(null);
    try {
      const response = await askAnalyst({ message, history, context_case_code: contextCase });
      setMessages((current) => [...current, { role: "assistant", content: response.answer, response }]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo completar la consulta");
    } finally {
      setSending(false);
    }
  }

  if (loadingStatus) return <main className="px-4 py-6 sm:px-6 lg:px-8"><LoadingState label="Verificando modelo local" /></main>;

  return <main className="px-4 py-6 sm:px-6 lg:px-8"><div className="mx-auto max-w-[1400px] space-y-6">
    <PageHeader eyebrow="Consulta asistida" title="Analista IA" description="Consulta y explica la información ya calculada por los módulos del proceso comercial." action={<button type="button" onClick={() => { setMessages([]); setQuestion(""); setError(null); }} className="rounded-lg border border-line bg-white px-4 py-2 text-sm font-bold">Nueva conversación</button>} />

    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="space-y-4">
        {error && <ErrorState message={error} onRetry={!status ? () => void loadStatus() : undefined} />}
        <SectionCard className="min-h-[410px]">
          {messages.length === 0 ? <div className="py-5 text-center"><div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-brand-100 text-sm font-black text-brand-800">IA</div><h2 className="mt-4 text-xl font-bold">¿Qué deseas revisar?</h2><p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-muted">Las respuestas consultan herramientas de solo lectura. Los datos actuales son simulados y no representan resultados comerciales reales de G&amp;V.</p><div className="mx-auto mt-5 grid max-w-3xl gap-2 sm:grid-cols-2">{suggestions.map((item) => <button key={item} type="button" disabled={!status?.available} onClick={() => setQuestion(item)} className="rounded-lg border border-line bg-surface-muted px-4 py-3 text-left text-sm font-semibold hover:border-brand-500 disabled:cursor-not-allowed disabled:opacity-50">{item}</button>)}</div></div> : <div aria-live="polite" className="space-y-4">{messages.map((item, index) => <article key={`${item.role}-${index}`} className={`rounded-xl border p-4 ${item.role === "user" ? "ml-auto max-w-3xl border-brand-100 bg-brand-50" : "mr-auto max-w-4xl border-line bg-white"}`}><p className="text-xs font-bold uppercase tracking-wide text-muted">{item.role === "user" ? "Tu consulta" : "Analista IA"}</p><AnswerText content={item.content} />{item.response && <div className="mt-4 border-t border-line pt-3"><div className="flex flex-wrap items-center gap-2 text-xs text-muted"><span>{item.response.tool_rounds} ronda(s) de consulta</span><span>·</span><span>{(item.response.duration_ms / 1000).toFixed(1)} s</span><span>·</span><span>Solo lectura</span></div>{item.response.tool_calls.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{item.response.tool_calls.map((tool, toolIndex) => <span key={`${tool.name}-${toolIndex}`} className="rounded-md bg-surface-muted px-2 py-1 text-xs font-semibold">{TOOL_LABELS[tool.name] ?? "Consulta"}: {tool.status === "success" ? "completada" : tool.status === "not_found" ? "sin datos" : "no completada"}</span>)}</div>}{item.response.evidence.length > 0 && <div className="mt-3"><p className="text-xs font-bold uppercase text-muted">Evidencia consultada</p><div className="mt-2 flex flex-wrap gap-2">{item.response.evidence.map((evidence, evidenceIndex) => <EvidenceLink key={`${evidence.type}-${evidenceIndex}`} item={evidence} />)}</div></div>}</div>}</article>)}{sending && <div role="status" className="mr-auto max-w-sm rounded-xl border border-line bg-white p-4 text-sm text-muted">Consultando el modelo y las fuentes del sistema…</div>}</div>}
        </SectionCard>

        <form onSubmit={(event) => { event.preventDefault(); void submit(); }} className="rounded-xl border border-line bg-white p-4"><label htmlFor="analyst-question" className="text-sm font-bold">Pregunta al Analista</label><textarea id="analyst-question" rows={3} maxLength={2000} value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void submit(); } }} disabled={!status?.available || sending} placeholder={status?.available ? "Escribe una consulta sobre casos, variantes, desviaciones, riesgo estimado o alertas…" : "El Analista IA no está disponible"} className="mt-2 w-full resize-y rounded-lg border border-line px-3 py-3 text-sm disabled:bg-slate-50" /><div className="mt-3 flex items-center justify-between gap-3"><p className="text-xs text-muted">Enter para enviar · Shift + Enter para nueva línea</p><button type="submit" disabled={!question.trim() || !status?.available || sending} className="rounded-lg bg-brand-700 px-5 py-2.5 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50">{sending ? "Consultando…" : "Consultar"}</button></div></form>
      </div>

      <aside className="space-y-4">
        <SectionCard title="Modelo local"><div className="flex items-center justify-between gap-3"><span className="text-sm font-semibold">Estado</span><span className={`rounded-full px-3 py-1 text-xs font-bold ${status?.available ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-700"}`}>{status?.available ? "Disponible" : "No disponible"}</span></div><dl className="mt-4 space-y-3 text-sm"><div><dt className="text-xs font-bold uppercase text-muted">Modelo</dt><dd className="mt-1 break-all font-semibold">{status?.model ?? "No configurado"}</dd></div><div><dt className="text-xs font-bold uppercase text-muted">Operación</dt><dd className="mt-1">Solo consulta</dd></div></dl><p className="mt-4 rounded-lg bg-brand-50 p-3 text-xs leading-5 text-brand-800">Procesamiento mediante modelo de IA local, sin costo por llamada a una API de inferencia pagada.</p>{!status?.available && <p className="mt-3 text-xs leading-5 text-muted">{status?.message ?? "Comprueba que Ollama y el modelo configurado estén disponibles."}</p>}</SectionCard>
        {contextCase && <SectionCard title="Contexto del caso"><p className="text-sm text-muted">Las preguntas de esta conversación pueden referirse al caso:</p><p className="mt-2 font-bold text-brand-700">{contextCase}</p><p className="mt-3 text-xs text-muted">El contexto orienta la consulta; los valores concretos se obtienen siempre mediante herramientas.</p></SectionCard>}
        <SectionCard title="Alcance"><ul className="space-y-2 text-sm text-muted"><li>Consulta casos y timelines.</li><li>Explica conformidad y desviaciones.</li><li>Lee riesgos estimados y alertas persistidas.</li><li>No modifica ni recalcula información.</li></ul></SectionCard>
      </aside>
    </div>
  </div></main>;
}
