"use client";

import { useState, useEffect } from "react";
import {
  getLabStatus,
  startCapture,
  stopCapture,
  startTraffic,
  stopTraffic,
  relayCapture,
  runInference,
} from "@/lib/simulation-api";
import {
  startRealtimePipeline,
  stopRealtimePipeline,
  getFullSimulationStatus,
  startNormalSimulation,
  stopNormalSimulation,
  injectAnomaly,
  getStorageInfo,
} from "@/lib/api";
import {
  Activity,
  Play,
  Square,
  Cpu,
  Send,
  Network,
  Clock,
  Zap,
  AlertTriangle,
  Wifi,
  Gauge,
  Droplets,
  Shield,
  Bug,
  Siren,
  Database,
  FolderOpen,
} from "lucide-react";
import { DashboardLayout } from "@/components/dashboard-layout";
import { useToast } from "@/hooks/use-toast";
import { TopologyGraph } from "@/components/topology-graph";

const ANOMALY_CONFIGS = [
  {
    type: "congestion",
    label: "Congestion",
    icon: Gauge,
    color: "orange",
    desc: "Rate-limit a node (4 Mbit)",
  },
  {
    type: "latency",
    label: "Latency",
    icon: Clock,
    color: "orange",
    desc: "300 ms delay spike",
  },
  {
    type: "packet_loss",
    label: "Packet Loss",
    icon: Droplets,
    color: "red",
    desc: "8% random drops",
  },
  {
    type: "jitter",
    label: "Jitter",
    icon: Wifi,
    color: "orange",
    desc: "80 ms jitter on link",
  },
  {
    type: "brownout",
    label: "Brownout",
    icon: AlertTriangle,
    color: "orange",
    desc: "Combined degradation",
  },
  {
    type: "ddos",
    label: "DDoS",
    icon: Zap,
    color: "red",
    desc: "50 Mbit UDP flood",
  },
  {
    type: "portscan",
    label: "Port Scan",
    icon: Bug,
    color: "orange",
    desc: "Rapid port sweep",
  },
  {
    type: "brute_force",
    label: "Brute Force",
    icon: Shield,
    color: "red",
    desc: "SSH connection burst",
  },
] as const;

type AnomalyType = (typeof ANOMALY_CONFIGS)[number]["type"];

const ANOMALY_NODES: Record<AnomalyType, string[]> = {
  congestion: ["e1_pc1", "e2_pc1", "h2_nas", "e1_erp"],
  latency: ["h1_pc", "e2_pc1", "dc_monitor", "h2_pc"],
  packet_loss: ["dc_web", "dc_monitor", "h2_pc", "e1_pc2"],
  jitter: ["h1_tv", "h2_cam", "h1_iot", "e2_pc2"],
  brownout: ["dc_web", "dc_monitor", "h1_pc", "e2_crm"],
  ddos: ["dc_web"],
  portscan: ["dc_web", "dc_vpn"],
  brute_force: ["dc_vpn"],
};

const colorMap: Record<string, string> = {
  orange: "border-orange-500/30 text-orange-600 hover:bg-orange-500/10",
  red: "border-red-500/30 text-red-600 hover:bg-red-500/10",
  gray: "border-border text-muted-foreground hover:bg-muted",
};

const colorActiveMap: Record<string, string> = {
  orange: "bg-orange-500/10 border-orange-500/30 text-orange-600",
  red: "bg-red-500/10 border-red-500/30 text-red-600",
  gray: "bg-muted border-border text-foreground",
};

