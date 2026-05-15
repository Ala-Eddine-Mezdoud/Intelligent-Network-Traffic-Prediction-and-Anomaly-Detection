import type { Transition, Variants } from "framer-motion";

export const springSnappy = {
  type: "spring" as const,
  stiffness: 420,
  damping: 34,
  mass: 0.55,
};

export const springSoft = {
  type: "spring" as const,
  stiffness: 280,
  damping: 32,
  mass: 0.7,
};

export const springGentle = {
  type: "spring" as const,
  stiffness: 200,
  damping: 28,
  mass: 0.8,
};

export const easeOut: Transition = {
  duration: 0.35,
  ease: [0.22, 1, 0.36, 1],
};

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 10 },
  visible: (i: number = 0) => ({
    opacity: 1,
    y: 0,
    transition: { ...springSoft, delay: i * 0.04 },
  }),
};

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: easeOut },
};

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.98 },
  visible: { opacity: 1, scale: 1, transition: springSoft },
};

export const hoverLift = {
  y: -4,
  transition: springSnappy,
};

export const staggerContainer: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.05, delayChildren: 0.02 },
  },
};
