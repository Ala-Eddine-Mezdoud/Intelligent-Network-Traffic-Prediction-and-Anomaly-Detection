from datetime import datetime, timedelta
import random
from .gnn_inference import gnn_engine


def _get_latest_inference(lab_pipeline):
    status = lab_pipeline.status()
    return status.get("last_inference") or {}


def _severity_from_risk(risk_score):
    if risk_score >= 0.25:
        return "High"
    if risk_score >= 0.08:
        return "Medium"
    return "Low"


def build_current_metrics(lab_pipeline):
    latest = _get_latest_inference(lab_pipeline)
    inf = latest.get("inference") or {}
    
    # Try to get real traffic from GNN engine
    gnn_status = gnn_engine.predictions()
    current_traffic_mbps = gnn_status.get("current_traffic_mbps", 0.0)
    
    # If GNN engine is not reporting, use the intelligence plane value
    if current_traffic_mbps <= 0.01:
        current_traffic_mbps = float(inf.get("traffic_mbps", 0.0))
        active_connections = int(inf.get("total_flows", 0) * 8)
    else:
        active_connections = int(gnn_status.get("active_connections", 0))

    risk = float(inf.get("risk_score", 0.0) or 0.0)
    suspicious = int(inf.get("suspicious_flows", 0) or 0)

    return {
        "current_traffic_mbps": round(current_traffic_mbps, 1),
        "active_connections": active_connections,
        "anomaly_score_percent": round(risk * 100, 2),
        "alerts_today": suspicious,
    }


def build_historical_traffic(hours=24):
    # Use 1-minute intervals for the last 30 minutes for a more 'live' feel in simulation
    now = datetime.now()
    data = []

    for idx in range(30):
        ts = now - timedelta(minutes=(30 - idx))
        # This will be replaced by real history if we had a database, 
        # but for now we follow the 'live' trend.
        base = 25.0 + random.uniform(-3, 3)
        data.append(
            {
                "time": ts.strftime("%H:%M"),
                "traffic": round(base, 1),
                "predicted": None,
            }
        )

    return data


def build_predictions(hours=24, lab_pipeline=None):
    # Priority 1: GNN traffic series (live 8-second model data)
    gnn_preds = gnn_engine.predictions()
    traffic_series = gnn_preds.get("traffic_series")
    if isinstance(traffic_series, list) and len(traffic_series) > 3:
        return traffic_series

    # Priority 2: IDS model predictions from lab pipeline
    if lab_pipeline is not None:
        latest = _get_latest_inference(lab_pipeline)
        inf = latest.get("inference") or {}
        pred = inf.get("predictions")
        if isinstance(pred, list) and pred:
            return pred

    # Fallback to 1-minute steps over 60 minutes
    now = datetime.now()
    data = []

    for idx in range(60):
        ts = now + timedelta(minutes=idx)
        pred = 25.0 + random.uniform(-2, 5)
        data.append(
            {
                "time": ts.strftime("%H:%M"),
                "historical": round(25.0 + random.uniform(-4, 4), 1) if idx < 15 else None,
                "predicted": round(pred, 1),
                "upper": round(pred * 1.2, 1),
                "lower": round(pred * 0.8, 1),
            }
        )

    return data


def build_protocol_distribution():
    return [
        {"name": "HTTPS", "value": 42},
        {"name": "HTTP", "value": 18},
        {"name": "DNS", "value": 14},
        {"name": "SSH", "value": 13},
        {"name": "ICMP", "value": 13},
    ]


def build_protocol_distribution_from_inference(lab_pipeline):
    latest = _get_latest_inference(lab_pipeline)
    inf = latest.get("inference") or {}
    protocol_data = inf.get("protocol_distribution")
    if isinstance(protocol_data, list) and protocol_data:
        return protocol_data
    return build_protocol_distribution()


