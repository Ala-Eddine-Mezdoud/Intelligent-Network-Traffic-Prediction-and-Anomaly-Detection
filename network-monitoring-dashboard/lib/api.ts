const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// Metrics API
export async function getCurrentMetrics() {
  return fetchApi<{
    current_traffic_mbps: number;
    active_connections: number;
    anomaly_score_percent: number;
    alerts_today: number;
  }>('/metrics/current');
}

export async function getHistoricalTraffic() {
  return fetchApi<{
    data: Array<{ time: string; traffic: number; predicted: number }>;
  }>('/metrics/traffic/historical');
}

export async function getTrafficPrediction() {
  return fetchApi<{
    data: Array<{ time: string; predicted: number; upper: number; lower: number }>;
  }>('/metrics/traffic/prediction');
}

export async function getProtocolDistribution() {
  return fetchApi<{
    data: Array<{ name: string; value: number }>;
  }>('/metrics/protocols/distribution');
}

export async function getSystemStatus() {
  return fetchApi<{
    network_health_percent: number;
    anomaly_detection_percent: number;
    system_uptime_percent: number;
    threat_level: string;
  }>('/metrics/system/status');
}

// Alerts API
export async function getAlerts() {
  return fetchApi<{
    alerts: Array<{
      id: string;
      title: string;
      description: string;
      time: string;
      severity: string;
    }>;
  }>('/alerts');
}

export async function getAlertStats() {
  return fetchApi<{
    total: number;
    critical: number;
    warnings: number;
  }>('/alerts/stats');
}

// Anomalies API
export async function getAnomalies(search?: string, severity?: string) {
  const params = new URLSearchParams();
  if (search) params.append('search', search);
  if (severity && severity !== 'all') params.append('severity', severity);
  
  return fetchApi<{
    anomalies: Array<{
      id: string;
      timestamp: string;
      source_ip: string;
      dest_ip: string;
      threat_type: string;
      severity: string;
      status: string;
    }>;
    total: number;
  }>(`/anomalies?${params.toString()}`);
}

// Historical API
export async function getHistoricalData(range: string = 'week') {
  return fetchApi<{
    weekly_data: Array<{ day: string; traffic: number; anomalies: number }>;
    monthly_data: Array<{ week: string; traffic: number; peak: number }>;
  }>(`/historical/traffic?range=${range}`);
}

export async function getHistoricalStats() {
  return fetchApi<{
    average_traffic_mbps: number;
    peak_traffic_mbps: number;
    total_anomalies: number;
    avg_response_time_ms: number;
  }>('/historical/stats');
}

// Predictions API
export async function getPredictions() {
  return fetchApi<{
    data: Array<{
      time: string;
      historical: number | null;
      predicted: number;
      upper: number;
      lower: number;
    }>;
  }>('/predictions');
}

export async function getModelMetrics() {
  return fetchApi<{
    mae_mbps: number;
    rmse_mbps: number;
    accuracy_percent: number;
  }>('/predictions/model/metrics');
}

export async function getModelInfo() {
  return fetchApi<{
    model_type: string;
    training_data: string;
    last_updated: string;
    prediction_horizon: string;
  }>('/predictions/model/info');
}

// Settings API
export async function getSettings() {
  return fetchApi<{
    system_name: string;
    refresh_interval_seconds: number;
    alert_threshold_mbps: number;
    anomaly_detection: boolean;
    email_alerts: boolean;
    slack_notifications: boolean;
    theme: string;
  }>('/settings');
}

export async function updateSettings(settings: Partial<{
  system_name: string;
  refresh_interval_seconds: number;
  alert_threshold_mbps: number;
  anomaly_detection: boolean;
  email_alerts: boolean;
  slack_notifications: boolean;
  theme: string;
}>) {
  return fetchApi<{
    success: boolean;
    settings: {
      system_name: string;
      refresh_interval_seconds: number;
      alert_threshold_mbps: number;
      anomaly_detection: boolean;
      email_alerts: boolean;
      slack_notifications: boolean;
      theme: string;
    };
  }>('/settings', {
    method: 'POST',
    body: JSON.stringify(settings),
  });
}

export async function retrainModel() {
  return fetchApi<{
    success: boolean;
    message: string;
  }>('/settings/model/retrain', {
    method: 'POST',
  });
}
