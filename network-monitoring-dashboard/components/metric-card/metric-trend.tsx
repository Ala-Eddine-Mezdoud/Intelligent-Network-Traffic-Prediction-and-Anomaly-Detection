"use client";

import { motion } from "framer-motion";
import { ArrowDown, ArrowRight, ArrowUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { fadeUp, healthAccent, type MetricHealth } from "./constants";

type Trend = "up" | "down" | "stable";

interface MetricTrendProps {
  trend: Trend;
  trendValue?: string;
  health?: MetricHealth;
  isLive?: boolean;
}

const trendIcon = {
  up: ArrowUp,
  down: ArrowDown,
  stable: ArrowRight,
};

const trendColor: Record<Trend, string> = {
  up: healthAccent.healthy.text,
  down: healthAccent.critical.text,
  stable: "text-muted-foreground",
};

export function MetricTrend({
  trend,
  trendValue,
  health,
  isLive,
}: MetricTrendProps) {
  if (!trendValue) return null;

  const Icon = trendIcon[trend];
  const color =
    trend === "up" && health === "critical"
      ? healthAccent.critical.text
      : trend === "down" && health === "healthy"
        ? healthAccent.healthy.text
        : trendColor[trend];

  return (
    <motion.div
      className="flex items-center gap-2 text-xs text-muted-foreground"
      initial={{ opacity: 0, x: -4 }}
      animate={{ opacity: 1, x: 0 }}
      transition={fadeUp}
    >
      <motion.span
        className={cn(
          "inline-flex items-center justify-center rounded-md bg-muted p-1",
          color,
        )}
        animate={
          isLive && trend !== "stable"
            ? { y: [0, -2, 0] }
            : { y: 0 }
        }
        transition={
          isLive
            ? { duration: 2, repeat: Infinity, ease: "easeInOut" }
            : undefined
        }
        whileHover={{ scale: 1.12 }}
      >
        <Icon className="h-3.5 w-3.5" strokeWidth={2.5} />
      </motion.span>
      <span className="leading-snug">{trendValue}</span>
    </motion.div>
  );
}
