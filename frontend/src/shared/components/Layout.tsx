import type { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between"><div>{eyebrow && <p className="text-xs font-bold uppercase tracking-[0.15em] text-brand-700">{eyebrow}</p>}<h1 className="mt-1 text-3xl font-bold tracking-tight text-ink-950 sm:text-4xl">{title}</h1>{description && <p className="mt-2 max-w-3xl text-sm leading-6 text-muted sm:text-base">{description}</p>}</div>{action && <div className="shrink-0">{action}</div>}</header>;
}

export function KpiCard({ label, value, detail }: { label: string; value: string | number; detail?: string }) {
  return <article className="rounded-xl border border-line bg-white p-4"><p className="text-xs font-bold uppercase tracking-wide text-muted">{label}</p><p className="mt-2 text-3xl font-bold text-ink-950">{value}</p>{detail && <p className="mt-1 text-xs text-muted">{detail}</p>}</article>;
}

export function SectionCard({ title, description, action, children, className = "" }: { title?: string; description?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  const hasHeader = Boolean(title || description || action);
  return <section className={`rounded-xl border border-line bg-white ${className}`}>{hasHeader && <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4">{title || description ? <div>{title && <h2 className="text-lg font-bold text-ink-950">{title}</h2>}{description && <p className="mt-1 text-sm text-muted">{description}</p>}</div> : <span />}{action}</div>}<div className="p-5">{children}</div></section>;
}

export function DatasetNotice() {
  const notice = import.meta.env.VITE_DATASET_NOTICE || "Datos simulados de demostración";
  return <div className="inline-flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-900"><span aria-hidden="true">i</span><span>{notice}</span></div>;
}
