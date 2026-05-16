"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { fadeIn } from "@/lib/motion";
import { ShimmerBlock } from "./shimmer-block";

export function TopologySkeleton({ className }: { className?: string }) {
  return (
    <motion.div
      variants={fadeIn}
      initial="hidden"
      animate="visible"
      className={cn(
        "relative h-full min-h-[480px] w-full overflow-hidden rounded-3xl border border-border bg-muted",
        className,
      )}
    >
      <div
        className="absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            "linear-gradient(#e5e7eb 1px, transparent 1px), linear-gradient(90deg, #e5e7eb 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />
      <div className="absolute left-4 top-4 flex flex-col gap-2">
        <ShimmerBlock className="h-10 w-64 rounded-xl" />
        <div className="flex gap-2">
          <ShimmerBlock className="h-10 w-10 rounded-xl" />
          <ShimmerBlock className="h-10 w-10 rounded-xl" />
        </div>
      </div>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="relative h-64 w-80">
          <ShimmerBlock className="absolute left-1/2 top-0 h-12 w-12 -translate-x-1/2 rounded-full" />
          <ShimmerBlock className="absolute bottom-0 left-0 h-10 w-10 rounded-lg" />
          <ShimmerBlock className="absolute bottom-0 right-0 h-10 w-10 rounded-lg" />
          <ShimmerBlock className="absolute left-1/2 top-1/2 h-14 w-14 -translate-x-1/2 -translate-y-1/2 rounded-xl" />
          <ShimmerBlock className="absolute left-0 top-1/3 h-8 w-8 rounded-full" />
          <ShimmerBlock className="absolute right-0 top-1/3 h-8 w-8 rounded-full" />
        </div>
      </div>
      <div className="absolute bottom-4 left-4 rounded-xl border border-border bg-card p-3 shadow-sm">
        <div className="flex gap-4">
          <ShimmerBlock className="h-3 w-16" />
          <ShimmerBlock className="h-3 w-16" />
          <ShimmerBlock className="h-3 w-16" />
        </div>
      </div>
    </motion.div>
  );
}
