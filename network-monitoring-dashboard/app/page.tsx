'use client';

import { useEffect, useState } from 'react';
import { Activity, AlertTriangle, Zap, TrendingUp } from 'lucide-react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DashboardLayout } from '@/components/dashboard-layout';
import { MetricCard } from '@/components/metric-card';
import {
  getCurrentMetrics,
  getHistoricalTraffic,
  getTrafficPrediction,
  getProtocolDistribution,
  getSystemStatus,
} from '@/lib/api';

const COLORS = ['#a78bfa', '#67e8f9', '#ef4444', '#fbbf24', '#6366f1'];

interface MetricsData {
  current_traffic_mbps: number;
  active_connections: number;
  anomaly_score_percent: number;
  alerts_today: number;
}

interface TrafficPoint {
  time: string;
  traffic: number;
  predicted: number;
}

interface PredictionPoint {
  time: string;
  predicted: number;
  upper: number;
  lower: number;
}

interface ProtocolItem {
  name: string;
  value: number;
}

interface SystemStatus {
  network_health_percent: number;
  anomaly_detection_percent: number;
  system_uptime_percent: number;
  threat_level: string;
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [trafficData, setTrafficData] = useState<TrafficPoint[]>([]);
  const [predictionData, setPredictionData] = useState<PredictionPoint[]>([]);
  const [protocolData, setProtocolData] = useState<ProtocolItem[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [metricsRes, trafficRes, predictionRes, protocolRes, statusRes] = await Promise.all([
          getCurrentMetrics(),
          getHistoricalTraffic(),
          getTrafficPrediction(),
          getProtocolDistribution(),
          getSystemStatus(),
        ]);
        setMetrics(metricsRes);
        setTrafficData(trafficRes.data);
        setPredictionData(predictionRes.data);
        setProtocolData(protocolRes.data);
        setSystemStatus(statusRes);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchData();
  }, []);

  if (isLoading || !metrics || !systemStatus) {
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
      {/* Metrics Grid */}
      <div className="grid grid-cols-1 gap-4 sm:gap-6 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Current Traffic"
          value={metrics.current_traffic_mbps}
          unit="Mbps"
          icon={<Zap className="h-5 w-5" />}
          trend="up"
          trendValue="+12% from baseline"
          description="Real-time network traffic"
        />
        <MetricCard
          title="Active Connections"
          value={metrics.active_connections}
          icon={<Activity className="h-5 w-5" />}
          trend="stable"
          trendValue="Stable"
          description="Current TCP/UDP connections"
        />
        <MetricCard
          title="Anomaly Score"
          value={metrics.anomaly_score_percent}
          unit="%"
          icon={<AlertTriangle className="h-5 w-5" />}
          trend="down"
          trendValue="-2.3% from last hour"
          description="Network anomaly likelihood"
        />
        <MetricCard
          title="Alerts Today"
          value={metrics.alerts_today}
          icon={<TrendingUp className="h-5 w-5" />}
          trend="up"
          trendValue="3 critical"
          description="Total security alerts"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-2">
        {/* Traffic Chart */}
        <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
          <CardHeader>
            <CardTitle>Network Traffic (Last 24 Hours)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trafficData}>
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
                <Line
                  type="monotone"
                  dataKey="traffic"
                  stroke="#a78bfa"
                  dot={false}
                  strokeWidth={2}
                  name="Actual Traffic"
                />
                <Line
                  type="monotone"
                  dataKey="predicted"
                  stroke="#67e8f9"
                  dot={false}
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  name="Predicted Traffic"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Prediction Chart */}
        <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
          <CardHeader>
            <CardTitle>Predicted Traffic (Next 6 Hours)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={predictionData}>
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
                <Area
                  type="monotone"
                  dataKey="upper"
                  fill="#67e8f9"
                  stroke="#67e8f9"
                  fillOpacity={0.2}
                  dot={false}
                  name="Upper Bound"
                />
                <Area
                  type="monotone"
                  dataKey="lower"
                  fill="#67e8f9"
                  stroke="#67e8f9"
                  fillOpacity={0}
                  dot={false}
                  name="Lower Bound"
                />
                <Line
                  type="monotone"
                  dataKey="predicted"
                  stroke="#a78bfa"
                  strokeWidth={2}
                  dot={false}
                  name="Prediction"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-2">
        {/* Protocol Distribution */}
        <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
          <CardHeader>
            <CardTitle>Traffic Distribution by Protocol</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={protocolData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name} ${value}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {protocolData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1a1a2e',
                    border: '1px solid #16213e',
                    borderRadius: '8px',
                    color: '#ffffff',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* System Status */}
        <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
          <CardHeader>
            <CardTitle>System Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Network Health</span>
                <span className="text-sm font-semibold text-green-500">{systemStatus.network_health_percent}%</span>
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div className="h-full rounded-full bg-green-500" style={{ width: `${systemStatus.network_health_percent}%` }} />
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Anomaly Detection</span>
                <span className="text-sm font-semibold text-accent">{systemStatus.anomaly_detection_percent}%</span>
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div className="h-full rounded-full bg-accent" style={{ width: `${systemStatus.anomaly_detection_percent}%` }} />
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">System Uptime</span>
                <span className="text-sm font-semibold text-green-500">{systemStatus.system_uptime_percent}%</span>
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div className="h-full rounded-full bg-green-500" style={{ width: `${systemStatus.system_uptime_percent}%` }} />
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Threat Level</span>
                <span className={`text-sm font-semibold ${systemStatus.threat_level === 'Low' ? 'text-green-500' : systemStatus.threat_level === 'Medium' ? 'text-yellow-500' : 'text-red-500'}`}>
                  {systemStatus.threat_level}
                </span>
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div className={`h-full rounded-full ${systemStatus.threat_level === 'Low' ? 'bg-green-500' : systemStatus.threat_level === 'Medium' ? 'bg-yellow-500' : 'bg-red-500'}`} style={{ width: `${systemStatus.threat_level === 'Low' ? '33%' : systemStatus.threat_level === 'Medium' ? '66%' : '100%'}` }} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
