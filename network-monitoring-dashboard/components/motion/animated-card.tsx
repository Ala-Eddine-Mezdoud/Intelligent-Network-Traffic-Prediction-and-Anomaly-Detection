"use client";

import { motion, type HTMLMotionProps } from "framer-motion";
import { hoverLift, springSoft } from "@/lib/motion";
import { cn } from "@/lib/utils";

interface AnimatedCardProps extends HTMLMotionProps<"motion.div"> {
  children: React.ReactNode;
  liftOnHover?: boolean;
  delay?: number;
}

export function AnimatedCard({
  children,
  className,
  liftOnHover = true,
  delay = 0,
  ...props
}: AnimatedCardProps) {
  return (
    <motion.div
      className={cn(
        "rounded-2xl border border-gray-200 bg-white shadow-sm",
        "transition-[box-shadow,border-color] duration-500 ease-out",
        liftOnHover && "hover:border-gray-200 hover:shadow-md",
        className,
      )}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ ...springSoft, delay }}
      whileHover={liftOnHover ? hoverLift : undefined}
      {...props}
    >
      {children}
    </motion.div>
  );
}