export default function SimulationPage() {
  const [status, setStatus] = useState<any>(null);
  const [simStatus, setSimStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [simLoading, setSimLoading] = useState(false);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);

  const [storageInfo, setStorageInfo] = useState<any>(null);

  // Anomaly injection state
  const [selectedAnomaly, setSelectedAnomaly] = useState<AnomalyType | null>(
    null,
  );
  const [selectedNode, setSelectedNode] = useState<string>("");
  const [duration, setDuration] = useState(30);
  const [injecting, setInjecting] = useState(false);
  const [lastInjected, setLastInjected] = useState<string | null>(null);

  const { toast } = useToast();

  const canRelay =
    !loading && !status?.capture_running && !!status?.last_capture_id;
  const canInfer = !loading && !!status?.last_relay;
  const relayBlockedReason = status?.capture_running
    ? "Stop capture before relay."
    : !status?.last_capture_id
      ? "Start and stop a capture first."
      : null;
  const inferBlockedReason = !status?.last_relay
    ? "Run Relay Capture first."
    : null;

  const isRealtimeRunning = simStatus?.pipeline?.running ?? false;
  const isNormalRunning = simStatus?.normal?.running ?? false;
  const anySimRunning = isRealtimeRunning || isNormalRunning;
  const gnnActive = simStatus?.gnn?.status?.running ?? false;
  const predsMade = simStatus?.gnn?.status?.predictions_made ?? 0;
  const windowState =
    simStatus?.gnn?.predictions?.window_prediction?.state ?? null;
  const anomalyCount = simStatus?.gnn?.predictions?.anomaly_count ?? 0;
  const nextAttack = simStatus?.pipeline?.next_attack_profile;
  const nextAttackIn = simStatus?.pipeline?.next_attack_in_seconds;
  const lastAttack = simStatus?.pipeline?.last_attack;
  const activeOpAnomalies = [
    ...(simStatus?.pipeline?.active_operational_anomalies ?? []),
    ...(simStatus?.normal?.active_operational_anomalies ?? []),
  ];

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [labData, simData, storeData] = await Promise.all([
          getLabStatus(),
          getFullSimulationStatus(),
          getStorageInfo(),
        ]);
        setStatus(labData);
        if (simData) setSimStatus(simData);
        if (storeData) setStorageInfo(storeData);
      } catch {
        console.error("Failed to connect to simulation backend");
      }
    };
    fetchAll();
    const interval = setInterval(fetchAll, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleStartNormal = async () => {
    setSimLoading(true);
    try {
      await startNormalSimulation();
      toast({
        title: "Normal simulation started",
        description: "Steady background traffic + GNN inference running.",
      });
    } catch (e: any) {
      toast({
        title: "Failed to start",
        description: e?.message ?? "Unknown error",
        variant: "destructive",
      });
    } finally {
      setSimLoading(false);
    }
  };

  const handleStopNormal = async () => {
    setSimLoading(true);
    try {
      await stopNormalSimulation();
      toast({ title: "Normal simulation stopped" });
    } catch (e: any) {
      toast({
        title: "Failed to stop",
        description: e?.message ?? "Unknown error",
        variant: "destructive",
      });
    } finally {
      setSimLoading(false);
    }
  };

  const handleStartRealtime = async () => {
    setSimLoading(true);
    try {
      await startRealtimePipeline(30);
      toast({
        title: "Full simulation started",
        description: "Traffic + attack injection + GNN inference.",
      });
    } catch (e: any) {
      toast({
        title: "Failed to start",
        description: e?.message ?? "Unknown error",
        variant: "destructive",
      });
    } finally {
      setSimLoading(false);
    }
  };

  const handleStopRealtime = async () => {
    setSimLoading(true);
    try {
      await stopRealtimePipeline();
      toast({ title: "Simulation stopped" });
    } catch (e: any) {
      toast({
        title: "Failed to stop",
        description: e?.message ?? "Unknown error",
        variant: "destructive",
      });
    } finally {
      setSimLoading(false);
    }
  };

  const handleInjectAnomaly = async () => {
    if (!selectedAnomaly) return;
    setInjecting(true);
    try {
      const node = selectedNode || undefined;
      await injectAnomaly(selectedAnomaly, node, duration);
      const label =
        ANOMALY_CONFIGS.find((a) => a.type === selectedAnomaly)?.label ??
        selectedAnomaly;
      const target = node || "default";
      setLastInjected(`${label} on ${target} for ${duration}s`);
      toast({
        title: `Injected: ${label}`,
        description: `Applied to ${target} for ${duration}s — watch GNN panel.`,
      });
    } catch (e: any) {
      toast({
        title: "Injection failed",
        description: e?.message ?? "No simulation running",
        variant: "destructive",
      });
    } finally {
      setInjecting(false);
    }
  };

  const handleAction = async (
    actionFn: () => Promise<any>,
    actionLabel: string,
    successTitle: string,
    successDescription: string,
  ) => {
    setLoading(true);
    setActiveAction(actionLabel);
    try {
      const result = await actionFn();
      if (result?.error) throw new Error(result.error);
      const newStatus = await getLabStatus();
      setStatus(newStatus);
      setLastError(null);
      toast({ title: successTitle, description: successDescription });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setLastError(message);
      toast({
        title: "Action failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
      setActiveAction(null);
    }
  };

  const isActive = (key: string) => loading && activeAction === key;

  const availableNodes = selectedAnomaly ? ANOMALY_NODES[selectedAnomaly] : [];

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full w-full gap-6 px-2 py-4">
        {/* ── Page Header ──────────────────────────────────────────────── */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              Network Simulation Lab
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Run steady-state or full simulation, then inject anomalies to test
              GNN detection.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted border border-border rounded-full px-3 py-1.5">
            <span
              className={`w-2 h-2 rounded-full ${anySimRunning ? "bg-green-500 animate-pulse" : "bg-muted-foreground/30"}`}
            />
            {anySimRunning
              ? isNormalRunning
                ? "Normal Mode"
                : "Full Mode"
              : "Idle"}
          </div>
        </div>

        {/* ── GNN Status Bar ─────────────────────────────────────────── */}
        {gnnActive && (
          <div className="rounded-2xl border border-border bg-muted px-4 py-3 flex items-center gap-4 flex-wrap shadow-sm">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Network className="h-4 w-4 text-foreground" />
              <span className="font-semibold text-foreground">GNN Active</span>
              <span className="text-muted-foreground">·</span>
              <span>{predsMade} predictions</span>
            </div>
            {windowState && (
              <div
                className={`flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border ${
                  windowState === "NORMAL"
                    ? "border-green-500/30 text-foreground bg-green-500/10"
                    : windowState === "WARNING"
                      ? "border-orange-500/30 text-orange-600 bg-orange-500/10 animate-pulse"
                      : "border-red-500/30 text-red-600 bg-red-500/10 animate-pulse"
                }`}
              >
                {windowState !== "NORMAL" && <Siren className="h-3 w-3" />}
                {windowState}
                {anomalyCount > 0 && (
                  <span className="ml-1 text-red-600">
                    · {anomalyCount} nodes
                  </span>
                )}
              </div>
            )}
            {isRealtimeRunning && nextAttack && nextAttackIn != null && (
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-card border border-border rounded-full px-2.5 py-0.5">
                <Clock className="h-3 w-3" />
                Next: {nextAttack} in {nextAttackIn}s
              </div>
            )}
            {lastAttack && (
              <span className="text-xs text-muted-foreground">
                Last attack:{" "}
                <span className="text-foreground">{lastAttack.name}</span>
              </span>
            )}
            {activeOpAnomalies.length > 0 && (
              <div className="flex flex-wrap gap-1.5 items-center">
                <span className="text-[11px] text-muted-foreground">Active:</span>
                {activeOpAnomalies.map((a: any, i: number) => (
                  <span
                    key={i}
                    className="text-[11px] bg-muted border border-border rounded-full px-2 py-0.5 text-muted-foreground"
                  >
                    {a.node} · {a.profile} ·{" "}
                    {Math.max(0, Math.round(a.expires_at - Date.now() / 1000))}s
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Simulation Mode Selector ──────────────────────────────── */}
        <div className="bg-card border border-border shadow-sm rounded-2xl p-4 space-y-3">
          <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
            Simulation Mode
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Normal Mode */}
            <div
              className={`rounded-lg border p-4 space-y-3 transition-colors ${isNormalRunning ? "border-green-500/30 bg-green-500/10" : "border-border bg-muted"}`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full shrink-0 ${isNormalRunning ? "bg-green-500 animate-pulse" : "bg-muted-foreground/30"}`}
                />
                <span className="text-sm font-semibold text-foreground">
                  Normal Simulation
                </span>
                <span
                  className={`ml-auto text-[11px] px-2 py-0.5 rounded-full border ${isNormalRunning ? "border-green-500/30 text-foreground bg-green-500/10" : "border-border text-muted-foreground"}`}
                >
                  {isNormalRunning ? "Running" : "Stopped"}
                </span>
              </div>
              <p className="text-[12px] text-muted-foreground leading-snug">
                Steady balanced traffic across all 26 nodes — matching GNN
                training conditions. No auto-attacks. Use the injection panel
                below to test anomaly detection.
              </p>
              <div className="flex gap-2">
                {isNormalRunning ? (
                  <button
                    onClick={handleStopNormal}
                    disabled={simLoading || isRealtimeRunning}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border border-border text-muted-foreground hover:bg-muted transition-colors disabled:opacity-40"
                  >
                    <Square className="w-3 h-3 fill-current" />
                    {simLoading ? "Stopping…" : "Stop"}
                  </button>
                ) : (
                  <button
                    onClick={handleStartNormal}
                    disabled={simLoading || anySimRunning}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-foreground hover:bg-foreground/90 text-background transition-colors disabled:opacity-40"
                  >
                    <Play className="w-3 h-3 fill-current" />
                    {simLoading ? "Starting…" : "Start Normal"}
                  </button>
                )}
              </div>
            </div>

            {/* Full Mode */}
            <div
              className={`rounded-lg border p-4 space-y-3 transition-colors ${isRealtimeRunning ? "border-green-500/30 bg-green-500/10" : "border-border bg-muted"}`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full shrink-0 ${isRealtimeRunning ? "bg-green-500 animate-pulse" : "bg-muted-foreground/30"}`}
                />
                <span className="text-sm font-semibold text-foreground">
                  Full Simulation
                </span>
                <span
                  className={`ml-auto text-[11px] px-2 py-0.5 rounded-full border ${isRealtimeRunning ? "border-green-500/30 text-foreground bg-green-500/10" : "border-border text-muted-foreground"}`}
                >
                  {isRealtimeRunning ? "Running" : "Stopped"}
                </span>
              </div>
              <p className="text-[12px] text-muted-foreground leading-snug">
                Full realtime pipeline with periodic attack injection (DDoS,
                PortScan, SSH-Patator…), pcap capture, and IDS inference every
                30 s.
              </p>
              <div className="flex gap-2">
                {isRealtimeRunning ? (
                  <button
                    onClick={handleStopRealtime}
                    disabled={simLoading || isNormalRunning}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border border-border text-muted-foreground hover:bg-muted transition-colors disabled:opacity-40"
                  >
                    <Square className="w-3 h-3 fill-current" />
                    {simLoading ? "Stopping…" : "Stop"}
                  </button>
                ) : (
                  <button
                    onClick={handleStartRealtime}
                    disabled={simLoading || anySimRunning}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-foreground hover:bg-foreground/90 text-background transition-colors disabled:opacity-40"
                  >
                    <Play className="w-3 h-3 fill-current" />
                    {simLoading ? "Starting…" : "Start Full"}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* ── Manual Anomaly Injection ──────────────────────────────── */}
        <div className="bg-card border border-border shadow-sm rounded-2xl p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-foreground">
                Manual Anomaly Injection
              </p>
              <p className="text-[12px] text-muted-foreground mt-0.5">
                Inject a specific anomaly and observe GNN detection in real
                time.
              </p>
            </div>
            {!anySimRunning && (
              <span className="text-[11px] text-muted-foreground bg-muted border border-border rounded-full px-2.5 py-0.5">
                Start a simulation first
              </span>
            )}
          </div>

          {/* Anomaly Type Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {ANOMALY_CONFIGS.map(({ type, label, icon: Icon, color, desc }) => {
              const isSelected = selectedAnomaly === type;
              return (
                <button
                  key={type}
                  onClick={() => {
                    setSelectedAnomaly(type);
                    setSelectedNode("");
                  }}
                  className={`flex flex-col items-start gap-1 p-3 rounded-lg border text-left transition-all ${
                    isSelected
                      ? colorActiveMap[color]
                      : `bg-card ${colorMap[color]}`
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span className="text-[12px] font-semibold leading-tight">
                    {label}
                  </span>
                  <span className="text-[10px] text-muted-foreground leading-tight">
                    {desc}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Config Row */}
          {selectedAnomaly && (
            <div className="flex flex-wrap items-end gap-3 pt-2 border-t border-border/40">
              {/* Node selector */}
              <div className="flex flex-col gap-1">
                <label className="text-[11px] text-muted-foreground uppercase tracking-wider">
                  Target Node
                </label>
                <select
                  value={selectedNode}
                  onChange={(e) => setSelectedNode(e.target.value)}
                  className="bg-card border border-border rounded-md px-2.5 py-1.5 text-xs text-foreground outline-none focus:border-ring"
                >
                  <option value="">Auto (default)</option>
                  {availableNodes.map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </div>

              {/* Duration */}
              <div className="flex flex-col gap-1 min-w-32">
                <label className="text-[11px] text-muted-foreground uppercase tracking-wider">
                  Duration:{" "}
                  <span className="text-foreground font-semibold">
                    {duration}s
                  </span>
                </label>
                <input
                  type="range"
                  min={10}
                  max={120}
                  step={5}
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                  className="w-full accent-orange-500"
                />
              </div>

              {/* Inject button */}
              <button
                onClick={handleInjectAnomaly}
                disabled={!anySimRunning || injecting}
                className="flex items-center gap-1.5 px-4 py-2 rounded-md text-xs font-semibold bg-foreground hover:bg-foreground/90 text-background transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Zap className="w-3.5 h-3.5" />
                {injecting
                  ? "Injecting…"
                  : `Inject ${ANOMALY_CONFIGS.find((a) => a.type === selectedAnomaly)?.label}`}
              </button>

              {lastInjected && (
                <span className="text-[11px] text-muted-foreground bg-muted border border-border rounded-full px-2.5 py-1">
                  ✓ {lastInjected}
                </span>
              )}
            </div>
          )}
        </div>

        {/* ── Data & Results Storage ──────────────────────────────── */}
        {storageInfo && (
          <div className="bg-card border border-border shadow-sm rounded-2xl p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-muted-foreground" />
              <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                Data & Results Storage
              </p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <StorageCard
                icon={<FolderOpen className="h-3.5 w-3.5" />}
                label="PCAP Captures"
                count={storageInfo.captures?.pcap_files ?? 0}
                path="captures/"
                latest={storageInfo.captures?.latest_pcap}
                color="gray"
              />
              <StorageCard
                icon={<Cpu className="h-3.5 w-3.5" />}
                label="IDS Inference"
                count={storageInfo.intelligence_out?.inference_files ?? 0}
                path="captures/intelligence_out/"
                latest={storageInfo.intelligence_out?.latest_inference}
                color="orange"
              />
              <StorageCard
                icon={<Siren className="h-3.5 w-3.5" />}
                label="GNN Anomalies"
                count={storageInfo.gnn_inference?.anomaly_files ?? 0}
                path="captures/gnn_inference/"
                latest={storageInfo.gnn_inference?.latest_anomaly}
                color="red"
              />
              <StorageCard
                icon={<Network className="h-3.5 w-3.5" />}
                label="GNN Datasets"
                count={storageInfo.gnn_datasets?.dataset_count ?? 0}
                path="captures/gnn_datasets/"
                latest={storageInfo.gnn_datasets?.latest_dataset}
                color="orange"
              />
              <StorageCard
                icon={<Database className="h-3.5 w-3.5" />}
                label="Collector Inbox"
                count={storageInfo.collector_inbox?.pending_files ?? 0}
                path="captures/collector_inbox/"
                latest={null}
                color="gray"
              />
            </div>
            <div className="pt-2 border-t border-border/40 grid grid-cols-1 md:grid-cols-3 gap-2 text-[11px] font-mono text-muted-foreground">
              <div>
                <span className="text-muted-foreground">GNN model:</span>{" "}
                ml_training/gnn_model_complete.pt
              </div>
              <div>
                <span className="text-muted-foreground">Best model:</span>{" "}
                ml_training/best_model.pt
              </div>
              <div>
                <span className="text-muted-foreground">Backend models:</span>{" "}
                mininetDashboard/backend/models/
              </div>
            </div>
          </div>
        )}

        {/* ── Main Grid: Topology + Lab Controls ───────────────────── */}
        <div
          className="grid grid-cols-1 lg:grid-cols-4 gap-4 flex-1 min-h-0"
          style={{ height: 700 }}
        >
          {/* Topology Graph */}
          <div className="lg:col-span-3 bg-card border border-border shadow-sm rounded-2xl overflow-hidden">
            <TopologyGraph />
          </div>

          {/* Lab Control Panel */}
          <div className="flex flex-col gap-4 overflow-y-auto">
            <section className="bg-card border border-border shadow-sm rounded-2xl p-4">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-3">
                Lab Status
              </p>
              <div className="grid grid-cols-2 gap-2">
                <StatusBadge
                  label="Capture"
                  active={!!status?.capture_running}
                  activeText="Active"
                  inactiveText="Idle"
                  activeColor="text-foreground bg-green-500/10 border-green-500/30"
                />
                <StatusBadge
                  label="Traffic"
                  active={!!status?.traffic_running}
                  activeText="Running"
                  inactiveText="Idle"
                  activeColor="text-foreground bg-green-500/10 border-green-500/30"
                />
                <StatusBadge
                  label="Relay"
                  active={!!status?.last_relay}
                  activeText="Ready"
                  inactiveText="Not done"
                  activeColor="text-foreground bg-green-500/10 border-green-500/30"
                />
                <StatusBadge
                  label="Inference"
                  active={!!status?.last_inference}
                  activeText={
                    status?.last_inference?.inference?.severity?.toUpperCase?.() ??
                    "Done"
                  }
                  inactiveText="Not run"
                  activeColor="text-foreground bg-green-500/10 border-green-500/30"
                />
              </div>
              {status?.last_capture_id && (
                <p className="mt-3 text-[11px] font-mono text-muted-foreground">
                  Last ID:{" "}
                  <span className="text-foreground">
                    {status.last_capture_id}
                  </span>
                </p>
              )}
            </section>

            <PhaseCard
              phase="01"
              title="Packet Capture"
              accent="gray"
              description="Start and stop pcap collection across interfaces."
            >
              <div className="grid grid-cols-2 gap-2">
                <ActionButton
                  onClick={() =>
                    handleAction(
                      startCapture,
                      "start_capture",
                      "Capture started",
                      "Packet capture is now active.",
                    )
                  }
                  disabled={loading || status?.capture_running}
                  loading={isActive("start_capture")}
                  loadingLabel="Starting…"
                  icon={<Play className="w-3.5 h-3.5" />}
                  label="Start"
                  variant="solid"
                  color="gray"
                />
                <ActionButton
                  onClick={() =>
                    handleAction(
                      stopCapture,
                      "stop_capture",
                      "Capture stopped",
                      "Packet capture has been stopped.",
                    )
                  }
                  disabled={loading || !status?.capture_running}
                  loading={isActive("stop_capture")}
                  loadingLabel="Stopping…"
                  icon={<Square className="w-3.5 h-3.5" />}
                  label="Stop"
                  variant="ghost"
                  color="gray"
                />
              </div>
            </PhaseCard>

            <PhaseCard
              phase="02"
              title="Traffic Generation"
              accent="green"
              description="Inject synthetic network traffic for 90 seconds."
            >
              <div className="grid grid-cols-2 gap-2">
                <ActionButton
                  onClick={() =>
                    handleAction(
                      () => startTraffic(90),
                      "start_traffic",
                      "Traffic started",
                      "Synthetic traffic generation is running.",
                    )
                  }
                  disabled={loading}
                  loading={isActive("start_traffic")}
                  loadingLabel="Starting…"
                  icon={<Activity className="w-3.5 h-3.5" />}
                  label="Run"
                  variant="solid"
                  color="green"
                />
                <ActionButton
                  onClick={() =>
                    handleAction(
                      stopTraffic,
                      "stop_traffic",
                      "Traffic stopped",
                      "Synthetic traffic has been stopped.",
                    )
                  }
                  disabled={loading}
                  loading={isActive("stop_traffic")}
                  loadingLabel="Stopping…"
                  icon={<Square className="w-3.5 h-3.5" />}
                  label="Stop"
                  variant="ghost"
                  color="green"
                />
              </div>
            </PhaseCard>

            <PhaseCard
              phase="03"
              title="Relay Capture"
              accent="orange"
              description="Forward capture files to the collector inbox."
              blockedReason={
                !canRelay ? (relayBlockedReason ?? undefined) : undefined
              }
            >
              <ActionButton
                onClick={() =>
                  handleAction(
                    relayCapture,
                    "relay_capture",
                    "Capture relayed",
                    "Capture files relayed to collector inbox.",
                  )
                }
                disabled={!canRelay}
                loading={isActive("relay_capture")}
                loadingLabel="Relaying…"
                icon={<Send className="w-3.5 h-3.5" />}
                label="Relay Capture"
                variant="solid"
                color="orange"
                full
              />
              {status?.last_relay?.collector_inbox && (
                <p className="mt-2 text-[11px] font-mono text-muted-foreground truncate">
                  → {status.last_relay.collector_inbox}
                </p>
              )}
            </PhaseCard>

            <PhaseCard
              phase="04"
              title="AI Inference"
              accent="orange"
              description="Run the threat detection model on the latest capture."
              blockedReason={
                !canInfer ? (inferBlockedReason ?? undefined) : undefined
              }
            >
              <ActionButton
                onClick={() =>
                  handleAction(
                    runInference,
                    "run_inference",
                    "Inference complete",
                    "AI inference finished for the latest capture.",
                  )
                }
                disabled={!canInfer}
                loading={isActive("run_inference")}
                loadingLabel="Running…"
                icon={<Cpu className="w-3.5 h-3.5" />}
                label="Run Inference"
                variant="solid"
                color="orange"
                full
              />
              {status?.last_inference?.inference && (
                <div className="mt-2 grid grid-cols-3 gap-1 text-[11px] font-mono">
                  <InferenceStat
                    label="Severity"
                    value={status.last_inference.inference.severity}
                    color="text-foreground"
                  />
                  <InferenceStat
                    label="Risk"
                    value={status.last_inference.inference.risk_score}
                    color="text-foreground"
                  />
                  <InferenceStat
                    label="Flows"
                    value={`${status.last_inference.inference.suspicious_flows}/${status.last_inference.inference.total_flows}`}
                    color="text-muted-foreground"
                  />
                </div>
              )}
            </PhaseCard>

            {lastError && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2.5 text-xs font-mono text-red-600">
                <p className="text-red-600 text-[11px] uppercase tracking-wider mb-1">
                  Error
                </p>
                <p>{lastError}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatusBadge({
  label,
  active,
  activeText,
  inactiveText,
  activeColor,
}: {
  label: string;
  active: boolean;
  activeText: string;
  inactiveText: string;
  activeColor: string;
}) {
  return (
    <div className="flex flex-col gap-0.5 rounded-lg border border-border bg-muted px-2.5 py-2">
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span
        className={`text-xs font-medium rounded px-1.5 py-0.5 w-fit border ${active ? activeColor : "text-muted-foreground bg-transparent border-transparent"}`}
      >
        {active ? activeText : inactiveText}
      </span>
    </div>
  );
}

const accentMap: Record<string, string> = {
  gray: "border-l-gray-500",
  green: "border-l-green-500",
  orange: "border-l-orange-500",
};
const phaseTextMap: Record<string, string> = {
  gray: "text-muted-foreground",
  green: "text-green-500",
  orange: "text-orange-500",
};

function PhaseCard({
  phase,
  title,
  accent,
  description,
  children,
  blockedReason,
}: {
  phase: string;
  title: string;
  accent: string;
  description: string;
  children: React.ReactNode;
  blockedReason?: string;
}) {
  return (
    <section
      className={`border border-border border-l-2 ${accentMap[accent]} bg-card rounded-xl p-4 flex flex-col gap-3 shadow-sm`}
    >
      <div>
        <div className="flex items-center gap-2 mb-0.5">
          <span
            className={`text-[10px] font-bold font-mono ${phaseTextMap[accent]}`}
          >
            PHASE {phase}
          </span>
          <span className="text-[10px] text-muted-foreground">·</span>
          <span className="text-xs font-medium text-foreground">{title}</span>
        </div>
        <p className="text-[11px] text-muted-foreground leading-snug">{description}</p>
      </div>
      {children}
      {blockedReason && (
        <p className={`text-[11px] ${phaseTextMap[accent]} opacity-70`}>
          {blockedReason}
        </p>
      )}
    </section>
  );
}

function ActionButton({
  onClick,
  disabled,
  loading,
  loadingLabel,
  icon,
  label,
  variant,
  color,
  full,
}: {
  onClick: () => void;
  disabled: boolean;
  loading: boolean;
  loadingLabel: string;
  icon: React.ReactNode;
  label: string;
  variant: "solid" | "ghost";
  color: string;
  full?: boolean;
}) {
  const base =
    "flex items-center justify-center gap-1.5 px-3 py-2 rounded-md text-xs font-medium transition-colors disabled:cursor-not-allowed";
  const solid = "bg-foreground hover:bg-foreground/90 text-background disabled:opacity-40";
  const ghost =
    "border border-border text-muted-foreground hover:bg-muted disabled:opacity-40";
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`${base} ${variant === "solid" ? solid : ghost} ${full ? "w-full" : ""}`}
    >
      {icon}
      {loading ? loadingLabel : label}
    </button>
  );
}

function InferenceStat({
  label,
  value,
  color,
}: {
  label: string;
  value: any;
  color: string;
}) {
  return (
    <div className="flex flex-col items-center bg-muted rounded-md px-1.5 py-1.5 border border-border">
      <span className="text-[9px] uppercase tracking-wider text-muted-foreground mb-0.5">
        {label}
      </span>
      <span
        className={`text-[11px] font-semibold ${color} truncate max-w-full`}
      >
        {value}
      </span>
    </div>
  );
}

const storageColorMap: Record<string, string> = {
  gray: "text-muted-foreground border-border bg-muted",
  orange: "text-orange-600 border-orange-500/30 bg-orange-500/10",
  red: "text-red-600 border-red-500/30 bg-red-500/10",
};

function StorageCard({
  icon,
  label,
  count,
  path,
  latest,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  path: string;
  latest: string | null;
  color: string;
}) {
  return (
    <div
      className={`rounded-lg border p-3 space-y-1.5 ${storageColorMap[color]}`}
    >
      <div className="flex items-center gap-1.5">
        {icon}
        <span className="text-[11px] font-semibold">{label}</span>
        <span className="ml-auto text-lg font-bold">{count}</span>
      </div>
      <div className="text-[10px] text-muted-foreground font-mono truncate">{path}</div>
      {latest && (
        <div
          className="text-[10px] text-muted-foreground font-mono truncate"
          title={latest}
        >
          Latest: {latest}
        </div>
      )}
    </div>
  );
}
