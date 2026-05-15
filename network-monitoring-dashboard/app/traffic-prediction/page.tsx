"use client";

import { Activity, useEffect, useState } from "react";
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
import { DashboardLayout } from "@/components/dashboard-layout";
import { getPredictions, getModelMetrics, getModelInfo } from "@/lib/api";
import { MetricCard, MetricCardSkeletonGrid } from "@/components/metric-card";
import { ChartSkeleton } from "@/components/skeletons";
import { TrendingUp, Zap } from "lucide-react";
import { TrafficPredictionChart } from "@/components/traffic-prediction-chart";
import { loadingState, pageSubtitle, pageTitle } from "@/lib/ui-theme";

interface PredictionPoint {
  time: string;
  historical: number | null;
  predicted: number;
  upper: number;
  lower: number;
}

interface ModelMetrics {
  mae_mbps: number;
  rmse_mbps: number;
  accuracy_percent: number;
}

interface ModelInfo {
  model_type: string;
  training_data: string;
  last_updated: string;
  prediction_horizon: string;
}

export default function TrafficPrediction() {
  const [predictionData, setPredictionData] = useState<PredictionPoint[]>([]);
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function fetchData() {
      try {
        setError(null);
        const [predictionsRes, metricsRes, infoRes] = await Promise.all([
          getPredictions(),
          getModelMetrics(),
          getModelInfo(),
        ]);
        if (!mounted) {
          return;
        }
        setPredictionData(predictionsRes.data);
        setMetrics(metricsRes);
        setModelInfo(infoRes);
      } catch (error) {
        console.error("Failed to fetch prediction data:", error);
        if (!mounted) {
          return;
        }
        setError(error instanceof Error ? error.message : "Unknown API error");
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    fetchData();

    const timer = setInterval(fetchData, 30000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  if (isLoading || !metrics || !modelInfo) {
    if (!isLoading && error) {
      return (
        <DashboardLayout>
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="font-semibold text-gray-900">
                Prediction API unavailable
              </div>
              <div className="mt-2 text-sm text-gray-500">{error}</div>
            </div>
          </div>
        </DashboardLayout>
      );
    }

    return (
      <DashboardLayout>
        <div className="space-y-6">
          <div className="h-8 w-56 rounded-xl metric-shimmer bg-gray-100" />
          <ChartSkeleton height={450} />
          <MetricCardSkeletonGrid count={3} className="mb-4" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className={pageTitle}>Traffic Prediction</h1>
          <p className={pageSubtitle}>
            AI-powered network traffic forecasting with confidence intervals
          </p>
        </div>

        {/* Main Chart */}
        <TrafficPredictionChart 
          data={predictionData} 
          title="Historical & Predicted Traffic"
          height={450}
        />

       {/* ── Model Performance Metrics ───────────────────────────────────── */}
<div className="grid grid-cols-1 gap-4 sm:gap-6 md:grid-cols-2 lg:grid-cols-3 mb-4">
  <MetricCard
    index={0}
    title="Mean Absolute Error"
    value={metrics.mae_mbps}
    unit="Mbps"
    icon={<Activity className="h-5 w-5" />}
    trend={metrics.mae_mbps < 10 ? "down" : "up"}
    health={
      metrics.mae_mbps < 10
        ? "healthy"
        : metrics.mae_mbps < 20
          ? "warning"
          : "critical"
    }
    variant="traffic"
    description="Average prediction deviation"
  />

  <MetricCard
    index={1}
    title="Root Mean Squared Error"
    value={metrics.rmse_mbps}
    unit="Mbps"
    icon={<TrendingUp className="h-5 w-5" />}
    trend={metrics.rmse_mbps < 15 ? "down" : "up"}
    health={
      metrics.rmse_mbps < 15
        ? "healthy"
        : metrics.rmse_mbps < 30
          ? "warning"
          : "critical"
    }
    variant="connections"
    description="Squared error measurement"
  />

  <MetricCard
    index={2}
    title="Model Accuracy"
    value={metrics.accuracy_percent}
    unit="%"
    icon={<Zap className="h-5 w-5" />}
    trend={metrics.accuracy_percent > 90 ? "up" : "down"}
    health={
      metrics.accuracy_percent > 90
        ? "healthy"
        : metrics.accuracy_percent > 75
          ? "warning"
          : "critical"
    }
    variant="anomaly"
    description="Overall prediction accuracy"
  />
</div>

        {/* Additional Info */}
        <Card>
          <CardHeader>
            <CardTitle>Model Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-3 md:gap-4 md:grid-cols-2">
              <div>
                <h3 className="mb-2 font-semibold text-gray-900">Model Type</h3>
                <p className="text-gray-600">{modelInfo.model_type}</p>
              </div>
              <div>
                <h3 className="mb-2 font-semibold text-gray-900">
                  Training Data
                </h3>
                <p className="text-gray-600">{modelInfo.training_data}</p>
              </div>
              <div>
                <h3 className="mb-2 font-semibold text-gray-900">
                  Last Updated
                </h3>
                <p className="text-gray-600">{modelInfo.last_updated}</p>
              </div>
              <div>
                <h3 className="mb-2 font-semibold text-gray-900">
                  Prediction Horizon
                </h3>
                <p className="text-gray-600">
                  {modelInfo.prediction_horizon}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
