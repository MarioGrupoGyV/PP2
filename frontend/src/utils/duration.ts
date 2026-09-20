export function formatDuration(totalSeconds: number): string {
  if (!Number.isFinite(totalSeconds) || totalSeconds < 0) return "—";
  if (totalSeconds < 60) return `${Math.round(totalSeconds)} s`;
  if (totalSeconds < 3600) return `${(totalSeconds / 60).toFixed(1)} min`;
  if (totalSeconds < 86400) return `${(totalSeconds / 3600).toFixed(1)} h`;
  return `${(totalSeconds / 86400).toFixed(1)} días`;
}
