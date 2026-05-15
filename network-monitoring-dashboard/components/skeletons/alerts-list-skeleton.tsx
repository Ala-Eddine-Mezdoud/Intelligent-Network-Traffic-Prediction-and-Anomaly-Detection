"use client";

import { motion } from "framer-motion";
import { staggerContainer, fadeUp } from "@/lib/motion";
import { ShimmerBlock } from "./shimmer-block";

interface AlertsListSkeletonProps {
  count?: number;
}

export function AlertsListSkeleton({ count = 4 }: AlertsListSkeletonProps) {
  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      animate="visible"
      className="space-y-3"
    >
      {Array.from({ length: count }).map((_, i) => (
        <motion.div
          key={i}
          variants={fadeUp}
          custom={i}
          className="rounded-3xl border border-gray-200 bg-white p-5 shadow-sm md:p-6"
        >
          <div className="flex items-start gap-4">
            <ShimmerBlock className="h-6 w-16 rounded-full" />
            <div className="flex-1 space-y-3">
              <ShimmerBlock className="h-5 w-2/3 max-w-sm" />
              <ShimmerBlock className="h-4 w-full" />
              <ShimmerBlock className="h-3 w-24" />
            </div>
          </div>
        </motion.div>
      ))}
    </motion.div>
  );
}
