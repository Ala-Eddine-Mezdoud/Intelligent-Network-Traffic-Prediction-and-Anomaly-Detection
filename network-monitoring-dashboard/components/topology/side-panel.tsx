"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, Shield, Activity, Clock } from "lucide-react";
import { TopoNode } from "@/lib/topology-data";
import { GRAPH_COLORS } from "./graph-constants";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { primaryButton } from "@/lib/ui-theme";
import { cn } from "@/lib/utils";
import { springSoft } from "@/lib/motion";

interface SidePanelProps {
  node: TopoNode | null;
  onClose: () => void;
}

export function SidePanel({ node, onClose }: SidePanelProps) {
  const healthColor = node?.health
    ? GRAPH_COLORS[node.health]
    : GRAPH_COLORS.neutral;

  return (
    <AnimatePresence mode="wait">
      {node && (
        <motion.aside
          key={node.id}
          initial={{ x: "100%", opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: "100%", opacity: 0 }}
          transition={springSoft}
          className="absolute bottom-4 right-4 top-4 z-50 flex w-80 flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-lg"
        >
          <div className="relative border-b border-gray-200 p-5">
            <motion.button
              type="button"
              onClick={onClose}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="absolute right-4 top-4 rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-900"
            >
              <X className="h-4 w-4" />
            </motion.button>

            <div className="mb-4 flex items-center gap-3 pr-8">
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="rounded-xl border border-gray-200 bg-gray-50 p-3"
                style={{ color: healthColor }}
              >
                <Shield className="h-6 w-6" />
              </motion.div>
              <motion.div
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.05 }}
              >
                <h3 className="text-lg font-semibold text-gray-900">{node.id}</h3>
                <p className="font-mono text-xs text-gray-500">
                  {node.ip || "No IP assigned"}
                </p>
              </motion.div>
            </div>

            <motion.div
              className="flex gap-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.08 }}
            >
              <Badge variant="outline" className="border-gray-200 text-gray-600">
                {node.type}
              </Badge>
              <Badge
                variant="outline"
                style={{ borderColor: `${healthColor}40`, color: healthColor }}
              >
                {node.health || "neutral"}
              </Badge>
            </motion.div>
          </div>

          <div className="flex-1 space-y-6 overflow-y-auto p-5">
            <div className="grid grid-cols-2 gap-3">
              <MetricSmall label="Load" value="12%" icon={Activity} />
              <MetricSmall label="Latency" value="2.4ms" icon={Clock} />
            </div>

            <section className="space-y-2">
              <h4 className="text-[10px] font-semibold uppercase tracking-widest text-gray-500">
                Network zone
              </h4>
              <div className="flex items-center justify-between rounded-xl border border-gray-200 bg-gray-50 p-4">
                <span className="text-sm capitalize text-gray-700">
                  {node.zone.replace(/-/g, " ")}
                </span>
                <span
                  className="h-2 w-2 rounded-full live-pulse"
                  style={{ backgroundColor: healthColor }}
                />
              </div>
            </section>

            <section className="space-y-3">
              <h4 className="text-[10px] font-semibold uppercase tracking-widest text-gray-500">
                Recent events
              </h4>
              <EventItem time="14:22" msg="Connection established" type="neutral" />
              <EventItem time="12:05" msg="Traffic spike detected" type="warning" />
            </section>
          </div>

          <div className="border-t border-gray-200 p-4">
            <Button className={cn("w-full", primaryButton)}>Node analysis</Button>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}

function MetricSmall({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: typeof Activity;
}) {
  return (
    <motion.div
      whileHover={{ y: -2 }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      className="rounded-xl border border-gray-200 bg-gray-50 p-3"
    >
      <motion.div className="mb-1 flex items-center gap-2">
        <Icon className="h-3 w-3 text-gray-400" />
        <span className="text-[9px] font-semibold uppercase tracking-wider text-gray-500">
          {label}
        </span>
      </motion.div>
      <p className="text-sm font-semibold text-gray-900">{value}</p>
    </motion.div>
  );
}

function EventItem({
  time,
  msg,
  type,
}: {
  time: string;
  msg: string;
  type: "warning" | "neutral";
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-center gap-3 text-[11px]"
    >
      <span className="font-mono text-gray-400">{time}</span>
      <span
        className={`h-1.5 w-1.5 rounded-full ${type === "warning" ? "bg-orange-500" : "bg-gray-300"}`}
      />
      <span className="text-gray-600">{msg}</span>
    </motion.div>
  );
}
