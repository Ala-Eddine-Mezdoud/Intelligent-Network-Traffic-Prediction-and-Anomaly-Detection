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
        <div className="flex items-center justify-center h-64">
          <div className="text-muted-foreground">Loading...</div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      navbarStatus={getNavbarStatus()}
      breadcrumbs={[{ label: "Dashboard" }, { label: "Network Overview" }]}
    >
      {/* ── Simulation Control Bar ─────────────────────────────────── */}
      <div className="mb-4 rounded-xl border border-border bg-card/60 backdrop-blur p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4 flex-wrap">
            {/* Running indicator */}
            <div className="flex items-center gap-2">
              <span
                className={`w-2.5 h-2.5 rounded-full ${isRunning ? "bg-sky-400 animate-pulse" : "bg-zinc-600"}`}
              />
              <span className="text-sm font-medium">
                {isRunning ? "Simulation Running" : "Simulation Idle"}
              </span>
            </div>

            {/* GNN status */}
            {gnnRunning && (
              <div className="flex items-center gap-1.5 text-xs text-sky-300 bg-sky-950/20 border border-sky-500/30 rounded-full px-2.5 py-1">
                <Network className="h-3 w-3" />
                GNN active · {predsMade} predictions
              </div>
            )}

            {/* Next attack countdown */}
            {isRunning && nextAttack && nextAttackIn != null && (
              <div className="flex items-center gap-1.5 text-xs text-slate-400 bg-slate-950/20 border border-slate-700/20 rounded-full px-2.5 py-1">
                <Clock className="h-3 w-3" />
                Next: <span className="font-semibold ml-1">{nextAttack}</span>
                <span className="ml-1 text-zinc-400">in {nextAttackIn}s</span>
              </div>
            )}

            {/* Last attack */}
            {lastAttack && (
              <div className="flex items-center gap-1.5 text-xs text-zinc-400">
                <ChevronRight className="h-3 w-3" />
                Last attack:{" "}
                <span className="text-zinc-200 font-medium ml-1">
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
                className="border-sky-500/50 text-sky-300 hover:bg-slate-900/30"
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
                className="bg-linear-to-r from-sky-500 to-blue-600 hover:from-sky-600 hover:to-blue-700 text-white font-semibold shadow-lg shadow-sky-500/20"
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
            <span className="text-xs text-zinc-500 self-center">
              Active anomalies:
            </span>
            {activeOpAnomalies.map((a, i) => (
              <span
                key={i}
                className="text-xs bg-zinc-800 border border-border rounded-full px-2.5 py-0.5 text-zinc-300"
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
                  className="text-xs font-mono bg-black/20 border border-current/20 rounded px-2 py-0.5"
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
        <div className="mb-4 rounded-xl border border-zinc-700/60 bg-zinc-900/50 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Siren className="h-4 w-4 text-sky-400" />
            <h3 className="text-sm font-semibold text-zinc-200">
              GNN Anomaly History
            </h3>
            <span className="ml-auto text-xs text-zinc-500">
              {anomalyHistory.length} events this session
            </span>
          </div>
          <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
            {anomalyHistory.slice(0, 20).map((event: any, i: number) => {
              const stateClass =
                STATE_COLORS[event.state] ??
                "text-sky-300 bg-sky-950/30 border-sky-500/40";
              const textColor = stateClass.split(" ")[0];
              return (
                <div
                  key={i}
                  className="flex items-center gap-3 text-xs bg-zinc-950/70 border border-zinc-800/80 rounded-lg px-3 py-2"
                >
                  <span className="text-zinc-500 font-mono shrink-0 w-16">
                    {event.timestamp?.split(" ")[1] ?? "—"}
                  </span>
                  <span className={`font-semibold shrink-0 ${textColor}`}>
                    {event.state.replace(/_/g, " ")}
                  </span>
                  <span className="text-zinc-500 shrink-0">
                    {(event.confidence * 100).toFixed(0)}%
                  </span>
                  <span className="text-zinc-600 truncate flex-1">
                    {event.anomaly_nodes?.map((n: any) => n.node).join(", ") ||
                      "—"}
                  </span>
                  <span className="text-zinc-500 font-mono shrink-0">
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
        <h2 className="text-2xl font-bold tracking-tight text-foreground">
          Network Overview
        </h2>
        <p className="text-muted-foreground text-sm">
          Real-time traffic monitoring and GNN anomaly detection · refreshes
          every 8s
        </p>
      </div>

      {/* ── Metric Cards ───────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:gap-6 md:grid-cols-2 lg:grid-cols-4 mb-4">
        <MetricCard
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
       
        />
        <MetricCard
          title="Active Connections"
          value={metrics.active_connections}
          icon={<Activity className="h-5 w-5" />}
          trend={metrics.active_connections > 80 ? "up" : "stable"}
          health="healthy"
          variant="connections"
          description="Concurrent session count"
         
        />
        <MetricCard
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
         
        />
        <MetricCard
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
        <Card className="border-border bg-card/50 backdrop-blur supports-backdrop-filter:bg-card/40">
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
                  fill="#8884d8"
                  dataKey="value"
                >
                  {protocolData.map((_, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={DASHBOARD_COLORS[index % DASHBOARD_COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1a1a2e",
                    border: "1px solid #16213e",
                    borderRadius: "8px",
                    color: "#ffffff",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* System Status */}
        <Card className="border-border bg-card/50 backdrop-blur supports-backdrop-filter:bg-card/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              System Status
              {simStatus?.gnn?.status?.running && (
                <span className="text-[11px] font-normal text-sky-300 bg-sky-950/30 border border-sky-500/30 rounded-full px-2 py-0.5 ml-auto">
                  GNN active · {windowState}
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <StatusBar
              label="Network Health"
              value={systemStatus.network_health_percent}
              color="bg-sky-500"
              textColor="text-sky-500"
            />
            <StatusBar
              label="Anomaly Detection"
              value={systemStatus.anomaly_detection_percent}
              color="bg-accent"
              textColor="text-accent"
            />
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">
                  Threat Level
                </span>
                <span
                  className={`text-sm font-semibold ${systemStatus.threat_level === "Low" ? "text-sky-400" : systemStatus.threat_level === "Medium" ? "text-sky-300" : "text-sky-300"}`}
                >
                  {systemStatus.threat_level}
                </span>
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div
                  className={`h-full rounded-full ${systemStatus.threat_level === "Low" ? "bg-sky-500" : systemStatus.threat_level === "Medium" ? "bg-sky-500" : "bg-sky-500"}`}
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
              <div className="pt-2 border-t border-border/50 text-xs text-zinc-500 space-y-1">
                <div className="flex justify-between">
                  <span>GNN window state</span>
                  <span
                    className={`font-medium ${isAnomaly ? "text-sky-300" : "text-sky-300"}`}
                  >
                    {windowState}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Anomaly nodes</span>
                  <span className="text-zinc-300">
                    {gnnPreds.anomaly_count} / {gnnPreds.total_nodes}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Last inference</span>
                  <span className="text-zinc-300 font-mono">
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
        <span className="text-sm text-muted-foreground">{label}</span>
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
