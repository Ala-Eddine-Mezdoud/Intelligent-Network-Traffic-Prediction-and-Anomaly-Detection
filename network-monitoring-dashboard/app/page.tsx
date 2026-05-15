"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Activity,
  AlertTriangle,
  Zap,
  TrendingUp,
  Play,
  Square,
  Loader2,
  Shield,
  Network,
  Clock,
  ChevronRight,
  Siren,
} from "lucide-react";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DashboardLayout } from "@/components/dashboard-layout";
import { MetricCard } from "@/components/metric-card";
import { DashboardPageSkeleton } from "@/components/skeletons";
import {
  getCurrentMetrics,
  getHistoricalTraffic,
  getPredictions,
  getProtocolDistribution,
  getSystemStatus,
  startRealtimePipeline,
  stopRealtimePipeline,
  getFullSimulationStatus,
  getGnnAnomalyHistory,
} from "@/lib/api";
import { DASHBOARD_COLORS, STATE_COLORS } from "@/lib/dashboard-theme";
import { TrafficPredictionChart } from "@/components/traffic-prediction-chart";
import {
  chartTooltipStyle,
  idleDot,
  mutedBadge,
  pageSection,
  pageSubtitle,
  pageTitle,
  primaryButton,
  loadingState,
  runningDot,
  statusBadge,
} from "@/lib/ui-theme";
import { cn } from "@/lib/utils";

// Redundant definitions removed - using centralized lib/dashboard-theme.ts

interface MetricsData {
  current_traffic_mbps: number;
  active_connections: number;
  anomaly_score_percent: number;
  alerts_today: number;
}

interface SystemStatus {
  network_health_percent: number;
  anomaly_detection_percent: number;
  threat_level: string;
}

interface GnnWindowPrediction {
  state: string;
  confidence: number;
  is_anomaly: boolean;
}

interface GnnNodeInfo {
  predicted_state: string;
  confidence: number;
  is_anomaly: boolean;
  current_traffic_mbps: number;
  forecast_30s_mbps: number;
  ip: string;
}

interface AnomalyNode {
  node: string;
  state: string;
  confidence: number;
}

interface GnnPredictions {
  timestamp: string;
  window_prediction: GnnWindowPrediction;
  per_node: Record<string, GnnNodeInfo>;
  anomaly_nodes: AnomalyNode[];
  anomaly_count: number;
  total_nodes: number;
  current_traffic_mbps: number;
  active_connections: number;
  traffic_series: Array<{
    time: string;
    historical: number | null;
    predicted: number | null;
    upper: number | null;
    lower: number | null;
  }>;
}

interface SimStatus {
  pipeline: {
    running: boolean;
    interval_seconds: number;
    next_attack_profile: string | null;
    next_attack_in_seconds: number | null;
    last_attack: { name: string; timestamp: string } | null;
    active_operational_anomalies: Array<{
      node: string;
      profile: string;
      duration_seconds: number;
    }>;
    gnn_inference: {
      running: boolean;
      predictions_made: number;
      window_state: string | null;
      anomaly_count: number;
    };
  };
  gnn: {
    status: { model_loaded: boolean; running: boolean; error: string | null };
    predictions: GnnPredictions | null;
  };
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [predictionData, setPredictionData] = useState<any[]>([]);
  const [protocolData, setProtocolData] = useState<any[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [simStatus, setSimStatus] = useState<SimStatus | null>(null);
  const [trafficHistory, setTrafficHistory] = useState<number[]>([]);
  const [anomalyHistory, setAnomalyHistory] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isPipelineStarting, setIsPipelineStarting] = useState(false);
  const [isPipelineStopping, setIsPipelineStopping] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [
        metricsRes,
        trafficHistRes,
        predictionRes,
        protocolRes,
        statusRes,
        simRes,
        histRes,
      ] = await Promise.all([
        getCurrentMetrics(),
        getHistoricalTraffic(),
        getPredictions(),
        getProtocolDistribution(),
        getSystemStatus(),
        getFullSimulationStatus(),
        getGnnAnomalyHistory(),
      ]);

      setMetrics(metricsRes);
      setTrafficHistory(
        Array.isArray(trafficHistRes.data)
          ? trafficHistRes.data.map((item) =>
              typeof item === "number"
                ? item
                : typeof item?.historical === "number"
                  ? item.historical
                  : typeof item?.value === "number"
                    ? item.value
                    : 0,
            )
          : [],
      );
      setPredictionData(predictionRes.data);
      setProtocolData(protocolRes.data);
      setSystemStatus(statusRes);
      if (simRes) setSimStatus(simRes as SimStatus);
      if (histRes?.events) setAnomalyHistory(histRes.events);
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    const run = async () => {
      if (mounted) await fetchData();
    };
    run();
    const timer = setInterval(run, 8000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, [fetchData]);

