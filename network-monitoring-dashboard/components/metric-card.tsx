import { ReactNode } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon?: ReactNode;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  description?: string;
}

export function MetricCard({
  title,
  value,
  unit,
  icon,
  trend,
  trendValue,
  description,
}: MetricCardProps) {
  return (
    <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {title}
          </CardTitle>
          {icon && <div className="text-accent">{icon}</div>}
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex items-baseline gap-1">
          <div className="text-3xl font-bold text-foreground">{value}</div>
          {unit && <span className="text-sm text-muted-foreground">{unit}</span>}
        </div>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
        {trendValue && trend && (
          <div className="flex items-center gap-1">
            <span
              className={`text-xs font-semibold ${
                trend === 'up'
                  ? 'text-red-500'
                  : trend === 'down'
                    ? 'text-green-500'
                    : 'text-blue-500'
              }`}
            >
              {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'} {trendValue}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
