'use client';

import { useEffect, useState } from 'react';
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
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DashboardLayout } from '@/components/dashboard-layout';
import { getPredictions, getModelMetrics, getModelInfo } from '@/lib/api';

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
        console.error('Failed to fetch prediction data:', error);
        if (!mounted) {
          return;
        }
        setError(error instanceof Error ? error.message : 'Unknown API error');
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
              <div className="text-foreground font-semibold">Prediction API unavailable</div>
              <div className="text-muted-foreground text-sm mt-2">{error}</div>
            </div>
          </div>
        </DashboardLayout>
      );
    }

    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-muted-foreground">Loading...</div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-foreground mb-2">
            Traffic Prediction
          </h1>
          <p className="text-muted-foreground">
            AI-powered network traffic forecasting with confidence intervals
          </p>
        </div>

        {/* Main Chart */}
        <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
          <CardHeader>
            <CardTitle>Historical & Predicted Traffic</CardTitle>
          </CardHeader>
          <CardContent>
            {predictionData.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 gap-2">
                <p className="text-muted-foreground text-lg font-medium">No simulation running</p>
                <p className="text-muted-foreground text-sm">Start a simulation to see live traffic predictions</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={450}>
                <ComposedChart data={predictionData}>
                  <defs>
                    <linearGradient id="colorUpper" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#67e8f9" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#67e8f9" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff1a" />
                  <XAxis
                    dataKey="time"
                    stroke="#ffffff80"
                    style={{ fontSize: '12px' }}
                  />
                  <YAxis stroke="#ffffff80" style={{ fontSize: '12px' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1a1a2e',
                      border: '1px solid #16213e',
                      borderRadius: '8px',
                    }}
                    labelStyle={{ color: '#ffffff' }}
                  />
                  <Legend wrapperStyle={{ color: '#ffffff' }} />
                  <Area
                    type="monotone"
                    dataKey="upper"
                    fill="url(#colorUpper)"
                    stroke="none"
                    name="Confidence Interval"
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
                    dot={{ fill: '#a78bfa', r: 4 }}
                    activeDot={{ r: 6 }}
                    strokeWidth={2.5}
                    name="Historical Traffic"
                  />
                  <Line
                    type="monotone"
                    dataKey="predicted"
                    stroke="#67e8f9"
                    strokeDasharray="5 5"
                    dot={{ fill: '#67e8f9', r: 4 }}
                    activeDot={{ r: 6 }}
                    strokeWidth={2.5}
                    name="Predicted Traffic"
                  />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Model Performance Metrics */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 sm:gap-6 md:gap-6">
          <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Mean Absolute Error (MAE)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-accent">{metrics.mae_mbps} Mbps</div>
              <p className="text-xs text-muted-foreground mt-2">
                Average prediction deviation
              </p>
            </CardContent>
          </Card>

          <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Root Mean Squared Error (RMSE)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-accent">{metrics.rmse_mbps} Mbps</div>
              <p className="text-xs text-muted-foreground mt-2">
                Squared error measurement
              </p>
            </CardContent>
          </Card>

          <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Model Accuracy
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-accent">{metrics.accuracy_percent}%</div>
              <p className="text-xs text-muted-foreground mt-2">
                Overall prediction accuracy
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Additional Info */}
        <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
          <CardHeader>
            <CardTitle>Model Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-3 md:gap-4 md:grid-cols-2">
              <div>
                <h3 className="font-semibold text-foreground mb-2">Model Type</h3>
                <p className="text-muted-foreground">
                  {modelInfo.model_type}
                </p>
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-2">Training Data</h3>
                <p className="text-muted-foreground">
                  {modelInfo.training_data}
                </p>
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-2">Last Updated</h3>
                <p className="text-muted-foreground">
                  {modelInfo.last_updated}
                </p>
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-2">
                  Prediction Horizon
                </h3>
                <p className="text-muted-foreground">{modelInfo.prediction_horizon}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
