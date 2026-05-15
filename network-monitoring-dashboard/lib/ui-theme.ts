/** Shared white-mode design tokens for the dashboard. */

export const dashboardCard =
  "bg-white border border-gray-200 shadow-sm rounded-2xl transition-shadow hover:shadow-md";

export const dashboardCardPadding = "p-5 md:p-6";

export const pageSection =
  "rounded-2xl border border-gray-200 bg-white shadow-sm p-5 md:p-6";

export const pageTitle = "text-2xl font-semibold tracking-tight text-gray-900";

export const pageSubtitle = "text-sm text-gray-500";

export const mutedBadge =
  "inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs text-gray-600";

export const statusBadge = {
  healthy:
    "inline-flex items-center rounded-full border border-green-500/30 bg-green-500/10 px-2.5 py-0.5 text-xs font-medium text-green-600",
  warning:
    "inline-flex items-center rounded-full border border-orange-500/30 bg-orange-500/10 px-2.5 py-0.5 text-xs font-medium text-orange-600",
  critical:
    "inline-flex items-center rounded-full border border-red-500/30 bg-red-500/10 px-2.5 py-0.5 text-xs font-medium text-red-600",
  neutral:
    "inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2.5 py-0.5 text-xs font-medium text-gray-600",
} as const;

export const healthText = {
  healthy: "text-green-500",
  warning: "text-orange-500",
  critical: "text-red-500",
} as const;

export const healthIconBg = {
  healthy: "bg-green-500/10 text-green-500 border-green-500/20",
  warning: "bg-orange-500/10 text-orange-500 border-orange-500/20",
  critical: "bg-red-500/10 text-red-500 border-red-500/20",
  neutral: "bg-gray-100 text-gray-600 border-gray-200",
} as const;

/** Chart palette: green, red, orange, gray only */
export const CHART_COLORS = [
  "#22c55e",
  "#ef4444",
  "#f97316",
  "#9ca3af",
  "#6b7280",
  "#d1d5db",
] as const;

export const CHART_STROKE = {
  historical: "#6b7280",
  predicted: "#22c55e",
  confidence: "#e5e7eb",
  grid: "#f3f4f6",
  axis: "#9ca3af",
} as const;

export const chartTooltipStyle = {
  backgroundColor: "#ffffff",
  border: "1px solid #e5e7eb",
  borderRadius: "12px",
  boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.08)",
  color: "#111827",
  fontSize: "12px",
} as const;

export const runningDot = "bg-green-500 animate-pulse";
export const idleDot = "bg-gray-300";

/** Meta-style sidebar / nav item states (neutral grays only) */
export const navItem =
  "group flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium transition-all duration-200 ease-out";

export const navItemIdle =
  "text-gray-600 hover:bg-[#f0f2f5] hover:text-gray-900 active:bg-[#e4e6eb]";

export const navItemActive =
  "bg-[#f0f2f5] text-gray-900 font-semibold shadow-sm";

export const navItemIcon =
  "h-5 w-5 shrink-0 transition-colors duration-200";

export const navItemIconIdle =
  "text-gray-500 group-hover:text-gray-900";

export const navItemIconActive = "text-gray-900";

export const navSectionButton =
  "group flex w-full items-center gap-3 rounded-2xl px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500 transition-all duration-200 ease-out hover:bg-[#f0f2f5] hover:text-gray-700 active:bg-[#e4e6eb]";

export const navIconButton =
  "rounded-lg p-2 text-gray-600 transition-all duration-200 ease-out hover:bg-[#f0f2f5] hover:text-gray-900 active:bg-[#e4e6eb]";

export const primaryButton =
  "bg-gray-900 font-semibold text-white hover:bg-gray-800";

export const outlineButton =
  "border border-gray-200 text-gray-700 hover:bg-gray-50";

export const loadingState = "text-gray-500";

export const tableHead =
  "text-xs font-medium uppercase tracking-wide text-gray-500 md:text-sm";

export const tableRow =
  "border-gray-200 hover:bg-gray-50 transition-colors";

export const tableCell = "text-sm text-gray-900 px-2 md:px-4";

export const tableCellMuted = "text-sm text-gray-600 px-2 md:px-4";

/** Left accent border for alert list cards by severity */
export function getAlertCardAccent(severity: string): string {
  const s = severity.toLowerCase();
  if (s === "critical" || s === "high") return "border-l-4 border-l-red-500";
  if (s === "warning" || s === "medium") return "border-l-4 border-l-orange-500";
  if (s === "low") return "border-l-4 border-l-green-500";
  return "border-l-4 border-l-gray-300";
}
