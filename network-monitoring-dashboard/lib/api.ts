import { supabase } from './supabase'

// Metrics API -> Supabase RPC helpers
export async function getCurrentMetrics() {
  const { data, error } = await supabase.rpc('get_current_metrics')
  if (error) throw new Error(error.message)
  return data as {
    current_traffic_mbps: number;
    active_connections: number;
    anomaly_score_percent: number;
    alerts_today: number;
  }
}

export async function getHistoricalTraffic() {
  const { data, error } = await supabase
    .from('historical_aggregates')
    .select('*')
    .eq('bucket_type', 'daily')
    .order('bucket_start', { ascending: true })
    .limit(7)
  if (error) throw new Error(error.message)
  return {
    data: (data || []).map((row) => ({
      time: new Date(row.bucket_start).toLocaleDateString('en-US', { weekday: 'short' }),
      traffic: Number(row.avg_traffic_mbps || 0),
      predicted: Number(row.peak_traffic_mbps || 0),
    })),
  }
}

export async function getTrafficPrediction() {
  const { data, error } = await supabase
    .from('predictions')
    .select('prediction_for, predicted_value, upper_bound, lower_bound')
    .order('prediction_for', { ascending: true })
    .limit(24)
  if (error) throw new Error(error.message)
  return {
    data: (data || []).map((row) => ({
      time: new Date(row.prediction_for).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      predicted: Number(row.predicted_value),
      upper: Number(row.upper_bound),
      lower: Number(row.lower_bound),
    })),
  }
}

export async function getProtocolDistribution() {
  const { data, error } = await supabase
    .from('protocol_distribution')
    .select('name, value_pct')
    .order('sampled_at', { ascending: false })
    .limit(10)
  if (error) throw new Error(error.message)
  return {
    data: (data || []).map((row) => ({ name: row.name, value: Number(row.value_pct) })),
  }
}

export async function getSystemStatus() {
  const { data, error } = await supabase.rpc('get_current_metrics')
  if (error) throw new Error(error.message)
  const safe = data as any
  return {
    network_health_percent: Number(safe?.current_traffic_mbps || 0),
    anomaly_detection_percent: Number(safe?.anomaly_score_percent || 0),
    threat_level: safe?.alerts_today > 5 ? 'High' : safe?.alerts_today > 0 ? 'Medium' : 'Low',
  }
}

// Alerts API
export async function getAlerts() {
  const { data, error } = await supabase
    .from('alerts')
    .select('id, title, description, triggered_at, severity, status')
    .order('triggered_at', { ascending: false })
    .limit(50)
  if (error) throw new Error(error.message)
  return {
    alerts: (data || []).map((row) => ({
      id: row.id,
      title: row.title,
      description: row.description,
      time: new Date(row.triggered_at).toLocaleString('en-US'),
      severity: row.severity,
    })),
  }
}

export async function getAlertStats() {
  const { data, error } = await supabase.rpc('get_alert_stats')
  if (error) throw new Error(error.message)
  return data as { total: number; critical: number; warnings: number }
}

// Anomalies API
export async function getAnomalies(search?: string, severity?: string) {
  let query = supabase
    .from('anomalies')
    .select('id, detected_at, source_ip, dest_ip, threat_type, severity, status', { count: 'exact' })
    .order('detected_at', { ascending: false })

  if (severity && severity !== 'all') {
    query = query.eq('severity', severity)
  }
  if (search) {
    query = query.ilike('threat_type', `%${search}%`)
  }

  const { data, error, count } = await query.limit(50)
  if (error) throw new Error(error.message)
  return {
    anomalies: (data || []).map((row) => ({
      id: row.id,
      timestamp: new Date(row.detected_at).toLocaleString('en-US'),
      source_ip: row.source_ip ?? 'unknown',
      dest_ip: row.dest_ip ?? 'unknown',
      threat_type: row.threat_type,
      severity: row.severity,
      status: row.status,
    })),
    total: count || 0,
  }
}

