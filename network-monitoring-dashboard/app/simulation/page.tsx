"use client";

import { useState, useEffect } from "react";
import {
  getLabStatus, startCapture, stopCapture,
  startTraffic, stopTraffic, relayCapture, runInference
} from "@/lib/simulation-api";
import {
  startRealtimePipeline, stopRealtimePipeline, getFullSimulationStatus,
  startNormalSimulation, stopNormalSimulation, injectAnomaly, getStorageInfo,
} from "@/lib/api";
import {
  Activity, Play, Square, Cpu, Send, Network, Clock,
  Zap, AlertTriangle, Wifi, Gauge, Droplets, Shield, Bug, Siren,
  Database, FolderOpen,
} from "lucide-react";
import { DashboardLayout } from "@/components/dashboard-layout";
import { useToast } from "@/hooks/use-toast";
import { TopologyGraph } from "@/components/topology-graph";

const ANOMALY_CONFIGS = [
  { type: "congestion",    label: "Congestion",    icon: Gauge,         color: "orange",  desc: "Rate-limit a node (4 Mbit)" },
  { type: "latency",       label: "Latency",        icon: Clock,         color: "yellow",  desc: "300 ms delay spike" },
  { type: "packet_loss",   label: "Packet Loss",    icon: Droplets,      color: "red",     desc: "8% random drops" },
  { type: "jitter",        label: "Jitter",         icon: Wifi,          color: "purple",  desc: "80 ms jitter on link" },
  { type: "brownout",      label: "Brownout",       icon: AlertTriangle, color: "amber",   desc: "Combined degradation" },
  { type: "ddos",          label: "DDoS",           icon: Zap,           color: "red",     desc: "50 Mbit UDP flood" },
  { type: "portscan",      label: "Port Scan",      icon: Bug,           color: "cyan",    desc: "Rapid port sweep" },
  { type: "brute_force",   label: "Brute Force",    icon: Shield,        color: "pink",    desc: "SSH connection burst" },
] as const;

type AnomalyType = typeof ANOMALY_CONFIGS[number]["type"];

const ANOMALY_NODES: Record<AnomalyType, string[]> = {
  congestion:   ["e1_pc1", "e2_pc1", "h2_nas", "e1_erp"],
  latency:      ["h1_pc", "e2_pc1", "dc_monitor", "h2_pc"],
  packet_loss:  ["dc_web", "dc_monitor", "h2_pc", "e1_pc2"],
  jitter:       ["h1_tv", "h2_cam", "h1_iot", "e2_pc2"],
  brownout:     ["dc_web", "dc_monitor", "h1_pc", "e2_crm"],
  ddos:         ["dc_web"],
  portscan:     ["dc_web", "dc_vpn"],
  brute_force:  ["dc_vpn"],
};

const colorMap: Record<string, string> = {
  orange: "border-orange-500/40 text-orange-400 hover:bg-orange-950/30",
  yellow: "border-yellow-500/40 text-yellow-400 hover:bg-yellow-950/30",
  red:    "border-red-500/40    text-red-400    hover:bg-red-950/30",
  purple: "border-purple-500/40 text-purple-400 hover:bg-purple-950/30",
  amber:  "border-amber-500/40  text-amber-400  hover:bg-amber-950/30",
  cyan:   "border-cyan-500/40   text-cyan-400   hover:bg-cyan-950/30",
  pink:   "border-pink-500/40   text-pink-400   hover:bg-pink-950/30",
};

