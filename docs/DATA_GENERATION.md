# Data Generation for GNN-Based Predictive Network Analysis

## 1. Overview

This module generates **time-windowed, graph-structured, labeled datasets** for training Graph Neural Network (GNN) models that **predict** operational anomalies and attacks before they fully manifest.

### Detection vs Prediction

| Aspect | Detection (current IDS) | Prediction (GNN target) |
|--------|------------------------|------------------------|
| **Data unit** | Individual flow (5-tuple) | Time window (5s graph snapshot) |
| **Label meaning** | "This flow IS a DDoS" | "In 30s, node X WILL experience congestion" |
| **Features** | Per-flow stats | Per-node + per-link telemetry |
| **Model input** | Flat feature vector | Graph: nodes × features + edges × features |
| **Temporal context** | None | Sequence of T past snapshots |

The existing CICIDS-2017 IDS model is **kept** for real-time flow detection. The GNN operates alongside it for prediction.

---

## 2. Architecture

```
Mininet topology
     │
     ├── Background traffic (HTTP, DNS, MQTT, RTP via iperf3, ...)
     ├── Scenario execution (phased anomaly/attack injection)
     │
     ▼
TelemetryCollector (every 5s)
     │
     ├── Per-node: bytes, packets, drops, latency, jitter, queue, netem state
     ├── Per-edge: throughput, utilization, flow count, protocol mix
     │
     ▼
Labeling engine
     │
     ├── Current label: what IS happening now (from scenario phase)
     ├── Predictive labels: what WILL happen at t+15s, t+30s, t+60s
     │
     ▼
Graph export (PyG-compatible JSON + tabular CSV)
```

### Key modules

| Module | Purpose |
|--------|---------|
| `backend/telemetry.py` | Collects node/link metrics via `ip -s link`, `tc -s qdisc`, `ping`, `ss` |
| `backend/scenarios.py` | 12 scripted scenarios with NORMAL→BUILDUP→ACTIVE→RECOVERY phases |
| `backend/services_heavy.py` | iperf3 server/client management for sustained heavy traffic |
| `backend/labeling.py` | Applies current + multi-horizon predictive labels |
| `backend/graph_export.py` | Exports PyTorch Geometric-compatible JSON + tabular CSV |
| `backend/gnn_data_generator.py` | End-to-end orchestrator |

---

## 3. Telemetry features

### Node features (14 per node, per window)

| # | Feature | Source |
|---|---------|--------|
| 0 | `bytes_sent` | `ip -s link` delta |
| 1 | `bytes_recv` | `ip -s link` delta |
| 2 | `pkts_sent` | `ip -s link` delta |
| 3 | `pkts_recv` | `ip -s link` delta |
| 4 | `pkt_drops` | `ip -s link` delta |
| 5 | `latency_ms` | `ping` to gateway |
| 6 | `jitter_ms` | `ping` mdev |
| 7 | `tcp_connections` | `ss -s` |
| 8 | `retransmits` | `ss -s` |
| 9 | `queue_depth_bytes` | `tc -s qdisc` backlog |
| 10 | `queue_depth_pkts` | `tc -s qdisc` backlog |
| 11 | `bandwidth_limit_mbit` | `tc qdisc` rate |
| 12 | `netem_delay_ms` | `tc qdisc` delay |
| 13 | `netem_loss_pct` | `tc qdisc` loss |

### Edge features (6 per edge, per window)

| # | Feature | Source |
|---|---------|--------|
| 0 | `bytes_through` | Endpoint counters averaged |
| 1 | `utilization_pct` | bytes / (capacity × window) |
| 2 | `active_flows` | Unique src-dst pairs |
| 3 | `protocol_tcp_pct` | TCP fraction |
| 4 | `protocol_udp_pct` | UDP fraction |
| 5 | `protocol_icmp_pct` | ICMP fraction |

---

## 4. Scenario library

Each scenario follows the pattern: **NORMAL → BUILDUP → ACTIVE → RECOVERY → NORMAL**. This temporal structure teaches the GNN to recognize precursor patterns.

| # | Scenario | What it teaches |
|---|----------|-----------------|
| 1 | DDoS ramp-up | UDP flood grows from 1M→5M→20M bps |
| 2 | Congestion buildup | TCP flows saturate enterprise uplink |
| 3 | Latency degradation | Progressive delay from 50→150→300ms |
| 4 | Packet loss cascade | Loss grows 1%→3%→8% with retransmit amplification |
| 5 | Port scan → exploitation | Recon precedes brute force (attack kill-chain) |
| 6 | Link failure (brownout) | Gradual degradation toward failure |
| 7 | Bandwidth saturation | Multiple streams exhaust link capacity |
| 8 | Service degradation | Application-level slowdown from netem |
| 9 | Multi-node congestion | Congestion spreads across topology |
| 10 | Mixed attack + operational | DDoS during existing congestion |
| 11 | VoIP/RTP quality degradation | Real-time protocol sensitivity to jitter/loss |
| 12 | Brute force escalation | SSH brute force accelerates over time |

