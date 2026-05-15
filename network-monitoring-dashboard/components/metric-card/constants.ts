import type { Transition } from "framer-motion";

export type MetricHealth = "healthy" | "warning" | "critical";

export const cardSpring = {
  type: "spring" as const,
  stiffness: 400,
  damping: 32,
  mass: 0.6,
};

export const hoverLift = {
  y: -6,
  scale: 1.008,
  transition: cardSpring,
};

export const valueSpring = {
  stiffness: 120,
  damping: 28,
  mass: 0.65,
};

export const fadeUp: Transition = {
  type: "spring",
  stiffness: 380,
  damping: 34,
};

export const healthAccent: Record<
  MetricHealth,
  { dot: string; border: string; text: string; icon: string }
> = {
  healthy: {
    dot: "bg-green-500",
    border: "border-l-green-500",
    text: "text-green-500",
    icon: "text-green-500",
  },
  warning: {
    dot: "bg-orange-500",
    border: "border-l-orange-500",
    text: "text-orange-500",
    icon: "text-orange-500",
  },
  critical: {
    dot: "bg-red-500",
    border: "border-l-red-500",
    text: "text-red-500",
    icon: "text-red-500",
  },
};

export const healthLabel: Record<MetricHealth, string> = {
  healthy: "Healthy",
  warning: "Warning",
  critical: "Critical",
};

export const sparkStroke: Record<MetricHealth, string> = {
  healthy: "#22c55e",
  warning: "#f97316",
  critical: "#ef4444",
};
