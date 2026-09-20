import { StatusCard } from "../components/ui/StatusCard";
import { useInfrastructureStatus } from "../hooks/useInfrastructureStatus";

export function HomePage() {
  const { backend, database, refresh, isRefreshing } =
    useInfrastructureStatus();

  return (
    <main className="relative min-h-screen overflow-hidden bg-slate-50 px-5 py-10 sm:px-8 lg:py-16">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-96 bg-gradient-to-b from-teal-100/70 to-transparent" />
      <div className="pointer-events-none absolute -right-28 top-16 h-72 w-72 rounded-full bg-cyan-200/30 blur-3xl" />

      <section className="relative mx-auto max-w-5xl">
        <div className="mb-10 flex flex-col gap-6 sm:mb-12 sm:flex-row sm:items-end sm:justify-between">
          <header className="max-w-3xl">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-teal-200 bg-white/80 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-teal-700 shadow-sm backdrop-blur">
              <span className="h-2 w-2 rounded-full bg-teal-500" />
              Sprint 4 · Desviaciones
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-5xl sm:leading-[1.08]">
              Sistema de minería de procesos con alertas predictivas
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg">
              Descubrimiento y visualización del proceso comercial observado a
              partir del Event Log persistido.
            </p>
          </header>

          <div className="flex shrink-0 flex-col gap-3 sm:items-stretch">
            <a
              href="/deviations"
              className="inline-flex items-center justify-center rounded-xl bg-amber-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-amber-600/15 transition hover:bg-amber-700"
            >
              Ver desviaciones
            </a>
            <a
              href="/process-mining"
              className="inline-flex items-center justify-center rounded-xl bg-teal-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-teal-600/15 transition hover:bg-teal-700"
            >
              Ver minería de procesos
            </a>
            <a
              href="/imports"
              className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-teal-500 hover:text-teal-700"
            >
              Importar Event Log
            </a>
            <button
              type="button"
              onClick={refresh}
              disabled={isRefreshing}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-slate-950/10 transition hover:bg-slate-800 disabled:cursor-wait disabled:opacity-60"
            >
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                fill="none"
                className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`}
              >
                <path
                  d="M20 11a8.1 8.1 0 0 0-15.5-2M4 4v5h5M4 13a8.1 8.1 0 0 0 15.5 2M20 20v-5h-5"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              {isRefreshing ? "Comprobando" : "Volver a comprobar"}
            </button>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <StatusCard
            title="Frontend"
            description="React, TypeScript y Vite"
            state="success"
            successText="Frontend operativo"
          />
          <StatusCard
            title="Backend"
            description="API REST con FastAPI"
            state={backend.state}
            successText="Backend conectado"
            errorText={backend.message}
          />
          <StatusCard
            title="PostgreSQL"
            description="Conexión mediante SQLAlchemy"
            state={database.state}
            successText="PostgreSQL conectado"
            errorText={database.message}
          />
        </div>

        <footer className="mt-7 flex items-center justify-between border-t border-slate-200/80 pt-5 text-xs text-slate-500">
          <span>GYV · Gestión comercial inmobiliaria</span>
          <span>API v1</span>
        </footer>
      </section>
    </main>
  );
}