---

## 5. Label taxonomy

Labels are hierarchical by severity. Each node gets its own label per window.

### Operational labels
- `NORMAL` — healthy state
- `RECOVERY` — transitioning back to normal
- `CONGESTION_BUILDUP` / `CONGESTION_ACTIVE` — traffic approaching/exceeding capacity
- `LATENCY_DEGRADING` / `LATENCY_CRITICAL` — latency increasing
- `PACKET_LOSS_MILD` / `PACKET_LOSS_SEVERE` — loss events
- `JITTER_HIGH` — jitter above threshold
- `BANDWIDTH_THROTTLED` — rate limit applied
- `BROWNOUT` / `LINK_FAILURE` — partial/full degradation

### Attack labels
- `DDOS_BUILDUP` / `DDOS_ACTIVE` / `DDOS_SOURCE` / `DDOS_TARGET`
- `PORTSCAN_RECON` — reconnaissance scanning
- `BRUTE_FORCE_PROBE` / `BRUTE_FORCE_ACTIVE` — credential attack
- `LATERAL_MOVEMENT` — compromised host scanning
- `EXFILTRATION` — abnormal outbound transfer

### Predictive labels
Each window has labels at **three horizons**: what will happen at **t+15s**, **t+30s**, **t+60s**. This is the GNN training target.

---

## 6. Output format

### Directory structure
```
captures/gnn_datasets/
  gnn_20260422_141500/
    metadata.json           # Topology, feature names, label mapping
    snapshots/
      window_0000.json      # Graph snapshot at t=0
      window_0001.json      # Graph snapshot at t=5s
      ...
    tabular.csv             # Flattened per-(window,node) for baselines
    dataset_summary.json    # Label distribution, duration, stats
```

### Snapshot format (window_NNNN.json)

Each file is a complete graph with node features, edges, and labels:

```json
{
  "timestamp": 1714000000.0,
  "window_index": 42,
  "node_features": [[bytes_sent, bytes_recv, ...], ...],
  "edge_index": [[0, 1, ...], [1, 0, ...]],
  "edge_features": [[bytes_through, util, ...], ...],
  "current_labels": {
    "window": "CONGESTION_BUILDUP",
    "nodes": ["NORMAL", "CONGESTION_BUILDUP", ...],
    "node_indices": [0, 2, ...]
  },
  "prediction_labels": {
    "horizon_15s": {"window": "CONGESTION_ACTIVE", "nodes": [...], "node_indices": [...]},
    "horizon_30s": {"window": "CONGESTION_ACTIVE", "nodes": [...], "node_indices": [...]},
    "horizon_60s": {"window": "RECOVERY", "nodes": [...], "node_indices": [...]}
  }
}
```

### Loading in PyTorch Geometric

```python
import json
import torch
from torch_geometric.data import Data

with open("window_0042.json") as f:
    snap = json.load(f)

data = Data(
    x=torch.tensor(snap["node_features"], dtype=torch.float),
    edge_index=torch.tensor(snap["edge_index"], dtype=torch.long),
    edge_attr=torch.tensor(snap["edge_features"], dtype=torch.float),
    y=torch.tensor(snap["prediction_labels"]["horizon_30s"]["node_indices"], dtype=torch.long),
)
```

---

## 7. Running a data generation session

### Via API

```bash
# Start all 12 scenarios (~30 min)
curl -X POST http://localhost:5000/api/lab/run-gnn-capture \
  -H "Content-Type: application/json" \
  -d '{"window_seconds": 5, "prediction_horizons": [15, 30, 60]}'

# Check progress
curl http://localhost:5000/api/lab/gnn-capture/status

# Stop early
curl -X POST http://localhost:5000/api/lab/gnn-capture/stop

# List generated datasets
curl http://localhost:5000/api/lab/gnn-datasets
```

### Specific scenarios only

```bash
curl -X POST http://localhost:5000/api/lab/run-gnn-capture \
  -H "Content-Type: application/json" \
  -d '{"scenarios": ["ddos_ramp_dc_web", "congestion_buildup_ent1"]}'
```

---

## 8. Adding new scenarios

Add a new function in `backend/scenarios.py`:

```python
def _scenario_my_custom() -> Scenario:
    return Scenario(
        name="my_custom_scenario",
        description="Description of what this scenario tests",
        phases=[
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
            ScenarioPhase("CONGESTION_BUILDUP", 30,
                          _baseline_actions() + [_iperf_tcp("e1_pc1", "dc_web", "30M", 30)],
                          ["dc_web"], {"dc_web": "CONGESTION_BUILDUP"}),
            # ... more phases ...
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
        ],
    )
```

Then add it to the `build_scenario_library()` function.

---

## 9. Prerequisites

- **iperf3**: `sudo apt-get install -y iperf3`
- **tshark**: Already required for the IDS pipeline
- **iproute2**: `ip`, `tc`, `ss` commands (pre-installed on Ubuntu/Mininet)
- **Mininet**: Running with the `RealWorldTopo` topology
