import type { AlertStatus } from "../../types/alerts";
import type { DeviationSeverity } from "../../types/deviations";
import type { RiskLevel } from "../../types/predictions";
import type { CaseStatus } from "../../types/cases";
import {
  ALERT_STATUS_LABELS,
  CASE_STATUS_LABELS,
  RISK_LABELS,
  SEVERITY_LABELS,
} from "../constants/labels";

const RISK_STYLE: Record<RiskLevel, string> = {
  LOW: "border-sky-200 bg-sky-50 text-sky-800",
  MEDIUM: "border-amber-200 bg-amber-50 text-amber-800",
  HIGH: "border-red-200 bg-red-50 text-red-800",
};
const ALERT_STYLE: Record<AlertStatus, string> = {
  ACTIVE: "border-red-200 bg-red-50 text-red-800",
  ATTENDED: "border-amber-200 bg-amber-50 text-amber-800",
  RESOLVED: "border-emerald-200 bg-emerald-50 text-emerald-800",
  DISMISSED: "border-slate-300 bg-slate-100 text-slate-700",
};
const CASE_STYLE: Record<CaseStatus, string> = {
  ACTIVE: "border-blue-200 bg-blue-50 text-blue-800",
  CLOSED: "border-emerald-200 bg-emerald-50 text-emerald-800",
  CANCELLED: "border-slate-300 bg-slate-100 text-slate-700",
};

function Badge({ label, className }: { label: string; className: string }) {
  return <span className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-bold ${className}`}>{label}</span>;
}

export function RiskBadge({ level }: { level: RiskLevel }) {
  return <Badge label={RISK_LABELS[level]} className={RISK_STYLE[level]} />;
}

export function SeverityBadge({ severity }: { severity: DeviationSeverity }) {
  return <Badge label={SEVERITY_LABELS[severity]} className={RISK_STYLE[severity]} />;
}

export function AlertStatusBadge({ status }: { status: AlertStatus }) {
  return <Badge label={ALERT_STATUS_LABELS[status]} className={ALERT_STYLE[status]} />;
}

export function CaseStatusBadge({ status }: { status: CaseStatus }) {
  return <Badge label={CASE_STATUS_LABELS[status]} className={CASE_STYLE[status]} />;
}
