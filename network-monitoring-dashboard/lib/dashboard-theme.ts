export const DASHBOARD_COLORS = ["#a78bfa", "#67e8f9", "#ef4444", "#fbbf24", "#6366f1"];

export const STATE_COLORS: Record<string, string> = {
  DDOS: "text-red-400 bg-red-950/20 border-red-500/40",
  BRUTE_FORCE: "text-orange-400 bg-orange-950/20 border-orange-500/40",
  SCANNING: "text-yellow-400 bg-yellow-950/20 border-yellow-500/40",
  INFRA_FAILURE: "text-rose-400 bg-rose-950/20 border-rose-500/40",
  CONGESTION: "text-amber-400 bg-amber-950/20 border-amber-500/40",
  LATENCY: "text-indigo-400 bg-indigo-950/20 border-indigo-500/40",
  PACKET_LOSS: "text-violet-400 bg-violet-950/20 border-violet-500/40",
  JITTER: "text-purple-400 bg-purple-950/20 border-purple-500/40",
  BANDWIDTH: "text-blue-400 bg-blue-950/20 border-blue-500/40",
  NORMAL: "text-emerald-400 bg-emerald-950/20 border-emerald-500/40",
};

export const SEVERITY_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  critical: {
    bg: "bg-red-500/10",
    text: "text-red-400",
    border: "border-red-500/30",
  },
  high: {
    bg: "bg-red-500/10",
    text: "text-red-400",
    border: "border-red-500/30",
  },
  warning: {
    bg: "bg-orange-500/10",
    text: "text-orange-400",
    border: "border-orange-500/30",
  },
  medium: {
    bg: "bg-orange-500/10",
    text: "text-orange-400",
    border: "border-orange-500/30",
  },
  info: {
    bg: "bg-sky-500/10",
    text: "text-sky-400",
    border: "border-sky-500/30",
  },
  low: {
    bg: "bg-green-500/10",
    text: "text-green-400",
    border: "border-green-500/30",
  },
  default: {
    bg: "bg-slate-900/20",
    text: "text-slate-300",
    border: "border-border",
  },
};
