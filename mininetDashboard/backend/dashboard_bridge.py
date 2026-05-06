from datetime import datetime, timedelta


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

    risk = float(inf.get("risk_score", 0.0) or 0.0)
    suspicious = int(inf.get("suspicious_flows", 0) or 0)
    total = int(inf.get("total_flows", 0) or 0)

    current_traffic_mbps = round(80 + min(120, total * 0.15), 1)
    active_connections = max(150, total * 8)

    return {
        "current_traffic_mbps": current_traffic_mbps,
        "active_connections": active_connections,
        "anomaly_score_percent": round(risk * 100, 2),
        "alerts_today": suspicious,
    }


def build_historical_traffic(hours=24):
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    data = []

    for idx in range(hours):
        ts = now - timedelta(hours=(hours - idx))
        base = 45 + ((idx * 7) % 38)
        predicted = base + (4 if idx % 5 == 0 else -2)
        data.append(
            {
                "time": ts.strftime("%H:%M"),
                "traffic": round(base, 1),
                "predicted": round(predicted, 1),
            }
        )

    return data


def build_predictions(hours=24, lab_pipeline=None):
    if lab_pipeline is not None:
        latest = _get_latest_inference(lab_pipeline)
        inf = latest.get("inference") or {}
        pred = inf.get("predictions")
        if isinstance(pred, list) and pred:
            return pred

    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    data = []

    for idx in range(hours):
        ts = now + timedelta(hours=idx)
        pred = 70 + ((idx * 9) % 32)
        data.append(
            {
                "time": ts.strftime("%H:%M"),
                "historical": round(60 + ((idx * 5) % 24), 1) if idx < 10 else None,
                "predicted": round(pred, 1),
                "upper": round(pred * 1.12, 1),
                "lower": round(pred * 0.88, 1),
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

    return {
        "network_health_percent": round(health, 2),
        "anomaly_detection_percent": round(detection, 2),
        "threat_level": sev,
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


def build_alert_stats(alerts):
    return {
        "total": len(alerts),
        "critical": sum(1 for alert in alerts if alert["severity"] in {"Critical", "High"}),
        "warnings": sum(1 for alert in alerts if alert["severity"] == "Medium"),
    }


def build_anomalies(lab_pipeline):
    latest = _get_latest_inference(lab_pipeline)
    inf = latest.get("inference") or {}

    anomaly_items = inf.get("anomaly_items")
    if isinstance(anomaly_items, list) and anomaly_items:
        return anomaly_items

    suspicious = int(inf.get("suspicious_flows", 0) or 0)
    sev = str(inf.get("severity", "low")).title()

    anomalies = []
    for idx in range(max(1, suspicious)):
        anomalies.append(
            {
                "id": f"n-{idx + 1:03d}",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source_ip": f"10.10.1.{40 + idx}",
                "dest_ip": "172.16.1.20",
                "threat_type": "Traffic Anomaly",
                "severity": sev if suspicious > 0 else "Low",
                "status": "Investigating" if suspicious > 0 else "Resolved",
            }
        )

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
        "model_type": "Hybrid (Forecasting + Anomaly Detection)",
        "training_data": "CICIDS-style generated flows + simulated replay",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
        "prediction_horizon": "24 hours ahead",
    }

    return payload
