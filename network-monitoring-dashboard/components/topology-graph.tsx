"use client";

import { TopologyGraph as GraphCore } from "./topology/graph-core";

/**
 * TopologyGraph.tsx
 * 
 * Re-designed SOC/NOC Network Visualization.
 * Uses D3.js for physics and Framer Motion for premium UI interactions.
 * 
 * Refactored into modular components in /components/topology/
 */
export function TopologyGraph() {
  return <GraphCore />;
}