// Predictions API
export async function getPredictions() {
  const { data, error } = await supabase
    .from('predictions')
    .select('prediction_for, historical_value, predicted_value, upper_bound, lower_bound')
    .order('prediction_for', { ascending: true })
    .limit(24)
  if (error) throw new Error(error.message)
  return {
    data: (data || []).map((row) => ({
      time: new Date(row.prediction_for).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      historical: row.historical_value ? Number(row.historical_value) : null,
      predicted: Number(row.predicted_value),
      upper: Number(row.upper_bound),
      lower: Number(row.lower_bound),
    })),
  }
}

export async function getModelMetrics() {
  const { data, error } = await supabase
    .from('model_registry')
    .select('mae_mbps, rmse_mbps, accuracy_percent')
    .eq('is_production', true)
    .limit(1)
    .single()
  if (error) {
    return { mae_mbps: 0, rmse_mbps: 0, accuracy_percent: 0 }
  }
  return data as { mae_mbps: number; rmse_mbps: number; accuracy_percent: number }
}

export async function getModelInfo() {
  const { data, error } = await supabase
    .from('model_registry')
    .select('model_type, training_data, last_deployed_at, name')
    .eq('is_production', true)
    .limit(1)
    .single()
  if (error) {
    return { model_type: 'N/A', training_data: 'N/A', last_updated: 'N/A', prediction_horizon: 'N/A' }
  }
  return {
    model_type: data.model_type,
    training_data: data.training_data || 'N/A',
    last_updated: data.last_deployed_at ? new Date(data.last_deployed_at).toLocaleDateString('en-US') : 'N/A',
    prediction_horizon: data.name || 'N/A',
  }
}

// ----- GNN Data Generation API (placeholder using Supabase) -----
export async function startGnnCapture(params: {
  scenarios?: string[];
  window_seconds?: number;
  prediction_horizons?: number[];
  random_seed?: number;
}) {
  const { data, error } = await supabase
    .from('gnn_datasets')
    .insert({
      run_id: `run_${Date.now()}`,
      window_seconds: params.window_seconds ?? 5,
      prediction_horizons: params.prediction_horizons ?? [15, 30, 60],
      scenario_names: params.scenarios ?? [],
      status: 'pending',
      started_at: new Date().toISOString(),
    })
    .select()
    .single()
  if (error) throw new Error(error.message)
  return { started: true, id: data.id }
}

export async function stopGnnCapture() {
  return { stopped: true }
}

export async function getGnnCaptureStatus() {
  const { data, error } = await supabase
    .from('gnn_datasets')
    .select('status, scenario_names, started_at, completed_at, error_message')
    .order('started_at', { ascending: false })
    .limit(1)
    .single()
  if (error) {
    return {
      running: false,
      current_scenario: null,
      current_phase: null,
      progress_pct: 0,
      last_run: null,
      last_error: null,
      last_result: null,
    }
  }
  const running = data?.status === 'running' || data?.status === 'pending'
  return {
    running,
    current_scenario: data?.scenario_names?.[0] ?? null,
    current_phase: running ? 'running' : data?.status ?? null,
    progress_pct: data?.status === 'completed' ? 100 : running ? 50 : 0,
    last_run: data?.started_at ? new Date(data.started_at).toISOString() : null,
    last_error: data?.error_message ?? null,
    last_result: data,
  }
}

export async function getGnnDatasets() {
  const { data, error } = await supabase
    .from('gnn_datasets')
    .select('run_id, dataset_path, total_windows, status, label_distribution')
    .order('started_at', { ascending: false })
    .limit(20)
  if (error) throw new Error(error.message)
  return {
    datasets: (data || []).map((row) => ({
      run_id: row.run_id,
      path: row.dataset_path || '',
      summary: {
        total_windows: row.total_windows,
        label_distribution: row.label_distribution,
        status: row.status,
      },
    })),
  }
}

