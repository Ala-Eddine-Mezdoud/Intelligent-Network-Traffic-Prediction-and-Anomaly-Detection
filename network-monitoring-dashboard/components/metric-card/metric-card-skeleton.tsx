"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { fadeUp } from "./constants";

function Shimmer({ className }: { className?: string }) {
  return (
    <motion.div
      className={cn("metric-shimmer rounded-lg bg-gray-100", className)}
      initial={{ opacity: 0.5 }}
      animate={{ opacity: [0.5, 0.85, 0.5] }}
      transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
    />
  );
}

interface MetricCardSkeletonProps {
  className?: string;
  showSparkline?: boolean;
}

export function MetricCardSkeleton({
  className,
  showSparkline = false,
}: MetricCardSkeletonProps) {
  return (
    <motion.div
      className={cn(
        "flex h-full min-h-[168px] flex-col rounded-3xl border border-gray-200 bg-white p-6 shadow-sm",
        className,
      )}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={fadeUp}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-2.5">
          <Shimmer className="h-3 w-24" />
          <Shimmer className="h-2.5 w-32" />
        </div>
        <Shimmer className="h-11 w-11 shrink-0 rounded-2xl" />
      </div>
      <div className="mt-8 space-y-3">
        <Shimmer className="h-10 w-28" />
        <Shimmer className="h-3 w-20" />
      </div>
      {showSparkline && (
        <div className="mt-5">
          <Shimmer className="h-16 w-full rounded-2xl" />
        </div>
      )}
    </motion.div>
  );
}

export function MetricCardSkeletonGrid({
  count = 4,
  showSparkline = false,
  className,
}: {
  count?: number;
  showSparkline?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "grid grid-cols-1 gap-4 sm:gap-6 md:grid-cols-2 lg:grid-cols-4",
        className,
      )}
    >
      {Array.from({ length: count }).map((_, i) => (
        <MetricCardSkeleton key={i} showSparkline={showSparkline && i === 0} />
      ))}
    </div>
  );
}