  const handleStartPipeline = async () => {
    setIsPipelineStarting(true);
    try {
      await startRealtimePipeline(30);
      await fetchData();
    } catch (error) {
      console.error("Failed to start pipeline:", error);
    } finally {
      setIsPipelineStarting(false);
    }
  };

  const handleStopPipeline = async () => {
    setIsPipelineStopping(true);
    try {
      await stopRealtimePipeline();
      await fetchData();
    } catch (error) {
      console.error("Failed to stop pipeline:", error);
    } finally {
      setIsPipelineStopping(false);
    }
  };

  const isRunning = simStatus?.pipeline?.running ?? false;
  const gnnPreds = simStatus?.gnn?.predictions;
  const windowState = gnnPreds?.window_prediction?.state ?? "NORMAL";
  const windowConf = gnnPreds?.window_prediction?.confidence ?? 0;
  const isAnomaly = gnnPreds?.window_prediction?.is_anomaly ?? false;
  const anomalyNodes = gnnPreds?.anomaly_nodes ?? [];
  const nextAttack = simStatus?.pipeline?.next_attack_profile;
  const nextAttackIn = simStatus?.pipeline?.next_attack_in_seconds;
  const lastAttack = simStatus?.pipeline?.last_attack;
  const activeOpAnomalies =
    simStatus?.pipeline?.active_operational_anomalies ?? [];
  const gnnRunning = simStatus?.pipeline?.gnn_inference?.running ?? false;
  const predsMade = simStatus?.pipeline?.gnn_inference?.predictions_made ?? 0;

  const trafficSparkline =
    trafficHistory.length > 1 ? trafficHistory.slice(-6) : undefined;
  const previousTraffic =
    trafficSparkline && trafficSparkline.length > 1
      ? trafficSparkline[trafficSparkline.length - 2]
      : metrics?.current_traffic_mbps || 0;
  const trafficTrendValue = previousTraffic
    ? `${Math.round(
        ((metrics.current_traffic_mbps - previousTraffic) /
          Math.max(previousTraffic, 1)) *
          100,
      )}% vs last interval`
    : undefined;

  // Determine navbar status based on system health
  const getNavbarStatus = () => {
    if (metrics.anomaly_score_percent > 70 || metrics.alerts_today > 10)
      return "critical";
    if (metrics.anomaly_score_percent > 30 || metrics.alerts_today > 5)
      return "warning";
    return "healthy";
  };

  if (isLoading || !metrics || !systemStatus) {
    return (
      <DashboardLayout navbarStatus="healthy">
        <DashboardPageSkeleton />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      navbarStatus={getNavbarStatus()}
      breadcrumbs={[{ label: "Dashboard" }, { label: "Network Overview" }]}
    >
      {/* ── Simulation Control Bar ─────────────────────────────────── */}
      <div className={cn(pageSection, "mb-4")}>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4 flex-wrap">
            {/* Running indicator */}
            <div className="flex items-center gap-2">
              <span
                className={cn("h-2.5 w-2.5 rounded-full", isRunning ? runningDot : idleDot)}
              />
              <span className="text-sm font-medium">
                {isRunning ? "Simulation Running" : "Simulation Idle"}
              </span>
            </div>

            {/* GNN status */}
            {gnnRunning && (
              <div className={cn(mutedBadge, statusBadge.healthy)}>
                <Network className="h-3 w-3" />
                GNN active · {predsMade} predictions
              </div>
            )}

            {/* Next attack countdown */}
            {isRunning && nextAttack && nextAttackIn != null && (
              <div className={mutedBadge}>
                <Clock className="h-3 w-3" />
                Next: <span className="font-semibold ml-1">{nextAttack}</span>
                <span className="ml-1 text-gray-400">in {nextAttackIn}s</span>
              </div>
            )}

            {/* Last attack */}
            {lastAttack && (
              <div className="flex items-center gap-1.5 text-xs text-gray-400">
                <ChevronRight className="h-3 w-3" />
                Last attack:{" "}
                <span className="font-medium text-gray-700 ml-1">
                  {lastAttack.name}
                </span>
              </div>
            )}
          </div>

          {/* Start / Stop button */}
          <div className="flex items-center gap-2">
            {isRunning ? (
              <Button
                onClick={handleStopPipeline}
                disabled={isPipelineStopping}
                variant="outline"
                size="sm"
                className="border-gray-200 text-gray-700 hover:bg-gray-50"
              >
                {isPipelineStopping ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Square className="mr-2 h-4 w-4 fill-current" />
                )}
                Stop Simulation
              </Button>
            ) : (
              <Button
                onClick={handleStartPipeline}
                disabled={isPipelineStarting}
                size="sm"
                className={primaryButton}
              >
                {isPipelineStarting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Play className="mr-2 h-4 w-4 fill-current" />
                )}
                Start Simulation
              </Button>
            )}
          </div>
        </div>

