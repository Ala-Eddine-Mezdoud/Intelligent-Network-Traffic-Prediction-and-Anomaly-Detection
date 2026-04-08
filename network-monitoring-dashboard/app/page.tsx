'use client';

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
import { trafficData, protocolData } from '@/lib/mock-data';

const COLORS = ['#a78bfa', '#67e8f9', '#ef4444', '#fbbf24', '#6366f1'];

export default function Dashboard() {
  const currentTraffic = 112;
  const activeConnections = 2847;
  const anomalyScore = 18.5;
  const alertsToday = 7;

  return (
    <DashboardLayout>
      {/* Metrics Grid */}
      <div className="grid grid-cols-1 gap-4 sm:gap-6 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Current Traffic"
          value={currentTraffic}
          unit="Mbps"
          icon={<Zap className="h-5 w-5" />}
          trend="up"
          trendValue="+12% from baseline"
          description="Real-time network traffic"
        />
        <MetricCard
          title="Active Connections"
          value={activeConnections}
          icon={<Activity className="h-5 w-5" />}
          trend="stable"
          trendValue="Stable"
          description="Current TCP/UDP connections"
        />
        <MetricCard
          title="Anomaly Score"
          value={anomalyScore}
          unit="%"
          icon={<AlertTriangle className="h-5 w-5" />}
          trend="down"
          trendValue="-2.3% from last hour"
          description="Network anomaly likelihood"
        />
        <MetricCard
          title="Alerts Today"
          value={alertsToday}
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
              <AreaChart
                data={[
                  { time: '00:00', predicted: 45, upper: 52, lower: 38 },
                  { time: '01:00', predicted: 55, upper: 63, lower: 47 },
                  { time: '02:00', predicted: 42, upper: 50, lower: 34 },
                  { time: '03:00', predicted: 32, upper: 40, lower: 24 },
                  { time: '04:00', predicted: 25, upper: 33, lower: 17 },
                  { time: '05:00', predicted: 28, upper: 36, lower: 20 },
                ]}
              >
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
                <span className="text-sm font-semibold text-green-500">98%</span>
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div className="h-full w-[98%] rounded-full bg-green-500" />
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Anomaly Detection</span>
                <span className="text-sm font-semibold text-accent">95%</span>
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div className="h-full w-[95%] rounded-full bg-accent" />
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">System Uptime</span>
                <span className="text-sm font-semibold text-green-500">99.9%</span>
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div className="h-full w-[99.9%] rounded-full bg-green-500" />
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Threat Level</span>
                <span className="text-sm font-semibold text-yellow-500">Medium</span>
              </div>
              <div className="h-2 rounded-full bg-muted">
                <div className="h-full w-[65%] rounded-full bg-yellow-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
