"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { fadeIn } from "@/lib/motion";
import { ShimmerBlock } from "./shimmer-block";

interface ChartSkeletonProps {
  height?: number;
  className?: string;
  title?: boolean;
}

export function ChartSkeleton({
  height = 380,
  className,
  title = true,
}: ChartSkeletonProps) {
  return (
    <motion.div
      variants={fadeIn}
      initial="hidden"
      animate="visible"
      className={cn(
        "flex flex-col rounded-3xl border border-border bg-card p-5 shadow-sm md:p-6",
        className,
      )}
    >
      {title && (
        <div className="mb-5 flex items-center justify-between">
          <ShimmerBlock className="h-5 w-40" />
          <ShimmerBlock className="h-6 w-24 rounded-full" />
        </div>
      )}
      <div className="flex flex-1 items-end gap-2" style={{ height }}>
        {Array.from({ length: 12 }).map((_, i) => (
          <ShimmerBlock
            key={i}
            className="flex-1 rounded-t-lg"
            style={{ height: `${30 + ((i * 17) % 55)}%` }}
          />
        ))}
      </div>
    </motion.div>
  );
}
