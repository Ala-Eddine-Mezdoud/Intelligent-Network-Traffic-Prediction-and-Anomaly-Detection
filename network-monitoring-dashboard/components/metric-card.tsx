import Link from "next/link";
import { ReactNode } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon?: ReactNode;
  trend?: "up" | "down" | "stable";
  trendValue?: string;
  description?: string;
  health?: "healthy" | "warning" | "critical";
  variant?: "traffic" | "connections" | "anomaly" | "alerts";
  sparklineData?: number[];
  detailHref?: string;
}

const statusLabels: Record<string, string> = {
  healthy: "Healthy",
  warning: "Warning",
  critical: "Critical",
};

function getVariantStyles(variant?: string, health?: string) {
  const base =
    "bg-white/5 border border-white/10 backdrop-blur-xl ring-1 ring-white/5";

  if (variant === "traffic") {
    return `${base} bg-cyan-500/5 ring-cyan-500/20`;
  }
  if (variant === "connections") {
    return `${base} bg-violet-500/5 ring-violet-500/20`;
  }
  if (variant === "anomaly") {
    if (health === "critical") {
      return `${base} bg-red-500/10 ring-red-500/30`;
    }
    if (health === "warning") {
      return `${base} bg-orange-500/10 ring-orange-500/30`;
    }
    return `${base} bg-emerald-500/10 ring-emerald-500/30`;
  }
  if (variant === "alerts") {
    if (health === "critical") {
      return `${base} bg-red-500/10 ring-red-500/30`;
    }
    if (health === "warning") {
      return `${base} bg-orange-500/10 ring-orange-500/30`;
    }
    return `${base} bg-emerald-500/10 ring-emerald-500/30`;
  }
  return base;
}

function renderSparkline(data: number[]) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const width = 120;
  const height = 30;
  const points = data
    .map((value, index) => {
      const x = (index / (data.length - 1)) * width;
      const normalized = max === min ? 0.5 : (value - min) / (max - min);
      const y = height - normalized * height;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="h-8 w-full overflow-visible"
    >
      <defs>
        <linearGradient id="sparklineGradient" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#38bdf8" />
          <stop offset="100%" stopColor="#818cf8" />
        </linearGradient>
      </defs>
      <polyline
        fill="none"
        stroke="url(#sparklineGradient)"
        strokeWidth="2.5"
        points={points}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle
        cx={0}
        cy={height - ((data[0] - min) / (max - min || 1)) * height}
        r="2.5"
        fill="#38bdf8"
      />
      <circle
        cx={width}
        cy={
          height - ((data[data.length - 1] - min) / (max - min || 1)) * height
        }
        r="2.5"
        fill="#818cf8"
      />
    </svg>
  );
}

export function MetricCard({
  title,
  value,
  unit,
  icon,
  trend,
  trendValue,
  description,
  health = "healthy",
  variant,
  sparklineData,
  detailHref,
}: MetricCardProps) {
  const trendSymbol = trend === "up" ? "↑" : trend === "down" ? "↓" : "→";
  const trendColor =
    trend === "up"
      ? "text-emerald-300"
      : trend === "down"
        ? "text-rose-300"
        : "text-amber-300";
  const statusColor =
    health === "critical"
      ? "bg-red-500/15 text-red-200"
      : health === "warning"
        ? "bg-orange-500/15 text-orange-200"
        : "bg-emerald-500/15 text-emerald-200";

  const cardContent = (
    <Card
      className={`${getVariantStyles(variant, health)} group relative overflow-hidden rounded-[18px] p-4 transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_28px_85px_-35px_rgba(56,189,248,0.35)]`}
      title={description ? `${title}: ${description}` : title}
    >
      <CardHeader className="p-0">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-300/90">
              {title}
            </CardTitle>
            {description && (
              <p className="mt-2 max-w-[14rem] text-xs text-slate-400">
                {description}
              </p>
            )}
          </div>
          {icon && (
            <div className="flex h-11 w-11 items-center justify-center rounded-3xl border border-white/10 bg-white/10 text-slate-100 shadow-lg shadow-cyan-500/10 transition duration-300 group-hover:scale-105">
              <span className="animate-pulse">{icon}</span>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="p-0 mt-5 space-y-4">
        <div className="flex items-end gap-3">
          <div className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            {value}
            {unit && (
              <span className="ml-1 text-base font-medium text-slate-300">
                {unit}
              </span>
            )}
          </div>
          <span
            className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase ${statusColor}`}
          >
            {statusLabels[health]}
          </span>
        </div>

        {trendValue && trend && (
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-300">
            <span className={`font-semibold ${trendColor}`}>{trendSymbol}</span>
            <span>{trendValue}</span>
          </div>
        )}

        {sparklineData && sparklineData.length > 1 ? (
          <div className="mt-2 rounded-3xl border border-white/10 bg-white/5 p-3">
            {renderSparkline(sparklineData)}
            <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
              <span>Last 24h</span>
              <span>{sparklineData[sparklineData.length - 1]}</span>
            </div>
          </div>
        ) : null}

        {detailHref && (
          <div className="mt-3">
            <Button
              asChild
              variant="secondary"
              className="w-full border border-white/10 bg-white/10 text-white hover:bg-white/15"
            >
              <Link href={detailHref}>View Details</Link>
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );

  return detailHref ? (
    <Link href={detailHref} className="block">
      {cardContent}
    </Link>
  ) : (
    cardContent
  );
}
