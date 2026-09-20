import { normalizePath } from "./router/routes";
import { AppShell } from "../components/layout/AppShell";
import { DashboardPage } from "../pages/DashboardPage";
import { CasesPage } from "../pages/CasesPage";
import { CaseDetailPage } from "../pages/CaseDetailPage";
import { DemoPage } from "../pages/DemoPage";
import { ImportsPage } from "../pages/ImportsPage";
import { ProcessMiningPage } from "../pages/ProcessMiningPage";
import { DeviationsPage } from "../pages/DeviationsPage";
import { PredictionsPage } from "../pages/PredictionsPage";
import { AlertsPage } from "../pages/AlertsPage";

export function App() {
  const path = normalizePath(window.location.pathname);
  let page;
  const caseMatch = path.match(/^\/cases\/([^/]+)$/);
  if (path === "/" || path === "/dashboard") page = <DashboardPage />;
  else if (path === "/cases") page = <CasesPage />;
  else if (caseMatch) page = <CaseDetailPage caseId={decodeURIComponent(caseMatch[1])} />;
  else if (path === "/imports") page = <ImportsPage />;
  else if (path === "/process-mining") page = <ProcessMiningPage />;
  else if (path === "/deviations") page = <DeviationsPage />;
  else if (path === "/predictions") page = <PredictionsPage />;
  else if (path === "/alerts") page = <AlertsPage />;
  else if (path === "/demo") page = <DemoPage />;
  else page = <main className="px-6 py-12"><h1 className="text-3xl font-bold">Página no encontrada</h1><a href="/" className="mt-4 inline-flex font-bold text-brand-700">Volver al Dashboard</a></main>;
  return <AppShell pathname={path}>{page}</AppShell>;
}
