import { HomePage } from "../pages/HomePage";
import { ImportsPage } from "../pages/ImportsPage";
import { ProcessMiningPage } from "../pages/ProcessMiningPage";
import { DeviationsPage } from "../pages/DeviationsPage";
import { PredictionsPage } from "../pages/PredictionsPage";

export function App() {
  const path = window.location.pathname.replace(/\/$/, "") || "/";
  if (path === "/imports") return <ImportsPage />;
  if (path === "/process-mining") return <ProcessMiningPage />;
  if (path === "/deviations") return <DeviationsPage />;
  if (path === "/predictions") return <PredictionsPage />;
  return <HomePage />;
}
