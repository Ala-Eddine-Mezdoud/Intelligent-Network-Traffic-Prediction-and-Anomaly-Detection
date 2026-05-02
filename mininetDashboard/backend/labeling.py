"""Predictive label generation for GNN training data.

Annotates each time window with both current-state and future-state labels
so the GNN learns to predict anomalies before they fully manifest.
"""

from typing import Any, Dict, List, Optional

from .telemetry import GraphSnapshot


# Full label taxonomy
LABEL_TAXONOMY = [
    "NORMAL",
    "RECOVERY",
    # Operational
    "CONGESTION_BUILDUP",
    "CONGESTION_ACTIVE",
    "LATENCY_DEGRADING",
    "LATENCY_CRITICAL",
    "PACKET_LOSS_MILD",
    "PACKET_LOSS_SEVERE",
    "JITTER_HIGH",
    "BANDWIDTH_THROTTLED",
    "BROWNOUT",
    "LINK_FAILURE",
    # Attack
    "DDOS_BUILDUP",
    "DDOS_ACTIVE",
    "DDOS_SOURCE",
    "DDOS_TARGET",
    "PORTSCAN_RECON",
    "BRUTE_FORCE_PROBE",
    "BRUTE_FORCE_ACTIVE",
    "LATERAL_MOVEMENT",
    "EXFILTRATION",
]

# Map labels to numeric indices for model training
LABEL_TO_INDEX = {label: idx for idx, label in enumerate(LABEL_TAXONOMY)}


def _worst_label(labels: List[str]) -> str:
    """Pick the most severe label from a set (higher index = worse)."""
    if not labels:
        return "NORMAL"
    indices = [LABEL_TO_INDEX.get(l, 0) for l in labels]
    return LABEL_TAXONOMY[max(indices)]


def apply_scenario_labels(snapshots: List[GraphSnapshot],
                          phase_timeline: List[Dict[str, Any]],
                          all_node_names: List[str]):
    """Apply current-state labels from the scenario phase timeline.

    Args:
        snapshots: Telemetry snapshots collected during the scenario.
        phase_timeline: List of dicts with keys: start_ts, end_ts,
            label, node_labels (dict node→label).
        all_node_names: All node names in the topology.
    """
    for snap in snapshots:
        ts = snap.timestamp
        # Find which phase this snapshot falls into
        matched_phase = None
        for phase in phase_timeline:
            if phase["start_ts"] <= ts < phase["end_ts"]:
                matched_phase = phase
                break

        if matched_phase:
            snap.current_label = matched_phase["label"]
            snap.phase_name = matched_phase.get("phase_name", "")
            # Set per-node labels
            phase_node_labels = matched_phase.get("node_labels", {})
            for name in all_node_names:
                snap.node_labels[name] = phase_node_labels.get(name, "NORMAL")
        else:
            snap.current_label = "NORMAL"
            for name in all_node_names:
                snap.node_labels[name] = "NORMAL"


def apply_predictive_labels(snapshots: List[GraphSnapshot],
                            horizons: List[int] = None,
                            window_seconds: int = 5,
                            all_node_names: List[str] = None):
    """Apply look-ahead predictive labels to each snapshot.

    For each snapshot at time t, look ahead by each horizon and assign
    the label that will be active at t + horizon.

    Args:
        snapshots: Labeled snapshots (current_label already set).
        horizons: Prediction horizons in seconds (default [15, 30, 60]).
        window_seconds: Duration of each time window.
        all_node_names: All node names.
    """
    if horizons is None:
        horizons = [15, 30, 60]
    if all_node_names is None:
        all_node_names = []

    n = len(snapshots)

    for i, snap in enumerate(snapshots):
        snap.prediction_labels = {}

        for horizon_s in horizons:
            # How many windows ahead is this horizon?
            windows_ahead = max(1, horizon_s // window_seconds)
            future_idx = i + windows_ahead

            if future_idx < n:
                future = snapshots[future_idx]
                future_window_label = future.current_label
                future_node_labels = dict(future.node_labels)
            else:
                # Beyond the end of recording — use last known state
                future_window_label = snapshots[-1].current_label
                future_node_labels = dict(snapshots[-1].node_labels)

            key = f"horizon_{horizon_s}s"
            snap.prediction_labels[key] = {
                "window": future_window_label,
                "nodes": future_node_labels,
            }


def label_summary(snapshots: List[GraphSnapshot]) -> Dict[str, Any]:
    """Generate summary statistics for the labeled dataset."""
    from collections import Counter

    current_dist = Counter()
    prediction_dist: Dict[str, Counter] = {}
    node_label_dist = Counter()

    for snap in snapshots:
        current_dist[snap.current_label] += 1

        for node_name, node_label in snap.node_labels.items():
            node_label_dist[node_label] += 1

        for horizon_key, pred in snap.prediction_labels.items():
            if horizon_key not in prediction_dist:
                prediction_dist[horizon_key] = Counter()
            prediction_dist[horizon_key][pred["window"]] += 1

    return {
        "total_windows": len(snapshots),
        "current_label_distribution": dict(current_dist),
        "prediction_label_distribution": {
            k: dict(v) for k, v in prediction_dist.items()
        },
        "node_label_distribution": dict(node_label_dist),
        "label_taxonomy": LABEL_TAXONOMY,
        "label_to_index": LABEL_TO_INDEX,
    }
