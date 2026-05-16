# Setup Guide

## Prerequisites

| Requirement | Version | Install |
|-------------|---------|---------|
| Linux (Ubuntu 20.04+) | — | VM or bare metal |
| Mininet | 2.3+ | `sudo apt-get install mininet` |
| Open vSwitch | — | `sudo apt-get install openvswitch-switch` |
| iperf3 | — | `sudo apt-get install iperf3` |
| tshark | — | `sudo apt-get install tshark` |
| Python | 3.10+ | system or Anaconda |
| Ryu SDN controller | — | `pip install ryu` |
| Node.js | 20+ | `curl -fsSL https://deb.nodesource.com/setup_20.x \| sudo bash - && sudo apt-get install nodejs` |

---

## First-Time Setup

### 1. Install Python dependencies

```bash
cd mininetDashboard
pip install -r requirements.txt
```

Key packages: `Flask`, `torch`, `torch-geometric`, `scikit-learn`, `numpy`, `requests`, `scapy`

### 2. Install dashboard dependencies

```bash
cd network-monitoring-dashboard
npm install
```

If the build fails with a missing native binary error, run:

```bash
# Fix @tailwindcss/oxide native binary (required on Linux)
cp node_modules/@tailwindcss/oxide-linux-x64-gnu/tailwindcss-oxide.linux-x64-gnu.node \
   node_modules/@tailwindcss/oxide/tailwindcss-oxide.linux-x64-gnu.node

# Fix lightningcss native binary if missing
npm install lightningcss-linux-x64-gnu --legacy-peer-deps
```

### 3. Verify Ryu is available

```bash
ryu-manager --version
```

---

## Running the System

Three terminals are required. All run on the **Linux VM**, not inside Mininet namespaces.

### Terminal 1 — Ryu SDN Controller

```bash
ryu-manager ryu.app.simple_switch_13 ryu.app.ofctl_rest
```

Leave this running. Ryu listens on port 6633 (OpenFlow) and port 8080 (REST).

### Terminal 2 — Flask Backend + Mininet

```bash
cd mininetDashboard
sudo -E env PYTHONPATH="$HOME/.local/lib/python3.10/site-packages" /usr/bin/python3 sdn_dashboard.py
```

Adjust `python3.10` to match your installed Python version. The `sudo -E` preserves environment variables so pip-installed packages are found.

Mininet takes 10–30 seconds to initialize. Check readiness:

```bash
curl -s http://127.0.0.1:5000/api/topology
```

When topology returns a JSON object with nodes and links (not `{"error":"Mininet is still starting"}`), the backend is ready.

### Terminal 3 — Next.js Dashboard

```bash
cd network-monitoring-dashboard
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Starting a Simulation

From the dashboard Overview page, click **Start Simulation**.

Or via API:

```bash
# Start simulation (30-second pipeline cycle)
curl -X POST http://127.0.0.1:5000/api/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{"interval_seconds": 30}'

# Check status
curl -s http://127.0.0.1:5000/api/pipeline/status

# Stop simulation
curl -X POST http://127.0.0.1:5000/api/pipeline/stop
```

The GNN inference engine starts automatically when the simulation starts and polls telemetry every 8 seconds. The first GNN prediction appears after 40 seconds (5 windows × 8 seconds).

---

## Environment Variables

Create `network-monitoring-dashboard/.env.local` to override defaults:

```env
# Flask backend URL (default: http://127.0.0.1:5000)
NEXT_PUBLIC_API_URL=http://192.168.56.101:5000
```

The VM's IP address can be found from inside the VM:

```bash
ip addr show | grep "inet " | grep -v "127.0.0.1"
```

If accessing the dashboard from a different machine, use the VM's bridged or host-only adapter IP.

---

## Generating a GNN Training Dataset

With the simulation running:

```bash
# Start dataset generation (all 12 scenarios, ~30 minutes)
curl -X POST http://127.0.0.1:5000/api/lab/run-gnn-capture \
  -H "Content-Type: application/json" \
  -d '{"window_seconds": 5, "prediction_horizons": [15, 30, 60]}'

# Check progress
curl http://127.0.0.1:5000/api/lab/gnn-capture/status

# List completed datasets
curl http://127.0.0.1:5000/api/lab/gnn-datasets
```

Datasets are saved to `mininetDashboard/captures/gnn_datasets/`. See [DATA_GENERATION.md](DATA_GENERATION.md) for details.

---

## Troubleshooting

### Backend

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Can't find module` error on start | pip packages not found under sudo | Use `sudo -E env PYTHONPATH=...` as shown above |
| Topology returns `"Mininet is still starting"` | Normal during boot | Wait 10–30 s and retry |
| Port 5000 already in use | Previous instance still running | `sudo pkill -f sdn_dashboard.py` then `sudo mn -c` |
| `mn -c` needed before restart | Mininet leftover state | `sudo mn -c` cleans all OVS/namespace state |
| GNN model not found | Missing `.pt` file | Check `mininetDashboard/backend/models/` for `gnn_model_complete.pt` |

### Dashboard

| Symptom | Cause | Fix |
|---------|-------|-----|
| All pages show 0 / loading forever | Backend unreachable | Verify `curl http://127.0.0.1:5000/api/metrics/current` returns JSON |
| Native binary error on `npm install` | Linux optional dependency bug | Follow the binary copy steps in First-Time Setup above |
| Port 3000 in use | Another Next.js instance | Next.js will automatically use the next available port |
| `Hydration` error in console | Clock SSR mismatch | Already fixed in codebase; clear browser cache |

### Simulation

| Symptom | Cause | Fix |
|---------|-------|-----|
| Dashboard pages stuck after start | Mininet still booting | Check topology API readiness before starting simulation |
| No anomalies shown in normal mode | Expected | IDS and GNN suppress false positives from iperf3 flows |
| Traffic shows 200–500 Mbps | Expected | TCP saturation + both-endpoint counting; see [SIMULATION.md](SIMULATION.md#traffic-scale) |
| GNN shows no prediction for 40 s | Normal warm-up | Engine needs 5 windows (40 s) to start predicting |
