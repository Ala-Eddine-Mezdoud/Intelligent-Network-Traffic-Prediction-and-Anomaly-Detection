'use client';

import { useEffect, useState } from 'react';
import { Search } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { DashboardLayout } from '@/components/dashboard-layout';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { getAnomalies } from '@/lib/api';

interface Anomaly {
  id: string;
  timestamp: string;
  source_ip: string;
  dest_ip: string;
  threat_type: string;
  severity: string;
  status: string;
}

export default function AnomalyDetection() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchAnomalies() {
      try {
        const res = await getAnomalies(searchTerm, severityFilter);
        setAnomalies(res.anomalies);
      } catch (error) {
        console.error('Failed to fetch anomalies:', error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchAnomalies();
  }, [searchTerm, severityFilter]);

  const filteredAnomalies = anomalies;

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'High':
        return 'bg-red-500/20 text-red-300 border-red-500/30';
      case 'Medium':
        return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
      case 'Low':
        return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
      default:
        return 'bg-gray-500/20 text-gray-300';
    }
  };

  const getStatusColor = (status: string) => {
    return status === 'Ongoing'
      ? 'bg-red-500/20 text-red-300 border-red-500/30'
      : 'bg-green-500/20 text-green-300 border-green-500/30';
  };

  if (isLoading) {
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
            Anomaly Detection
          </h1>
          <p className="text-muted-foreground">
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
        <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
          <CardHeader>
            <CardTitle>Detected Anomalies ({filteredAnomalies.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto -mx-4 md:mx-0">
              <Table>
                <TableHeader>
                  <TableRow className="border-border hover:bg-transparent whitespace-nowrap">
                    <TableHead className="text-foreground text-xs md:text-sm px-2 md:px-4">Timestamp</TableHead>
                    <TableHead className="text-foreground text-xs md:text-sm px-2 md:px-4">Source IP</TableHead>
                    <TableHead className="text-foreground text-xs md:text-sm px-2 md:px-4">Dest IP</TableHead>
                    <TableHead className="text-foreground text-xs md:text-sm px-2 md:px-4">Threat</TableHead>
                    <TableHead className="text-foreground text-xs md:text-sm px-2 md:px-4">Severity</TableHead>
                    <TableHead className="text-foreground text-xs md:text-sm px-2 md:px-4">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredAnomalies.map((anomaly) => (
                    <TableRow
                      key={anomaly.id}
                      className="border-border hover:bg-muted/50 cursor-pointer transition-colors whitespace-nowrap"
                    >
                      <TableCell className="text-foreground font-mono text-xs md:text-sm px-2 md:px-4">
                        {anomaly.timestamp}
                      </TableCell>
                      <TableCell className="text-foreground font-mono text-xs md:text-sm px-2 md:px-4">
                        {anomaly.source_ip}
                      </TableCell>
                      <TableCell className="text-foreground font-mono text-xs md:text-sm px-2 md:px-4">
                        {anomaly.dest_ip}
                      </TableCell>
                      <TableCell className="text-foreground text-xs md:text-sm px-2 md:px-4">
                        {anomaly.threat_type}
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