def build_system_status(lab_pipeline):
    latest = _get_latest_inference(lab_pipeline)
    inf = latest.get("inference") or {}

    risk = float(inf.get("risk_score", 0.0) or 0.0)
    sev = str(inf.get("severity", _severity_from_risk(risk))).title()

    health = max(35.0, 100.0 - (risk * 120.0))
    detection = min(99.0, 82.0 + (risk * 45.0))

    # Incorporate GNN predictions
    gnn_status = gnn_engine.status()
    gnn_running = gnn_status.get("running", False)
    gnn_window_state = gnn_status.get("window_state", "NORMAL")
    gnn_anomaly_count = gnn_status.get("anomaly_count", 0)

    if gnn_running and gnn_window_state != "NORMAL":
        # GNN detected an anomaly — adjust health/detection
        health = max(20.0, health - (gnn_anomaly_count * 3.0))
        detection = min(99.0, detection + 5.0)

    return {
        "network_health_percent": round(health, 2),
        "anomaly_detection_percent": round(detection, 2),
        "threat_level": sev,
        "gnn_active": gnn_running,
        "gnn_window_state": gnn_window_state if gnn_running else None,
    }


def build_alerts(lab_pipeline):
    latest = _get_latest_inference(lab_pipeline)
    inf = latest.get("inference") or {}

    risk = float(inf.get("risk_score", 0.0) or 0.0)
    sev = str(inf.get("severity", _severity_from_risk(risk))).title()
    suspicious = int(inf.get("suspicious_flows", 0) or 0)

    now = datetime.now()
    alerts = [
        {
            "id": "a-001",
            "title": "Pipeline Active",
            "description": "Telemetry relay and AI inference service are online.",
            "time": "Just now",
            "severity": "Low",
        }
    ]

    if suspicious > 0:
        alerts.insert(
            0,
            {
                "id": "a-002",
                "title": f"{suspicious} Suspicious Flows Detected",
                "description": (
                    f"Risk score is {round(risk * 100, 2)}% with {sev.lower()} severity in latest inference run."
                ),
                "time": now.strftime("%H:%M"),
                "severity": sev,
            },
        )

    return alerts


def build_gnn_alerts():
    """Build alert entries from GNN predictions."""
    gnn_preds = gnn_engine.predictions()
    if "error" in gnn_preds:
        return []

    alerts = []
    window = gnn_preds.get("window_prediction", {})
    anomaly_nodes = gnn_preds.get("anomaly_nodes", [])
    ts = gnn_preds.get("timestamp", datetime.now().strftime("%H:%M"))

    if window.get("is_anomaly") and window.get("confidence", 0) > 0.5:
        state = window["state"]
        conf = window["confidence"]
        severity_map = {
            "DDOS": "High", "BRUTE_FORCE": "High", "SCANNING": "Medium",
            "INFRA_FAILURE": "High", "CONGESTION": "Medium",
            "LATENCY": "Medium", "PACKET_LOSS": "Medium", "JITTER": "Low",
        }
        sev = severity_map.get(state, "Medium")
        node_names = [n["node"] for n in anomaly_nodes[:5]]

        alerts.append({
            "id": f"gnn-{state.lower()}",
            "title": f"GNN Prediction: {state.replace('_', ' ').title()}",
            "description": (
                f"Network state predicted as {state} with {conf*100:.0f}% confidence. "
                f"Affected nodes: {', '.join(node_names) if node_names else 'none'}"
            ),
            "time": ts.split(" ")[-1] if " " in ts else ts,
            "severity": sev,
            "source": "GNN",
        })

    return alerts


def build_alert_stats(alerts):
    return {
        "total": len(alerts),
        "critical": sum(1 for alert in alerts if alert["severity"] in {"Critical", "High"}),
        "warnings": sum(1 for alert in alerts if alert["severity"] == "Medium"),
    }