const colorActiveMap: Record<string, string> = {
  orange: "bg-orange-900/40 border-orange-400 text-orange-300",
  yellow: "bg-yellow-900/40 border-yellow-400 text-yellow-300",
  red:    "bg-red-900/40    border-red-400    text-red-300",
  purple: "bg-purple-900/40 border-purple-400 text-purple-300",
  amber:  "bg-amber-900/40  border-amber-400  text-amber-300",
  cyan:   "bg-cyan-900/40   border-cyan-400   text-cyan-300",
  pink:   "bg-pink-900/40   border-pink-400   text-pink-300",
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
  const [selectedAnomaly, setSelectedAnomaly] = useState<AnomalyType | null>(null);
  const [selectedNode, setSelectedNode] = useState<string>("");
  const [duration, setDuration] = useState(30);
  const [injecting, setInjecting] = useState(false);
  const [lastInjected, setLastInjected] = useState<string | null>(null);

  const { toast } = useToast();

  const canRelay = !loading && !status?.capture_running && !!status?.last_capture_id;
  const canInfer = !loading && !!status?.last_relay;
  const relayBlockedReason = status?.capture_running
    ? "Stop capture before relay."
    : !status?.last_capture_id
    ? "Start and stop a capture first."
    : null;
  const inferBlockedReason = !status?.last_relay ? "Run Relay Capture first." : null;

  const isRealtimeRunning = simStatus?.pipeline?.running ?? false;
  const isNormalRunning   = simStatus?.normal?.running ?? false;
  const anySimRunning     = isRealtimeRunning || isNormalRunning;
  const gnnActive         = simStatus?.gnn?.status?.running ?? false;
  const predsMade         = simStatus?.gnn?.status?.predictions_made ?? 0;
  const windowState       = simStatus?.gnn?.predictions?.window_prediction?.state ?? null;
  const anomalyCount      = simStatus?.gnn?.predictions?.anomaly_count ?? 0;
  const nextAttack        = simStatus?.pipeline?.next_attack_profile;
  const nextAttackIn      = simStatus?.pipeline?.next_attack_in_seconds;
  const lastAttack        = simStatus?.pipeline?.last_attack;
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
      toast({ title: "Normal simulation started", description: "Steady background traffic + GNN inference running." });
    } catch (e: any) {
      toast({ title: "Failed to start", description: e?.message ?? "Unknown error", variant: "destructive" });
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
      toast({ title: "Failed to stop", description: e?.message ?? "Unknown error", variant: "destructive" });
    } finally {
      setSimLoading(false);
    }
  };

  const handleStartRealtime = async () => {
    setSimLoading(true);
    try {
      await startRealtimePipeline(30);
      toast({ title: "Full simulation started", description: "Traffic + attack injection + GNN inference." });
    } catch (e: any) {
      toast({ title: "Failed to start", description: e?.message ?? "Unknown error", variant: "destructive" });
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
      toast({ title: "Failed to stop", description: e?.message ?? "Unknown error", variant: "destructive" });
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
      const label = ANOMALY_CONFIGS.find(a => a.type === selectedAnomaly)?.label ?? selectedAnomaly;
      const target = node || "default";
      setLastInjected(`${label} on ${target} for ${duration}s`);
      toast({ title: `Injected: ${label}`, description: `Applied to ${target} for ${duration}s — watch GNN panel.` });
    } catch (e: any) {
      toast({ title: "Injection failed", description: e?.message ?? "No simulation running", variant: "destructive" });
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
      toast({ title: "Action failed", description: message, variant: "destructive" });
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
            <h1 className="text-2xl font-semibold tracking-tight">Network Simulation Lab</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Run steady-state or full simulation, then inject anomalies to test GNN detection.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground bg-zinc-900 border border-border rounded-full px-3 py-1.5">
            <span className={`w-2 h-2 rounded-full ${anySimRunning ? "bg-green-400 animate-pulse" : "bg-zinc-600"}`} />
            {anySimRunning ? (isNormalRunning ? "Normal Mode" : "Full Mode") : "Idle"}
          </div>
        </div>

        {/* ── GNN Status Bar ─────────────────────────────────────────── */}
        {gnnActive && (
          <div className="rounded-xl border border-cyan-500/20 bg-cyan-950/20 px-4 py-3 flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2 text-xs text-cyan-400">
              <Network className="h-4 w-4" />
              <span className="font-semibold">GNN Active</span>
              <span className="text-zinc-500">·</span>
              <span>{predsMade} predictions</span>
            </div>
            {windowState && (
              <div className={`flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border ${
                windowState === "NORMAL"
                  ? "border-green-500/30 text-green-400 bg-green-950/20"
                  : "border-red-500/30 text-red-400 bg-red-950/20 animate-pulse"
              }`}>
                {windowState !== "NORMAL" && <Siren className="h-3 w-3" />}
                {windowState}
                {anomalyCount > 0 && <span className="ml-1 text-orange-400">· {anomalyCount} nodes</span>}
              </div>
            )}
            {isRealtimeRunning && nextAttack && nextAttackIn != null && (
              <div className="flex items-center gap-1.5 text-xs text-amber-400 bg-amber-900/20 border border-amber-500/20 rounded-full px-2.5 py-0.5">
                <Clock className="h-3 w-3" />
                Next: {nextAttack} in {nextAttackIn}s
              </div>
            )}
            {lastAttack && (
              <span className="text-xs text-zinc-500">
                Last attack: <span className="text-zinc-300">{lastAttack.name}</span>
              </span>
            )}
            {activeOpAnomalies.length > 0 && (
              <div className="flex flex-wrap gap-1.5 items-center">
                <span className="text-[11px] text-zinc-500">Active:</span>
                {activeOpAnomalies.map((a: any, i: number) => (
                  <span key={i} className="text-[11px] bg-zinc-800 border border-border rounded-full px-2 py-0.5 text-zinc-300">
                    {a.node} · {a.profile} · {Math.max(0, Math.round((a.expires_at - Date.now() / 1000)))}s
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Simulation Mode Selector ──────────────────────────────── */}
        <div className="rounded-xl border border-border bg-card/70 p-4 space-y-3">
          <p className="text-xs font-bold uppercase tracking-widest text-zinc-400">Simulation Mode</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">

            {/* Normal Mode */}
            <div className={`rounded-lg border p-4 space-y-3 transition-colors ${isNormalRunning ? "border-green-500/40 bg-green-950/10" : "border-border"}`}>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${isNormalRunning ? "bg-green-400 animate-pulse" : "bg-zinc-600"}`} />
                <span className="text-sm font-semibold text-zinc-200">Normal Simulation</span>
                <span className={`ml-auto text-[11px] px-2 py-0.5 rounded-full border ${isNormalRunning ? "border-green-500/30 text-green-400 bg-green-950/20" : "border-border text-zinc-500"}`}>
                  {isNormalRunning ? "Running" : "Stopped"}
                </span>
              </div>
              <p className="text-[12px] text-zinc-400 leading-snug">
                Steady balanced traffic across all 26 nodes — matching GNN training conditions. No auto-attacks. Use the injection panel below to test anomaly detection.
              </p>
              <div className="flex gap-2">
                {isNormalRunning ? (
                  <button onClick={handleStopNormal} disabled={simLoading || isRealtimeRunning}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border border-red-500/50 text-red-400 hover:bg-red-950/30 transition-colors disabled:opacity-40">
                    <Square className="w-3 h-3 fill-current" />
                    {simLoading ? "Stopping…" : "Stop"}
                  </button>
                ) : (
                  <button onClick={handleStartNormal} disabled={simLoading || anySimRunning}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-green-700 hover:bg-green-600 text-white transition-colors disabled:opacity-40">
                    <Play className="w-3 h-3 fill-current" />
                    {simLoading ? "Starting…" : "Start Normal"}
                  </button>
                )}
              </div>
            </div>

            {/* Full Mode */}
            <div className={`rounded-lg border p-4 space-y-3 transition-colors ${isRealtimeRunning ? "border-cyan-500/40 bg-cyan-950/10" : "border-border"}`}>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${isRealtimeRunning ? "bg-cyan-400 animate-pulse" : "bg-zinc-600"}`} />
                <span className="text-sm font-semibold text-zinc-200">Full Simulation</span>
                <span className={`ml-auto text-[11px] px-2 py-0.5 rounded-full border ${isRealtimeRunning ? "border-cyan-500/30 text-cyan-400 bg-cyan-950/20" : "border-border text-zinc-500"}`}>
                  {isRealtimeRunning ? "Running" : "Stopped"}
                </span>
              </div>
              <p className="text-[12px] text-zinc-400 leading-snug">
                Full realtime pipeline with periodic attack injection (DDoS, PortScan, SSH-Patator…), pcap capture, and IDS inference every 30 s.
              </p>
              <div className="flex gap-2">
                {isRealtimeRunning ? (
                  <button onClick={handleStopRealtime} disabled={simLoading || isNormalRunning}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border border-red-500/50 text-red-400 hover:bg-red-950/30 transition-colors disabled:opacity-40">
                    <Square className="w-3 h-3 fill-current" />
                    {simLoading ? "Stopping…" : "Stop"}
                  </button>
                ) : (
                  <button onClick={handleStartRealtime} disabled={simLoading || anySimRunning}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-cyan-700 hover:bg-cyan-600 text-white transition-colors disabled:opacity-40">
                    <Play className="w-3 h-3 fill-current" />
                    {simLoading ? "Starting…" : "Start Full"}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* ── Manual Anomaly Injection ──────────────────────────────── */}
        <div className="rounded-xl border border-border bg-card/70 p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-orange-400">Manual Anomaly Injection</p>
              <p className="text-[12px] text-zinc-500 mt-0.5">Inject a specific anomaly and observe GNN detection in real time.</p>
            </div>
            {!anySimRunning && (
              <span className="text-[11px] text-amber-400 bg-amber-900/20 border border-amber-500/20 rounded-full px-2.5 py-0.5">
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
                  onClick={() => { setSelectedAnomaly(type); setSelectedNode(""); }}
                  className={`flex flex-col items-start gap-1 p-3 rounded-lg border text-left transition-all ${
                    isSelected ? colorActiveMap[color] : `bg-zinc-950 ${colorMap[color]}`
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span className="text-[12px] font-semibold leading-tight">{label}</span>
                  <span className="text-[10px] text-zinc-500 leading-tight">{desc}</span>
                </button>
              );
            })}
          </div>

          {/* Config Row */}
          {selectedAnomaly && (
            <div className="flex flex-wrap items-end gap-3 pt-2 border-t border-border/40">
              {/* Node selector */}
              <div className="flex flex-col gap-1">
                <label className="text-[11px] text-zinc-500 uppercase tracking-wider">Target Node</label>
                <select
                  value={selectedNode}
                  onChange={e => setSelectedNode(e.target.value)}
                  className="bg-zinc-900 border border-border rounded-md px-2.5 py-1.5 text-xs text-zinc-200 outline-none focus:border-zinc-500"
                >
                  <option value="">Auto (default)</option>
                  {availableNodes.map(n => (
                    <option key={n} value={n}>{n}</option>
                  ))}
                </select>
              </div>

              {/* Duration */}
              <div className="flex flex-col gap-1 min-w-32">
                <label className="text-[11px] text-zinc-500 uppercase tracking-wider">
                  Duration: <span className="text-zinc-300 font-semibold">{duration}s</span>
                </label>
                <input
                  type="range"
                  min={10} max={120} step={5}
                  value={duration}
                  onChange={e => setDuration(Number(e.target.value))}
                  className="w-full accent-orange-400"
                />
              </div>

              {/* Inject button */}
              <button
                onClick={handleInjectAnomaly}
                disabled={!anySimRunning || injecting}
                className="flex items-center gap-1.5 px-4 py-2 rounded-md text-xs font-semibold bg-orange-600 hover:bg-orange-500 text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Zap className="w-3.5 h-3.5" />
                {injecting ? "Injecting…" : `Inject ${ANOMALY_CONFIGS.find(a => a.type === selectedAnomaly)?.label}`}
              </button>

              {lastInjected && (
                <span className="text-[11px] text-orange-300 bg-orange-950/30 border border-orange-500/20 rounded-full px-2.5 py-1">
                  ✓ {lastInjected}
                </span>
              )}
            </div>
          )}
        </div>

        {/* ── Data & Results Storage ──────────────────────────────── */}
        {storageInfo && (
          <div className="rounded-xl border border-border bg-card/70 p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-zinc-400" />
              <p className="text-xs font-bold uppercase tracking-widest text-zinc-400">Data & Results Storage</p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <StorageCard
                icon={<FolderOpen className="h-3.5 w-3.5" />}
                label="PCAP Captures"
                count={storageInfo.captures?.pcap_files ?? 0}
                path="captures/"
                latest={storageInfo.captures?.latest_pcap}
                color="blue"
              />
              <StorageCard
                icon={<Cpu className="h-3.5 w-3.5" />}
                label="IDS Inference"
                count={storageInfo.intelligence_out?.inference_files ?? 0}
                path="captures/intelligence_out/"
                latest={storageInfo.intelligence_out?.latest_inference}
                color="purple"
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
                color="cyan"
              />
              <StorageCard
                icon={<Database className="h-3.5 w-3.5" />}
                label="Collector Inbox"
                count={storageInfo.collector_inbox?.pending_files ?? 0}
                path="captures/collector_inbox/"
                latest={null}
                color="amber"
              />
            </div>
            <div className="pt-2 border-t border-border/40 grid grid-cols-1 md:grid-cols-3 gap-2 text-[11px] font-mono text-zinc-500">
              <div><span className="text-zinc-400">GNN model:</span> ml_training/gnn_model_complete.pt</div>
              <div><span className="text-zinc-400">Best model:</span> ml_training/best_model.pt</div>
              <div><span className="text-zinc-400">Backend models:</span> mininetDashboard/backend/models/</div>
            </div>
          </div>
        )}

        {/* ── Main Grid: Topology + Lab Controls ───────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 flex-1 min-h-0" style={{ height: 700 }}>

          {/* Topology Graph */}
          <div className="lg:col-span-3 border border-border bg-card rounded-xl overflow-hidden shadow-sm">
            <TopologyGraph />
          </div>

          {/* Lab Control Panel */}
          <div className="flex flex-col gap-4 overflow-y-auto">

            <section className="border border-border bg-card rounded-xl p-4">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-3">
                Lab Status
              </p>
              <div className="grid grid-cols-2 gap-2">
                <StatusBadge label="Capture"   active={!!status?.capture_running}  activeText="Active"    inactiveText="Idle"     activeColor="text-green-400 bg-green-400/10 border-green-400/20" />
                <StatusBadge label="Traffic"   active={!!status?.traffic_running}   activeText="Running"   inactiveText="Idle"     activeColor="text-blue-400 bg-blue-400/10 border-blue-400/20" />
                <StatusBadge label="Relay"     active={!!status?.last_relay}        activeText="Ready"     inactiveText="Not done" activeColor="text-amber-400 bg-amber-400/10 border-amber-400/20" />
                <StatusBadge label="Inference" active={!!status?.last_inference}    activeText={status?.last_inference?.inference?.severity?.toUpperCase?.() ?? "Done"} inactiveText="Not run" activeColor="text-purple-400 bg-purple-400/10 border-purple-400/20" />
              </div>
              {status?.last_capture_id && (
                <p className="mt-3 text-[11px] font-mono text-zinc-500">
                  Last ID: <span className="text-zinc-300">{status.last_capture_id}</span>
                </p>
              )}
            </section>

            <PhaseCard phase="01" title="Packet Capture" accent="blue" description="Start and stop pcap collection across interfaces.">
              <div className="grid grid-cols-2 gap-2">
                <ActionButton onClick={() => handleAction(startCapture, "start_capture", "Capture started", "Packet capture is now active.")} disabled={loading || status?.capture_running} loading={isActive("start_capture")} loadingLabel="Starting…" icon={<Play className="w-3.5 h-3.5" />} label="Start" variant="solid" color="blue" />
                <ActionButton onClick={() => handleAction(stopCapture, "stop_capture", "Capture stopped", "Packet capture has been stopped.")} disabled={loading || !status?.capture_running} loading={isActive("stop_capture")} loadingLabel="Stopping…" icon={<Square className="w-3.5 h-3.5" />} label="Stop" variant="ghost" color="blue" />
              </div>
            </PhaseCard>

            <PhaseCard phase="02" title="Traffic Generation" accent="emerald" description="Inject synthetic network traffic for 90 seconds.">
              <div className="grid grid-cols-2 gap-2">
                <ActionButton onClick={() => handleAction(() => startTraffic(90), "start_traffic", "Traffic started", "Synthetic traffic generation is running.")} disabled={loading} loading={isActive("start_traffic")} loadingLabel="Starting…" icon={<Activity className="w-3.5 h-3.5" />} label="Run" variant="solid" color="emerald" />
                <ActionButton onClick={() => handleAction(stopTraffic, "stop_traffic", "Traffic stopped", "Synthetic traffic has been stopped.")} disabled={loading} loading={isActive("stop_traffic")} loadingLabel="Stopping…" icon={<Square className="w-3.5 h-3.5" />} label="Stop" variant="ghost" color="emerald" />
              </div>
            </PhaseCard>

            <PhaseCard phase="03" title="Relay Capture" accent="amber" description="Forward capture files to the collector inbox." blockedReason={!canRelay ? relayBlockedReason ?? undefined : undefined}>
              <ActionButton onClick={() => handleAction(relayCapture, "relay_capture", "Capture relayed", "Capture files relayed to collector inbox.")} disabled={!canRelay} loading={isActive("relay_capture")} loadingLabel="Relaying…" icon={<Send className="w-3.5 h-3.5" />} label="Relay Capture" variant="solid" color="amber" full />
              {status?.last_relay?.collector_inbox && (
                <p className="mt-2 text-[11px] font-mono text-zinc-500 truncate">→ {status.last_relay.collector_inbox}</p>
              )}
            </PhaseCard>

            <PhaseCard phase="04" title="AI Inference" accent="purple" description="Run the threat detection model on the latest capture." blockedReason={!canInfer ? inferBlockedReason ?? undefined : undefined}>
              <ActionButton onClick={() => handleAction(runInference, "run_inference", "Inference complete", "AI inference finished for the latest capture.")} disabled={!canInfer} loading={isActive("run_inference")} loadingLabel="Running…" icon={<Cpu className="w-3.5 h-3.5" />} label="Run Inference" variant="solid" color="purple" full />
              {status?.last_inference?.inference && (
                <div className="mt-2 grid grid-cols-3 gap-1 text-[11px] font-mono">
                  <InferenceStat label="Severity" value={status.last_inference.inference.severity} color="text-purple-400" />
                  <InferenceStat label="Risk" value={status.last_inference.inference.risk_score} color="text-purple-300" />
                  <InferenceStat label="Flows" value={`${status.last_inference.inference.suspicious_flows}/${status.last_inference.inference.total_flows}`} color="text-zinc-400" />
                </div>
              )}
            </PhaseCard>

            {lastError && (
              <div className="rounded-lg border border-red-500/30 bg-red-950/30 px-3 py-2.5 text-xs font-mono text-red-300">
                <p className="text-red-400 text-[11px] uppercase tracking-wider mb-1">Error</p>
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

function StatusBadge({ label, active, activeText, inactiveText, activeColor }: {
  label: string; active: boolean; activeText: string; inactiveText: string; activeColor: string;
}) {
  return (
    <div className="flex flex-col gap-0.5 rounded-lg border border-border bg-zinc-950 px-2.5 py-2">
      <span className="text-[10px] uppercase tracking-wider text-zinc-500">{label}</span>
      <span className={`text-xs font-medium rounded px-1.5 py-0.5 w-fit border ${active ? activeColor : "text-zinc-500 bg-transparent border-transparent"}`}>
        {active ? activeText : inactiveText}
      </span>
    </div>
  );
}

const accentMap: Record<string, string> = {
  blue: "border-l-blue-500", emerald: "border-l-emerald-500",
  amber: "border-l-amber-500", purple: "border-l-purple-500",
};
const phaseTextMap: Record<string, string> = {
  blue: "text-blue-400", emerald: "text-emerald-400",
  amber: "text-amber-400", purple: "text-purple-400",
};

function PhaseCard({ phase, title, accent, description, children, blockedReason }: {
  phase: string; title: string; accent: string; description: string;
  children: React.ReactNode; blockedReason?: string;
}) {
  return (
    <section className={`border border-border border-l-2 ${accentMap[accent]} bg-card rounded-xl p-4 flex flex-col gap-3`}>
      <div>
        <div className="flex items-center gap-2 mb-0.5">
          <span className={`text-[10px] font-bold font-mono ${phaseTextMap[accent]}`}>PHASE {phase}</span>
          <span className="text-[10px] text-zinc-600">·</span>
          <span className="text-xs font-medium text-zinc-200">{title}</span>
        </div>
        <p className="text-[11px] text-zinc-500 leading-snug">{description}</p>
      </div>
      {children}
      {blockedReason && <p className={`text-[11px] ${phaseTextMap[accent]} opacity-70`}>{blockedReason}</p>}
    </section>
  );
}

const btnSolidMap: Record<string, string> = {
  blue:    "bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/30",
  emerald: "bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/30",
  amber:   "bg-amber-600 hover:bg-amber-500 disabled:bg-amber-600/30",
  purple:  "bg-purple-600 hover:bg-purple-500 disabled:bg-purple-600/30",
};

function ActionButton({ onClick, disabled, loading, loadingLabel, icon, label, variant, color, full }: {
  onClick: () => void; disabled: boolean; loading: boolean; loadingLabel: string;
  icon: React.ReactNode; label: string; variant: "solid" | "ghost"; color: string; full?: boolean;
}) {
  const base = "flex items-center justify-center gap-1.5 px-3 py-2 rounded-md text-xs font-medium transition-colors disabled:cursor-not-allowed text-white";
  const solid = btnSolidMap[color] ?? "";
  const ghost = "border border-border hover:bg-zinc-800 disabled:opacity-40";
  return (
    <button onClick={onClick} disabled={disabled || loading}
      className={`${base} ${variant === "solid" ? solid : ghost} ${full ? "w-full" : ""}`}>
      {icon}
      {loading ? loadingLabel : label}
    </button>
  );
}

function InferenceStat({ label, value, color }: { label: string; value: any; color: string }) {
  return (
    <div className="flex flex-col items-center bg-zinc-950 rounded-md px-1.5 py-1.5 border border-border">
      <span className="text-[9px] uppercase tracking-wider text-zinc-600 mb-0.5">{label}</span>
      <span className={`text-[11px] font-semibold ${color} truncate max-w-full`}>{value}</span>
    </div>
  );
}

const storageColorMap: Record<string, string> = {
  blue:   "text-blue-400 border-blue-500/20 bg-blue-950/10",
  purple: "text-purple-400 border-purple-500/20 bg-purple-950/10",
  red:    "text-red-400 border-red-500/20 bg-red-950/10",
  cyan:   "text-cyan-400 border-cyan-500/20 bg-cyan-950/10",
  amber:  "text-amber-400 border-amber-500/20 bg-amber-950/10",
};

function StorageCard({ icon, label, count, path, latest, color }: {
  icon: React.ReactNode; label: string; count: number;
  path: string; latest: string | null; color: string;
}) {
  return (
    <div className={`rounded-lg border p-3 space-y-1.5 ${storageColorMap[color]}`}>
      <div className="flex items-center gap-1.5">
        {icon}
        <span className="text-[11px] font-semibold">{label}</span>
        <span className="ml-auto text-lg font-bold">{count}</span>
      </div>
      <div className="text-[10px] text-zinc-500 font-mono truncate">{path}</div>
      {latest && (
        <div className="text-[10px] text-zinc-600 font-mono truncate" title={latest}>
          Latest: {latest}
        </div>
      )}
    </div>
  );
}
