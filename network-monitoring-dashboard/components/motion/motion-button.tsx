"use client";

import { motion, type HTMLMotionProps } from "framer-motion";
import { springSnappy } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";
import type { VariantProps } from "class-variance-authority";

type MotionButtonProps = HTMLMotionProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    children: React.ReactNode;
  };

export function MotionButton({
  className,
  variant,
  size,
  children,
  ...props
}: MotionButtonProps) {
  return (
    <motion.button
      type="button"
      className={cn(buttonVariants({ variant, size, className }))}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      transition={springSnappy}
      {...props}
    >
      {children}
    </motion.button>
  );
}