        {/* Active operational anomalies row */}
        {activeOpAnomalies.length > 0 && (
          <div className="mt-3 pt-3 border-t border-border/50 flex flex-wrap gap-2">
            <span className="text-xs text-gray-500 self-center">
              Active anomalies:
            </span>
            {activeOpAnomalies.map((a, i) => (
              <span
                key={i}
                className="rounded-full border border-gray-200 bg-gray-100 px-2.5 py-0.5 text-xs text-gray-600"
              >
                {a.node} · {a.profile} · {a.duration_seconds}s
              </span>
            ))}
          </div>
        )}
      </div>

      {/* ── GNN Anomaly Banner ─────────────────────────────────────── */}
      {gnnRunning && isAnomaly && (
        <div
          className={`mb-4 rounded-xl border px-5 py-3.5 flex items-center justify-between ${STATE_COLORS[windowState] ?? STATE_COLORS.NORMAL}`}
        >
          <div className="flex items-center gap-3">
            <Siren className="h-5 w-5 shrink-0" />
            <div>
              <p className="text-sm font-semibold">
                GNN Detected: {windowState.replace(/_/g, " ")}
              </p>
              <p className="text-xs opacity-75">
                Confidence {(windowConf * 100).toFixed(0)}%
                {anomalyNodes.length > 0 &&
                  ` · ${anomalyNodes.length} node${anomalyNodes.length > 1 ? "s" : ""} affected`}
              </p>
            </div>
          </div>
          {anomalyNodes.length > 0 && (
            <div className="flex flex-wrap gap-1.5 justify-end">
              {anomalyNodes.slice(0, 6).map((n) => (
                <span
                  key={n.node}
                  className="rounded border border-current/20 bg-gray-100 px-2 py-0.5 font-mono text-xs"
                >
                  {n.node}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── GNN Anomaly History Panel ──────────────────────────────── */}
      {anomalyHistory.length > 0 && (
        <div className={cn(pageSection, "mb-4")}>
          <div className="flex items-center gap-2 mb-3">
            <Siren className="h-4 w-4 text-orange-500" />
            <h3 className="text-sm font-semibold text-gray-900">
              GNN Anomaly History
            </h3>
            <span className="ml-auto text-xs text-gray-500">
              {anomalyHistory.length} events this session
            </span>
          </div>
          <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
            {anomalyHistory.slice(0, 20).map((event: any, i: number) => {
              const stateClass =
                STATE_COLORS[event.state] ??
                "text-orange-500 bg-orange-500/10 border-orange-500/30";
              const textColor = stateClass.split(" ")[0];
              return (
                <div
                  key={i}
                  className="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs"
                >
                  <span className="text-gray-500 font-mono shrink-0 w-16">
                    {event.timestamp?.split(" ")[1] ?? "—"}
                  </span>
                  <span className={`font-semibold shrink-0 ${textColor}`}>
                    {event.state.replace(/_/g, " ")}
                  </span>
                  <span className="text-gray-500 shrink-0">
                    {(event.confidence * 100).toFixed(0)}%
                  </span>
                  <span className="text-gray-600 truncate flex-1">
                    {event.anomaly_nodes?.map((n: any) => n.node).join(", ") ||
                      "—"}
                  </span>
                  <span className="text-gray-500 font-mono shrink-0">
                    {event.total_traffic_mbps} Mbps
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Page Title ─────────────────────────────────────────────── */}
      <div className="mb-4">
        <h2 className={pageTitle}>Network Overview</h2>
        <p className={pageSubtitle}>
          Real-time traffic monitoring and GNN anomaly detection · refreshes
          every 8s
        </p>
      </div>

      {/* ── Metric Cards ───────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:gap-6 md:grid-cols-2 lg:grid-cols-4 mb-4">
        <MetricCard
          index={0}
          title="Current Traffic"
          value={metrics.current_traffic_mbps}
          unit="Mbps"
          icon={<Zap className="h-5 w-5" />}
          trend={metrics.current_traffic_mbps > previousTraffic ? "up" : "down"}
          trendValue={trafficTrendValue}
          health="healthy"
          variant="traffic"
          description="Network throughput capacity"
          sparklineData={trafficSparkline}
          isLive
        />
        <MetricCard
          index={1}
          title="Active Connections"
          value={metrics.active_connections}
          icon={<Activity className="h-5 w-5" />}
          trend={metrics.active_connections > 80 ? "up" : "stable"}
          health="healthy"
          variant="connections"
          description="Concurrent session count"
          isLive
        />
        <MetricCard
          index={2}
          title="Anomaly Score"
          value={metrics.anomaly_score_percent}
          unit="%"
          icon={<AlertTriangle className="h-5 w-5" />}
          trend={metrics.anomaly_score_percent > 70 ? "up" : "down"}
          health={
            metrics.anomaly_score_percent > 70
              ? "critical"
              : metrics.anomaly_score_percent > 30
                ? "warning"
                : "healthy"
          }
          variant="anomaly"
          description="AI detection confidence"
          isLive
        />
        <MetricCard
          index={3}
          title="Alerts Today"
          value={metrics.alerts_today}
          icon={<TrendingUp className="h-5 w-5" />}
          trend={metrics.alerts_today > 5 ? "up" : "stable"}
          health={
            metrics.alerts_today > 10
              ? "critical"
              : metrics.alerts_today > 5
                ? "warning"
                : "healthy"
          }
          variant="alerts"
          description="Security incident volume"
          isLive
        />
      </div>

      {/* ── Anomaly Nodes (when GNN running + anomalies) ───────────── */}
      {gnnRunning && anomalyNodes.length > 0 && (
        <div className="mb-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {anomalyNodes.map((node) => {
            const nodeInfo = gnnPreds?.per_node?.[node.node];
            const colorClass = STATE_COLORS[node.state] ?? STATE_COLORS.NORMAL;
            return (
              <div
                key={node.node}
                className={`rounded-lg border p-3 ${colorClass}`}
              >
                <p className="text-xs font-mono font-semibold mb-1">
                  {node.node}
                </p>
                <p className="text-[11px] opacity-80">
                  {node.state.replace(/_/g, " ")}
                </p>
                <p className="text-[10px] opacity-60 mt-1">
                  {(node.confidence * 100).toFixed(0)}% conf
                  {nodeInfo
                    ? ` · ${nodeInfo.current_traffic_mbps.toFixed(1)} Mbps`
                    : ""}
                </p>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Traffic Prediction Chart ────────────────────────────────── */}
      <TrafficPredictionChart 
        data={predictionData} 
        showLiveBadge={gnnRunning} 
      />

      {/* ── Charts Row ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-2">
        {/* Protocol Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Traffic by Protocol</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center">
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={protocolData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name} ${value}%`}
                  outerRadius={80}
                  fill={DASHBOARD_COLORS[0]}
                  dataKey="value"
                >
                  {protocolData.map((_, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={DASHBOARD_COLORS[index % DASHBOARD_COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip contentStyle={chartTooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* System Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              System Status
              {simStatus?.gnn?.status?.running && (
                <span className={cn(mutedBadge, statusBadge.healthy, "ml-auto font-normal")}>
                  GNN active · {windowState}
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <StatusBar
              label="Network Health"
              value={systemStatus.network_health_percent}
              color="bg-green-500"
              textColor="text-green-500"
            />
            <StatusBar
              label="Anomaly Detection"
              value={systemStatus.anomaly_detection_percent}
              color="bg-orange-500"
              textColor="text-orange-500"
            />
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Threat Level</span>
                <span
                  className={`text-sm font-semibold ${systemStatus.threat_level === "Low" ? "text-green-500" : systemStatus.threat_level === "Medium" ? "text-orange-500" : "text-red-500"}`}
                >
                  {systemStatus.threat_level}
                </span>
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div
                  className={`h-full rounded-full ${systemStatus.threat_level === "Low" ? "bg-green-500" : systemStatus.threat_level === "Medium" ? "bg-orange-500" : "bg-red-500"}`}
                  style={{
                    width:
                      systemStatus.threat_level === "Low"
                        ? "33%"
                        : systemStatus.threat_level === "Medium"
                          ? "66%"
                          : "100%",
                  }}
                />
              </div>
            </div>
            {gnnRunning && gnnPreds && (
              <div className="pt-2 border-t border-border/50 text-xs text-gray-500 space-y-1">
                <div className="flex justify-between">
                  <span>GNN window state</span>
                  <span
                    className={`font-medium ${isAnomaly ? "text-red-500" : "text-green-500"}`}
                  >
                    {windowState}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Anomaly nodes</span>
                  <span className="text-gray-600">
                    {gnnPreds.anomaly_count} / {gnnPreds.total_nodes}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Last inference</span>
                  <span className="font-mono text-gray-600">
                    {gnnPreds.timestamp?.split(" ")[1] ?? "–"}
                  </span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

function StatusBar({
  label,
  value,
  color,
  textColor,
}: {
  label: string;
  value: number;
  color: string;
  textColor: string;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-600">{label}</span>
        <span className={`text-sm font-semibold ${textColor}`}>{value}%</span>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}
