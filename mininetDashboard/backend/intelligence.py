import statistics
from collections import Counter, deque
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

try:
    import joblib
    import pandas as pd
except Exception:
    joblib = None
    pd = None


CLASS_NAMES = {
    0: "BENIGN",
    1: "Bot",
    2: "DDoS",
    3: "DoS GoldenEye",
    4: "DoS Hulk",
    5: "DoS Slowhttptest",
    6: "DoS slowloris",
    7: "FTP-Patator",
    8: "Heartbleed",
    9: "Infiltration",
    10: "PortScan",
    11: "SSH-Patator",
    12: "Web Attack - Brute Force",
    13: "Web Attack - SQL Injection",
    14: "Web Attack - XSS",
}

ATTACK_SEVERITY = {
    "BENIGN": "Low",
    "Bot": "High",
    "DDoS": "High",
    "DoS GoldenEye": "High",
    "DoS Hulk": "High",
    "DoS Slowhttptest": "Medium",
    "DoS slowloris": "Medium",
    "FTP-Patator": "Medium",
    "Heartbleed": "Critical",
    "Infiltration": "Critical",
    "PortScan": "Medium",
    "SSH-Patator": "Medium",
    "Web Attack - Brute Force": "High",
    "Web Attack - SQL Injection": "Critical",
    "Web Attack - XSS": "High",
}

TOP_FEATURES = [
    "Bwd Packet Length Mean", "Bwd Packet Length Max", "Idle Mean", "PSH Flag Count",
    "Flow IAT Max", "Fwd IAT Std", "Packet Length Mean", "Packet Length Variance",
    "min_seg_size_forward", "Destination Port", "Max Packet Length", "Flow Duration",
    "Bwd Packet Length Min", "Init_Win_bytes_forward", "act_data_pkt_fwd", "ACK Flag Count",
    "Flow IAT Std", "FIN Flag Count", "Total Fwd Packets", "Min Packet Length",
    "Fwd Header Length", "Fwd Packet Length Std", "Bwd IAT Total", "Flow IAT Mean",
    "Fwd Packet Length Mean", "Fwd IAT Mean", "Down/Up Ratio", "Bwd Header Length",
    "Bwd IAT Max", "Fwd Packet Length Max", "Bwd IAT Std", "Total Length of Fwd Packets",
    "Bwd Packets/s", "Fwd PSH Flags", "Fwd Packet Length Min", "URG Flag Count",
    "Bwd IAT Mean", "Init_Win_bytes_backward", "Idle Std", "Fwd IAT Min",
    "Flow IAT Min", "Flow Packets/s", "Bwd IAT Min", "Active Mean", "Active Max",
    "Active Min", "Flow Bytes/s", "Active Std", "RST Flag Count", "Fwd URG Flags",
]


