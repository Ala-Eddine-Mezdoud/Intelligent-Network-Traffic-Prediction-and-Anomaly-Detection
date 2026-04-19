"""Anomalies API routes using IDS classification model."""
import os
import random
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fastapi import APIRouter, Query

from app.schemas.anomalies import AnomalyItem, AnomaliesResponse

router = APIRouter(prefix="/anomalies", tags=["anomalies"])

# Load the IDS pipeline model once at startup
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "models", "ids_pipeline.pkl")
_model = None

# Class mapping from notebook training
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
    12: "Web Attack – Brute Force",
    13: "Web Attack – SQL Injection",
    14: "Web Attack – XSS",
}

# Severity mapping for different attack types
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
    "Web Attack – Brute Force": "High",
    "Web Attack – SQL Injection": "Critical",
    "Web Attack – XSS": "High",
}

# Features the model expects (extracted from error message)
TOP_FEATURES = [
    'Bwd Packet Length Mean', 'Bwd Packet Length Max', 'Idle Mean', 'PSH Flag Count',
    'Flow IAT Max', 'Fwd IAT Std', 'Packet Length Mean', 'Packet Length Variance',
    'min_seg_size_forward', 'Destination Port', 'Max Packet Length', 'Flow Duration',
    'Bwd Packet Length Min', 'Init_Win_bytes_forward', 'act_data_pkt_fwd', 'ACK Flag Count',
    'Flow IAT Std', 'FIN Flag Count', 'Total Fwd Packets', 'Min Packet Length',
    'Fwd Header Length', 'Fwd Packet Length Std', 'Bwd IAT Total', 'Flow IAT Mean',
    'Fwd Packet Length Mean', 'Fwd IAT Mean', 'Down/Up Ratio', 'Bwd Header Length',
    'Bwd IAT Max', 'Fwd Packet Length Max', 'Bwd IAT Std', 'Total Length of Fwd Packets',
    'Bwd Packets/s', 'Fwd PSH Flags', 'Fwd Packet Length Min', 'URG Flag Count',
    'Bwd IAT Mean', 'Init_Win_bytes_backward', 'Idle Std', 'Fwd IAT Min',
    'Flow IAT Min', 'Flow Packets/s', 'Bwd IAT Min', 'Active Mean', 'Active Max',
    'Active Min', 'Flow Bytes/s', 'Active Std', 'RST Flag Count', 'Fwd URG Flags'
]


def load_model():
    """Lazy-load the IDS pipeline model."""
    global _model
    if _model is None:
        if os.path.exists(MODEL_PATH):
            loaded = joblib.load(MODEL_PATH)
            # Handle dict format: extract model from common keys
            if isinstance(loaded, dict):
                for key in ['model', 'pipeline', 'classifier', 'estimator', 'clf']:
                    if key in loaded:
                        _model = loaded[key]
                        break
                else:
                    # If no recognized key, try the first value
                    _model = list(loaded.values())[0]
            else:
                _model = loaded
        else:
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
    return _model


