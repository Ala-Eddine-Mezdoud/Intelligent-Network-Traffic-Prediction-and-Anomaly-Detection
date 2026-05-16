"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface ShimmerBlockProps {
  className?: string;
  style?: React.CSSProperties;
}

export function ShimmerBlock({ className, style }: ShimmerBlockProps) {
  return (
    <motion.div
      style={style}
      className={cn("metric-shimmer rounded-xl bg-muted", className)}
      initial={{ opacity: 0.55 }}
      animate={{ opacity: [0.55, 0.9, 0.55] }}
      transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
    />
  );
}
