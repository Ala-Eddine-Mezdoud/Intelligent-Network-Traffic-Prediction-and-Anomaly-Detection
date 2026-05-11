"""
Build ids_pipeline.pkl and forecasting_benign.pkl on Python 3.8 + sklearn 0.22.x.

Run with:
    python3 models_api/build_models.py

Generates synthetic flow training data that matches the 50 TOP_FEATURES
produced by intelligence.py's _build_ids_features() method.
"""
import os
import sys
import glob
import random
import numpy as np

# sklearn 0.22.x uses deprecated numpy type aliases (np.float, np.int, etc.)
# that were removed in numpy 1.24+. Restore them before any sklearn import.
np.float = float
np.int = int
np.complex = complex
np.object = object
np.bool = bool
np.str = str

# Shim for models pickled on numpy 2.x (numpy._core → numpy.core)
try:
    import numpy.core as _core
    sys.modules["numpy._core"] = _core
except ImportError:
    pass

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "models_api", "models")
os.makedirs(OUT_DIR, exist_ok=True)

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

# Maps to the CLASS_NAMES in intelligence.py
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

rng = np.random.default_rng(42)


def _r(lo, hi, size=1):
    """Uniform random in [lo, hi)."""
    return rng.uniform(lo, hi, size=size)


def _make_flow(
    dst_port,
    fwd_pkt_len_mean, bwd_pkt_len_mean,
    fwd_pkts, bwd_pkts,
    duration_s,       # SECONDS — matches _build_flow_features() output from tshark
    byte_rate,        # bytes/s
    pkt_rate,         # pkts/s
    iat_mean_s,       # seconds — matches _build_ids_features() which reads raw tshark IAT
    down_up_ratio,
    pkt_len_std=None,
):
    """Build one feature vector matching the _build_ids_features() mapping.

    All time values must be in SECONDS because _build_flow_features() stores
    them in seconds (epoch-timestamp deltas from tshark) and _build_ids_features()
    passes them straight through without unit conversion.
    """
    if pkt_len_std is None:
        pkt_len_std = fwd_pkt_len_mean * 0.15

    iat_std = iat_mean_s * rng.uniform(0.1, 0.5)
    iat_max = iat_mean_s * rng.uniform(2.0, 8.0)
    iat_min = iat_mean_s * rng.uniform(0.05, 0.3)

    fwd_bytes = fwd_pkts * fwd_pkt_len_mean
    bwd_bytes = bwd_pkts * bwd_pkt_len_mean

    row = {
        "Bwd Packet Length Mean": float(bwd_pkt_len_mean),
        "Bwd Packet Length Max": bwd_pkt_len_mean * float(rng.uniform(1.1, 1.5)),
        "Idle Mean": 0.0,
        "PSH Flag Count": 0.0,
        "Flow IAT Max": float(iat_max),
        "Fwd IAT Std": float(iat_std),
        "Packet Length Mean": (fwd_pkt_len_mean + bwd_pkt_len_mean) / 2.0,
        "Packet Length Variance": float(pkt_len_std ** 2),
        "min_seg_size_forward": 20.0,
        "Destination Port": float(dst_port),
        "Max Packet Length": fwd_pkt_len_mean * float(rng.uniform(1.0, 1.4)),
        "Flow Duration": float(duration_s),          # SECONDS
        "Bwd Packet Length Min": bwd_pkt_len_mean * float(rng.uniform(0.5, 0.9)),
        "Init_Win_bytes_forward": 0.0,
        "act_data_pkt_fwd": float(fwd_pkts),
        "ACK Flag Count": 0.0,
        "Flow IAT Std": float(iat_std),
        "FIN Flag Count": 0.0,
        "Total Fwd Packets": float(fwd_pkts),
        "Min Packet Length": fwd_pkt_len_mean * float(rng.uniform(0.3, 0.7)),
        "Fwd Header Length": 20.0,
        "Fwd Packet Length Std": float(pkt_len_std),
        "Bwd IAT Total": float(iat_mean_s * bwd_pkts),  # seconds × count
        "Flow IAT Mean": float(iat_mean_s),              # SECONDS
        "Fwd Packet Length Mean": float(fwd_pkt_len_mean),
        "Fwd IAT Mean": float(iat_mean_s),
        "Down/Up Ratio": float(down_up_ratio),
        "Bwd Header Length": 20.0,
        "Bwd IAT Max": float(iat_max),
        "Fwd Packet Length Max": fwd_pkt_len_mean * float(rng.uniform(1.1, 1.5)),
        "Bwd IAT Std": float(iat_std),
        "Total Length of Fwd Packets": float(fwd_bytes),
        "Bwd Packets/s": float(bwd_pkts / max(duration_s, 1e-9)),  # pkts/s
        "Fwd PSH Flags": 0.0,
        "Fwd Packet Length Min": fwd_pkt_len_mean * float(rng.uniform(0.3, 0.7)),
        "URG Flag Count": 0.0,
        "Bwd IAT Mean": float(iat_mean_s),
        "Init_Win_bytes_backward": 0.0,
        "Idle Std": 0.0,
        "Fwd IAT Min": float(iat_min),
        "Flow IAT Min": float(iat_min),
        "Flow Packets/s": float(pkt_rate),
        "Bwd IAT Min": float(iat_min),
        "Active Mean": 0.0,
        "Active Max": 0.0,
        "Active Min": 0.0,
        "Flow Bytes/s": float(byte_rate),
        "Active Std": 0.0,
        "RST Flag Count": 0.0,
        "Fwd URG Flags": 0.0,
    }
    return [row[f] for f in TOP_FEATURES]