def generate_mock_network_flows(n_flows: int = 20) -> pd.DataFrame:
    """Generate mock network flow data matching the model's expected features."""
    np.random.seed(42)
    flows = []

    for i in range(n_flows):
        is_attack = random.random() < 0.3

        if is_attack:
            base_flow = {
                # Features in model order
                'Bwd Packet Length Mean': random.uniform(50, 1000),
                'Bwd Packet Length Max': random.uniform(100, 2000),
                'Idle Mean': random.uniform(0, 1000000),
                'PSH Flag Count': random.choice([0, 1, 1, 1]),
                'Flow IAT Max': random.uniform(100, 10000000),
                'Fwd IAT Std': random.uniform(0, 500000),
                'Packet Length Mean': random.uniform(50, 1000),
                'Packet Length Variance': random.uniform(100, 100000),
                'min_seg_size_forward': random.uniform(0, 64),
                'Destination Port': random.choice([22, 23, 80, 443, 3389, 445, 21]),
                'Max Packet Length': random.uniform(100, 2000),
                'Flow Duration': random.uniform(1000, 10000000),
                'Bwd Packet Length Min': random.uniform(0, 100),
                'Init_Win_bytes_forward': random.uniform(100, 65535),
                'act_data_pkt_fwd': random.uniform(0, 5000),
                'ACK Flag Count': random.choice([0, 1, 1, 1]),
                'Flow IAT Std': random.uniform(10, 500000),
                'FIN Flag Count': random.choice([0, 0, 0, 1]),
                'Total Fwd Packets': random.uniform(10, 10000),
                'Min Packet Length': random.uniform(0, 100),
                'Fwd Header Length': random.uniform(20, 500),
                'Fwd Packet Length Std': random.uniform(10, 400),
                'Bwd IAT Total': random.uniform(0, 5000000),
                'Flow IAT Mean': random.uniform(10, 100000),
                'Fwd Packet Length Mean': random.uniform(50, 800),
                'Fwd IAT Mean': random.uniform(0, 100000),
                'Down/Up Ratio': random.uniform(0.1, 10),
                'Bwd Header Length': random.uniform(20, 500),
                'Bwd IAT Max': random.uniform(0, 5000000),
                'Fwd Packet Length Max': random.uniform(100, 1500),
                'Bwd IAT Std': random.uniform(0, 250000),
                'Total Length of Fwd Packets': random.uniform(500, 1000000),
                'Bwd Packets/s': random.uniform(1, 5000),
                'Fwd PSH Flags': random.choice([0, 1]),
                'Fwd Packet Length Min': random.uniform(0, 100),
                'URG Flag Count': random.choice([0, 0, 0, 1]),
                'Bwd IAT Mean': random.uniform(0, 50000),
                'Init_Win_bytes_backward': random.uniform(100, 65535),
                'Idle Std': random.uniform(0, 500000),
                'Fwd IAT Min': random.uniform(0, 1000),
                'Flow IAT Min': random.uniform(0, 1000),
                'Flow Packets/s': random.uniform(1, 10000),
                'Bwd IAT Min': random.uniform(0, 1000),
                'Active Mean': random.uniform(0, 100000),
                'Active Max': random.uniform(0, 500000),
                'Active Min': random.uniform(0, 10000),
                'Flow Bytes/s': random.uniform(100, 1000000),
                'Active Std': random.uniform(0, 50000),
                'RST Flag Count': random.choice([0, 0, 0, 1]),
                'Fwd URG Flags': random.choice([0, 0, 0, 1]),
            }
        else:
            base_flow = {
                'Bwd Packet Length Mean': random.uniform(50, 800),
                'Bwd Packet Length Max': random.uniform(50, 1500),
                'Idle Mean': random.uniform(0, 100000),
                'PSH Flag Count': random.choice([0, 0, 1, 1]),
                'Flow IAT Max': random.uniform(100, 1000000),
                'Fwd IAT Std': random.uniform(0, 50000),
                'Packet Length Mean': random.uniform(50, 800),
                'Packet Length Variance': random.uniform(0, 10000),
                'min_seg_size_forward': random.uniform(0, 64),
                'Destination Port': random.choice([80, 443, 53, 123, 25, 110, 143, 993, 995]),
                'Max Packet Length': random.uniform(50, 1500),
                'Flow Duration': random.uniform(100, 1000000),
                'Bwd Packet Length Min': random.uniform(0, 100),
                'Init_Win_bytes_forward': random.uniform(1000, 65535),
                'act_data_pkt_fwd': random.uniform(0, 100),
                'ACK Flag Count': random.choice([0, 1, 1, 1, 1]),
                'Flow IAT Std': random.uniform(0, 50000),
                'FIN Flag Count': random.choice([0, 0, 0, 0, 1]),
                'Total Fwd Packets': random.uniform(1, 100),
                'Min Packet Length': random.uniform(0, 100),
                'Fwd Header Length': random.uniform(20, 200),
                'Fwd Packet Length Std': random.uniform(0, 400),
                'Bwd IAT Total': random.uniform(0, 500000),
                'Flow IAT Mean': random.uniform(10, 10000),
                'Fwd Packet Length Mean': random.uniform(50, 800),
                'Fwd IAT Mean': random.uniform(0, 10000),
                'Down/Up Ratio': random.uniform(0.5, 2),
                'Bwd Header Length': random.uniform(20, 200),
                'Bwd IAT Max': random.uniform(0, 500000),
                'Fwd Packet Length Max': random.uniform(50, 1500),
                'Bwd IAT Std': random.uniform(0, 25000),
                'Total Length of Fwd Packets': random.uniform(50, 50000),
                'Bwd Packets/s': random.uniform(0.1, 500),
                'Fwd PSH Flags': random.choice([0, 0, 0, 1]),
                'Fwd Packet Length Min': random.uniform(0, 100),
                'URG Flag Count': 0,
                'Bwd IAT Mean': random.uniform(0, 5000),
                'Init_Win_bytes_backward': random.uniform(1000, 65535),
                'Idle Std': random.uniform(0, 50000),
                'Fwd IAT Min': random.uniform(0, 1000),
                'Flow IAT Min': random.uniform(0, 1000),
                'Flow Packets/s': random.uniform(0.1, 1000),
                'Bwd IAT Min': random.uniform(0, 1000),
                'Active Mean': random.uniform(0, 10000),
                'Active Max': random.uniform(0, 50000),
                'Active Min': random.uniform(0, 1000),
                'Flow Bytes/s': random.uniform(10, 100000),
                'Active Std': random.uniform(0, 5000),
                'RST Flag Count': random.choice([0, 0, 0, 0, 1]),
                'Fwd URG Flags': 0,
            }

        flows.append(base_flow)

    df = pd.DataFrame(flows)
    return df


