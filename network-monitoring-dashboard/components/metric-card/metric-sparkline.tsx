"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import type { MetricHealth } from "./constants";
import { sparkStroke } from "./constants";

interface MetricSparklineProps {
  data: number[];
  health: MetricHealth;
}

export function MetricSparkline({ data, health }: MetricSparklineProps) {
  const { path, last } = useMemo(() => {
    if (!data || data.length < 2) return { path: "", last: 0 };
    const min = Math.min(...data);
    const max = Math.max(...data);
    const width = 140;
    const height = 36;
    const points = data.map((value, index) => {
      const x = (index / (data.length - 1)) * width;
      const normalized = max === min ? 0.5 : (value - min) / (max - min);
      const y = height - normalized * height;
      return `${x},${y}`;
    });
    return {
      path: points.join(" "),
      last: data[data.length - 1],
    };
  }, [data]);

  if (!path) return null;

  const stroke = sparkStroke[health];

  return (
    <motion.div
      className="rounded-2xl border border-border bg-muted/80 p-3.5"
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: "spring", stiffness: 350, damping: 30 }}
    >
      <svg viewBox="0 0 140 36" className="h-9 w-full overflow-visible">
        <motion.polyline
          fill="none"
          stroke={stroke}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          points={path}
          initial={{ opacity: 0.3 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        />
      </svg>
      <motion.div
        className="mt-2.5 flex items-center justify-between text-[11px] text-muted-foreground"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        <span>Last 24h</span>
        <motion.span
          key={last}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="font-medium tabular-nums text-foreground"
        >
          {last}
        </motion.span>
      </motion.div>
    </motion.div>
  );
}
