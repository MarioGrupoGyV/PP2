import type { RequestState } from "../../types/health";

interface StatusCardProps {
  title: string;
  description: string;
  state: RequestState;
  successText: string;
  errorText?: string;
}

const stateStyles: Record<RequestState, string> = {
  loading: "border-amber-200 bg-amber-50 text-amber-700",
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  error: "border-rose-200 bg-rose-50 text-rose-700",
};

const dotStyles: Record<RequestState, string> = {
  loading: "bg-amber-500 animate-pulse",
  success: "bg-emerald-500",
  error: "bg-rose-500",
};

export function StatusCard({
  title,
  description,
  state,
  successText,
  errorText,
}: StatusCardProps) {
  const label =
    state === "loading"
      ? "Comprobando conexión"
      : state === "success"
        ? successText
        : errorText || "Sin conexión";

  return (
    <article className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-[0_16px_50px_-28px_rgba(15,23,42,0.35)]">
      <div className="mb-8 flex h-11 w-11 items-center justify-center rounded-xl bg-slate-950 text-sm font-bold text-white shadow-md shadow-slate-950/15">
        {title.slice(0, 2).toUpperCase()}
      </div>
      <h2 className="text-lg font-bold text-slate-950">{title}</h2>
      <p className="mt-1 text-sm text-slate-500">{description}</p>
      <div
        role="status"
        className={`mt-5 flex min-h-10 items-center gap-2 rounded-xl border px-3 py-2 text-sm font-semibold ${stateStyles[state]}`}
      >
        <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${dotStyles[state]}`} />
        <span>{label}</span>
      </div>
    </article>
  );
}
