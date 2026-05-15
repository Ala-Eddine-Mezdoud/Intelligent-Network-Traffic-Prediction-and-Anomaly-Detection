/** Semantic status styling — green / red / orange / gray only. */

export const DASHBOARD_COLORS = [
  "#22c55e",
  "#ef4444",
  "#f97316",
  "#9ca3af",
  "#6b7280",
  "#d1d5db",
];

function stateTier(state: string): "critical" | "warning" | "healthy" | "neutral" {
  const s = state.toUpperCase();
  if (["DDOS", "BRUTE_FORCE", "INFRA_FAILURE"].includes(s)) return "critical";
  if (
    ["SCANNING", "CONGESTION", "LATENCY", "PACKET_LOSS", "JITTER", "BANDWIDTH"].includes(
      s,
    )
  )
    return "warning";
  if (s === "NORMAL") return "healthy";
  return "neutral";
}

const tierStyles = {
  critical: "text-red-500 bg-red-500/10 border-red-500/30",
  warning: "text-orange-500 bg-orange-500/10 border-orange-500/30",
  healthy: "text-green-500 bg-green-500/10 border-green-500/30",
  neutral: "text-gray-600 bg-gray-50 border-gray-200",
};

export function getStateColorClass(state: string): string {
  return tierStyles[stateTier(state)] ?? tierStyles.neutral;
}

export const STATE_COLORS: Record<string, string> = {
  DDOS: tierStyles.critical,
  BRUTE_FORCE: tierStyles.critical,
  INFRA_FAILURE: tierStyles.critical,
  SCANNING: tierStyles.warning,
  CONGESTION: tierStyles.warning,
  LATENCY: tierStyles.warning,
  PACKET_LOSS: tierStyles.warning,
  JITTER: tierStyles.warning,
  BANDWIDTH: tierStyles.warning,
  NORMAL: tierStyles.healthy,
};

export const SEVERITY_STYLES: Record<
  string,
  { bg: string; text: string; border: string }
> = {
  critical: {
    bg: "bg-red-500/10",
    text: "text-red-500",
    border: "border-red-500/30",
  },
  high: {
    bg: "bg-red-500/10",
    text: "text-red-500",
    border: "border-red-500/30",
  },
  warning: {
    bg: "bg-orange-500/10",
    text: "text-orange-500",
    border: "border-orange-500/30",
  },
  medium: {
    bg: "bg-orange-500/10",
    text: "text-orange-500",
    border: "border-orange-500/30",
  },
  low: {
    bg: "bg-green-500/10",
    text: "text-green-500",
    border: "border-green-500/30",
  },
  info: {
    bg: "bg-gray-100",
    text: "text-gray-600",
    border: "border-gray-200",
  },
  default: {
    bg: "bg-gray-50",
    text: "text-gray-600",
    border: "border-gray-200",
  },
};
