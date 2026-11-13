function pad(value: number): string {
  return String(value).padStart(2, "0");
}

/** Valor compatible con `<input type="datetime-local">` en la hora local del navegador. */
export function toDateTimeLocalValue(date: Date = new Date()): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/**
 * Convierte el valor de un `datetime-local` (hora local, sin zona) a ISO 8601
 * con el desplazamiento horario explícito, p. ej. `2026-11-13T09:30:00-05:00`.
 * Devuelve `null` si el valor no es una fecha válida.
 */
export function localInputToIso(value: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  const offsetMinutes = -date.getTimezoneOffset();
  const sign = offsetMinutes >= 0 ? "+" : "-";
  const absolute = Math.abs(offsetMinutes);
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}${sign}${pad(Math.floor(absolute / 60))}:${pad(absolute % 60)}`;
}
