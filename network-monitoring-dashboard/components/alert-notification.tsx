"use client";

import { useEffect, useRef } from "react";
import { useToast } from "@/hooks/use-toast";
import { getAlerts } from "@/lib/api";

interface Alert {
  id: string;
  title: string;
  description: string;
  time: string;
  severity: string;
}

type SeverityLevel = "critical" | "high" | "medium" | "low" | "info";

type ToastTrigger = ReturnType<typeof useToast>["toast"];

const SEVERITY_CONFIG: Record<
  SeverityLevel,
  {
    label: string;
    dot: string;
    bar: string;
    badge: string;
    icon: string;
  }
> = {
  critical: {
    label: "Critical",
    dot: "#ef4444",
    bar: "linear-gradient(180deg, #ef4444 0%, #b91c1c 100%)",
    badge:
      "background: rgba(239,68,68,0.12); color: #ef4444; border: 1px solid rgba(239,68,68,0.25);",
    icon: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1L13 12H1L7 1Z" stroke="#ef4444" stroke-width="1.5" stroke-linejoin="round"/><path d="M7 5.5V8" stroke="#ef4444" stroke-width="1.5" stroke-linecap="round"/><circle cx="7" cy="10" r="0.75" fill="#ef4444"/></svg>`,
  },
  high: {
    label: "High",
    dot: "#f97316",
    bar: "linear-gradient(180deg, #f97316 0%, #c2410c 100%)",
    badge:
      "background: rgba(249,115,22,0.12); color: #f97316; border: 1px solid rgba(249,115,22,0.25);",
    icon: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="#f97316" stroke-width="1.5"/><path d="M7 4.5V7.5" stroke="#f97316" stroke-width="1.5" stroke-linecap="round"/><circle cx="7" cy="9.5" r="0.75" fill="#f97316"/></svg>`,
  },
  medium: {
    label: "Medium",
    dot: "#eab308",
    bar: "linear-gradient(180deg, #eab308 0%, #a16207 100%)",
    badge:
      "background: rgba(234,179,8,0.12); color: #ca8a04; border: 1px solid rgba(234,179,8,0.25);",
    icon: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="#eab308" stroke-width="1.5"/><path d="M4.5 7H9.5" stroke="#eab308" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  },
  low: {
    label: "Low",
    dot: "#3b82f6",
    bar: "linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%)",
    badge:
      "background: rgba(59,130,246,0.12); color: #3b82f6; border: 1px solid rgba(59,130,246,0.25);",
    icon: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="#3b82f6" stroke-width="1.5"/><path d="M7 4.5V7" stroke="#3b82f6" stroke-width="1.5" stroke-linecap="round"/><circle cx="7" cy="9.5" r="0.75" fill="#3b82f6"/></svg>`,
  },
  info: {
    label: "Info",
    dot: "#8b5cf6",
    bar: "linear-gradient(180deg, #8b5cf6 0%, #6d28d9 100%)",
    badge:
      "background: rgba(139,92,246,0.12); color: #8b5cf6; border: 1px solid rgba(139,92,246,0.25);",
    icon: `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="#8b5cf6" stroke-width="1.5"/><path d="M7 6.5V9.5" stroke="#8b5cf6" stroke-width="1.5" stroke-linecap="round"/><circle cx="7" cy="4.5" r="0.75" fill="#8b5cf6"/></svg>`,
  },
};

function getSeverityConfig(severity: string) {
  const normalized = severity?.toLowerCase() as SeverityLevel;
  return SEVERITY_CONFIG[normalized] ?? SEVERITY_CONFIG.info;
}

function formatAlertTime(timeStr: string): string {
  try {
    const date = new Date(timeStr);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return timeStr;
  }
}

function AlertToastDescription({
  alert,
  config,
}: {
  alert: Alert;
  config: (typeof SEVERITY_CONFIG)[SeverityLevel];
}) {
  return (
    <div className="space-y-2 font-sans text-sm text-foreground">
      <div className="flex items-center gap-2">
        <span
          className="inline-flex items-center gap-2 rounded-md px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em]"
          style={{
            border: `1px solid ${config.badge.split("border: 1px solid ")[1] ?? "#d1d5db"}`,
            backgroundColor:
              config.badge.match(/background: ([^;]+)/)?.[1] ?? "transparent",
            color: config.badge.match(/color: ([^;]+)/)?.[1] ?? "#111827",
          }}
        >
          <span dangerouslySetInnerHTML={{ __html: config.icon }} />
          {config.label}
        </span>
        <span className="ml-auto text-[11px] text-slate-500">
          {formatAlertTime(alert.time)}
        </span>
      </div>
      <p className="m-0 text-slate-700 leading-6">{alert.description}</p>
      <div className="flex items-center gap-2 pt-2 border-t border-slate-200 text-[11px] text-slate-500">
        <span
          className="h-1.5 w-1.5 rounded-full"
          style={{ backgroundColor: config.dot }}
        />
        <span>Alert ID: {alert.id}</span>
      </div>
    </div>
  );
}

export function showAlertToast(toast: ToastTrigger, alert: Alert) {
  const config = getSeverityConfig(alert.severity);
  const isCritical =
    alert.severity?.toLowerCase() === "critical" ||
    alert.severity?.toLowerCase() === "high";

  toast({
    title: alert.title,
    description: <AlertToastDescription alert={alert} config={config} />,
    variant: isCritical ? "destructive" : "default",
    duration: 10000,
  });
}

export function AlertNotification() {
  const { toast } = useToast();
  const seenAlertsRef = useRef<Set<string>>(new Set());
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const checkForNewAlerts = async () => {
      try {
        const response = await getAlerts();
        const alerts: Alert[] = response.alerts || [];

        const newAlerts = alerts.filter(
          (alert) => !seenAlertsRef.current.has(alert.id),
        );

        newAlerts.forEach((alert) => {
          showAlertToast(toast, alert);

          seenAlertsRef.current.add(alert.id);
        });

        if (seenAlertsRef.current.size > 100) {
          const recentAlerts = alerts.slice(-50).map((a) => a.id);
          seenAlertsRef.current = new Set(recentAlerts);
        }
      } catch (error) {
        console.error("Failed to check for new alerts:", error);
      }
    };

    checkForNewAlerts();
    intervalRef.current = setInterval(checkForNewAlerts, 30000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [toast]);

  return null;
}
