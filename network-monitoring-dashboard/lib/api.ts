// Flask backend API client
// All calls go to the Mininet Flask backend at NEXT_PUBLIC_API_URL

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:5000';

async function fetchApi(path: string, options?: RequestInit) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

// ----- Dashboard Metrics -----

export async function getCurrentMetrics() {
  try {
    const data = await fetchApi('/metrics/current');
    return {
      current_traffic_mbps: data.current_traffic_mbps ?? 0,
      active_connections: data.active_connections ?? 0,
      anomaly_score_percent: data.anomaly_score_percent ?? 0,
      alerts_today: data.alerts_today ?? 0,
    };
  } catch {
    return { current_traffic_mbps: 0, active_connections: 0, anomaly_score_percent: 0, alerts_today: 0 };
  }
}

export async function getHistoricalTraffic() {
  try {
    const result = await fetchApi('/metrics/traffic/historical');
    return { data: result.data || [] };
  } catch {
    return { data: [] };
  }
}

export async function getTrafficPrediction() {
  try {
    const result = await fetchApi('/metrics/traffic/prediction');
    return { data: result.data || [] };
  } catch {
    return { data: [] };
  }
}

export async function getProtocolDistribution() {
  try {
    const result = await fetchApi('/metrics/protocols/distribution');
    return { data: result.data || [] };
  } catch {
    return { data: [] };
  }
}

export async function getSystemStatus() {
  try {
    const data = await fetchApi('/metrics/system/status');
    return {
      network_health_percent: data.network_health_percent ?? 0,
      anomaly_detection_percent: data.anomaly_detection_percent ?? 0,
      threat_level: data.threat_level ?? 'Low',
    };
  } catch {
    return { network_health_percent: 0, anomaly_detection_percent: 0, threat_level: 'Low' };
  }
}

// ----- Alerts -----

export async function getAlerts() {
  try {
    const result = await fetchApi('/alerts');
    return { alerts: result.alerts || [] };
  } catch {
    return { alerts: [] };
  }
}

export async function getAlertStats() {
  try {
    return await fetchApi('/alerts/stats');
  } catch {
    return { total: 0, critical: 0, warnings: 0 };
  }
}

// ----- Anomalies -----

export async function getAnomalies(search?: string, severity?: string) {
  try {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (severity && severity !== 'all') params.set('severity', severity);
    const qs = params.toString() ? `?${params.toString()}` : '';
    const result = await fetchApi(`/anomalies${qs}`);
    return { anomalies: result.anomalies || [], total: result.total || 0 };
  } catch {
    return { anomalies: [], total: 0 };
  }
}

// ----- Predictions -----

export async function getPredictions() {
  try {
    const result = await fetchApi('/predictions');
    return { data: result.data || [] };
  } catch {
    return { data: [] };
  }
}

export async function startRealtimePipeline(intervalSeconds: number = 30) {
  try {
    return await fetchApi('/api/pipeline/start', {
      method: 'POST',
      body: JSON.stringify({ interval_seconds: intervalSeconds }),
    });
  } catch (error) {
    console.error('Failed to start pipeline:', error);
    throw error;
  }
}

export async function stopRealtimePipeline() {
  try {
    return await fetchApi('/api/pipeline/stop', { method: 'POST' });
  } catch (error) {
    console.error('Failed to stop pipeline:', error);
    throw error;
  }
}

export async function getGnnPredictions() {
  try {
    return await fetchApi('/api/gnn/inference/predictions');
  } catch {
    return null;
  }
}

export async function getGnnAnomalyHistory() {
  try {
    return await fetchApi('/api/gnn/inference/anomaly_history');
  } catch {
    return { events: [], total: 0 };
  }
}

export async function getFullSimulationStatus() {
  try {
    return await fetchApi('/api/simulation/status');
  } catch {
    return null;
  }
}

export async function startNormalSimulation() {
  return await fetchApi('/api/simulation/normal/start', { method: 'POST' });
}

export async function stopNormalSimulation() {
  return await fetchApi('/api/simulation/normal/stop', { method: 'POST' });
}

export async function injectAnomaly(type: string, node?: string, duration_s?: number) {
  return await fetchApi('/api/simulation/inject', {
    method: 'POST',
    body: JSON.stringify({ type, node, duration_s: duration_s ?? 30 }),
  });
}

export async function getAnomalyTypes() {
  try {
    return await fetchApi('/api/simulation/anomaly_types');
  } catch {
    return {};
  }
}

export async function getStorageInfo() {
  try {
    return await fetchApi('/api/storage/info');
  } catch {
    return null;
  }
}

export async function getModelMetrics() {
  try {
    return await fetchApi('/predictions/model/metrics');
  } catch {
    return { mae_mbps: 0, rmse_mbps: 0, accuracy_percent: 0 };
  }
}

export async function getModelInfo() {
  try {
    return await fetchApi('/predictions/model/info');
  } catch {
    return { model_type: 'N/A', training_data: 'N/A', last_updated: 'N/A', prediction_horizon: 'N/A' };
  }
}

// ----- Simulation / Pipeline -----

export async function getSimulationStatus() {
  try {
    return await fetchApi('/api/pipeline/status');
  } catch {
    return { pipeline: 'realtime', running: false };
  }
}

export async function startSimulation(params?: { interval_seconds?: number }) {
  return fetchApi('/api/pipeline/start', {
    method: 'POST',
    body: JSON.stringify(params || {}),
  });
}

export async function stopSimulation() {
  return fetchApi('/api/pipeline/stop', { method: 'POST' });
}

// ----- GNN Data Generation (Flask backend) -----

export async function startGnnCapture(params: {
  scenarios?: string[];
  window_seconds?: number;
  prediction_horizons?: number[];
  random_seed?: number;
}) {
  return fetchApi('/api/lab/run-gnn-capture', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function stopGnnCapture() {
  return fetchApi('/api/lab/gnn-capture/stop', { method: 'POST' });
}

export async function getGnnCaptureStatus() {
  try {
    return await fetchApi('/api/lab/gnn-capture/status');
  } catch {
    return {
      running: false,
      current_scenario: null,
      current_phase: null,
      progress_pct: 0,
      last_run: null,
      last_error: null,
      last_result: null,
    };
  }
}

export async function getGnnDatasets() {
  try {
    return await fetchApi('/api/lab/gnn-datasets');
  } catch {
    return { datasets: [] };
  }
}

// ----- Topology -----

export async function getTopology() {
  return fetchApi('/api/topology');
}
