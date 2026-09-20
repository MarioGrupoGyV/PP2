import { HomePage } from "../pages/HomePage";
import { ImportsPage } from "../pages/ImportsPage";

export function App() {
  const path = window.location.pathname.replace(/\/$/, "") || "/";
  return path === "/imports" ? <ImportsPage /> : <HomePage />;
}