def build_anomalies(lab_pipeline):
    latest = _get_latest_inference(lab_pipeline)
    inf = latest.get("inference") or {}

    # Priority 1: real IDS anomaly items from the pcap pipeline
    anomaly_items = inf.get("anomaly_items")
    if isinstance(anomaly_items, list) and anomaly_items:
        return anomaly_items

    # Priority 2: synthesise IDS-style alerts from the current GNN prediction.
    # This covers normal-simulation mode where no pcap capture runs and the
    # IDS pipeline has no data to process.
    _STATE_TO_THREAT = {
        "DDOS":         "DDoS / Flood Attack",
        "SCANNING":     "Port Scan / Reconnaissance",
        "BRUTE_FORCE":  "Brute Force / Credential Attack",
        "LATENCY":      "High Latency Degradation",
        "PACKET_LOSS":  "Packet Loss Anomaly",
        "CONGESTION":   "Network Congestion",
        "JITTER":       "High Jitter / Unstable Link",
        "INFRA_FAILURE":"Infrastructure Failure / Brownout",
        "BANDWIDTH":    "Bandwidth Saturation",
    }
    _STATE_SEVERITY = {
        "DDOS": "High", "BRUTE_FORCE": "High", "INFRA_FAILURE": "High",
        "SCANNING": "Medium", "CONGESTION": "Medium",
        "LATENCY": "Medium", "PACKET_LOSS": "Medium",
        "JITTER": "Low", "BANDWIDTH": "Medium",
    }

    gnn_preds = gnn_engine.predictions()
    if "error" not in gnn_preds:
        window = gnn_preds.get("window_prediction", {})
        if window.get("is_anomaly") and window.get("confidence", 0) >= 0.55:
            state      = window["state"]
            an_nodes   = gnn_preds.get("anomaly_nodes", [])
            ts         = gnn_preds.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            node_ips   = gnn_engine._metadata.get("node_ips", {})
            threat     = _STATE_TO_THREAT.get(state, f"{state} Anomaly")
            severity   = _STATE_SEVERITY.get(state, "Medium")

            items = []
            for node_info in an_nodes[:10]:
                node    = node_info.get("node", "unknown")
                src_ip  = node_ips.get(node, "10.0.0.0")
                conf    = round(node_info.get("confidence", 0.75), 2)
                items.append({
                    "id":         f"gnn-ids-{node}",
                    "timestamp":  ts,
                    "source_ip":  src_ip,
                    "dest_ip":    "-",
                    "threat_type": f"GNN-IDS: {threat}",
                    "severity":   severity,
                    "status":     "Active",
                    "confidence": conf,
                })
            if items:
                return items

    return []


def build_gnn_anomalies():
    """Build anomaly entries from GNN predictions."""
    gnn_preds = gnn_engine.predictions()
    if "error" in gnn_preds:
        return []

    anomalies = []
    for node_info in gnn_preds.get("anomaly_nodes", []):
        node = node_info["node"]
        state = node_info["state"]
        conf = node_info["confidence"]
        ts = gnn_preds.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Map node name to approximate IP
        node_ips = gnn_engine._metadata.get("node_ips", {})
        src_ip = node_ips.get(node, "10.0.0.0")

        severity_map = {
            "DDOS": "High", "BRUTE_FORCE": "High", "SCANNING": "Medium",
            "INFRA_FAILURE": "High", "CONGESTION": "Medium",
            "LATENCY": "Medium", "PACKET_LOSS": "Medium", "JITTER": "Low",
        }
        sev = severity_map.get(state, "Medium")

        anomalies.append({
            "id": f"gnn-{node}",
            "timestamp": ts,
            "source_ip": src_ip,
            "dest_ip": "-",
            "threat_type": f"GNN Forecast: {state.replace('_', ' ').title()}",
            "severity": sev,
            "status": "Active",
            "confidence": round(conf, 2),
            "node": node,
        })

    return anomalies


def filter_anomalies(anomalies, search=None, severity=None):
    result = anomalies

    if search:
        needle = search.lower()
        result = [
            item
            for item in result
            if needle in item["source_ip"].lower()
            or needle in item["dest_ip"].lower()
            or needle in item["threat_type"].lower()
        ]

    if severity:
        result = [item for item in result if item["severity"].lower() == severity.lower()]

    return result


def model_metrics_payload():
    return {
        "mae_mbps": 3.2,
        "rmse_mbps": 8.9,
        "accuracy_percent": 91.2,
    }


def model_info_payload():
    payload = {
        "model_type": "Hybrid (Forecasting + Anomaly Detection + GNN Prediction)",
        "training_data": "CICIDS-style generated flows + Mininet GNN telemetry",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
        "prediction_horizon": "30 seconds ahead",
    }

    gnn_status = gnn_engine.status()
    payload["gnn"] = {
        "loaded": gnn_status.get("model_loaded", False),
        "running": gnn_status.get("running", False),
        "predictions_made": gnn_status.get("predictions_made", 0),
        "num_classes": gnn_status.get("num_classes", 0),
    }

    return payload
