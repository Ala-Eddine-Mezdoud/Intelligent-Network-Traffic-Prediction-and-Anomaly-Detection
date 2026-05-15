"use client";

import { useEffect, useMemo, useRef } from "react";
import { motion, useMotionValueEvent, useSpring } from "framer-motion";
import { cn } from "@/lib/utils";
import { valueSpring } from "./constants";

interface ParsedValue {
  numeric: number;
  decimals: number;
  prefix: string;
  suffix: string;
}

function parseValue(value: string | number): ParsedValue | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    const decimals = Number.isInteger(value) ? 0 : 2;
    return { numeric: value, decimals, prefix: "", suffix: "" };
  }

  const raw = String(value).trim();
  const match = raw.match(/^([^\d.-]*)([-+]?[\d,]*\.?\d+)(.*)$/);
  if (!match) return null;

  const numeric = Number.parseFloat(match[2].replace(/,/g, ""));
  if (!Number.isFinite(numeric)) return null;

  const fraction = match[2].includes(".") ? (match[2].split(".")[1]?.length ?? 1) : 0;

  return {
    numeric,
    decimals: fraction,
    prefix: match[1],
    suffix: match[3],
  };
}

function formatParsed(parsed: ParsedValue, n: number) {
  const rounded =
    parsed.decimals > 0 ? n.toFixed(parsed.decimals) : String(Math.round(n));
  return `${parsed.prefix}${rounded}${parsed.suffix}`;
}

interface AnimatedMetricValueProps {
  value: string | number;
  className?: string;
  onPulse?: () => void;
}

export function AnimatedMetricValue({
  value,
  className,
  onPulse,
}: AnimatedMetricValueProps) {
  const parsed = useMemo(() => parseValue(value), [value]);
  const spring = useSpring(parsed?.numeric ?? 0, valueSpring);
  const displayRef = useRef<HTMLSpanElement>(null);
  const prevNumeric = useRef(parsed?.numeric);

  useEffect(() => {
    if (!parsed) return;
    spring.set(parsed.numeric);
    if (
      prevNumeric.current !== undefined &&
      prevNumeric.current !== parsed.numeric
    ) {
      onPulse?.();
    }
    prevNumeric.current = parsed.numeric;
  }, [parsed, spring, onPulse]);

  useMotionValueEvent(spring, "change", (latest) => {
    if (!displayRef.current || !parsed) return;
    displayRef.current.textContent = formatParsed(parsed, latest);
  });

  if (!parsed) {
    return (
      <motion.span
        key={String(value)}
        className={cn("tabular-nums", className)}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 400, damping: 35 }}
      >
        {value}
      </motion.span>
    );
  }

  return (
    <span ref={displayRef} className={cn("tabular-nums tracking-tight", className)}>
      {formatParsed(parsed, parsed.numeric)}
    </span>
  );
}
