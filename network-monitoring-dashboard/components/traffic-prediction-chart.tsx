"use client";

import { motion } from "framer-motion";
import { useTheme } from "next-themes";
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  CHART_STROKE,
  CHART_STROKE_DARK,
  chartTooltipStyle,
  chartTooltipStyleDark,
  mutedBadge,
} from "@/lib/ui-theme";
import { cn } from "@/lib/utils";
import { ChartSkeleton } from "@/components/skeletons";
import { hoverLift, springSoft } from "@/lib/motion";

interface TrafficPredictionChartProps {
  data: any[];
  title?: string;
  height?: number;
  showLiveBadge?: boolean;
  isLoading?: boolean;
}

export function TrafficPredictionChart({
  data,
  title = "Traffic Prediction",
  height = 380,
  showLiveBadge = false,
  isLoading = false,
}: TrafficPredictionChartProps) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const stroke = isDark ? CHART_STROKE_DARK : CHART_STROKE;
  const tooltipStyle = isDark ? chartTooltipStyleDark : chartTooltipStyle;

  if (isLoading) {
    return <ChartSkeleton height={height} className="mb-4" />;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springSoft}
      whileHover={hoverLift}
      className="mb-4"
    >
      <Card className="overflow-hidden transition-shadow duration-500 hover:shadow-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {title}
            {showLiveBadge && (
              <span className={cn(mutedBadge, "font-normal text-green-600")}>
                <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-green-500 live-pulse" />
                Live forecast
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {data.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex h-48 flex-col items-center justify-center gap-2"
            >
              <p className="text-lg font-medium text-foreground">No data available</p>
              <p className="text-sm text-muted-foreground">
                Start a simulation to see traffic predictions
              </p>
            </motion.div>
          ) : (
            <ResponsiveContainer width="100%" height={height}>
              <ComposedChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke={stroke.grid} />
                <XAxis
                  dataKey="time"
                  stroke={stroke.axis}
                  tick={{ fill: stroke.axis, fontSize: 11 }}
                />
                <YAxis
                  stroke={stroke.axis}
                  tick={{ fill: stroke.axis, fontSize: 11 }}
                />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 12, color: stroke.axis }} />
                <Area
                  type="monotone"
                  dataKey="upper"
                  fill={stroke.confidence}
                  stroke="none"
                  name="Confidence range"
                  legendType="none"
                />
                <Line
                  type="monotone"
                  dataKey="historical"
                  stroke={stroke.historical}
                  dot={{ fill: stroke.historical, r: 2 }}
                  activeDot={{ r: 4 }}
                  strokeWidth={2}
                  name="Historical"
                />
                <Line
                  type="monotone"
                  dataKey="predicted"
                  stroke={stroke.predicted}
                  strokeDasharray="6 4"
                  dot={false}
                  strokeWidth={2}
                  name="Predicted"
                />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
