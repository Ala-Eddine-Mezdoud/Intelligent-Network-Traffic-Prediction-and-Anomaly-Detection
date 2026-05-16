# Intelligent Network Traffic Prediction & Anomaly Detection

A full-stack platform for real-time network traffic monitoring, AI-powered anomaly detection, and traffic forecasting — built on a Mininet software-defined network simulation running on a Linux VM.

---

## What It Does

- **Traffic prediction** — EWMA-based short-term forecasting with confidence bands, updated every 8 seconds from live GNN telemetry
- **Anomaly detection** — two independent detection layers running in parallel:
  - A TemporalGAT Graph Neural Network classifying live node telemetry into 9 network states
  - A Random Forest IDS classifying pcap-derived CICIDS-style flow features using a 9-rule priority heuristic
- **Simulation control** — injects realistic background traffic and on-demand attack scenarios (DDoS, port scan, brute force, link degradation) directly into the emulated network
- **Data generation** — produces labeled graph-structured datasets for training predictive GNN models
- **Monitoring dashboard** — Next.js frontend with real-time charts, topology visualization, alerts, and dark/light mode

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Next.js Dashboard  :3000                        │
│   Overview · Traffic Prediction · Anomaly Detection · Alerts        │
│   Simulation · Data Generation · Support                            │
└───────────────────────┬─────────────────────────────────────────────┘
                        │ HTTP polling (8–30 s)
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Flask API Backend  :5000                          │
│                                                                     │
│  ┌─────────────────┐  ┌───────────────────┐  ┌──────────────────┐  │
│  │  GNN Inference  │  │  IDS / Intelligence│  │   Lab Pipeline   │  │
│  │  Engine (8 s)   │  │  Plane (90 s snap) │  │  (Mininet ctrl)  │  │
│  └────────┬────────┘  └────────┬──────────┘  └────────┬─────────┘  │
└───────────┼────────────────────┼─────────────────────┬┼────────────┘
            │                    │                      │
            └────────────────────┴──────────────────────┘
                                 │ telemetry / control
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Mininet Network  (kernel namespaces)            │
│                                                                     │
│  isp_core ── isp_r1 ── r_ent1 ── ent1_sw ── e1_pc1, e1_pc2 ...    │
│                     ├── r_ent2 ── ent2_sw ── e2_pc1, e2_crm ...    │
│                     ├── r_home1 ─ home1_sw ─ h1_pc, h1_tv ...      │
│                     ├── r_home2 ─ home2_sw ─ h2_pc, h2_cam ...     │
│                     └── r_dc   ── dc_sw   ── dc_web, dc_vpn ...    │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                    Ryu SDN Controller  :6633 / :8080
```

The **Ryu controller** handles OpenFlow switch programming. The **Flask backend** owns the Mininet lifecycle, runs the GNN inference loop, processes pcap captures for the IDS, and exposes all data through a single REST API on port 5000. The **Next.js dashboard** reads exclusively from this Flask API.

The `models_api/` FastAPI service is a standalone legacy component with pre-trained sklearn models; it is not required for the main simulation pipeline.

---

## Prerequisites

- **Linux** (tested on Ubuntu 20.04) inside a VM or bare metal
- **Mininet** (`sudo apt-get install mininet`)
- **Open vSwitch** (`sudo apt-get install openvswitch-switch`)
- **iperf3** (`sudo apt-get install iperf3`)
- **tshark** (`sudo apt-get install tshark`)
- **Python 3.10+** with packages: `Flask`, `requests`, `torch`, `torch-geometric`, `scikit-learn`, `numpy`
- **Ryu** SDN controller (`pip install ryu`)
- **Node.js 20+** with npm

Install Python dependencies:
```bash
cd mininetDashboard
pip install -r requirements.txt
```

---

## Quick Start

Three terminals are required, all run on the **Linux VM** (not inside Mininet host namespaces).

### Terminal 1 — Ryu SDN Controller

```bash
ryu-manager ryu.app.simple_switch_13 ryu.app.ofctl_rest
```

### Terminal 2 — Flask Backend + Mininet Simulation

```bash
cd mininetDashboard
sudo -E env PYTHONPATH="$HOME/.local/lib/python3.10/site-packages" /usr/bin/python3 sdn_dashboard.py
```

Mininet takes 10–30 seconds to fully start. Wait until the topology API returns a valid response:

```bash
curl -s http://127.0.0.1:5000/api/topology | python3 -m json.tool | head -5
```

### Terminal 3 — Next.js Dashboard

```bash
cd network-monitoring-dashboard
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in a browser.

### Starting a Simulation

Click **Start Simulation** on the dashboard Overview page, or use the API directly:

```bash
curl -X POST http://127.0.0.1:5000/api/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{"interval_seconds": 30}'
```

---

## Environment Variables

Create `network-monitoring-dashboard/.env.local` if the Flask backend is not on localhost:

```env
NEXT_PUBLIC_API_URL=http://<VM-IP>:5000
```

Find the VM IP from inside the VM:
```bash
ip addr | grep "192.168\|10\."
```

---

## Project Structure

```
.
├── mininetDashboard/           # Flask backend + Mininet simulation
│   ├── sdn_dashboard.py        # Entry point
│   ├── backend/
│   │   ├── app.py              # Flask app factory
│   │   ├── network_manager.py  # Mininet lifecycle
│   │   ├── topology.py         # Network topology definition
│   │   ├── lab.py              # Lab pipeline (traffic generation, capture)
│   │   ├── intelligence.py     # IDS heuristics + forecasting
│   │   ├── gnn_inference.py    # TemporalGAT live inference engine
│   │   ├── gnn_data_generator.py # Dataset generation orchestrator
│   │   ├── telemetry.py        # Per-node/link metric collection
│   │   ├── scenarios.py        # Anomaly injection scenarios
│   │   └── models/             # Trained model artifacts (.pt, .pkl)
│   └── captures/               # PCAP and inference output
│
├── network-monitoring-dashboard/  # Next.js frontend
│   ├── app/                    # Page routes
│   ├── components/             # React components
│   └── lib/                    # API client, themes, utilities
│
├── ml_training/                # GNN offline training pipeline
│   ├── gnn_model.py            # TemporalGAT architecture
│   ├── train_gnn.py            # Training script
│   ├── inference_gnn.py        # Inference script
│   └── README_GNN.md           # Training reference
│
├── models_api/                 # Standalone FastAPI service (legacy sklearn models)
│
└── docs/                       # Project documentation
    ├── SETUP.md                # Detailed setup and troubleshooting
    ├── ARCHITECTURE.md         # Backend and pipeline architecture
    ├── SIMULATION.md           # Simulation engine reference
    ├── AI_MODELS.md            # GNN and IDS model reference
    └── DATA_GENERATION.md      # GNN dataset generation reference
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/SETUP.md](docs/SETUP.md) | Full setup guide, environment variables, troubleshooting |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Backend architecture and data pipeline |
| [docs/SIMULATION.md](docs/SIMULATION.md) | Simulation topology, traffic flows, anomaly injection |
| [docs/AI_MODELS.md](docs/AI_MODELS.md) | GNN and IDS model specifications |
| [docs/DATA_GENERATION.md](docs/DATA_GENERATION.md) | GNN training dataset generation |
| [ml_training/README_GNN.md](ml_training/README_GNN.md) | GNN training and inference commands |
