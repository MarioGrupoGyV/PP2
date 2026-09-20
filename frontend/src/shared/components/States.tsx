export function LoadingState({ label = "Cargando información…" }: { label?: string }) {
  return <div role="status" className="rounded-xl border border-line bg-white p-6"><div className="h-3 w-36 animate-pulse rounded bg-slate-200" /><div className="mt-4 h-3 w-2/3 animate-pulse rounded bg-slate-100" /><p className="sr-only">{label}</p></div>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-5 text-red-900"><p className="font-bold">No fue posible cargar la información</p><p className="mt-1 text-sm">{message}</p>{onRetry && <button type="button" onClick={onRetry} className="mt-3 rounded-lg border border-red-300 bg-white px-3 py-2 text-sm font-bold">Reintentar</button>}</div>;
}

export function EmptyState({ title, description, actionHref, actionLabel }: { title: string; description: string; actionHref?: string; actionLabel?: string }) {
  return <div className="rounded-xl border border-dashed border-line bg-surface-muted p-7 text-center"><p className="font-bold text-ink-950">{title}</p><p className="mx-auto mt-1 max-w-lg text-sm text-muted">{description}</p>{actionHref && actionLabel && <a href={actionHref} className="mt-4 inline-flex rounded-lg bg-brand-700 px-4 py-2 text-sm font-bold text-white">{actionLabel}</a>}</div>;
}
