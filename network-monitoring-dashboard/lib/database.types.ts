export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      historical_aggregates: {
        Row: {
          id: string
          bucket_type: string
          bucket_start: string
          bucket_end: string
          avg_traffic_mbps: number | null
          peak_traffic_mbps: number | null
          min_traffic_mbps: number | null
          total_packets: number | null
          total_bytes: number | null
          created_at: string | null
        }
        Insert: {
          id?: string
          bucket_type: string
          bucket_start: string
          bucket_end: string
          avg_traffic_mbps?: number | null
          peak_traffic_mbps?: number | null
          min_traffic_mbps?: number | null
          total_packets?: number | null
          total_bytes?: number | null
          created_at?: string | null
        }
        Update: {
          id?: string
          bucket_type?: string
          bucket_start?: string
          bucket_end?: string
          avg_traffic_mbps?: number | null
          peak_traffic_mbps?: number | null
          min_traffic_mbps?: number | null
          total_packets?: number | null
          total_bytes?: number | null
          created_at?: string | null
        }
      }
      predictions: {
        Row: {
          id: string
          prediction_for: string
          historical_value: number | null
          predicted_value: number
          upper_bound: number | null
          lower_bound: number | null
          model_id: string | null
          confidence_score: number | null
          created_at: string | null
        }
        Insert: {
          id?: string
          prediction_for: string
          historical_value?: number | null
          predicted_value: number
          upper_bound?: number | null
          lower_bound?: number | null
          model_id?: string | null
          confidence_score?: number | null
          created_at?: string | null
        }
        Update: {
          id?: string
          prediction_for?: string
          historical_value?: number | null
          predicted_value?: number
          upper_bound?: number | null
          lower_bound?: number | null
          model_id?: string | null
          confidence_score?: number | null
          created_at?: string | null
        }
      }
      protocol_distribution: {
        Row: {
          id: string
          name: string
          value_pct: number
          packet_count: number | null
          byte_count: number | null
          sampled_at: string | null
        }
        Insert: {
          id?: string
          name: string
          value_pct: number
          packet_count?: number | null
          byte_count?: number | null
          sampled_at?: string | null
        }
        Update: {
          id?: string
          name?: string
          value_pct?: number
          packet_count?: number | null
          byte_count?: number | null
          sampled_at?: string | null
        }
      }
      alerts: {
        Row: {
          id: string
          title: string
          description: string | null
          severity: string
          status: string | null
          triggered_at: string | null
          resolved_at: string | null
          source_ip: unknown | null
          dest_ip: unknown | null
          anomaly_id: string | null
        }
        Insert: {
          id?: string
          title: string
          description?: string | null
          severity: string
          status?: string | null
          triggered_at?: string | null
          resolved_at?: string | null
          source_ip?: unknown | null
          dest_ip?: unknown | null
          anomaly_id?: string | null
        }
        Update: {
          id?: string
          title?: string
          description?: string | null
          severity?: string
          status?: string | null
          triggered_at?: string | null
          resolved_at?: string | null
          source_ip?: unknown | null
          dest_ip?: unknown | null
          anomaly_id?: string | null
        }
      }
      anomalies: {
        Row: {
          id: string
          detected_at: string | null
          source_ip: unknown | null
          dest_ip: unknown | null
          threat_type: string
          severity: string
          status: string | null
          confidence_score: number | null
          details: Json | null
          resolved_at: string | null
        }
        Insert: {
          id?: string
          detected_at?: string | null
          source_ip?: unknown | null
          dest_ip?: unknown | null
          threat_type: string
          severity: string
          status?: string | null
          confidence_score?: number | null
          details?: Json | null
          resolved_at?: string | null
        }
        Update: {
          id?: string
          detected_at?: string | null
          source_ip?: unknown | null
          dest_ip?: unknown | null
          threat_type?: string
          severity?: string
          status?: string | null
          confidence_score?: number | null
          details?: Json | null
          resolved_at?: string | null
        }
      }
      model_registry: {
        Row: {
          id: string
          name: string
          model_type: string
          version: string | null
          training_data: string | null
          mae_mbps: number | null
          rmse_mbps: number | null
          accuracy_percent: number | null
          is_production: boolean | null
          last_deployed_at: string | null
          created_at: string | null
        }
        Insert: {
          id?: string
          name: string
          model_type: string
          version?: string | null
          training_data?: string | null
          mae_mbps?: number | null
          rmse_mbps?: number | null
          accuracy_percent?: number | null
          is_production?: boolean | null
          last_deployed_at?: string | null
          created_at?: string | null
        }
        Update: {
          id?: string
          name?: string
          model_type?: string
          version?: string | null
          training_data?: string | null
          mae_mbps?: number | null
          rmse_mbps?: number | null
          accuracy_percent?: number | null
          is_production?: boolean | null
          last_deployed_at?: string | null
          created_at?: string | null
        }
      }
      gnn_datasets: {
        Row: {
          id: string
          run_id: string
          window_seconds: number | null
          prediction_horizons: number[] | null
          scenario_names: string[] | null
          total_windows: number | null
          dataset_path: string | null
          label_distribution: Json | null
          status: string | null
          started_at: string | null
          completed_at: string | null
          error_message: string | null
        }
        Insert: {
          id?: string
          run_id: string
          window_seconds?: number | null
          prediction_horizons?: number[] | null
          scenario_names?: string[] | null
          total_windows?: number | null
          dataset_path?: string | null
          label_distribution?: Json | null
          status?: string | null
          started_at?: string | null
          completed_at?: string | null
          error_message?: string | null
        }
        Update: {
          id?: string
          run_id?: string
          window_seconds?: number | null
          prediction_horizons?: number[] | null
          scenario_names?: string[] | null
          total_windows?: number | null
          dataset_path?: string | null
          label_distribution?: Json | null
          status?: string | null
          started_at?: string | null
          completed_at?: string | null
          error_message?: string | null
        }
      }
      realtime_metrics: {
        Row: {
          id: string
          metric_name: string
          metric_value: number
          unit: string | null
          sampled_at: string | null
        }
        Insert: {
          id?: string
          metric_name: string
          metric_value: number
          unit?: string | null
          sampled_at?: string | null
        }
        Update: {
          id?: string
          metric_name?: string
          metric_value?: number
          unit?: string | null
          sampled_at?: string | null
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      get_current_metrics: {
        Args: Record<string, never>
        Returns: {
          current_traffic_mbps: number
          active_connections: number
          anomaly_score_percent: number
          alerts_today: number
        }[]
      }
      get_alert_stats: {
        Args: Record<string, never>
        Returns: {
          total: number
          critical: number
          warnings: number
        }[]
      }
      get_historical_traffic: {
        Args: {
          bucket_type_filter?: string
          limit_count?: number
        }
        Returns: {
          bucket_start: string
          avg_traffic_mbps: number
          peak_traffic_mbps: number
        }[]
      }
    }
    Enums: {
      [_ in never]: never
    }
  }
}