def _gen(class_id):
    """Return one (feature_row, label) pair for class_id.

    All time values use SECONDS to match the tshark-extracted flow features
    produced by _build_flow_features() in lab.py and consumed by
    _build_ids_features() in intelligence.py.
    """
    if class_id == 0:  # BENIGN — normal iperf3 TCP (3-15 Mbps)
        bw_bps = _r(3e6, 15e6)[0]
        dur_s = _r(25, 35)[0]
        pkt_len = _r(1200, 1460)[0]
        byte_rate = bw_bps / 8.0
        fwd_pkts = max(int(byte_rate * dur_s / pkt_len), 1)
        bwd_pkts = max(int(fwd_pkts * _r(0.02, 0.08)[0]), 1)
        iat_s = pkt_len / byte_rate  # seconds between packets
        row = _make_flow(
            dst_port=int(_r(5201, 5222)[0]),
            fwd_pkt_len_mean=pkt_len,
            bwd_pkt_len_mean=_r(40, 100)[0],
            fwd_pkts=fwd_pkts, bwd_pkts=bwd_pkts,
            duration_s=dur_s,
            byte_rate=byte_rate, pkt_rate=byte_rate / pkt_len,
            iat_mean_s=iat_s,
            down_up_ratio=bwd_pkts / fwd_pkts,
        )

    elif class_id == 1:  # Bot — periodic small C2 comms
        dur_s = _r(1, 30)[0]
        pkt_len = _r(200, 800)[0]
        byte_rate = _r(100, 10_000)[0]
        fwd_pkts = max(int(byte_rate * dur_s / pkt_len), 1)
        bwd_pkts = max(int(fwd_pkts * _r(0.3, 2.0)[0]), 1)
        iat_s = pkt_len / max(byte_rate, 1)
        row = _make_flow(
            dst_port=int(rng.choice([80, 443, 6667, 1080, 4444, 8080])),
            fwd_pkt_len_mean=pkt_len,
            bwd_pkt_len_mean=_r(200, 600)[0],
            fwd_pkts=fwd_pkts, bwd_pkts=bwd_pkts,
            duration_s=dur_s,
            byte_rate=byte_rate, pkt_rate=byte_rate / pkt_len,
            iat_mean_s=iat_s,
            down_up_ratio=bwd_pkts / fwd_pkts,
        )

    elif class_id == 2:  # DDoS — multi-source high-volume flood (15-50 Mbps per flow)
        bw_bps = _r(15e6, 50e6)[0]
        dur_s = _r(5, 20)[0]
        pkt_len = _r(100, 800)[0]
        byte_rate = bw_bps / 8.0
        fwd_pkts = max(int(byte_rate * dur_s / pkt_len), 1)
        bwd_pkts = max(int(fwd_pkts * _r(0.0, 0.02)[0]), 0)
        iat_s = pkt_len / byte_rate
        row = _make_flow(
            dst_port=int(rng.choice([80, 443, 5201])),
            fwd_pkt_len_mean=pkt_len,
            bwd_pkt_len_mean=_r(20, 80)[0],
            fwd_pkts=fwd_pkts, bwd_pkts=bwd_pkts,
            duration_s=dur_s,
            byte_rate=byte_rate, pkt_rate=byte_rate / pkt_len,
            iat_mean_s=iat_s,
            down_up_ratio=bwd_pkts / max(fwd_pkts, 1),
        )

    elif class_id == 3:  # DoS GoldenEye — HTTP Keep-Alive flood
        dur_s = _r(10, 120)[0]
        pkt_len = _r(400, 1200)[0]
        byte_rate = _r(10_000, 500_000)[0]
        fwd_pkts = max(int(byte_rate * dur_s / pkt_len), 1)
        bwd_pkts = max(int(fwd_pkts * _r(0.5, 1.5)[0]), 1)
        iat_s = pkt_len / byte_rate
        row = _make_flow(
            dst_port=int(rng.choice([80, 443])),
            fwd_pkt_len_mean=pkt_len,
            bwd_pkt_len_mean=_r(200, 800)[0],
            fwd_pkts=fwd_pkts, bwd_pkts=bwd_pkts,
            duration_s=dur_s,
            byte_rate=byte_rate, pkt_rate=byte_rate / pkt_len,
            iat_mean_s=iat_s,
            down_up_ratio=bwd_pkts / fwd_pkts,
        )

    elif class_id == 4:  # DoS Hulk — HTTP GET flood (high rate)
        dur_s = _r(5, 60)[0]
        pkt_len = _r(600, 1400)[0]
        byte_rate = _r(100_000, 2_000_000)[0]
        fwd_pkts = max(int(byte_rate * dur_s / pkt_len), 1)
        bwd_pkts = max(int(fwd_pkts * _r(0.5, 2.0)[0]), 1)
        iat_s = pkt_len / byte_rate
        row = _make_flow(
            dst_port=int(rng.choice([80, 443, 8080])),
            fwd_pkt_len_mean=pkt_len,
            bwd_pkt_len_mean=_r(300, 1000)[0],
            fwd_pkts=fwd_pkts, bwd_pkts=bwd_pkts,
            duration_s=dur_s,
            byte_rate=byte_rate, pkt_rate=byte_rate / pkt_len,
            iat_mean_s=iat_s,
            down_up_ratio=bwd_pkts / fwd_pkts,
        )

    elif class_id == 5:  # DoS Slowhttptest — slow body reads
        dur_s = _r(60, 600)[0]
        pkt_len = _r(100, 400)[0]
        byte_rate = _r(10, 500)[0]
        fwd_pkts = max(int(byte_rate * dur_s / pkt_len), 2)
        bwd_pkts = max(int(fwd_pkts * _r(0.5, 3.0)[0]), 1)
        iat_s = pkt_len / max(byte_rate, 1)
        row = _make_flow(
            dst_port=int(rng.choice([80, 443])),
            fwd_pkt_len_mean=pkt_len,
            bwd_pkt_len_mean=_r(100, 400)[0],
            fwd_pkts=fwd_pkts, bwd_pkts=bwd_pkts,
            duration_s=dur_s,
            byte_rate=byte_rate, pkt_rate=byte_rate / pkt_len,
            iat_mean_s=iat_s,
            down_up_ratio=bwd_pkts / fwd_pkts,
        )

    elif class_id == 6:  # DoS slowloris — very slow header trickle
        dur_s = _r(60, 600)[0]
        pkt_len = _r(40, 200)[0]
        byte_rate = _r(1, 200)[0]
        fwd_pkts = max(int(byte_rate * dur_s / max(pkt_len, 1)), 2)
        bwd_pkts = max(int(fwd_pkts * _r(0.1, 0.5)[0]), 0)
        iat_s = pkt_len / max(byte_rate, 1)
        row = _make_flow(
            dst_port=int(rng.choice([80, 443])),
            fwd_pkt_len_mean=pkt_len,
            bwd_pkt_len_mean=_r(40, 100)[0],
            fwd_pkts=fwd_pkts, bwd_pkts=bwd_pkts,
            duration_s=dur_s,
            byte_rate=byte_rate, pkt_rate=max(byte_rate / max(pkt_len, 1), 0.01),
            iat_mean_s=iat_s,
            down_up_ratio=bwd_pkts / max(fwd_pkts, 1),
        )

    elif class_id == 7:  # FTP-Patator — FTP brute force
        dur_s = _r(0.5, 5)[0]
        pkt_len = _r(100, 400)[0]
        byte_rate = _r(500, 20_000)[0]
        fwd_pkts = max(int(byte_rate * dur_s / pkt_len), 2)
        bwd_pkts = max(int(fwd_pkts * _r(0.5, 1.5)[0]), 1)
        iat_s = pkt_len / max(byte_rate, 1)
        row = _make_flow(
            dst_port=21,
            fwd_pkt_len_mean=pkt_len,
            bwd_pkt_len_mean=_r(100, 300)[0],
            fwd_pkts=fwd_pkts, bwd_pkts=bwd_pkts,
            duration_s=dur_s,
            byte_rate=byte_rate, pkt_rate=byte_rate / pkt_len,
            iat_mean_s=iat_s,
            down_up_ratio=bwd_pkts / fwd_pkts,
        )

    elif class_id == 8:  # Heartbleed — few malformed TLS packets, large bwd
        dur_s = _r(0.01, 0.5)[0]
        pkt_len = _r(60, 200)[0]
        fwd_pkts = int(_r(2, 10)[0])
        bwd_pkts = int(_r(2, 8)[0])
        byte_rate = (fwd_pkts * pkt_len) / max(dur_s, 1e-4)
        iat_s = dur_s / max(fwd_pkts, 1)
        row = _make_flow(
            dst_port=443,
            fwd_pkt_len_mean=pkt_len,
            bwd_pkt_len_mean=_r(100, 16_384)[0],
            fwd_pkts=fwd_pkts, bwd_pkts=bwd_pkts,
            duration_s=dur_s,
            byte_rate=byte_rate, pkt_rate=fwd_pkts / max(dur_s, 1e-4),
            iat_mean_s=iat_s,
            down_up_ratio=bwd_pkts / max(fwd_pkts, 1),
        )

    elif class_id == 9:  # Infiltration — stealthy exfil over common ports
        dur_s = _r(5, 120)[0]
        pkt_len = _r(200, 1000)[0]
        byte_rate = _r(500, 50_000)[0]
        fwd_pkts = max(int(byte_rate * dur_s / pkt_len), 2)
        bwd_pkts = max(int(fwd_pkts * _r(0.1, 0.4)[0]), 1)
        iat_s = pkt_len / max(byte_rate, 1)
        row = _make_flow(
            dst_port=int(rng.choice([443, 80, 8443, 4444])),
            fwd_pkt_len_mean=pkt_len,
            bwd_pkt_len_mean=_r(200, 800)[0],
            fwd_pkts=fwd_pkts, bwd_pkts=bwd_pkts,
            duration_s=dur_s,
            byte_rate=byte_rate, pkt_rate=byte_rate / pkt_len,
            iat_mean_s=iat_s,
            down_up_ratio=bwd_pkts / fwd_pkts,
        )

    elif class_id == 10:  # PortScan — SYN probes, random ports, very short duration
        dur_s = _r(0.0005, 0.5)[0]
        pkt_len = _r(40, 80)[0]
        fwd_pkts = int(_r(1, 3)[0])
        bwd_pkts = int(_r(0, 2)[0])
        byte_rate = (fwd_pkts * pkt_len) / max(dur_s, 1e-4)
        iat_s = dur_s / max(fwd_pkts, 1)
        row = _make_flow(
            dst_port=int(_r(1, 65535)[0]),
            fwd_pkt_len_mean=pkt_len,
            bwd_pkt_len_mean=_r(40, 80)[0],
            fwd_pkts=fwd_pkts, bwd_pkts=bwd_pkts,
            duration_s=dur_s,
            byte_rate=byte_rate, pkt_rate=fwd_pkts / max(dur_s, 1e-4),
            iat_mean_s=iat_s,
            down_up_ratio=bwd_pkts / max(fwd_pkts, 1),
        )

    elif class_id == 11:  # SSH-Patator — SSH brute force
        dur_s = _r(0.5, 10)[0]
        pkt_len = _r(200, 800)[0]
        byte_rate = _r(1_000, 50_000)[0]
        fwd_pkts = max(int(byte_rate * dur_s / pkt_len), 2)
        bwd_pkts = max(int(fwd_pkts * _r(0.5, 2.0)[0]), 1)
        iat_s = pkt_len / max(byte_rate, 1)
        row = _make_flow(
            dst_port=22,
            fwd_pkt_len_mean=pkt_len,
            bwd_pkt_len_mean=_r(100, 400)[0],
            fwd_pkts=fwd_pkts, bwd_pkts=bwd_pkts,
            duration_s=dur_s,
            byte_rate=byte_rate, pkt_rate=byte_rate / pkt_len,
            iat_mean_s=iat_s,
            down_up_ratio=bwd_pkts / fwd_pkts,
        )

    elif class_id == 12:  # Web Attack - Brute Force
        dur_s = _r(0.1, 5)[0]
        pkt_len = _r(300, 1000)[0]
        byte_rate = _r(1_000, 100_000)[0]
        fwd_pkts = max(int(byte_rate * dur_s / pkt_len), 2)
        bwd_pkts = max(int(fwd_pkts * _r(0.8, 2.0)[0]), 1)
        iat_s = pkt_len / max(byte_rate, 1)
        row = _make_flow(
            dst_port=int(rng.choice([80, 443, 8080, 8443])),
            fwd_pkt_len_mean=pkt_len,
            bwd_pkt_len_mean=_r(300, 1000)[0],
            fwd_pkts=fwd_pkts, bwd_pkts=bwd_pkts,
            duration_s=dur_s,
            byte_rate=byte_rate, pkt_rate=byte_rate / pkt_len,
            iat_mean_s=iat_s,
            down_up_ratio=bwd_pkts / fwd_pkts,
        )

    elif class_id == 13:  # Web Attack - SQL Injection
        dur_s = _r(0.05, 2)[0]
        pkt_len = _r(400, 1400)[0]
        byte_rate = _r(2_000, 200_000)[0]
        fwd_pkts = max(int(byte_rate * dur_s / pkt_len), 2)
        bwd_pkts = max(int(fwd_pkts * _r(1.0, 4.0)[0]), 1)
        iat_s = pkt_len / max(byte_rate, 1)
        row = _make_flow(
            dst_port=int(rng.choice([80, 443, 8080])),
            fwd_pkt_len_mean=pkt_len,
            bwd_pkt_len_mean=_r(500, 5_000)[0],
            fwd_pkts=fwd_pkts, bwd_pkts=bwd_pkts,
            duration_s=dur_s,
            byte_rate=byte_rate, pkt_rate=byte_rate / pkt_len,
            iat_mean_s=iat_s,
            down_up_ratio=bwd_pkts / fwd_pkts,
        )

    elif class_id == 14:  # Web Attack - XSS
        dur_s = _r(0.05, 2)[0]
        pkt_len = _r(300, 1200)[0]
        byte_rate = _r(1_000, 150_000)[0]
        fwd_pkts = max(int(byte_rate * dur_s / pkt_len), 2)
        bwd_pkts = max(int(fwd_pkts * _r(1.0, 3.0)[0]), 1)
        iat_s = pkt_len / max(byte_rate, 1)
        row = _make_flow(
            dst_port=int(rng.choice([80, 443, 8080])),
            fwd_pkt_len_mean=pkt_len,
            bwd_pkt_len_mean=_r(400, 2_000)[0],
            fwd_pkts=fwd_pkts, bwd_pkts=bwd_pkts,
            duration_s=dur_s,
            byte_rate=byte_rate, pkt_rate=byte_rate / pkt_len,
            iat_mean_s=iat_s,
            down_up_ratio=bwd_pkts / fwd_pkts,
        )
    else:
        return None, None

    return row, class_id


