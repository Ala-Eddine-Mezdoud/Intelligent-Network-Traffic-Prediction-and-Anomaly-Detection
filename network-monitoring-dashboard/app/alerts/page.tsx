"use client";

import { Activity, useEffect, useState } from "react";
import { AlertTriangle, ChevronRight, TrendingUp } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DashboardLayout } from "@/components/dashboard-layout";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { showAlertToast } from "@/components/alert-notification";
import { getAlerts, getAlertStats } from "@/lib/api";
import { MetricCard, MetricCardSkeletonGrid } from "@/components/metric-card";
import { AlertsListSkeleton } from "@/components/skeletons";
import { SEVERITY_STYLES } from "@/lib/dashboard-theme";
import { getAlertCardAccent, pageSubtitle, pageTitle } from "@/lib/ui-theme";

interface Alert {
  id: string;
  title: string;
  description: string;
  time: string;
  severity: string;
}

interface AlertStats {
  total: number;
  critical: number;
  warnings: number;
}

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();

  const simulateAlert = () => {
    const simulatedAlert: Alert = {
      id: `sim-${Date.now()}`,
      title: "Simulated Network Alert",
      description:
        "This popup simulates a real alert notification in the dashboard.",
      time: new Date().toISOString(),
      severity: "High",
    };

    showAlertToast(toast, simulatedAlert);
  };

  useEffect(() => {
    let mounted = true;

    async function fetchData() {
      try {
        const [alertsRes, statsRes] = await Promise.all([
          getAlerts(),
          getAlertStats(),
        ]);
        if (!mounted) {
          return;
        }
        setAlerts(alertsRes.alerts);
        setStats(statsRes);
      } catch (error) {
        console.error("Failed to fetch alerts:", error);
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    fetchData();

    const timer = setInterval(fetchData, 30000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  const getSeverityColor = (severity: string) => {
    const s = severity.toLowerCase();
    const config = SEVERITY_STYLES[s] || SEVERITY_STYLES.default;
    return `${config.bg} ${config.text} ${config.border}`;
  };

  const getSeverityTextColor = (severity: string) => {
    const s = severity.toLowerCase();
    return (SEVERITY_STYLES[s] || SEVERITY_STYLES.default).text;
  };

  if (isLoading || !stats) {
    return (
      <DashboardLayout>
        <MetricCardSkeletonGrid count={3} className="mb-4" />
        <AlertsListSkeleton count={5} />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
    <div className="relative z-10 space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className={pageTitle}>Alerts</h1>
            <p className={pageSubtitle}>
              Security alerts and notifications from your network
            </p>
          </div>
          <Button onClick={simulateAlert} variant="secondary">
            Simulate Alert
          </Button>
        </div>


      {/* ── Alert Statistics ───────────────────────────────────────────── */}
{/* ── Alert Statistics ───────────────────────────────────────────── */}
<div className="grid grid-cols-1 gap-4 sm:gap-6 md:grid-cols-3 mb-4">
  <MetricCard
    index={0}
    title="Total Alerts"
    value={stats.total}
    icon={<Activity className="h-5 w-5" />}
    trend={stats.total > 20 ? "up" : "stable"}
    health={
      stats.total > 50
        ? "critical"
        : stats.total > 20
          ? "warning"
          : "healthy"
    }
    variant="traffic"
    description="Overall detected incidents"
  />

  <MetricCard
    index={1}
    title="Critical Alerts"
    value={stats.critical}
    icon={<AlertTriangle className="h-5 w-5" />}
    trend={stats.critical > 0 ? "up" : "stable"}
    health="critical"
    variant="critical"
    description="High severity security events"
  />

  <MetricCard
    index={2}
    title="Warnings"
    value={stats.warnings}
    icon={<TrendingUp className="h-5 w-5" />}
    trend={stats.warnings > 5 ? "up" : "stable"}
    health="warning"
    variant="warning"
    description="Medium severity notifications"
  />
</div>
        {/* Alerts List */}
        <div className="space-y-2 md:space-y-3">
          {alerts.map((alert) => (
            <Card
              key={alert.id}
              className={`cursor-pointer transition-shadow hover:shadow-md ${getAlertCardAccent(alert.severity)}`}
            >
              <div className="p-4 md:p-6 flex flex-col md:flex-row md:items-start md:justify-between gap-4 md:gap-0">
                <div className="flex-1">
                  <div className="flex items-start gap-4 mb-2">
                    <Badge
                      variant="outline"
                      className={getSeverityColor(alert.severity)}
                    >
                      {alert.severity}
                    </Badge>
                    <h3
                      className={`text-lg font-semibold ${getSeverityTextColor(alert.severity)}`}
                    >
                      {alert.title}
                    </h3>
                  </div>
                  <p className="mb-3 text-muted-foreground">
                    {alert.description}
                  </p>
                  <div className="text-xs text-muted-foreground">
                    {alert.time}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-muted-foreground hover:bg-muted"
                >
                  <ChevronRight className="h-5 w-5" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </DashboardLayout>
  );
}
