"use client";

import Link from "next/link";
import {
  cloneElement,
  isValidElement,
  useEffect,
  useState,
  type ReactElement,
  type ReactNode,
} from "react";
import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { AnimatedMetricValue } from "./animated-metric-value";
import {
  cardSpring,
  fadeUp,
  healthAccent,
  healthLabel,
  hoverLift,
  type MetricHealth,
} from "./constants";
import { MetricCardSkeleton } from "./metric-card-skeleton";
import { MetricSparkline } from "./metric-sparkline";
import { MetricTrend } from "./metric-trend";

export interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon?: ReactNode;
  trend?: "up" | "down" | "stable";
  trendValue?: string;
  description?: string;
  health?: MetricHealth;
  variant?: "traffic" | "connections" | "anomaly" | "alerts";
  sparklineData?: number[];
  detailHref?: string;
  isLoading?: boolean;
  isLive?: boolean;
  className?: string;
  index?: number;
}

function StatusDot({ health }: { health: MetricHealth }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-gray-500">
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          healthAccent[health].dot,
          health === "healthy" && "shadow-[0_0_0_3px_rgba(34,197,94,0.15)]",
        )}
      />
      {healthLabel[health]}
    </span>
  );
}

function MetricIcon({
  icon,
  health,
}: {
  icon: ReactNode;
  health: MetricHealth;
}) {
  const accent = healthAccent[health];

  const enhanced =
    isValidElement(icon) && typeof icon !== "string"
      ? cloneElement(icon as ReactElement<{ className?: string }>, {
          className: cn(
            "h-5 w-5 transition-transform duration-300",
            accent.icon,
            (icon as ReactElement<{ className?: string }>).props.className,
          ),
        })
      : icon;

  return (
    <motion.div
      className={cn(
        "flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-gray-100 bg-gray-50",
        "transition-colors duration-300 group-hover:border-gray-200 group-hover:bg-white",
      )}
      whileHover={{ scale: 1.06, rotate: 2 }}
      transition={cardSpring}
    >
      {enhanced}
    </motion.div>
  );
}

function MetricCardInner({
  title,
  value,
  unit,
  icon,
  trend,
  trendValue,
  description,
  health = "healthy",
  sparklineData,
  detailHref,
  isLive = true,
  className,
  index = 0,
}: MetricCardProps) {
  const [pulse, setPulse] = useState(false);
  const accent = healthAccent[health];

  useEffect(() => {
    if (!pulse) return;
    const timer = window.setTimeout(() => setPulse(false), 550);
    return () => window.clearTimeout(timer);
  }, [pulse]);

  const body = (
    <motion.article
      className={cn(
        "group relative flex h-full min-h-[168px] flex-col overflow-hidden rounded-3xl border border-gray-200/80 bg-white p-6 shadow-sm",
        "transition-[box-shadow,border-color] duration-500 ease-out",
        "hover:border-gray-200 hover:shadow-lg",
        accent.border,
        "border-l-[3px]",
        className,
      )}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ ...fadeUp, delay: index * 0.05 }}
      whileHover={hoverLift}
      title={description ? `${title}: ${description}` : title}
    >
      <motion.div
        className={cn(
          "pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full opacity-0 blur-2xl transition-opacity duration-700 group-hover:opacity-100",
          health === "healthy" && "bg-green-500/5",
          health === "warning" && "bg-orange-500/5",
          health === "critical" && "bg-red-500/5",
        )}
        animate={pulse ? { scale: [1, 1.15, 1], opacity: [0, 0.6, 0] } : {}}
        transition={{ duration: 0.55 }}
        aria-hidden
      />

      <header className="relative flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-gray-500">
            {title}
          </p>
          {description && (
            <p className="max-w-[15rem] text-xs leading-relaxed text-gray-500">
              {description}
            </p>
          )}
        </div>
        {icon && <MetricIcon icon={icon} health={health} />}
      </header>

      <div className="relative mt-6 flex flex-1 flex-col justify-end space-y-3">
        <div className="flex flex-wrap items-end gap-x-3 gap-y-2">
          <motion.div
            className="flex items-baseline gap-1.5"
            animate={pulse ? { scale: [1, 1.02, 1] } : { scale: 1 }}
            transition={{ duration: 0.35 }}
          >
            <span
              className={cn(
                "text-3xl font-semibold tracking-tight sm:text-[2.25rem] sm:leading-none",
                accent.text,
              )}
            >
              <AnimatedMetricValue
                value={value}
                onPulse={() => setPulse(true)}
              />
            </span>
            {unit && (
              <span className="pb-0.5 text-sm font-medium text-gray-400">
                {unit}
              </span>
            )}
          </motion.div>
          <StatusDot health={health} />
        </div>

        {trend && trendValue && (
          <MetricTrend
            trend={trend}
            trendValue={trendValue}
            health={health}
            isLive={isLive}
          />
        )}

        {sparklineData && sparklineData.length > 1 && (
          <div className="pt-1">
            <MetricSparkline data={sparklineData} health={health} />
          </div>
        )}

        {detailHref && (
          <Button
            asChild
            variant="outline"
            className="mt-2 w-full border-gray-200 bg-white/80 text-gray-900 shadow-none transition-all hover:border-gray-300 hover:bg-gray-50 hover:shadow-sm"
          >
            <Link href={detailHref} className="gap-2">
              View details
              <ArrowUpRight className="h-3.5 w-3.5 opacity-60 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </Link>
          </Button>
        )}
      </div>
    </motion.article>
  );

  if (detailHref) {
    return (
      <Link href={detailHref} className="block h-full focus-visible:outline-none">
        {body}
      </Link>
    );
  }

  return body;
}

export function MetricCard(props: MetricCardProps) {
  const { isLoading, showSparkline, ...rest } = props as MetricCardProps & {
    showSparkline?: boolean;
  };

  if (isLoading) {
    return (
      <MetricCardSkeleton
        className={rest.className}
        showSparkline={showSparkline ?? Boolean(rest.sparklineData?.length)}
      />
    );
  }

  return <MetricCardInner {...rest} />;
}
