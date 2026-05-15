"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { fadeIn } from "@/lib/motion";
import { ShimmerBlock } from "./shimmer-block";

interface TableSkeletonProps {
  rows?: number;
  columns?: number;
  className?: string;
}

export function TableSkeleton({
  rows = 6,
  columns = 6,
  className,
}: TableSkeletonProps) {
  return (
    <motion.div
      variants={fadeIn}
      initial="hidden"
      animate="visible"
      className={cn(
        "rounded-3xl border border-gray-200 bg-white p-5 shadow-sm md:p-6",
        className,
      )}
    >
      <ShimmerBlock className="mb-5 h-5 w-48" />
      <div className="space-y-3">
        <div
          className="grid gap-3"
          style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}
        >
          {Array.from({ length: columns }).map((_, i) => (
            <ShimmerBlock key={`h-${i}`} className="h-3 w-full" />
          ))}
        </div>
        {Array.from({ length: rows }).map((_, row) => (
          <div
            key={row}
            className="grid gap-3 border-t border-gray-100 pt-3"
            style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}
          >
            {Array.from({ length: columns }).map((_, col) => (
              <ShimmerBlock
                key={`${row}-${col}`}
                className={cn("h-4", col === 0 ? "w-3/4" : "w-full")}
              />
            ))}
          </div>
        ))}
      </div>
    </motion.div>
  );
}