def generate_class(class_id, n):
    rows, labels = [], []
    for _ in range(n):
        row, label = _gen(class_id)
        if row is not None:
            rows.append(row)
            labels.append(label)
    return rows, labels


def build_ids_pipeline():
    print("Building ids_pipeline.pkl ...")

    # Samples per class — more BENIGN to reflect real-world imbalance
    counts = {
        0: 600,   # BENIGN
        1: 150,   # Bot
        2: 250,   # DDoS
        3: 150,   # DoS GoldenEye
        4: 150,   # DoS Hulk
        5: 120,   # DoS Slowhttptest
        6: 120,   # DoS slowloris
        7: 120,   # FTP-Patator
        8: 80,    # Heartbleed
        9: 80,    # Infiltration
        10: 200,  # PortScan
        11: 120,  # SSH-Patator
        12: 120,  # Web Attack - Brute Force
        13: 80,   # Web Attack - SQL Injection
        14: 80,   # Web Attack - XSS
    }

    all_rows, all_labels = [], []
    for cls_id, n in counts.items():
        rows, labels = generate_class(cls_id, n)
        all_rows.extend(rows)
        all_labels.extend(labels)
        print(f"  class {cls_id:2d} ({CLASS_NAMES[cls_id]:<30}): {len(rows)} samples")

    X = np.array(all_rows, dtype=np.float64)
    y = np.array(all_labels, dtype=np.int32)

    # Shuffle
    idx = rng.permutation(len(y))
    X, y = X[idx], y[idx]

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(
            n_estimators=100,
            max_depth=20,
            min_samples_leaf=2,
            n_jobs=-1,
            random_state=42,
        )),
    ])

    print(f"  Training on {len(y)} samples, {X.shape[1]} features ...")
    pipeline.fit(X, y)

    # Quick sanity check
    preds = pipeline.predict(X[:20])
    acc = np.mean(preds == y[:20])
    print(f"  Training accuracy (first 20): {acc:.2%}")

    out_path = os.path.join(OUT_DIR, "ids_pipeline.pkl")
    joblib.dump(pipeline, out_path, compress=0)
    print(f"  Saved: {out_path}")
    return pipeline


