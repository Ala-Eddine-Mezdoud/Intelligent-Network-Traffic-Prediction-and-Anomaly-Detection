import statistics
from collections import Counter, deque
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

import numpy as np
import sys

# sklearn 0.22.x uses deprecated numpy type aliases removed in numpy 1.24+.
# Restore them before any sklearn import so predict() does not raise AttributeError.
np.float = float
np.int = int
np.complex = complex
np.object = object
np.bool = bool
np.str = str

# Shim for models pickled with numpy 2.x (numpy._core → numpy.core).
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

        errors = []

        if self._forecast_model_path.exists():
            try:
                self._forecast_model = joblib.load(self._forecast_model_path)
                logger.info("Loaded forecast model: %s", type(self._forecast_model).__name__)
            except Exception as exc:
                errors.append(f"forecast: {exc}")
                logger.warning("Could not load forecast model: %s", exc)

        if self._ids_model_path.exists():
            try:
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
                logger.info("Loaded IDS model: %s", type(self._ids_model).__name__)
            except Exception as exc:
                errors.append(f"ids: {exc}")
                logger.warning("Could not load IDS model: %s", exc)

        if errors:
            self._model_error = "; ".join(errors)
        elif self._ids_model is None and self._forecast_model is None:
            self._model_error = "No model files found; using heuristic inference"

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
        """Classify flows using heuristics + ML model (when loaded).

        Architecture: heuristics run ALWAYS; ML model acts as a supplementary
        layer only when both (a) the model confidence is high and (b) the flow
        does not land on a known-benign port range (iperf3 5200-5330).

        This avoids the two failure modes seen in practice:
          - ML model path used to short-circuit aggregate-DDoS detection.
          - Low-confidence ML predictions misclassifying legitimate iperf3 flows.
        """
        BRUTE_FORCE_PORTS = {21, 22, 23, 25, 3389}
        WEB_PORTS = {80, 443, 8080, 8443}
        # iperf3 server ports used by the simulation — never attack targets
        IPERF3_PORTS = set(range(5200, 5331))

        # ── pre-compute per-flow aggregates ────────────────────────────────
        dst_ports_by_src: dict = {}
        flows_to_service_port: dict = {}
        agg_byterate_to_dst: dict = {}

        for row in flow_rows:
            src      = str(row.get("Src IP", ""))
            dst      = str(row.get("Dst IP", ""))
            dst_port = self._safe_int(row.get("Dst Port", 0))
            br       = self._safe_float(row.get("Flow Byts/s", 0.0))

            if src and dst_port > 0:
                dst_ports_by_src.setdefault(src, set()).add(dst_port)
                if dst_port in BRUTE_FORCE_PORTS:
                    key = (src, dst_port)
                    flows_to_service_port[key] = flows_to_service_port.get(key, 0) + 1
            # Exclude iperf3 simulation ports from the DDoS aggregate — TCP iperf3
            # ignores the -b rate hint and saturates at wire speed, causing the
            # aggregate to dwarf the detection threshold in normal simulation.
            if dst and dst_port not in IPERF3_PORTS:
                agg_byterate_to_dst[dst] = agg_byterate_to_dst.get(dst, 0.0) + br

        # DDoS threshold: aggregate byte-rate (excluding known-benign iperf3 ports)
        # >= 50 MB/s = 400 Mbps at a single destination.
        # Real DDoS in simulation uses hping3/scapy which generates thousands of
        # tiny packets per second at non-iperf3 ports; the aggregate easily crosses
        # this bar while normal iperf3 flows (all on ports 5201-5330) are excluded.
        DDOS_AGG_THRESHOLD = 50_000_000.0
        ddos_victims = {
            dst for dst, rate in agg_byterate_to_dst.items()
            if rate >= DDOS_AGG_THRESHOLD
        }

        # ── optional ML predictions (supplementary only) ───────────────────
        ml_preds = None
        ml_confs = None
        if self._ids_model is not None and pd is not None and flow_rows:
            try:
                features = self._build_ids_features(flow_rows)
                if features is not None:
                    raw_preds = self._ids_model.predict(features)
                    confs = [0.75] * len(raw_preds)
                    if hasattr(self._ids_model, "predict_proba"):
                        probs = self._ids_model.predict_proba(features)
                        confs = [float(np.max(r)) for r in probs]
                    ml_preds = raw_preds
                    ml_confs = confs
            except Exception as exc:
                logger.debug("ML IDS prediction skipped: %s", exc)

        # ── per-flow classification ────────────────────────────────────────
        anomalies = []
        suspicious_count = 0
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for idx, row in enumerate(flow_rows, start=1):
            pkt_rate  = self._safe_float(row.get("Flow Pkts/s"))
            byte_rate = self._safe_float(row.get("Flow Byts/s"))
            dst_port  = self._safe_int(row.get("Dst Port", 0))
            duration  = self._safe_float(row.get("Flow Duration", 0.0))
            src_ip    = str(row.get("Src IP", "0.0.0.0"))
            dst_ip    = str(row.get("Dst IP", "0.0.0.0"))
            label     = str(row.get("Label", "")).strip()

            is_suspicious = False
            threat_type   = f"IDS: {attack_hint}" if attack_hint else "IDS: Malicious Flow"
            severity      = "Medium"
            confidence    = 0.75

            # P1: labelled attacker IP — only during active attack simulations.
            # attack_hint is None during normal-sim IDS snapshots; in that context
            # the reserved attacker hosts (h1_iot, h2_cam) run legitimate iperf3
            # traffic and must NOT be flagged as malicious.
            if label == "MALICIOUS_SIM" and attack_hint is not None:
                is_suspicious = True
                threat_type   = f"IDS: Simulated Attack ({attack_hint})"
                severity  = "High"
                confidence = 0.90

            # P2: aggregate multi-source DDoS flood (non-iperf3 ports only).
            # Gate on per-flow rate > 1 MB/s (8 Mbps).  iperf3 test flows are
            # already excluded from ddos_victims (they saturate at wire speed
            # but are not attacks).
            elif (dst_ip in ddos_victims and byte_rate > 1_000_000.0
                  and dst_port not in IPERF3_PORTS):
                is_suspicious = True
                threat_type   = "IDS: DDoS/DoS — Multi-Source Flood"
                severity      = "High"
                confidence    = 0.88

            # P3: single-source extreme rate (>400 Mbps per flow, non-iperf3)
            elif byte_rate > 50_000_000.0 and dst_port not in IPERF3_PORTS:
                is_suspicious = True
                threat_type   = "IDS: DDoS/DoS — High Volume"
                severity      = "High"
                confidence    = 0.85

            # P4: tiny-packet flood (amplification / reflection)
            elif pkt_rate > 5000.0:
                is_suspicious = True
                threat_type   = "IDS: DDoS/DoS — High Packet Rate"
                severity      = "High"
                confidence    = 0.82

            # P5: port scan (8+ distinct dst ports from one source)
            elif len(dst_ports_by_src.get(src_ip, set())) >= 8:
                is_suspicious = True
                threat_type   = "IDS: Port Scan"
                severity      = "Medium"
                confidence    = 0.80

            # P6: brute-force (5+ flows to auth port from same source)
            elif dst_port in BRUTE_FORCE_PORTS:
                key = (src_ip, dst_port)
                if flows_to_service_port.get(key, 0) >= 5:
                    is_suspicious = True
                    port_name     = {
                        21: "FTP", 22: "SSH", 23: "Telnet",
                        25: "SMTP", 3389: "RDP",
                    }.get(dst_port, str(dst_port))
                    threat_type   = f"IDS: Brute Force ({port_name})"
                    severity      = "High"
                    confidence    = 0.82

            # P7: HTTP flood (elevated rate to web port)
            elif dst_port in WEB_PORTS and pkt_rate > 200.0:
                is_suspicious = True
                threat_type   = "IDS: HTTP Flood"
                severity      = "Medium"
                confidence    = 0.75

            # P8: Slowloris (long-lived, near-zero rate to web port)
            elif dst_port in WEB_PORTS and duration > 10.0 and byte_rate < 500.0:
                is_suspicious = True
                threat_type   = "IDS: Slow DoS (Slowloris)"
                severity      = "Medium"
                confidence    = 0.70

            # P9: ML model — supplementary, high-confidence only.
            # Require 0.90 confidence globally; 0.97 for iperf3 ports to
            # prevent misclassifying legitimate high-bandwidth test flows.
            elif ml_preds is not None:
                pred       = ml_preds[idx - 1]
                conf       = ml_confs[idx - 1]
                class_name = CLASS_NAMES.get(int(pred), "Unknown")
                in_iperf3  = dst_port in IPERF3_PORTS
                threshold  = 0.97 if in_iperf3 else 0.90

                if class_name != "BENIGN" and conf >= threshold:
                    is_suspicious = True
                    threat_type   = class_name
                    severity      = ATTACK_SEVERITY.get(class_name, "Medium")
                    confidence    = conf

            if is_suspicious:
                suspicious_count += 1
                anomalies.append({
                    "id": f"n-{idx:03d}",
                    "timestamp": ts,
                    "source_ip": src_ip,
                    "dest_ip": dst_ip,
                    "threat_type": threat_type,
                    "severity": severity,
                    "status": "Ongoing" if confidence >= 0.85 else "Investigating",
                    "confidence": round(float(confidence), 4),
                })

        return suspicious_count, anomalies

    def _build_predictions(self):
        now = datetime.now()
        history_bytes = list(self._traffic_history_bytes)

        # No data yet — return empty so the frontend shows nothing rather than
        # fabricating random values that would mislead the user.
        if len(history_bytes) < 2:
            return []

        # Each window in _traffic_history_bytes was appended once per infer() call.
        # Calls arrive every ~30 s (full sim pcap cycle) or ~90 s (normal sim IDS
        # snapshot), so we label each historical point at 30-second intervals back
        # from "now" for a consistent x-axis regardless of the actual cadence.
        WINDOW_S = 30
        history_mbps = [(v * 8.0 / 1_000_000.0) / WINDOW_S for v in history_bytes]

        if self._forecast_model is not None and len(history_bytes) >= 12:
            past_bytes = list(self._traffic_history_bytes)[-12:]
            past_mbps  = history_mbps[-12:]

            result = []
            n = len(past_mbps)
            for i, val in enumerate(past_mbps):
                offset_s = (n - i) * WINDOW_S
                result.append({
                    "time": (now - timedelta(seconds=offset_s)).strftime("%H:%M:%S"),
                    "historical": round(val, 2),
                    "predicted": None,
                })

            # Autoregressive forecast: feed model its own predictions back
            window = list(past_bytes)
            for i in range(1, 13):
                try:
                    X_pred   = np.array(window[-12:], dtype=np.float64).reshape(1, -1)
                    nb       = float(self._forecast_model.predict(X_pred)[0])
                    next_bytes = max(nb, 0.0)
                except Exception:
                    next_bytes = window[-1]
                next_mbps = max(0.5, (next_bytes * 8.0 / 1_000_000.0) / WINDOW_S)
                result.append({
                    "time": (now + timedelta(seconds=i * WINDOW_S)).strftime("%H:%M:%S"),
                    "historical": None,
                    "predicted": round(next_mbps, 2),
                    "upper":     round(next_mbps * 1.15, 2),
                    "lower":     round(next_mbps * 0.85, 2),
                })
                window.append(next_bytes)
            return result

        # Fallback: model not loaded or fewer than 12 history windows.
        # Show what history we have, plus a short trend projection (next 6 steps).
        recent = history_mbps[-6:] if len(history_mbps) >= 6 else history_mbps
        avg    = statistics.mean(recent)
        trend  = (recent[-1] - recent[0]) / max(len(recent) - 1, 1)

        result = []
        n = len(history_mbps)
        for i, val in enumerate(history_mbps):
            offset_s = (n - i) * WINDOW_S
            result.append({
                "time": (now - timedelta(seconds=offset_s)).strftime("%H:%M:%S"),
                "historical": round(val, 1),
                "predicted": None,
            })
        for idx in range(1, 7):
            pred = max(0.5, avg + trend * idx)
            result.append({
                "time": (now + timedelta(seconds=idx * WINDOW_S)).strftime("%H:%M:%S"),
                "historical": None,
                "predicted": round(pred, 1),
                "upper": round(pred * 1.12, 1),
                "lower": round(pred * 0.88, 1),
            })
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
