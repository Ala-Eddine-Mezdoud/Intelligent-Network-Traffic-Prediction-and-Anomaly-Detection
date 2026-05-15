"use client";

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

interface TrafficPredictionChartProps {
  data: any[];
  title?: string;
  height?: number;
  showLiveBadge?: boolean;
}

export function TrafficPredictionChart({
  data,
  title = "Traffic Prediction",
  height = 380,
  showLiveBadge = false,
}: TrafficPredictionChartProps) {
  return (
    <Card className="border-border bg-white/5 backdrop-blur-xl supports-backdrop-filter:bg-white/5">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {title}
          {showLiveBadge && (
            <span className="text-[11px] font-normal text-sky-300 bg-sky-950/30 border border-sky-500/30 rounded-full px-2 py-0.5">
              Live Forecast
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 gap-2">
            <p className="text-muted-foreground text-lg font-medium">
              No Data Available
            </p>
            <p className="text-muted-foreground text-sm">
              Start a simulation to see traffic predictions
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={height}>
            <ComposedChart data={data}>
              <defs>
                <linearGradient id="colorUpper" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.2} />
                  <stop offset="50%" stopColor="#818cf8" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0.1} />
                </linearGradient>
                <linearGradient id="colorPredicted" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#67e8f9" stopOpacity={0.8} />
                  <stop offset="100%" stopColor="#67e8f9" stopOpacity={0.3} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff1a" />
              <XAxis
                dataKey="time"
                stroke="#ffffff80"
                style={{ fontSize: "11px" }}
              />
              <YAxis stroke="#ffffff80" style={{ fontSize: "11px" }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "rgba(15, 23, 42, 0.9)",
                  backdropFilter: "blur(8px)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  borderRadius: "12px",
                  boxShadow: "0 10px 25px rgba(0,0,0,0.3)",
                }}
                labelStyle={{ color: "#e2e8f0", fontWeight: "600" }}
                itemStyle={{ color: "#e2e8f0" }}
              />
              <Legend
                wrapperStyle={{
                  color: "#e2e8f0",
                  fontSize: "12px",
                  paddingTop: "20px",
                }}
              />
              <Area
                type="monotone"
                dataKey="upper"
                fill="url(#colorUpper)"
                stroke="none"
                name="Confidence Range"
                legendType="none"
              />
              <Line
                type="monotone"
                dataKey="lower"
                stroke="none"
                fill="none"
                dot={false}
                legendType="none"
              />
              <Line
                type="monotone"
                dataKey="historical"
                stroke="#a78bfa"
                dot={{ fill: "#a78bfa", r: 3 }}
                activeDot={{ r: 5 }}
                strokeWidth={2.5}
                name="Historical (Mbps)"
              />
              <Line
                type="monotone"
                dataKey="predicted"
                stroke="#67e8f9"
                strokeDasharray="5 5"
                dot={{ fill: "#67e8f9", r: 3 }}
                activeDot={{ r: 5 }}
                strokeWidth={2.5}
                name="Predicted (Mbps)"
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