def build_forecast_model():
    print("Building forecasting_benign.pkl ...")

    # Load bytes_sent + bytes_recv per window from GNN tabular CSVs
    csv_glob = os.path.join(
        REPO_ROOT, "mininetDashboard", "captures", "gnn_datasets",
        "**", "tabular.csv",
    )
    csv_files = glob.glob(csv_glob, recursive=True)
    if not csv_files:
        csv_glob2 = os.path.join(REPO_ROOT, "ml_training", "data", "**", "tabular.csv")
        csv_files = glob.glob(csv_glob2, recursive=True)

    series = []
    for f in csv_files:
        try:
            df = pd.read_csv(f, usecols=["window_index", "bytes_sent", "bytes_recv"])
            # Aggregate bytes across all nodes per window
            agg = df.groupby("window_index")[["bytes_sent", "bytes_recv"]].sum()
            agg["total"] = agg["bytes_sent"] + agg["bytes_recv"]
            series.extend(agg["total"].tolist())
        except Exception as e:
            print(f"  Warning: could not load {f}: {e}")

    WINDOW = 12  # look-back: 12 × 8s = 96 s of history

    if len(series) < WINDOW + 10:
        print(f"  Insufficient real data ({len(series)} pts). Generating synthetic series.")
        # Synthesize a benign traffic series (Mbps-like values in bytes/window)
        t = np.linspace(0, 4 * np.pi, 2000)
        base = 18_000_000 + 4_000_000 * np.sin(t * 0.5)
        noise = rng.normal(0, 1_500_000, len(t))
        series = (base + noise).tolist()

    print(f"  Using {len(series)} data points from {len(csv_files)} CSV file(s).")

    # Build sliding-window regression dataset: predict step t+1 from t-W..t
    data = np.array(series, dtype=np.float64)
    X_fc, y_fc = [], []
    for i in range(WINDOW, len(data)):
        X_fc.append(data[i - WINDOW:i])
        y_fc.append(data[i])

    X_fc = np.array(X_fc)
    y_fc = np.array(y_fc)

    model = GradientBoostingRegressor(
        n_estimators=80,
        max_depth=4,
        learning_rate=0.1,
        random_state=42,
    )
    print(f"  Training on {len(y_fc)} sliding windows ...")
    model.fit(X_fc, y_fc)

    # Sanity check
    sample_pred = model.predict(X_fc[:5])
    sample_true = y_fc[:5]
    rel_err = np.mean(np.abs(sample_pred - sample_true) / np.maximum(np.abs(sample_true), 1))
    print(f"  Mean relative error (first 5): {rel_err:.2%}")

    out_path = os.path.join(OUT_DIR, "forecasting_benign.pkl")
    joblib.dump(model, out_path, compress=0)
    print(f"  Saved: {out_path}")
    return model


if __name__ == "__main__":
    build_ids_pipeline()
    print()
    build_forecast_model()
    print("\nDone. Both models saved to", OUT_DIR)
