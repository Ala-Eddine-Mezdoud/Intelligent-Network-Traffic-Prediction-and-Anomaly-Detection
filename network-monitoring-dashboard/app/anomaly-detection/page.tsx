"use client";

import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { DashboardLayout } from "@/components/dashboard-layout";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getAnomalies } from "@/lib/api";
import { cn } from "@/lib/utils";
import { TableSkeleton } from "@/components/skeletons";
import { SEVERITY_STYLES } from "@/lib/dashboard-theme";
import {
  pageSubtitle,
  pageTitle,
  tableCell,
  tableHead,
  tableRow,
} from "@/lib/ui-theme";
import { MetricCardSkeletonGrid } from "@/components/metric-card";

interface Anomaly {
  id: string;
  timestamp: string;
  source_ip: string;
  dest_ip: string;
  threat_type: string;
  severity: string;
  status: string;
  node?: string;
  confidence?: number;
}

export default function AnomalyDetection() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    async function fetchAnomalies() {
      try {
        const res = await getAnomalies(searchTerm, severityFilter);
        if (mounted) {
          setAnomalies(res.anomalies);
        }
      } catch (error) {
        console.error("Failed to fetch anomalies:", error);
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    fetchAnomalies();

    const timer = setInterval(fetchAnomalies, 30000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, [searchTerm, severityFilter]);

  const filteredAnomalies = anomalies;

  const getSeverityColor = (severity: string) => {
    const s = severity.toLowerCase();
    const config = SEVERITY_STYLES[s] || SEVERITY_STYLES.default;
    return `${config.bg} ${config.text} ${config.border}`;
  };

  const getStatusColor = (status: string) => {
    return status === "Ongoing"
      ? "bg-orange-500/10 text-orange-500 border-orange-500/30"
      : "bg-green-500/10 text-green-500 border-green-500/30";
  };

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="mb-6 space-y-2">
          <div className="h-8 w-48 rounded-lg metric-shimmer bg-muted" />
          <div className="h-4 w-72 rounded-lg metric-shimmer bg-muted" />
        </div>
        <MetricCardSkeletonGrid count={3} className="mb-6" />
        <TableSkeleton rows={8} columns={6} />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className={pageTitle}>Anomaly Detection</h1>
          <p className={pageSubtitle}>
            Monitor and analyze detected network anomalies
          </p>
        </div>

        {/* Filters */}
        <div className="grid grid-cols-1 gap-3 md:gap-4 md:grid-cols-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by IP or threat type..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select value={severityFilter} onValueChange={setSeverityFilter}>
            <SelectTrigger>
              <SelectValue placeholder="Filter by severity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Severities</SelectItem>
              <SelectItem value="High">High</SelectItem>
              <SelectItem value="Medium">Medium</SelectItem>
              <SelectItem value="Low">Low</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Anomalies Table */}
        <Card>
          <CardHeader>
            <CardTitle>
              Detected Anomalies ({filteredAnomalies.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto -mx-4 md:mx-0">
              <Table>
                <TableHeader>
                  <TableRow className="border-border hover:bg-transparent whitespace-nowrap">
                    <TableHead className={tableHead}>Timestamp</TableHead>
                    <TableHead className={tableHead}>Source IP</TableHead>
                    <TableHead className={tableHead}>Threat</TableHead>
                    <TableHead className={tableHead}>Affected Node</TableHead>
                    <TableHead className={tableHead}>Confidence</TableHead>
                    <TableHead className={tableHead}>Severity</TableHead>
                    <TableHead className={tableHead}>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredAnomalies.map((anomaly) => (
                    <TableRow
                      key={anomaly.id}
                      className={cn(tableRow, "cursor-pointer whitespace-nowrap")}
                    >
                      <TableCell className={cn(tableCell, "font-mono text-xs")}>
                        {anomaly.timestamp}
                      </TableCell>
                      <TableCell className={cn(tableCell, "font-mono")}>
                        {anomaly.source_ip}
                      </TableCell>
                      <TableCell className={tableCell}>
                        {anomaly.threat_type}
                      </TableCell>
                      <TableCell className={tableCell}>
                        {anomaly.node ? (
                          <Badge
                            variant="outline"
                            className="border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400 font-mono text-xs"
                          >
                            {anomaly.node}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell className={tableCell}>
                        {anomaly.confidence != null ? (
                          <span className={cn(
                            "font-medium text-sm",
                            anomaly.confidence >= 0.8 ? "text-red-500" :
                            anomaly.confidence >= 0.6 ? "text-orange-500" :
                            "text-muted-foreground"
                          )}>
                            {Math.round(anomaly.confidence * 100)}%
                          </span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell className="text-xs md:text-sm px-2 md:px-4">
                        <Badge
                          variant="outline"
                          className={getSeverityColor(anomaly.severity)}
                        >
                          {anomaly.severity}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs md:text-sm px-2 md:px-4">
                        <Badge
                          variant="outline"
                          className={getStatusColor(anomaly.status)}
                        >
                          {anomaly.status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            {filteredAnomalies.length === 0 && (
              <div className="py-8 text-center">
                <p className="text-muted-foreground">
                  No anomalies match your search criteria
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
