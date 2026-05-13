"use client";

import { useEffect, useState } from "react";
import { ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DashboardLayout } from "@/components/dashboard-layout";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { showAlertToast } from "@/components/alert-notification";
import { getAlerts, getAlertStats } from "@/lib/api";

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
    switch (severity) {
      case "High":
        return "bg-red-500/20 text-red-300 border-red-500/30";
      case "Medium":
        return "bg-yellow-500/20 text-yellow-300 border-yellow-500/30";
      case "Low":
        return "bg-blue-500/20 text-blue-300 border-blue-500/30";
      default:
        return "bg-gray-500/20 text-gray-300";
    }
  };

  const getSeverityBorderColor = (severity: string) => {
    switch (severity) {
      case "High":
        return "border-red-500/30 hover:border-red-500/50";
      case "Medium":
        return "border-yellow-500/30 hover:border-yellow-500/50";
      case "Low":
        return "border-blue-500/30 hover:border-blue-500/50";
      default:
        return "border-gray-500/30";
    }
  };

  if (isLoading || !stats) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-muted-foreground">Loading...</div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground mb-2">Alerts</h1>
            <p className="text-muted-foreground">
              Security alerts and notifications from your network
            </p>
          </div>
          <Button onClick={simulateAlert} variant="secondary">
            Simulate Alert
          </Button>
        </div>

        {/* Alert Statistics */}
        <div className="grid grid-cols-1 gap-3 sm:gap-4 md:grid-cols-3">
          <Card className="border-border bg-card/50 backdrop-blur supports-backdrop-filter:bg-card/40 p-4">
            <div className="text-sm text-muted-foreground mb-1">
              Total Alerts
            </div>
            <div className="text-3xl font-bold text-foreground">
              {stats.total}
            </div>
          </Card>
          <Card className="border-border bg-card/50 backdrop-blur supports-backdrop-filter:bg-card/40 p-4">
            <div className="text-sm text-muted-foreground mb-1">Critical</div>
            <div className="text-3xl font-bold text-red-500">
              {stats.critical}
            </div>
          </Card>
          <Card className="border-border bg-card/50 backdrop-blur supports-backdrop-filter:bg-card/40 p-4">
            <div className="text-sm text-muted-foreground mb-1">Warnings</div>
            <div className="text-3xl font-bold text-yellow-500">
              {stats.warnings}
            </div>
          </Card>
        </div>

        {/* Alerts List */}
        <div className="space-y-2 md:space-y-3">
          {alerts.map((alert) => (
            <Card
              key={alert.id}
              className={`border-border bg-card/50 backdrop-blur supports-backdrop-filter:bg-card/40 cursor-pointer transition-all hover:shadow-lg ${getSeverityBorderColor(alert.severity)}`}
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
                    <h3 className="text-lg font-semibold text-foreground">
                      {alert.title}
                    </h3>
                  </div>
                  <p className="text-muted-foreground mb-3">
                    {alert.description}
                  </p>
                  <div className="text-xs text-muted-foreground">
                    {alert.time}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-accent hover:bg-accent/20"
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
