"""Export telemetry snapshots to GNN-ready format (PyTorch Geometric compatible)."""

import csv
import json
import os
from typing import Any, Dict, List

from .labeling import LABEL_TO_INDEX, label_summary
from .telemetry import GraphSnapshot, NodeSnapshot, EdgeSnapshot


def export_gnn_dataset(
    snapshots: List[GraphSnapshot],
    topology_info: Dict[str, Any],
    scenario_name: str,
    run_id: str,
    output_base: str,
    metadata_extra: Dict[str, Any] = None,
):
    """Export snapshots as a GNN-ready dataset.

    Creates:
      - metadata.json (topology, feature names, label taxonomy)
      - snapshots/window_NNNN.json (per-window graph data)
      - tabular.csv (flattened per-node-per-window for baseline models)
      - dataset_summary.json (label distribution, stats)
    """
    out_dir = os.path.join(output_base, run_id)
    snap_dir = os.path.join(out_dir, "snapshots")
    os.makedirs(snap_dir, exist_ok=True)

    node_names = topology_info["node_names"]
    node_index = topology_info["node_index"]
    edge_index_raw = topology_info["edge_index"]

    # --- metadata.json ---
    meta = {
        "run_id": run_id,
        "scenario_name": scenario_name,
        "total_windows": len(snapshots),
        "window_seconds": _guess_window_seconds(snapshots),
        "node_names": node_names,
        "node_index": node_index,
        "node_ips": topology_info.get("node_ips", {}),
        "edges": topology_info.get("edges", []),
        "edge_index": edge_index_raw,
        "node_feature_names": NodeSnapshot.feature_names(),
        "edge_feature_names": EdgeSnapshot.feature_names(),
        "label_to_index": LABEL_TO_INDEX,
    }
    if metadata_extra:
        meta.update(metadata_extra)

    with open(os.path.join(out_dir, "metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)

    # --- Per-window snapshots ---
    for global_idx, snap in enumerate(snapshots):
        snap.window_index = global_idx
        _write_snapshot(snap, snap_dir, node_names, edge_index_raw)

    # --- Tabular CSV ---
    _write_tabular_csv(snapshots, node_names, out_dir)

    # --- Summary ---
    summary = label_summary(snapshots)
    summary["run_id"] = run_id
    summary["scenario_name"] = scenario_name
    if snapshots:
        summary["duration_seconds"] = round(
            snapshots[-1].timestamp - snapshots[0].timestamp, 2
        )

    with open(os.path.join(out_dir, "dataset_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    return {
        "output_dir": out_dir,
        "total_windows": len(snapshots),
        "summary": summary,
    }


def _write_snapshot(snap: GraphSnapshot, snap_dir: str,
                    node_names: List[str], edge_index: List[List[int]]):
    """Write a single window snapshot as JSON."""
    # Build node feature matrix (ordered by node_names)
    node_features = []
    for name in node_names:
        ns = snap.node_snapshots.get(name)
        if ns:
            node_features.append(ns.feature_vector())
        else:
            node_features.append([0.0] * len(NodeSnapshot.feature_names()))

    # Build edge feature matrix
    edge_features = []
    for es in snap.edge_snapshots:
        edge_features.append(es.feature_vector())

    # Build edge_index as [[src_indices], [dst_indices]] format (COO)
    src_list = [e[0] for e in edge_index]
    dst_list = [e[1] for e in edge_index]

    # Node labels as list ordered by node_names
    node_label_list = [snap.node_labels.get(name, "NORMAL") for name in node_names]
    node_label_indices = [LABEL_TO_INDEX.get(l, 0) for l in node_label_list]

    # Prediction labels
    pred_labels = {}
    for horizon_key, pred in snap.prediction_labels.items():
        pred_node_labels = [pred["nodes"].get(name, "NORMAL") for name in node_names]
        pred_labels[horizon_key] = {
            "window": pred["window"],
            "window_index": LABEL_TO_INDEX.get(pred["window"], 0),
            "nodes": pred_node_labels,
            "node_indices": [LABEL_TO_INDEX.get(l, 0) for l in pred_node_labels],
        }

    data = {
        "timestamp": snap.timestamp,
        "window_index": snap.window_index,
        "node_features": node_features,
        "edge_index": [src_list, dst_list],
        "edge_features": edge_features,
        "current_labels": {
            "window": snap.current_label,
            "window_index": LABEL_TO_INDEX.get(snap.current_label, 0),
            "nodes": node_label_list,
            "node_indices": node_label_indices,
        },
        "prediction_labels": pred_labels,
        "phase_name": snap.phase_name,
        "scenario_name": snap.scenario_name,
    }

    path = os.path.join(snap_dir, f"window_{snap.window_index:04d}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _write_tabular_csv(snapshots: List[GraphSnapshot],
                       node_names: List[str], out_dir: str):
    """Write flattened CSV with one row per (window, node) for tabular baselines."""
    if not snapshots:
        return

    feature_names = NodeSnapshot.feature_names()
    header = (
        ["window_index", "timestamp", "node_name", "node_ip", "zone", "node_type"]
        + feature_names
        + ["current_label", "current_label_index"]
    )

    # Add prediction horizon columns
    horizon_keys = []
    if snapshots[0].prediction_labels:
        horizon_keys = sorted(snapshots[0].prediction_labels.keys())
        for hk in horizon_keys:
            header.extend([f"pred_{hk}_label", f"pred_{hk}_index"])

    csv_path = os.path.join(out_dir, "tabular.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for snap in snapshots:
            for name in node_names:
                ns = snap.node_snapshots.get(name)
                row = [
                    snap.window_index,
                    round(snap.timestamp, 3),
                    name,
                    ns.ip if ns else "",
                    ns.zone if ns else "",
                    ns.node_type if ns else "",
                ]
                if ns:
                    row.extend(ns.feature_vector())
                else:
                    row.extend([0.0] * len(feature_names))

                curr_label = snap.node_labels.get(name, "NORMAL")
                row.extend([curr_label, LABEL_TO_INDEX.get(curr_label, 0)])

                for hk in horizon_keys:
                    pred = snap.prediction_labels.get(hk, {})
                    pred_nodes = pred.get("nodes", {})
                    pl = pred_nodes.get(name, "NORMAL")
                    row.extend([pl, LABEL_TO_INDEX.get(pl, 0)])

                writer.writerow(row)


def _guess_window_seconds(snapshots: List[GraphSnapshot]) -> int:
    if len(snapshots) < 2:
        return 5
    return max(1, round(snapshots[1].timestamp - snapshots[0].timestamp))
