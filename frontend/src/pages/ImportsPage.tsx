import { useCallback, useEffect, useState } from "react";

import {
  commitEventLog,
  getImportHistory,
  getImportTemplateUrl,
  previewEventLog,
} from "../services/api";
import type {
  EventLogImport,
  ImportPreview,
  ImportResult,
} from "../types/imports";
import { formatDateTime } from "../shared/utils/format";

const MAX_FILE_SIZE = 10 * 1024 * 1024;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Ocurrió un error inesperado";
}

export function ImportsPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [history, setHistory] = useState<EventLogImport[]>([]);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshHistory = useCallback(async () => {
    setIsLoadingHistory(true);
    try {
      setHistory(await getImportHistory());
    } catch {
      setHistory([]);
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    void refreshHistory();
  }, [refreshHistory]);

  function selectFile(selected: File | null) {
    setPreview(null);
    setResult(null);
    setError(null);
    if (!selected) {
      setFile(null);
      return;
    }
    if (!selected.name.toLowerCase().endsWith(".csv")) {
      setFile(null);
      setError("Selecciona un archivo con extensión CSV.");
      return;
    }
    if (selected.size > MAX_FILE_SIZE) {
      setFile(null);
      setError("El archivo supera el límite de 10 MB.");
      return;
    }
    setFile(selected);
  }

  async function handlePreview() {
    if (!file) return;
    setIsPreviewing(true);
    setError(null);
    setResult(null);
    try {
      setPreview(await previewEventLog(file));
    } catch (requestError) {
      setPreview(null);
      setError(errorMessage(requestError));
    } finally {
      setIsPreviewing(false);
    }
  }

  async function handleImport() {
    if (!file || !preview?.can_import) return;
    setIsImporting(true);
    setError(null);
    try {
      const importResult = await commitEventLog(file);
      setResult(importResult);
      await refreshHistory();
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setIsImporting(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-8 lg:py-12">
      <section className="mx-auto max-w-6xl">
        <div className="mb-8 flex justify-end">
          <a
            href={getImportTemplateUrl()}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-teal-500 hover:text-teal-700"
          >
            Descargar template CSV
          </a>
        </div>

        <header className="mb-8 max-w-3xl">
          <div className="mb-4 inline-flex rounded-full bg-teal-100 px-3 py-1 text-xs font-bold uppercase tracking-[0.14em] text-teal-700">
            Sprint 2 · Preparación de datos
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">
            Importar Event Log
          </h1>
          <p className="mt-3 text-base leading-7 text-slate-600">
            Valida el archivo antes de persistirlo. La importación es atómica: si
            una fila contiene errores, no se guarda ningún dato.
          </p>
        </header>

        <ol className="mb-8 grid gap-3 sm:grid-cols-3">
          {[
            ["1", "Seleccionar archivo", Boolean(file)],
            ["2", "Revisar preview", Boolean(preview)],
            ["3", "Confirmar importación", Boolean(result)],
          ].map(([number, label, completed]) => (
            <li
              key={String(number)}
              className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-sm font-semibold ${
                completed
                  ? "border-teal-200 bg-teal-50 text-teal-800"
                  : "border-slate-200 bg-white text-slate-500"
              }`}
            >
              <span
                className={`flex h-7 w-7 items-center justify-center rounded-full text-xs ${
                  completed ? "bg-teal-600 text-white" : "bg-slate-100 text-slate-600"
                }`}
              >
                {number}
              </span>
              {label}
            </li>
          ))}
        </ol>

        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="space-y-6">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
              <h2 className="text-lg font-bold text-slate-950">1. Seleccionar CSV</h2>
              <p className="mt-1 text-sm text-slate-500">
                Máximo 10 MB · UTF-8 · Solo archivos CSV
              </p>

              <label className="mt-5 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-center transition hover:border-teal-500 hover:bg-teal-50/40">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-white text-xl shadow-sm">
                  ↑
                </span>
                <span className="mt-3 text-sm font-bold text-slate-800">
                  Seleccionar archivo
                </span>
                <span className="mt-1 text-xs text-slate-500">
                  case_code, stage_code, activity y timestamp son obligatorios
                </span>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  className="sr-only"
                  onChange={(event) => selectFile(event.target.files?.[0] ?? null)}
                />
              </label>

              {file && (
                <div className="mt-4 flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold text-slate-900">{file.name}</p>
                    <p className="mt-0.5 text-xs text-slate-500">{formatBytes(file.size)}</p>
                  </div>
                  <button
                    type="button"
                    onClick={handlePreview}
                    disabled={isPreviewing}
                    className="rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-wait disabled:opacity-60"
                  >
                    {isPreviewing ? "Validando…" : "Generar preview"}
                  </button>
                </div>
              )}
            </section>

            {error && (
              <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm font-medium text-rose-800">
                {error}
              </div>
            )}

            {preview && (
              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h2 className="text-lg font-bold text-slate-950">2. Revisar preview</h2>
                    <p className="mt-1 text-sm text-slate-500">
                      Se muestran hasta las primeras 20 filas válidas.
                    </p>
                  </div>
                  <span
                    className={`w-fit rounded-full px-3 py-1 text-xs font-bold ${
                      preview.can_import
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-rose-100 text-rose-700"
                    }`}
                  >
                    {preview.can_import ? "Listo para importar" : "Requiere correcciones"}
                  </span>
                </div>

                <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {[
                    ["Filas", preview.total_rows],
                    ["Válidas", preview.valid_rows],
                    ["Inválidas", preview.invalid_rows],
                    ["Duplicadas", preview.duplicate_rows],
                  ].map(([label, value]) => (
                    <div key={String(label)} className="rounded-xl bg-slate-50 p-3">
                      <p className="text-xs font-semibold text-slate-500">{label}</p>
                      <p className="mt-1 text-xl font-bold text-slate-950">{value}</p>
                    </div>
                  ))}
                </div>

                {preview.errors.length > 0 && (
                  <div className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4">
                    <h3 className="text-sm font-bold text-rose-900">
                      Errores encontrados ({preview.errors.length})
                    </h3>
                    <ul className="mt-3 max-h-52 space-y-2 overflow-y-auto text-sm text-rose-800">
                      {preview.errors.map((item, index) => (
                        <li key={`${item.row}-${item.field}-${index}`}>
                          <span className="font-bold">Fila {item.row} · {item.field}:</span>{" "}
                          {item.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {preview.preview.length > 0 && (
                  <div className="mt-5 overflow-x-auto rounded-xl border border-slate-200">
                    <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                      <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                        <tr>
                          <th className="px-4 py-3">Fila</th>
                          <th className="px-4 py-3">Caso</th>
                          <th className="px-4 py-3">Etapa</th>
                          <th className="px-4 py-3">Actividad</th>
                          <th className="px-4 py-3">Timestamp</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-slate-700">
                        {preview.preview.map((row) => (
                          <tr key={`${row.row}-${row.case_code}`}>
                            <td className="px-4 py-3 text-slate-500">{row.row}</td>
                            <td className="px-4 py-3 font-semibold">{row.case_code}</td>
                            <td className="px-4 py-3">{row.stage_code}</td>
                            <td className="px-4 py-3">{row.activity}</td>
                            <td className="whitespace-nowrap px-4 py-3 text-xs">{row.timestamp}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                <div className="mt-6 flex items-center justify-end border-t border-slate-200 pt-5">
                  <button
                    type="button"
                    onClick={handleImport}
                    disabled={!preview.can_import || isImporting || Boolean(result)}
                    className="rounded-xl bg-teal-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-teal-600/15 transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:shadow-none"
                  >
                    {isImporting ? "Importando…" : result ? "Importación completada" : "Confirmar importación"}
                  </button>
                </div>
              </section>
            )}

            {result && (
              <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 sm:p-7">
                <h2 className="text-lg font-bold text-emerald-950">Importación exitosa</h2>
                <p className="mt-1 text-sm text-emerald-800">{result.filename}</p>
                <dl className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <div><dt className="text-xs text-emerald-700">Casos creados</dt><dd className="text-xl font-bold">{result.cases_created}</dd></div>
                  <div><dt className="text-xs text-emerald-700">Casos existentes</dt><dd className="text-xl font-bold">{result.cases_existing}</dd></div>
                  <div><dt className="text-xs text-emerald-700">Eventos</dt><dd className="text-xl font-bold">{result.events_imported}</dd></div>
                  <div><dt className="text-xs text-emerald-700">Omitidos</dt><dd className="text-xl font-bold">{result.duplicates_skipped}</dd></div>
                </dl>
              </section>
            )}
          </div>

          <aside className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:sticky lg:top-8">
            <h2 className="text-base font-bold text-slate-950">Importaciones recientes</h2>
            <p className="mt-1 text-xs text-slate-500">Trazabilidad de los últimos archivos.</p>
            {isLoadingHistory ? (
              <p className="mt-5 text-sm text-slate-500">Cargando historial…</p>
            ) : history.length === 0 ? (
              <p className="mt-5 rounded-lg bg-slate-50 p-3 text-sm text-slate-500">
                Todavía no existen importaciones.
              </p>
            ) : (
              <ul className="mt-4 divide-y divide-slate-100">
                {history.map((item) => (
                  <li key={item.id} className="py-4 first:pt-0 last:pb-0">
                    <p className="truncate text-sm font-bold text-slate-800">{item.filename}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      {item.imported_events.toLocaleString("es-PE")} eventos · {formatDateTime(item.created_at)}
                    </p>
                    {item.skipped_duplicates > 0 && (
                      <p className="mt-1 text-xs font-semibold text-amber-700">
                        {item.skipped_duplicates} duplicados omitidos
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </aside>
        </div>
      </section>
    </main>
  );
}
