# System Architecture

## Overview

The platform has three independent runtime processes:

| Process | Language | Port | Role |
|---------|----------|------|------|
| Ryu SDN controller | Python | 6633 (OpenFlow), 8080 (REST) | Programs OpenFlow flow tables on Mininet switches |
| Flask backend | Python | 5000 | Owns Mininet lifecycle, runs GNN and IDS, exposes REST API |
| Next.js dashboard | Node.js | 3000 | Frontend; polls Flask API for all data |

All three run on the **Linux VM OS**, not inside Mininet host namespaces.

---

## Flask Backend

**Entry point:** `mininetDashboard/sdn_dashboard.py`

### Module responsibilities

| Module | Responsibility |
|--------|---------------|
| `backend/app.py` | Creates Flask app, registers blueprints, triggers Mininet bootstrap |
| `backend/network_manager.py` | Thread-safe Mininet lifecycle (`mn -c`, topology build, IP/route setup) |
| `backend/topology.py` | Node definitions, subnet addressing, static routes, node classification |
| `backend/routes.py` | HTTP handlers — validates input, delegates to service modules |
| `backend/services.py` | Topology serialization, path computation, ping, Ryu flow queries |
| `backend/lab.py` | Lab pipeline: traffic generation, pcap capture, tshark extraction, export |
| `backend/intelligence.py` | IDS heuristic rules, EWMA forecast, anomaly aggregation |
| `backend/gnn_inference.py` | TemporalGAT live inference loop, telemetry collection, anomaly event log |
| `backend/gnn_data_generator.py` | Dataset generation orchestrator (scenarios → telemetry → graph export) |
| `backend/telemetry.py` | Per-node and per-link metric collection via `ip`, `tc`, `ss`, `ping` |
| `backend/scenarios.py` | 12 scripted anomaly scenarios with NORMAL→BUILDUP→ACTIVE→RECOVERY phases |
| `backend/services_heavy.py` | iperf3 server and client lifecycle management |
| `backend/graph_export.py` | PyTorch Geometric JSON and tabular CSV export |
| `backend/labeling.py` | Current + multi-horizon predictive label assignment |

### Startup sequence

1. `sdn_dashboard.py` calls `create_app()`
2. `app.py` registers Flask blueprints and spawns a background thread
3. Background thread runs `NetworkManager.start_async()`:
   - Executes `mn -c` to clean previous state
   - Builds `RealWorldTopo` via `topology.py`
   - Starts OVS switches and connects to Ryu controller
   - Applies IP addresses, static routes, DNS resolver configuration
4. API endpoints become available immediately; topology and lab endpoints return a startup error until Mininet is ready (typically 10–30 seconds)

---

## Data Pipeline

### Simulation pipeline

```
Lab pipeline (lab.py)
    │
    ├── Start iperf3 servers on dc_web, dc_monitor, dc_vpn, dc_pub_dns
    ├── Start iperf3 clients on source hosts (14 persistent TCP/UDP flows)
    │
    └── Every 90 s:
            tcpdump on dc_sw interfaces (10 s capture)
            │
            tshark → CICIDS-style flow features (CSV)
            │
            IDS heuristics (intelligence.py)
            │
            Store as _last_inference
```

### GNN inference pipeline

```
GNN Inference Engine (gnn_inference.py)
    │
    └── Every 8 s:
            Collect 14 features per non-router host via ip/tc/ss/ping
            │
            Build graph (nodes × features, edge_index from topology)
            │
            Feed sequence of 5 windows to TemporalGAT
            │
            Apply override rules (netem check, active injection, suppression)
            │
            Update traffic_series buffer (historical + forecast)
            │
            Store per-node predictions and anomaly event log
```

### Data flow to dashboard

```
Flask API endpoints
    ├── /metrics/current          → GNN: current_traffic_mbps, active_connections, anomaly_score
    ├── /metrics/traffic/historical → GNN: traffic_series historical portion
    ├── /api/predictions          → GNN: full traffic_series (historical + forecast)
    ├── /api/gnn/anomaly-history  → GNN: anomaly event log
    ├── /api/anomalies            → IDS + GNN: combined anomaly list
    ├── /api/alerts               → IDS: risk score, severity, suspicious flows
    ├── /api/topology             → Network topology graph (nodes + edges)
    ├── /api/pipeline/status      → Lab pipeline running state, next attack, GNN stats
    └── /api/lab/gnn-capture/*    → Dataset generation status
```

---

## Ryu Controller

Ryu programs OpenFlow 1.3 flow tables on the Open vSwitch instances. It handles:

- L2 MAC learning and forwarding (`simple_switch_13`)
- REST interface for flow table queries (`ofctl_rest`)

The Flask backend can query active flow tables via the Ryu REST API (`http://localhost:8080`) to show live path information in the topology view.

---

## Next.js Dashboard

**Directory:** `network-monitoring-dashboard/`

The frontend is a Next.js 16 application using:

- **Tailwind CSS v4** with CSS custom properties for theming
- **next-themes** for dark/light mode switching (class-based)
- **Recharts** for traffic charts
- **D3** for the topology graph visualization
- **Framer Motion** for animations

All API calls are defined in `lib/api.ts` and target `NEXT_PUBLIC_API_URL` (default: `http://127.0.0.1:5000`).

---

## Model Artifacts

Trained model files are stored in `mininetDashboard/backend/models/`:

| File | Type | Purpose |
|------|------|---------|
| `gnn_model_complete.pt` | PyTorch checkpoint | TemporalGAT weights for live GNN inference |
| `gnn_scaler.pkl` | sklearn scaler | Feature normalization for GNN input |
| `ids_pipeline.pkl` | sklearn Pipeline | IDS flow classifier (StandardScaler + RandomForest) |
| `forecasting_benign.pkl` | sklearn model | Traffic forecasting model (pcap scale; not used in live charts) |
| `label_mapping.json` | JSON | Index-to-class-name mapping for GNN output |
