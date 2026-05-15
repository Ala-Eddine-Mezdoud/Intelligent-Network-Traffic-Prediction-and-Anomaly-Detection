import { NodeZone, NodeType } from "@/lib/topology-data";

export const GRAPH_COLORS = {
  healthy: "#22c55e",
  warning: "#f97316",
  critical: "#ef4444",
  background: "#f9fafb",
  grid: "rgba(229, 231, 235, 0.8)",
  link: "rgba(156, 163, 175, 0.5)",
  particle: "#9ca3af",
  neutral: "#9ca3af",
};

export const ZONE_STYLES: Record<NodeZone, { color: string }> = {
  backbone: { color: "#6b7280" },
  "enterprise-a": { color: "#9ca3af" },
  "enterprise-b": { color: "#9ca3af" },
  "home-a": { color: "#d1d5db" },
  "home-b": { color: "#d1d5db" },
  datacenter: { color: "#6b7280" },
  "control-plane": { color: "#6b7280" },
};

export const NODE_CONFIG: Record<
  NodeType,
  { size: number; shape: "circle" | "diamond" | "square" | "hexagon"; glow: boolean }
> = {
  router: { size: 22, shape: "diamond", glow: false },
  switch: { size: 18, shape: "square", glow: false },
  controller: { size: 20, shape: "square", glow: false },
  server: { size: 20, shape: "circle", glow: true },
  enterprise: { size: 12, shape: "circle", glow: false },
  home: { size: 12, shape: "circle", glow: false },
  iot: { size: 10, shape: "circle", glow: false },
  security: { size: 14, shape: "circle", glow: false },
  dns: { size: 14, shape: "circle", glow: false },
  dhcp: { size: 14, shape: "circle", glow: false },
};
