"use client";

import { useEffect, useRef } from "react";
import { useToast } from "@/hooks/use-toast";
import { getAlerts } from "@/lib/api";
import { SEVERITY_STYLES } from "@/lib/dashboard-theme";
import { cn } from "@/lib/utils";

interface Alert {
  id: string;
  title: string;
  description: string;
  time: string;
  severity: string;
}

type SeverityLevel = "critical" | "high" | "medium" | "low" | "info";

type ToastTrigger = ReturnType<typeof useToast>["toast"];

const SEVERITY_DOT: Record<SeverityLevel, string> = {
  critical: "#ef4444",
  high: "#ef4444",
  medium: "#f97316",
  low: "#22c55e",
  info: "#9ca3af",
};

function getSeverityKey(severity: string): SeverityLevel {
  const normalized = severity?.toLowerCase() as SeverityLevel;
  if (normalized in SEVERITY_DOT) return normalized;
  return "info";
}

function formatAlertTime(timeStr: string): string {
  try {
    const date = new Date(timeStr);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return timeStr;
  }
}

function AlertToastDescription({ alert }: { alert: Alert }) {
  const key = getSeverityKey(alert.severity);
  const styles = SEVERITY_STYLES[key] ?? SEVERITY_STYLES.info;

  return (
    <div className="space-y-2 font-sans text-sm">
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "inline-flex rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide",
            styles.bg,
            styles.text,
            styles.border,
          )}
        >
          {alert.severity}
        </span>
        <span className="ml-auto text-[11px] text-gray-500">
          {formatAlertTime(alert.time)}
        </span>
      </div>
      <p className="m-0 leading-6 text-gray-600">{alert.description}</p>
      <div className="flex items-center gap-2 border-t border-gray-200 pt-2 text-[11px] text-gray-500">
        <span
          className="h-1.5 w-1.5 rounded-full"
          style={{ backgroundColor: SEVERITY_DOT[key] }}
        />
        <span>Alert ID: {alert.id}</span>
      </div>
    </div>
  );
}

export function showAlertToast(toast: ToastTrigger, alert: Alert) {
  const key = getSeverityKey(alert.severity);
  const isCritical = key === "critical" || key === "high";

  toast({
    title: alert.title,
    description: <AlertToastDescription alert={alert} />,
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
