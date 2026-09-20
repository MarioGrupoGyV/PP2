export interface NavigationRoute {
  path: string;
  label: string;
  shortLabel: string;
  matches: (pathname: string) => boolean;
}

export const NAVIGATION_ROUTES: NavigationRoute[] = [
  { path: "/", label: "Dashboard", shortLabel: "DB", matches: (path) => path === "/" || path === "/dashboard" },
  { path: "/cases", label: "Casos", shortLabel: "CA", matches: (path) => path === "/cases" || path.startsWith("/cases/") },
  { path: "/process-mining", label: "Minería de Procesos", shortLabel: "MP", matches: (path) => path === "/process-mining" },
  { path: "/deviations", label: "Desviaciones", shortLabel: "DV", matches: (path) => path === "/deviations" },
  { path: "/predictions", label: "Predicciones", shortLabel: "PR", matches: (path) => path === "/predictions" },
  { path: "/alerts", label: "Alertas", shortLabel: "AL", matches: (path) => path === "/alerts" },
  { path: "/imports", label: "Importaciones", shortLabel: "IM", matches: (path) => path === "/imports" },
];

export function normalizePath(pathname: string): string {
  return pathname.replace(/\/+$/, "") || "/";
}
