"use client";

import { useState, useEffect } from "react";
import {
  getLabStatus, startCapture, stopCapture,
  startTraffic, stopTraffic, relayCapture, runInference
} from "@/lib/simulation-api";
import { Activity, Play, Square, Cpu, Send, Circle, Radio } from "lucide-react";
import { DashboardLayout } from "@/components/dashboard-layout";
import { useToast } from "@/hooks/use-toast";
import { TopologyGraph } from "@/components/topology-graph";

export default function SimulationPage() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const { toast } = useToast();

  const canRelay = !loading && !status?.capture_running && !!status?.last_capture_id;
  const canInfer = !loading && !!status?.last_relay;
  const relayBlockedReason = status?.capture_running
    ? "Stop capture before relay."
    : !status?.last_capture_id
    ? "Start and stop a capture first."
    : null;
  const inferBlockedReason = !status?.last_relay ? "Run Relay Capture first." : null;

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await getLabStatus();
        setStatus(data);
      } catch {
        console.error("Failed to connect to simulation backend");
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

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

  return (
    <DashboardLayout>
      {/* Tighter horizontal padding so the graph breathes */}
      <div className="flex flex-col h-full w-full gap-6 px-2 py-4">

        {/* ── Page Header ──────────────────────────────────────────────── */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Network Simulation Lab</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Control the Mininet SDN data plane and generate datasets natively.
            </p>
          </div>

          {/* Live pulse indicator */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground bg-zinc-900 border border-border rounded-full px-3 py-1.5">
            <span
              className={`w-2 h-2 rounded-full ${
                status?.capture_running ? "bg-green-400 animate-pulse" : "bg-zinc-600"
              }`}
            />
            {status?.capture_running ? "Live" : "Idle"}
          </div>
        </div>

        {/* ── Main Grid ────────────────────────────────────────────────── */}
        {/*
          4-column grid: topology spans 3 cols, control panel 1 col.
          Previously it was 3-col (2+1) — this gives the graph 50% more room.
        */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 flex-1 min-h-0" style={{ height: 700 }}>

          {/* Topology Graph — 3 / 4 columns */}
          <div className="lg:col-span-3 border border-border bg-card rounded-xl overflow-hidden shadow-sm">
            <TopologyGraph />
          </div>

          {/* Control Panel — 1 / 4 columns */}
          <div className="flex flex-col gap-4 overflow-y-auto">

            {/* ── Status Overview ────────────────────────────────────── */}
            <section className="border border-border bg-card rounded-xl p-4">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-3">
                Status
              </p>
              <div className="grid grid-cols-2 gap-2">
                <StatusBadge
                  label="Capture"
                  active={!!status?.capture_running}
                  activeText="Active"
                  inactiveText="Idle"
                  activeColor="text-green-400 bg-green-400/10 border-green-400/20"
                />
                <StatusBadge
                  label="Traffic"
                  active={!!status?.traffic_running}
                  activeText="Running"
                  inactiveText="Idle"
                  activeColor="text-blue-400 bg-blue-400/10 border-blue-400/20"
                />
                <StatusBadge
                  label="Relay"
                  active={!!status?.last_relay}
                  activeText="Ready"
                  inactiveText="Not done"
                  activeColor="text-amber-400 bg-amber-400/10 border-amber-400/20"
                />
                <StatusBadge
                  label="Inference"
                  active={!!status?.last_inference}
                  activeText={status?.last_inference?.inference?.severity?.toUpperCase?.() ?? "Done"}
                  inactiveText="Not run"
                  activeColor="text-purple-400 bg-purple-400/10 border-purple-400/20"
                />
              </div>
              {status?.last_capture_id && (
                <p className="mt-3 text-[11px] font-mono text-zinc-500">
                  Last ID:{" "}
                  <span className="text-zinc-300">{status.last_capture_id}</span>
                </p>
              )}
            </section>

            {/* ── Phase 1: Capture ───────────────────────────────────── */}
            <PhaseCard
              phase="01"
              title="Packet Capture"
              accent="blue"
              description="Start and stop pcap collection across interfaces."
            >
              <div className="grid grid-cols-2 gap-2">
                <ActionButton
                  onClick={() => handleAction(startCapture, "start_capture", "Capture started", "Packet capture is now active.")}
                  disabled={loading || status?.capture_running}
                  loading={isActive("start_capture")}
                  loadingLabel="Starting…"
                  icon={<Play className="w-3.5 h-3.5" />}
                  label="Start"
                  variant="solid"
                  color="blue"
                />
                <ActionButton
                  onClick={() => handleAction(stopCapture, "stop_capture", "Capture stopped", "Packet capture has been stopped.")}
                  disabled={loading || !status?.capture_running}
                  loading={isActive("stop_capture")}
                  loadingLabel="Stopping…"
                  icon={<Square className="w-3.5 h-3.5" />}
                  label="Stop"
                  variant="ghost"
                  color="blue"
                />
              </div>
            </PhaseCard>

            {/* ── Phase 2: Traffic ───────────────────────────────────── */}
            <PhaseCard
              phase="02"
              title="Traffic Generation"
              accent="emerald"
              description="Inject synthetic network traffic for 90 seconds."
            >
              <div className="grid grid-cols-2 gap-2">
                <ActionButton
                  onClick={() => handleAction(() => startTraffic(90), "start_traffic", "Traffic started", "Synthetic traffic generation is running.")}
                  disabled={loading}
                  loading={isActive("start_traffic")}
                  loadingLabel="Starting…"
                  icon={<Activity className="w-3.5 h-3.5" />}
                  label="Run"
                  variant="solid"
                  color="emerald"
                />
                <ActionButton
                  onClick={() => handleAction(stopTraffic, "stop_traffic", "Traffic stopped", "Synthetic traffic has been stopped.")}
                  disabled={loading}
                  loading={isActive("stop_traffic")}
                  loadingLabel="Stopping…"
                  icon={<Square className="w-3.5 h-3.5" />}
                  label="Stop"
                  variant="ghost"
                  color="emerald"
                />
              </div>
            </PhaseCard>

            {/* ── Phase 3: Relay ─────────────────────────────────────── */}
            <PhaseCard
              phase="03"
              title="Relay Capture"
              accent="amber"
              description="Forward capture files to the collector inbox."
              blockedReason={!canRelay ? relayBlockedReason ?? undefined : undefined}
            >
              <ActionButton
                onClick={() => handleAction(relayCapture, "relay_capture", "Capture relayed", "Capture files relayed to collector inbox.")}
                disabled={!canRelay}
                loading={isActive("relay_capture")}
                loadingLabel="Relaying…"
                icon={<Send className="w-3.5 h-3.5" />}
                label="Relay Capture"
                variant="solid"
                color="amber"
                full
              />
              {status?.last_relay?.collector_inbox && (
                <p className="mt-2 text-[11px] font-mono text-zinc-500 truncate">
                  → {status.last_relay.collector_inbox}
                </p>
              )}
            </PhaseCard>

            {/* ── Phase 4: Inference ─────────────────────────────────── */}
            <PhaseCard
              phase="04"
              title="AI Inference"
              accent="purple"
              description="Run the threat detection model on the latest capture."
              blockedReason={!canInfer ? inferBlockedReason ?? undefined : undefined}
            >
              <ActionButton
                onClick={() => handleAction(runInference, "run_inference", "Inference complete", "AI inference finished for the latest capture.")}
                disabled={!canInfer}
                loading={isActive("run_inference")}
                loadingLabel="Running…"
                icon={<Cpu className="w-3.5 h-3.5" />}
                label="Run Inference"
                variant="solid"
                color="purple"
                full
              />
              {status?.last_inference?.inference && (
                <div className="mt-2 grid grid-cols-3 gap-1 text-[11px] font-mono">
                  <InferenceStat
                    label="Severity"
                    value={status.last_inference.inference.severity}
                    color="text-purple-400"
                  />
                  <InferenceStat
                    label="Risk"
                    value={status.last_inference.inference.risk_score}
                    color="text-purple-300"
                  />
                  <InferenceStat
                    label="Flows"
                    value={`${status.last_inference.inference.suspicious_flows}/${status.last_inference.inference.total_flows}`}
                    color="text-zinc-400"
                  />
                </div>
              )}
            </PhaseCard>

            {/* ── Error Banner ───────────────────────────────────────── */}
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

// ─── Sub-components ──────────────────────────────────────────────────────────

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
    <div className="flex flex-col gap-0.5 rounded-lg border border-border bg-zinc-950 px-2.5 py-2">
      <span className="text-[10px] uppercase tracking-wider text-zinc-500">{label}</span>
      <span
        className={`text-xs font-medium rounded px-1.5 py-0.5 w-fit border ${
          active ? activeColor : "text-zinc-500 bg-transparent border-transparent"
        }`}
      >
        {active ? activeText : inactiveText}
      </span>
    </div>
  );
}

const accentMap: Record<string, string> = {
  blue:    "border-l-blue-500",
  emerald: "border-l-emerald-500",
  amber:   "border-l-amber-500",
  purple:  "border-l-purple-500",
};

const phaseTextMap: Record<string, string> = {
  blue:    "text-blue-400",
  emerald: "text-emerald-400",
  amber:   "text-amber-400",
  purple:  "text-purple-400",
};

function PhaseCard({
  phase, title, accent, description, children, blockedReason,
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
      className={`border border-border border-l-2 ${accentMap[accent]} bg-card rounded-xl p-4 flex flex-col gap-3`}
    >
      <div>
        <div className="flex items-center gap-2 mb-0.5">
          <span className={`text-[10px] font-bold font-mono ${phaseTextMap[accent]}`}>
            PHASE {phase}
          </span>
          <span className="text-[10px] text-zinc-600">·</span>
          <span className="text-xs font-medium text-zinc-200">{title}</span>
        </div>
        <p className="text-[11px] text-zinc-500 leading-snug">{description}</p>
      </div>
      {children}
      {blockedReason && (
        <p className={`text-[11px] ${phaseTextMap[accent]} opacity-70`}>{blockedReason}</p>
      )}
    </section>
  );
}

const btnSolidMap: Record<string, string> = {
  blue:    "bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/30",
  emerald: "bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/30",
  amber:   "bg-amber-600 hover:bg-amber-500 disabled:bg-amber-600/30",
  purple:  "bg-purple-600 hover:bg-purple-500 disabled:bg-purple-600/30",
};

function ActionButton({
  onClick, disabled, loading, loadingLabel, icon, label, variant, color, full,
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
    "flex items-center justify-center gap-1.5 px-3 py-2 rounded-md text-xs font-medium transition-colors disabled:cursor-not-allowed text-white";
  const solid = btnSolidMap[color] ?? "";
  const ghost = "border border-border hover:bg-zinc-800 disabled:opacity-40";

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

function InferenceStat({ label, value, color }: { label: string; value: any; color: string }) {
  return (
    <div className="flex flex-col items-center bg-zinc-950 rounded-md px-1.5 py-1.5 border border-border">
      <span className="text-[9px] uppercase tracking-wider text-zinc-600 mb-0.5">{label}</span>
      <span className={`text-[11px] font-semibold ${color} truncate max-w-full`}>{value}</span>
    </div>
  );
}
