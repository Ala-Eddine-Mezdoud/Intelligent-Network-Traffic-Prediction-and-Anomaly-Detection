"use client";

import { motion, AnimatePresence } from "framer-motion";
import { TopoNode } from "@/lib/topology-data";
import { GRAPH_COLORS } from "./graph-constants";
import { springSoft } from "@/lib/motion";

interface TooltipProps {
  node: TopoNode | null;
  x: number;
  y: number;
}

const healthLabel = {
  healthy: "Healthy",
  warning: "Operational warning",
  critical: "Critical anomaly",
};

export function Tooltip({ node, x, y }: TooltipProps) {
  if (!node) return null;

  const health = node.health ?? "healthy";
  const healthColor = GRAPH_COLORS[health] ?? GRAPH_COLORS.neutral;

  return (
    <AnimatePresence>
    <motion.div
      key={node.id}
      initial={{ opacity: 0, y: 6, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 4, scale: 0.98 }}
      transition={springSoft}
      className="pointer-events-none fixed z-[100] min-w-[180px] rounded-2xl border border-gray-200 bg-white px-4 py-3 shadow-lg"
      style={{ left: x + 14, top: y + 14 }}
    >
      <div className="mb-2 flex items-center gap-2 border-b border-gray-100 pb-2">
        <span
          className="h-2 w-2 shrink-0 rounded-full"
          style={{ backgroundColor: healthColor }}
        />
        <span className="text-sm font-semibold text-gray-900">{node.id}</span>
      </div>
      <dl className="space-y-1.5 text-[11px]">
        <div className="flex justify-between gap-4">
          <dt className="text-gray-500">IP</dt>
          <dd className="font-mono text-gray-800">{node.ip || "—"}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-gray-500">Type</dt>
          <dd className="capitalize text-gray-800">{node.type}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-gray-500">Zone</dt>
          <dd className="capitalize text-gray-800">{node.zone.replace(/-/g, " ")}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-gray-500">Status</dt>
          <dd className="font-medium" style={{ color: healthColor }}>
            {healthLabel[health]}
          </dd>
        </div>
      </dl>
    </motion.div>
    </AnimatePresence>
  );
}