class IntelligencePlane:
    """Model-backed intelligence plane with heuristic fallback for real-time operation."""

    def __init__(self):
        repo_root = Path(__file__).resolve().parents[2]
        models_dir = repo_root / "models_api" / "models"
        self._forecast_model_path = models_dir / "forecasting_benign.pkl"
        self._ids_model_path = models_dir / "ids_pipeline.pkl"

        self._forecast_model = None
        self._ids_model = None
        self._model_error = None

        self._traffic_history_bytes = deque(maxlen=240)
        self._load_models()

    def _load_models(self):
        if joblib is None:
            self._model_error = "joblib/pandas unavailable; using heuristic inference"
            return

        try:
            if self._forecast_model_path.exists():
                self._forecast_model = joblib.load(self._forecast_model_path)

            if self._ids_model_path.exists():
                loaded = joblib.load(self._ids_model_path)
                if isinstance(loaded, dict):
                    for key in ["model", "pipeline", "classifier", "estimator", "clf"]:
                        if key in loaded:
                            self._ids_model = loaded[key]
                            break
                    if self._ids_model is None and loaded:
                        self._ids_model = list(loaded.values())[0]
                else:
                    self._ids_model = loaded
        except Exception as exc:
            self._model_error = str(exc)

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _safe_int(value, default=0):
        try:
            return int(value)
        except Exception:
            return default

    def _severity_from_risk(self, risk_score):
        if risk_score >= 0.25:
            return "High"
        if risk_score >= 0.08:
            return "Medium"
        return "Low"

    def _build_ids_features(self, flow_rows):
        rows = []
        for row in flow_rows:
            fwd_pkts = self._safe_float(row.get("Tot Fwd Pkts"))
            bwd_pkts = self._safe_float(row.get("Tot Bwd Pkts"))
            fwd_bytes = self._safe_float(row.get("TotLen Fwd Pkts"))
            bwd_bytes = self._safe_float(row.get("TotLen Bwd Pkts"))
            duration = max(self._safe_float(row.get("Flow Duration"), 0.0), 1e-6)
            total_pkts = max(fwd_pkts + bwd_pkts, 1.0)

            mapped = {
                "Bwd Packet Length Mean": bwd_bytes / max(bwd_pkts, 1.0),
                "Bwd Packet Length Max": self._safe_float(row.get("Pkt Len Max")),
                "Idle Mean": self._safe_float(row.get("Idle Mean")),
                "PSH Flag Count": 0.0,
                "Flow IAT Max": self._safe_float(row.get("Flow IAT Max")),
                "Fwd IAT Std": self._safe_float(row.get("Flow IAT Std")),
                "Packet Length Mean": self._safe_float(row.get("Pkt Len Mean")),
                "Packet Length Variance": self._safe_float(row.get("Pkt Len Std")) ** 2,
                "min_seg_size_forward": 20.0,
                "Destination Port": self._safe_float(row.get("Dst Port")),
                "Max Packet Length": self._safe_float(row.get("Pkt Len Max")),
                "Flow Duration": self._safe_float(row.get("Flow Duration")),
                "Bwd Packet Length Min": self._safe_float(row.get("Pkt Len Mean")),
                "Init_Win_bytes_forward": 0.0,
                "act_data_pkt_fwd": fwd_pkts,
                "ACK Flag Count": 0.0,
                "Flow IAT Std": self._safe_float(row.get("Flow IAT Std")),
                "FIN Flag Count": 0.0,
                "Total Fwd Packets": fwd_pkts,
                "Min Packet Length": self._safe_float(row.get("Pkt Len Mean")),
                "Fwd Header Length": 20.0,
                "Fwd Packet Length Std": self._safe_float(row.get("Pkt Len Std")),
                "Bwd IAT Total": self._safe_float(row.get("Flow IAT Mean")) * bwd_pkts,
                "Flow IAT Mean": self._safe_float(row.get("Flow IAT Mean")),
                "Fwd Packet Length Mean": fwd_bytes / max(fwd_pkts, 1.0),
                "Fwd IAT Mean": self._safe_float(row.get("Flow IAT Mean")),
                "Down/Up Ratio": bwd_pkts / max(fwd_pkts, 1.0),
                "Bwd Header Length": 20.0,
                "Bwd IAT Max": self._safe_float(row.get("Flow IAT Max")),
                "Fwd Packet Length Max": self._safe_float(row.get("Pkt Len Max")),
                "Bwd IAT Std": self._safe_float(row.get("Flow IAT Std")),
                "Total Length of Fwd Packets": fwd_bytes,
                "Bwd Packets/s": bwd_pkts / duration,
                "Fwd PSH Flags": 0.0,
                "Fwd Packet Length Min": self._safe_float(row.get("Pkt Len Mean")),
                "URG Flag Count": 0.0,
                "Bwd IAT Mean": self._safe_float(row.get("Flow IAT Mean")),
                "Init_Win_bytes_backward": 0.0,
                "Idle Std": self._safe_float(row.get("Idle Std")),
                "Fwd IAT Min": self._safe_float(row.get("Flow IAT Mean")),
                "Flow IAT Min": self._safe_float(row.get("Flow IAT Mean")),
                "Flow Packets/s": total_pkts / duration,
                "Bwd IAT Min": self._safe_float(row.get("Flow IAT Mean")),
                "Active Mean": self._safe_float(row.get("Active Mean")),
                "Active Max": self._safe_float(row.get("Active Mean")),
                "Active Min": self._safe_float(row.get("Active Mean")),
                "Flow Bytes/s": self._safe_float(row.get("Flow Byts/s")),
                "Active Std": self._safe_float(row.get("Active Std")),
                "RST Flag Count": 0.0,
                "Fwd URG Flags": 0.0,
            }

            rows.append({feature: self._safe_float(mapped.get(feature, 0.0)) for feature in TOP_FEATURES})

        if pd is None:
            return None
        return pd.DataFrame(rows)

    def _predict_anomalies(self, flow_rows):
        anomalies = []
        suspicious_count = 0

        if self._ids_model is not None and pd is not None and flow_rows:
            features = self._build_ids_features(flow_rows)
            predictions = self._ids_model.predict(features)
            confidences = [0.85] * len(predictions)

            if hasattr(self._ids_model, "predict_proba"):
                probs = self._ids_model.predict_proba(features)
                confidences = [float(np.max(row)) for row in probs]

            for idx, (row, pred, conf) in enumerate(zip(flow_rows, predictions, confidences), start=1):
                class_name = CLASS_NAMES.get(int(pred), "Unknown")
                heuristic_suspicious = (
                    str(row.get("Label", "")).strip() == "MALICIOUS_SIM"
                    or self._safe_float(row.get("Flow Pkts/s")) > 220.0
                    or self._safe_float(row.get("Flow Byts/s")) > 800000.0
                )
                model_suspicious = class_name != "BENIGN"

                if model_suspicious or heuristic_suspicious:
                    suspicious_count += 1
                    severity = ATTACK_SEVERITY.get(class_name, "Medium")
                    if heuristic_suspicious and class_name == "BENIGN":
                        class_name = "Traffic Anomaly"
                        severity = "Medium"

                    anomalies.append(
                        {
                            "id": f"n-{idx:03d}",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "source_ip": str(row.get("Src IP", "0.0.0.0")),
                            "dest_ip": str(row.get("Dst IP", "0.0.0.0")),
                            "threat_type": class_name,
                            "severity": severity,
                            "status": "Ongoing" if conf > 0.9 else "Investigating",
                            "confidence": round(float(conf), 4),
                        }
                    )

            return suspicious_count, anomalies

        for idx, row in enumerate(flow_rows, start=1):
            pkt_rate = self._safe_float(row.get("Flow Pkts/s"))
            byte_rate = self._safe_float(row.get("Flow Byts/s"))
            label = str(row.get("Label", "")).strip()
            if label == "MALICIOUS_SIM" or pkt_rate > 220.0 or byte_rate > 800000.0:
                suspicious_count += 1
                anomalies.append(
                    {
                        "id": f"n-{idx:03d}",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "source_ip": str(row.get("Src IP", "0.0.0.0")),
                        "dest_ip": str(row.get("Dst IP", "0.0.0.0")),
                        "threat_type": "Traffic Anomaly",
                        "severity": "Medium",
                        "status": "Investigating",
                        "confidence": 0.75,
                    }
                )

        return suspicious_count, anomalies

    def _build_predictions(self):
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        history_bytes = list(self._traffic_history_bytes)

        if len(history_bytes) < 2:
            base = 60.0
            return [
                {
                    "time": (now + timedelta(hours=idx)).strftime("%H:%M"),
                    "historical": base + (idx * 1.5) if idx < 12 else None,
                    "predicted": base + (idx * 2.0),
                    "upper": (base + (idx * 2.0)) * 1.12,
                    "lower": (base + (idx * 2.0)) * 0.88,
                }
                for idx in range(24)
            ]

        history_mbps = [val * 8.0 / 1_000_000.0 for val in history_bytes]

        if self._forecast_model is not None and len(history_bytes) >= 23:
            n_lags = 23
            past_values = list(history_bytes[-n_lags:])
            predictions_mbps = []
            upper = []
            lower = []

            for idx in range(24):
                ts = now + timedelta(hours=idx)
                features = {}
                for lag in range(1, n_lags + 1):
                    features[f"lag_{lag}"] = past_values[-lag]

                recent_3 = past_values[-3:]
                features["rolling_mean_3"] = float(np.mean(recent_3))
                features["rolling_std_3"] = float(np.std(recent_3))
                features["Hour"] = ts.hour
                features["DayOfWeek"] = ts.weekday()
                features["IsWeekend"] = 1 if ts.weekday() >= 5 else 0

                if pd is not None:
                    pred_log = float(self._forecast_model.predict(pd.DataFrame([features]))[0])
                else:
                    pred_log = 0.0

                pred_bytes = float(np.expm1(pred_log))
                pred_mbps = pred_bytes * 8.0 / 1_000_000.0
                band = pred_mbps * 0.15

                predictions_mbps.append(pred_mbps)
                upper.append(pred_mbps + band)
                lower.append(max(0.0, pred_mbps - band))

                past_values.append(pred_bytes)
                past_values.pop(0)

            result = []
            for idx in range(24):
                result.append(
                    {
                        "time": (now + timedelta(hours=idx)).strftime("%H:%M"),
                        "historical": round(history_mbps[-12 + idx], 1) if idx < 12 and len(history_mbps) >= 12 else None,
                        "predicted": round(predictions_mbps[idx], 1),
                        "upper": round(upper[idx], 1),
                        "lower": round(lower[idx], 1),
                    }
                )
            return result

        recent = history_mbps[-6:] if len(history_mbps) >= 6 else history_mbps
        avg = statistics.mean(recent)
        trend = (recent[-1] - recent[0]) / max(len(recent) - 1, 1)

        result = []
        for idx in range(24):
            pred = max(1.0, avg + trend * (idx + 1))
            result.append(
                {
                    "time": (now + timedelta(hours=idx)).strftime("%H:%M"),
                    "historical": round(history_mbps[-12 + idx], 1) if idx < 12 and len(history_mbps) >= 12 else None,
                    "predicted": round(pred, 1),
                    "upper": round(pred * 1.12, 1),
                    "lower": round(pred * 0.88, 1),
                }
            )
        return result

    def infer(self, flow_rows, capture_id):
        total = len(flow_rows)
        if total == 0:
            return {
                "capture_id": capture_id,
                "total_flows": 0,
                "suspicious_flows": 0,
                "risk_score": 0.0,
                "severity": "Low",
                "reasons": ["No flows decoded"],
                "anomaly_items": [],
                "protocol_distribution": [],
                "predictions": self._build_predictions(),
                "model_source": {
                    "ids_loaded": self._ids_model is not None,
                    "forecast_loaded": self._forecast_model is not None,
                    "error": self._model_error,
                },
            }

        suspicious_count, anomaly_items = self._predict_anomalies(flow_rows)
        risk_score = round(suspicious_count / total, 4)
        severity = self._severity_from_risk(risk_score)

        pkt_rates = [self._safe_float(row.get("Flow Pkts/s", 0.0)) for row in flow_rows]
        byte_rates = [self._safe_float(row.get("Flow Byts/s", 0.0)) for row in flow_rows]
        total_bytes = sum(
            self._safe_float(row.get("TotLen Fwd Pkts", 0.0)) + self._safe_float(row.get("TotLen Bwd Pkts", 0.0))
            for row in flow_rows
        )
        total_duration = max(
            sum(max(self._safe_float(row.get("Flow Duration", 0.0)), 0.0) for row in flow_rows),
            1.0,
        )

        self._traffic_history_bytes.append(total_bytes)

        protocol_counter = Counter()
        for row in flow_rows:
            proto = str(row.get("Protocol", "0"))
            if proto == "6":
                protocol_counter["TCP"] += 1
            elif proto == "17":
                protocol_counter["UDP"] += 1
            elif proto == "1":
                protocol_counter["ICMP"] += 1
            else:
                protocol_counter["Other"] += 1

        protocol_distribution = []
        for name, count in protocol_counter.items():
            protocol_distribution.append(
                {
                    "name": name,
                    "value": round((count / total) * 100.0, 2),
                }
            )

        reasons = [
            f"mean_pkt_rate={round(statistics.mean(pkt_rates), 3) if pkt_rates else 0}",
            f"mean_byte_rate={round(statistics.mean(byte_rates), 3) if byte_rates else 0}",
            f"traffic_mbps={round((total_bytes * 8.0 / 1_000_000.0) / total_duration, 3)}",
        ]

        return {
            "capture_id": capture_id,
            "total_flows": total,
            "suspicious_flows": suspicious_count,
            "risk_score": risk_score,
            "severity": severity,
            "reasons": reasons,
            "anomaly_items": anomaly_items,
            "protocol_distribution": protocol_distribution,
            "predictions": self._build_predictions(),
            "model_source": {
                "ids_loaded": self._ids_model is not None,
                "forecast_loaded": self._forecast_model is not None,
                "error": self._model_error,
            },
        }


intelligence_plane = IntelligencePlane()
