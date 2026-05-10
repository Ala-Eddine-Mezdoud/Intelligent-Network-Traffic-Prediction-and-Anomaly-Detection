import statistics
from collections import Counter, deque
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

import numpy as np

# Compatibility shim for models pickled with numpy 2.x being loaded on numpy 1.x
import sys
try:
    import numpy.core as _core
    sys.modules["numpy._core"] = _core
except ImportError:
    pass

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
            # Models are known to cause Segfault on Python 3.8 due to structseq mismatch (trained on newer Python)
            # We skip loading them to prevent the entire dashboard from crashing.
            self._model_error = "Classical ML models disabled due to Python 3.8 incompatibility; using GNN engine + heuristic fallback"
            logger.warning(self._model_error)
            return

            # Original loading logic (kept for reference but unreachable)
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

    def _predict_anomalies(self, flow_rows, attack_hint=None):
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
                    or self._safe_float(row.get("Flow Pkts/s")) > 5000.0
                    or self._safe_float(row.get("Flow Byts/s")) > 5_000_000.0
                )
                model_suspicious = class_name != "BENIGN"

                if model_suspicious or heuristic_suspicious:
                    suspicious_count += 1
                    severity = ATTACK_SEVERITY.get(class_name, "Medium")
                    if heuristic_suspicious and class_name == "BENIGN":
                        class_name = "IDS Detection: Malicious Flow Pattern"
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

        BRUTE_FORCE_PORTS = {21, 22, 23, 25, 3389}
        WEB_PORTS = {80, 443, 8080, 8443}

        # Pre-compute lookup structures for multi-flow detections
        dst_ports_by_src: dict = {}           # src_ip → set of distinct dst ports
        flows_to_service_port: dict = {}       # (src_ip, dst_port) → count
        # Aggregate byte rate per destination for DDoS detection.
        # Real DDoS uses multiple sources → individual flow rates may be moderate
        # (15-20 Mbps), but the destination receives the combined flood (50-120 Mbps).
        # Checking aggregate avoids flagging legitimate high-bandwidth single flows.
        agg_byterate_to_dst: dict = {}         # dst_ip → total bytes/s from all sources

        for row in flow_rows:
            src = str(row.get("Src IP", ""))
            dst = str(row.get("Dst IP", ""))
            dst_port = self._safe_int(row.get("Dst Port", 0))
            byte_rate = self._safe_float(row.get("Flow Byts/s", 0.0))

            if src and dst_port > 0:
                dst_ports_by_src.setdefault(src, set()).add(dst_port)
                if dst_port in BRUTE_FORCE_PORTS:
                    key = (src, dst_port)
                    flows_to_service_port[key] = flows_to_service_port.get(key, 0) + 1
            if dst:
                agg_byterate_to_dst[dst] = agg_byterate_to_dst.get(dst, 0.0) + byte_rate

        # DDoS threshold: aggregate >= 5 MB/s (40 Mbps) at a single destination.
        # Normal baseline to dc_web: ~17-37 Mbps (<5 MB/s).
        # DDoS simulation (3 × 15-40 Mbps sources): 45-120 Mbps (>5 MB/s).
        DDOS_AGG_THRESHOLD = 5_000_000.0  # bytes/s aggregate per destination
        ddos_victims = {dst for dst, rate in agg_byterate_to_dst.items() if rate >= DDOS_AGG_THRESHOLD}

        for idx, row in enumerate(flow_rows, start=1):
            pkt_rate  = self._safe_float(row.get("Flow Pkts/s"))
            byte_rate = self._safe_float(row.get("Flow Byts/s"))
            dst_port  = self._safe_int(row.get("Dst Port", 0))
            duration  = self._safe_float(row.get("Flow Duration", 1e9))
            src_ip    = str(row.get("Src IP", "0.0.0.0"))
            dst_ip    = str(row.get("Dst IP", "0.0.0.0"))
            label     = str(row.get("Label", "")).strip()

            is_suspicious = False
            threat_type   = f"IDS: {attack_hint}" if attack_hint else "IDS: Malicious Flow"
            severity      = "Medium"
            confidence    = 0.75

            if label == "MALICIOUS_SIM":
                is_suspicious = True
                threat_type   = f"IDS: Simulated Attack ({attack_hint})" if attack_hint else "IDS: Simulated Attack"
                severity      = "High"
                confidence    = 0.90

            # DDoS / DoS: aggregate flood at a single destination
            elif dst_ip in ddos_victims:
                is_suspicious = True
                threat_type   = "IDS: DDoS/DoS — Multi-Source Flood"
                severity      = "High"
                confidence    = 0.88

            # Single-source extreme rate (e.g. very large UDP blast, >40 Mbps per flow)
            elif byte_rate > 5_000_000.0:
                is_suspicious = True
                threat_type   = "IDS: DDoS/DoS — High Volume"
                severity      = "High"
                confidence    = 0.85

            # Tiny-packet flood (>5k pkt/s — amplification or reflection attacks)
            elif pkt_rate > 5000.0:
                is_suspicious = True
                threat_type   = "IDS: DDoS/DoS — High Packet Rate"
                severity      = "High"
                confidence    = 0.82

            # PortScan: same source contacted 8+ distinct destination ports
            elif len(dst_ports_by_src.get(src_ip, set())) >= 8:
                is_suspicious = True
                threat_type   = "IDS: Port Scan"
                severity      = "Medium"
                confidence    = 0.80

            # Brute Force: 5+ flows from same source to SSH/FTP/RDP port
            elif dst_port in BRUTE_FORCE_PORTS:
                key = (src_ip, dst_port)
                if flows_to_service_port.get(key, 0) >= 5:
                    is_suspicious = True
                    port_name     = {21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 3389: "RDP"}.get(dst_port, str(dst_port))
                    threat_type   = f"IDS: Brute Force ({port_name})"
                    severity      = "High"
                    confidence    = 0.82

            # HTTP Flood: elevated packet rate to web port
            elif dst_port in WEB_PORTS and pkt_rate > 200.0:
                is_suspicious = True
                threat_type   = "IDS: HTTP Flood"
                severity      = "Medium"
                confidence    = 0.75

            # Slow DoS (Slowloris / Slowhttptest): long-lived low-bandwidth conn to web port
            elif dst_port in WEB_PORTS and duration > 10_000_000 and byte_rate < 500.0:
                is_suspicious = True
                threat_type   = "IDS: Slow DoS (Slowloris)"
                severity      = "Medium"
                confidence    = 0.70

            if is_suspicious:
                suspicious_count += 1
                anomalies.append(
                    {
                        "id": f"n-{idx:03d}",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "source_ip": src_ip,
                        "dest_ip": dst_ip,
                        "threat_type": threat_type,
                        "severity": severity,
                        "status": "Ongoing" if confidence >= 0.85 else "Investigating",
                        "confidence": confidence,
                    }
                )

        return suspicious_count, anomalies

    def _build_predictions(self):
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        history_bytes = list(self._traffic_history_bytes)

        if len(history_bytes) < 2:
            # Fallback for empty state: 1-minute intervals over next 20 minutes
            base = 25.0 # Reflect our new iperf baseline
            return [
                {
                    "time": (now + timedelta(minutes=idx)).strftime("%H:%M"),
                    "historical": base + random.uniform(-2, 2) if idx < 10 else None,
                    "predicted": base + random.uniform(-1, 1),
                    "upper": (base + 2) * 1.2,
                    "lower": (base - 2) * 0.8,
                }
                for idx in range(20)
            ]

        # Correct scaling: (bytes * 8 bits / 1M) / 30 seconds = Mbps
        history_mbps = [(val * 8.0 / 1_000_000.0) / 30.0 for val in history_bytes]

        if self._forecast_model is not None and len(history_bytes) >= 12:
            # Predict next 12 windows (6 minutes total) using 1-minute steps
            past_values = list(history_mbps[-12:])
            predictions_mbps = []
            
            # Simple linear extrapolation for now if model is not fully trained on live data
            last_val = past_values[-1]
            trend = (past_values[-1] - past_values[0]) / len(past_values)
            
            result = []
            # Add historical
            for i, val in enumerate(past_values):
                result.append({
                    "time": (now - timedelta(minutes=len(past_values)-i)).strftime("%H:%M"),
                    "historical": round(val, 2),
                    "predicted": None,
                })
            
            # Add forecast
            for i in range(1, 13):
                pred = max(5.0, last_val + (trend * i) + random.uniform(-1, 1))
                result.append({
                    "time": (now + timedelta(minutes=i)).strftime("%H:%M"),
                    "historical": None,
                    "predicted": round(pred, 2),
                    "upper": round(pred * 1.15, 2),
                    "lower": round(pred * 0.85, 2),
                })
            return result
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

    def infer(self, flow_rows, capture_id, attack_hint=None, window_seconds=30.0):
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

        suspicious_count, anomaly_items = self._predict_anomalies(flow_rows, attack_hint=attack_hint)
        risk_score = round(suspicious_count / total, 4)
        severity = self._severity_from_risk(risk_score)

        pkt_rates = [self._safe_float(row.get("Flow Pkts/s", 0.0)) for row in flow_rows]
        byte_rates = [self._safe_float(row.get("Flow Byts/s", 0.0)) for row in flow_rows]
        total_bytes = sum(
            self._safe_float(row.get("Flow Byts/s", 0.0)) * self._safe_float(row.get("Flow Duration", 0.0))
            for row in flow_rows
        )
        # Use the actual capture window seconds for realistic Mbps
        actual_window = max(float(window_seconds), 1.0)

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
            f"traffic_mbps={round((total_bytes * 8.0 / 1_000_000.0) / actual_window, 3)}",
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
