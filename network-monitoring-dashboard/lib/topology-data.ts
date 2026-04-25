// topology-data.ts
// Types and zone display metadata only.
// Node + link data is now fetched live from GET /api/topology — see simulation-api.ts.

export type NodeType =
  | "switch"
  | "router"
  | "dns"
  | "dhcp"
  | "iot"
  | "security"
  | "enterprise"
  | "home"
  | "server"
  | "controller";  // returned by the backend for the SDN controller node

export type NodeZone =
  | "enterprise-a"
  | "enterprise-b"
  | "home-a"
  | "home-b"
  | "datacenter"
  | "backbone"
  | "control-plane"; // returned by the backend for the SDN controller node

export interface TopoNode {
  id: string;
  type: NodeType;
  zone: NodeZone;
  ip?: string;
}

export interface TopoLink {
  source: string;
  target: string;
  /** "data" for forwarding links, "control" for SDN control-plane sessions */
  kind?: "data" | "control";
}

// ─── Zone display metadata ────────────────────────────────────────────────────

export const ZONE_META: Record<NodeZone, { label: string; color: string; dimColor: string }> = {
  "backbone":       { label: "ISP Backbone",   color: "#94a3b8", dimColor: "#334155" },
  "enterprise-a":   { label: "Enterprise A",   color: "#60a5fa", dimColor: "#1e3a5f" },
  "enterprise-b":   { label: "Enterprise B",   color: "#38bdf8", dimColor: "#0c4a6e" },
  "home-a":         { label: "Home A",          color: "#34d399", dimColor: "#064e3b" },
  "home-b":         { label: "Home B",          color: "#6ee7b7", dimColor: "#065f46" },
  "datacenter":     { label: "Datacenter",      color: "#f59e0b", dimColor: "#78350f" },
  "control-plane":  { label: "Control Plane",   color: "#c084fc", dimColor: "#4a1d96" },
};