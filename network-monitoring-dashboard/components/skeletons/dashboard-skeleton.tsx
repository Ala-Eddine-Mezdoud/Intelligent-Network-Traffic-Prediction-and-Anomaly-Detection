"use client";

import { motion } from "framer-motion";
import { fadeIn } from "@/lib/motion";
import { MetricCardSkeletonGrid } from "@/components/metric-card";
import { ChartSkeleton } from "./chart-skeleton";
import { ShimmerBlock } from "./shimmer-block";

export function DashboardPageSkeleton() {
  return (
    <motion.div variants={fadeIn} initial="hidden" animate="visible" className="space-y-4">
      <ShimmerBlock className="h-20 w-full rounded-2xl" />
      <MetricCardSkeletonGrid count={4} showSparkline />
      <ChartSkeleton height={380} />
      <motion.div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartSkeleton height={280} />
        <ChartSkeleton height={280} />
      </motion.div>
    </motion.div>
  );
}
