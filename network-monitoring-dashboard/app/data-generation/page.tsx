'use client';

import { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Play, Square, RefreshCw, Database, Clock, Activity, FileJson } from 'lucide-react';
import { DashboardLayout } from '@/components/dashboard-layout';
import { startGnnCapture, stopGnnCapture, getGnnCaptureStatus, getGnnDatasets } from '@/lib/api';

export default function DataGenerationPage() {
  const [status, setStatus] = useState<any>(null);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [uiError, setUiError] = useState<string | null>(null);

  // Polling interval for status
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const currentStatus = await getGnnCaptureStatus();
        setStatus(currentStatus);
        
        // Also fetch datasets to update the list
        const dsets = await getGnnDatasets();
        setDatasets(dsets.datasets || []);
      } catch (error: any) {
        console.error('Failed to fetch GNN status:', error);
        // Only set UI error if it's not a generic network failure (to avoid blinking on transient errors)
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 3000); // Poll every 3s
    return () => clearInterval(interval);
  }, []);

  const handleStart = async () => {
    try {
      setLoading(true);
      await startGnnCapture({
        window_seconds: 5,
        prediction_horizons: [15, 30, 60]
      });
      // Force an immediate status update
      const newStatus = await getGnnCaptureStatus();
      setStatus(newStatus);
      setUiError(null);
    } catch (error: any) {
      console.error('Failed to start capture:', error);
      setUiError(error.message || 'Failed to start capture. Make sure Mininet is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    try {
      setLoading(true);
      await stopGnnCapture();
      const newStatus = await getGnnCaptureStatus();
      setStatus(newStatus);
      setUiError(null);
    } catch (error: any) {
      console.error('Failed to stop capture:', error);
      setUiError(error.message || 'Failed to stop capture.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout>
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight mb-2">GNN Data Generation</h1>
        <p className="text-muted-foreground">
          Generate time-windowed, graph-structured telemetry datasets for training predictive AI models.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-xl">Simulation Control</CardTitle>
              {status?.running ? (
                <Badge variant="default" className="bg-blue-500">Running</Badge>
              ) : (
                <Badge variant="secondary">Idle</Badge>
              )}
            </div>
            <CardDescription>
              Execute scenario library to generate labeled training data
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            
            {status?.running && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Current Scenario</span>
                    <span className="font-medium text-primary">{status.current_scenario || 'Starting...'}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Current Phase</span>
                    <span className="font-medium">{status.current_phase || '...'}</span>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Overall Progress</span>
                    <span>{status.progress_pct}%</span>
                  </div>
                  <Progress value={status.progress_pct} className="h-2" />
                </div>
              </div>
            )}

            {!status?.running && status?.last_error && !uiError && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-md text-red-500 text-sm">
                Last run failed: {status.last_error}
              </div>
            )}

            {uiError && (
              <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-md text-amber-500 text-sm">
                {uiError}
              </div>
            )}

            {!status?.running && status?.last_result && !uiError && (
              <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-md text-green-500 text-sm">
                Successfully generated dataset: {status.last_result.summary?.total_windows} windows.
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <Button 
                onClick={handleStart} 
                disabled={status?.running || loading}
                className="w-full bg-blue-600 hover:bg-blue-700"
              >
                <Play className="mr-2 h-4 w-4 flex-shrink-0" />
                <span className="truncate">Start Full Generation (~55m)</span>
              </Button>
              <Button 
                onClick={handleStop} 
                disabled={!status?.running || loading}
                variant="destructive"
                className="w-full"
              >
                <Square className="mr-2 h-4 w-4 flex-shrink-0" />
                <span className="truncate">Stop Capture</span>
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Generation Settings</CardTitle>
            <CardDescription>
              Configuration for the graph snapshot pipeline
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 border border-border rounded-lg bg-background/50">
                <div className="flex items-center gap-3">
                  <Clock className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Window Interval</p>
                    <p className="text-xs text-muted-foreground">Telemetry sampling rate</p>
                  </div>
                </div>
                <Badge variant="outline">5 Seconds</Badge>
              </div>

              <div className="flex items-center justify-between p-3 border border-border rounded-lg bg-background/50">
                <div className="flex items-center gap-3">
                  <Activity className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Prediction Horizons</p>
                    <p className="text-xs text-muted-foreground">Look-ahead labeling</p>
                  </div>
                </div>
                <Badge variant="outline">15s, 30s, 60s</Badge>
              </div>

              <div className="flex items-center justify-between p-3 border border-border rounded-lg bg-background/50">
                <div className="flex items-center gap-3">
                  <Database className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Scenario Library</p>
                    <p className="text-xs text-muted-foreground">Scripted anomaly patterns</p>
                  </div>
                </div>
                <Badge variant="outline">12 Scenarios</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-xl">Generated Datasets</CardTitle>
              <CardDescription>Historical GNN captures available for training</CardDescription>
            </div>
            <Button variant="outline" size="icon" onClick={() => {
              getGnnDatasets().then(d => setDatasets(d.datasets || []));
            }}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {datasets.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No datasets generated yet. Run a capture to create one.
            </div>
          ) : (
            <div className="space-y-4">
              {datasets.map((ds) => (
                <div key={ds.run_id} className="p-4 border border-border rounded-lg flex items-start justify-between bg-card hover:bg-accent/5 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <FileJson className="h-5 w-5 text-blue-500" />
                      <span className="font-medium">{ds.run_id}</span>
                      <Badge variant="secondary" className="text-xs">{ds.summary?.scenario_name || 'multi'}</Badge>
                    </div>
                    <div className="text-sm text-muted-foreground mt-2">
                      <span className="mr-4">Windows: <strong>{ds.summary?.total_windows || 0}</strong></span>
                      <span className="mr-4">Duration: <strong>{ds.summary?.duration_seconds ? `${Math.round(ds.summary.duration_seconds / 60)}m` : '0m'}</strong></span>
                    </div>
                  </div>
                  <div className="text-right space-y-2">
                    <div className="text-xs text-muted-foreground">{ds.path}</div>
                    {ds.summary?.current_label_distribution && (
                      <div className="flex gap-1 justify-end">
                        {Object.entries(ds.summary.current_label_distribution)
                          .sort((a: any, b: any) => b[1] - a[1])
                          .slice(0, 3)
                          .map(([label, count]: [string, any]) => (
                            <Badge key={label} variant="outline" className="text-[10px] px-1 py-0 h-4">
                              {label.replace(/_/g, ' ')} ({count})
                            </Badge>
                          ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
    </DashboardLayout>
  );
}
