"use client";

import { motion } from "framer-motion";
import { TopoNode } from "@/lib/topology-data";
import { NODE_CONFIG, GRAPH_COLORS } from "./graph-constants";

interface NodeRendererProps {
  node: TopoNode & { x?: number; y?: number };
  isFocused?: boolean;
  isHovered?: boolean;
  isDimmed?: boolean;
}

export function NodeRenderer({
  node,
  isFocused,
  isHovered,
  isDimmed,
}: NodeRendererProps) {
  const config = NODE_CONFIG[node.type] || NODE_CONFIG.enterprise;
  const health = node.health ?? "healthy";
  const healthColor =
    health === "critical"
      ? GRAPH_COLORS.critical
      : health === "warning"
        ? GRAPH_COLORS.warning
        : health === "healthy"
          ? GRAPH_COLORS.healthy
          : GRAPH_COLORS.neutral;

  const isAnomaly = health === "critical" || health === "warning";
  const scale = isHovered || isFocused ? 1.12 : 1;

  const renderShape = () => {
    const s = config.size;
    switch (config.shape) {
      case "diamond":
        return (
          <polygon
            points={`0,-${s} ${s},0 0,${s} -${s},0`}
            fill="#ffffff"
            stroke={healthColor}
            strokeWidth={isFocused ? 2 : 1.5}
          />
        );
      case "hexagon":
        return (
          <polygon
            points={`0,-${s} ${s * 0.86},-${s * 0.5} ${s * 0.86},${s * 0.5} 0,${s} -${s * 0.86},${s * 0.5} -${s * 0.86},-${s * 0.5}`}
            fill="#ffffff"
            stroke={healthColor}
            strokeWidth={isFocused ? 2 : 1.5}
          />
        );
      case "square":
        return (
          <rect
            x={-s}
            y={-s}
            width={s * 2}
            height={s * 2}
            rx={4}
            fill="#ffffff"
            stroke={healthColor}
            strokeWidth={isFocused ? 2 : 1.5}
          />
        );
      case "circle":
      default:
        return (
          <circle
            r={node.type === "server" ? s * 1.1 : s}
            fill="#ffffff"
            stroke={healthColor}
            strokeWidth={isFocused ? 2 : 1.5}
          />
        );
    }
  };

  return (
    <motion.g
      initial={false}
      animate={{ scale, opacity: isDimmed ? 0.22 : 1 }}
      transition={{ type: "spring", stiffness: 280, damping: 28 }}
      className="cursor-pointer"
    >
      {isAnomaly && (
        <motion.circle
          r={config.size + 6}
          fill="none"
          stroke={healthColor}
          strokeWidth={1}
          opacity={0.35}
          animate={{ scale: [1, 1.15, 1], opacity: [0.2, 0.45, 0.2] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
        />
      )}
      {(isFocused || isHovered) && (
        <circle
          r={config.size + 4}
          fill="none"
          stroke={healthColor}
          strokeWidth={1}
          opacity={0.25}
        />
      )}
      {renderShape()}
      <circle r={2} cy={0} fill={healthColor} />
      {(isHovered || isFocused) && (
        <text
          y={config.size + 14}
          textAnchor="middle"
          fill="#374151"
          className="pointer-events-none text-[10px] font-medium"
        >
          {node.id}
        </text>
      )}
    </motion.g>
  );
}