def predict_anomalies(flow_data: pd.DataFrame) -> list[tuple[int, str, float]]:
    """Run network flows through IDS model to detect anomalies.

    Returns list of (predicted_class, class_name, confidence) tuples.
    """
    model = load_model()

    # Select only the top features the model was trained on
    available_features = [f for f in TOP_FEATURES if f in flow_data.columns]
    X = flow_data[available_features].fillna(0)

    # Make predictions
    predictions = model.predict(X)

    # Get prediction probabilities if available
    try:
        proba = model.predict_proba(X)
        confidences = [np.max(p) for p in proba]
    except:
        confidences = [0.85] * len(predictions)  # Default confidence

    results = []
    for pred, conf in zip(predictions, confidences):
        class_name = CLASS_NAMES.get(int(pred), "Unknown")
        results.append((int(pred), class_name, float(conf)))

    return results


def generate_anomalies_from_predictions() -> list[AnomalyItem]:
    """Generate anomalies by running mock data through the IDS model."""
    # Generate mock network flows
    flow_data = generate_mock_network_flows(n_flows=20)

    # Get predictions from model
    predictions = predict_anomalies(flow_data)

    # Convert predictions to AnomalyItems
    anomalies = []
    base_time = datetime.now()

    for i, (pred_class, class_name, confidence) in enumerate(predictions):
        # Skip benign traffic (class 0) - only return actual anomalies
        if class_name == "BENIGN":
            continue

        # Generate realistic IP addresses
        source_ip = f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        dest_ip = f"192.168.{random.randint(0, 255)}.{random.randint(1, 254)}"

        # Map to severity
        severity = ATTACK_SEVERITY.get(class_name, "Medium")

        # Generate timestamp (recent)
        timestamp = (base_time - timedelta(minutes=random.randint(1, 120))).strftime("%Y-%m-%d %H:%M:%S")

        # Determine status based on confidence
        status = "Ongoing" if confidence > 0.9 else "Resolved" if confidence < 0.7 else "Investigating"

        anomalies.append(AnomalyItem(
            id=str(i + 1),
            timestamp=timestamp,
            source_ip=source_ip,
            dest_ip=dest_ip,
            threat_type=class_name,
            severity=severity,
            status=status,
        ))

    # If no attacks detected, add a few simulated ones for demo
    if len(anomalies) == 0:
        anomalies = [
            AnomalyItem(
                id="1",
                timestamp=(base_time - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S"),
                source_ip="203.0.113.45",
                dest_ip="192.168.1.100",
                threat_type="PortScan",
                severity="Medium",
                status="Ongoing",
            ),
            AnomalyItem(
                id="2",
                timestamp=(base_time - timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M:%S"),
                source_ip="198.51.100.22",
                dest_ip="192.168.1.50",
                threat_type="DoS Hulk",
                severity="High",
                status="Resolved",
            ),
        ]

    return anomalies


def filter_anomalies(
    anomalies: list[AnomalyItem],
    search: str | None,
    severity: str | None,
) -> list[AnomalyItem]:
    filtered = anomalies

    if search:
        search_lower = search.lower()
        filtered = [
            a for a in filtered
            if search in a.source_ip
            or search in a.dest_ip
            or search_lower in a.threat_type.lower()
        ]

    if severity and severity != "all":
        filtered = [a for a in filtered if a.severity == severity]

    return filtered


@router.get("", response_model=AnomaliesResponse)
async def read_anomalies(
    search: str | None = Query(None, description="Search by IP or threat type"),
    severity: str | None = Query(None, description="Filter by severity: High, Medium, Low, or all"),
):
    all_anomalies = generate_anomalies_from_predictions()
    filtered = filter_anomalies(all_anomalies, search, severity)
    return AnomaliesResponse(anomalies=filtered, total=len(filtered))
