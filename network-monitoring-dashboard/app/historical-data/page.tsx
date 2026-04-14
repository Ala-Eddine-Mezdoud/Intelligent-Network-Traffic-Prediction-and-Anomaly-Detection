'use client';

import { useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DashboardLayout } from '@/components/dashboard-layout';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { getHistoricalData, getHistoricalStats } from '@/lib/api';

interface WeeklyDataPoint {
  day: string;
  traffic: number;
  anomalies: number;
}

interface MonthlyDataPoint {
  week: string;
  traffic: number;
  peak: number;
}

interface HistoricalStats {
  average_traffic_mbps: number;
  peak_traffic_mbps: number;
  total_anomalies: number;
  avg_response_time_ms: number;
}

export default function HistoricalData() {
  const [timeRange, setTimeRange] = useState('week');
  const [weeklyData, setWeeklyData] = useState<WeeklyDataPoint[]>([]);
  const [monthlyData, setMonthlyData] = useState<MonthlyDataPoint[]>([]);
  const [stats, setStats] = useState<HistoricalStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [dataRes, statsRes] = await Promise.all([
          getHistoricalData(timeRange),
          getHistoricalStats(),
        ]);
        setWeeklyData(dataRes.weekly_data);
        setMonthlyData(dataRes.monthly_data);
        setStats(statsRes);
      } catch (error) {
        console.error('Failed to fetch historical data:', error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchData();
  }, [timeRange]);

  if (isLoading || !stats) {
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
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 md:gap-0">
          <div>
            <h1 className="text-3xl font-bold text-foreground mb-2">
              Historical Data
            </h1>
            <p className="text-muted-foreground">
              View network traffic and anomaly trends over time
            </p>
          </div>
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-full md:w-48">
              <SelectValue placeholder="Select time range" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="week">Last 7 Days</SelectItem>
              <SelectItem value="month">Last 30 Days</SelectItem>
              <SelectItem value="quarter">Last 90 Days</SelectItem>
              <SelectItem value="year">Last Year</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Charts */}
        {timeRange === 'week' ? (
          <>
            {/* Weekly Traffic and Anomalies */}
            <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
              <CardHeader>
                <CardTitle>Weekly Traffic and Anomalies</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={350}>
                  <ComposedChart data={weeklyData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff1a" />
                    <XAxis
                      dataKey="day"
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
                    <Bar
                      dataKey="traffic"
                      fill="#a78bfa"
                      name="Traffic (Mbps)"
                      radius={[8, 8, 0, 0]}
                    />
                    <Line
                      type="monotone"
                      dataKey="anomalies"
                      stroke="#ef4444"
                      strokeWidth={2}
                      name="Anomalies Detected"
                      yAxisId="right"
                    />
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      stroke="#ffffff80"
                      style={{ fontSize: '12px' }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </>
        ) : (
          <>
            {/* Monthly Traffic Trends */}
            <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
              <CardHeader>
                <CardTitle>Monthly Traffic Trends</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={350}>
                  <ComposedChart data={monthlyData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff1a" />
                    <XAxis
                      dataKey="week"
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
                    <Bar
                      dataKey="traffic"
                      fill="#67e8f9"
                      name="Total Traffic (Mbps)"
                      radius={[8, 8, 0, 0]}
                    />
                    <Line
                      type="monotone"
                      dataKey="peak"
                      stroke="#fbbf24"
                      strokeWidth={2}
                      name="Peak Traffic (Mbps)"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </>
        )}

        {/* Statistics */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:gap-6 md:grid-cols-4">
          <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Average Traffic
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-accent">{stats.average_traffic_mbps} Mbps</div>
            </CardContent>
          </Card>

          <Card className="border-border bg-card/50 backdrop-filter:bg-card/40">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Peak Traffic
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-accent">{stats.peak_traffic_mbps} Mbps</div>
            </CardContent>
          </Card>

          <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Anomalies
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-red-500">{stats.total_anomalies}</div>
            </CardContent>
          </Card>

          <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Avg Response Time
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-accent">{stats.avg_response_time_ms}ms</div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
