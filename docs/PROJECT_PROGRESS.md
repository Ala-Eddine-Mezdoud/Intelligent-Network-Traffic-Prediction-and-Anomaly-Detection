# AI-SDN Integration Progress



## Phase A: Baseline Infrastructure (Completed)
- Built the foundational Mininet topology and Ryu controller integration.
- Developed a closed-loop realtime pipeline (capture -> relay -> feature extraction -> inference).
- Created the legacy **Mininet Dashboard** to visualize live topology, trigger manual traffic flows, and visualize basic paths.
- Built initial detection models trained on standard static data.

## Phase B & C: Realistic Data Generation & Dashboard Split (Just Completed)
We identified that standard CICIDS data is insufficient for predicting operational network anomalies (like latency spikes and link failures) and lacks graph structure. We accomplished the following:

- **Heavy Protocol Emulation**: Added `services_heavy.py` to emulate realistic continuous traffic using `iperf3` (for bulk datacenter transfers) and `ffmpeg/RTP` (for continuous video streaming), replacing simplistic `ping/curl` baseline noise.
- **Spatio-Temporal Graph Generator**: Implemented `gnn_data_generator.py` and `telemetry.py`. The collector extracts continuous windowed node features (queues, TX/RX bytes, jitter) and edge features natively from Mininet.
- **Predictive Horizon Labeling**: Created a scenario orchestrator that executes 12 progressive network degradation and attack phases. The data is tagged with future labels at `$t+15s$`, `$t+30s$`, and `$t+60s$` to train the AI to predict anomalies *before* they peak.
- **21-Class Taxonomy**: Handled both operational anomalies (Brownouts, Congestion, Jitter) and malicious attacks (DDoS, Brute Force, Lateral Movement).
- **Concurrency & Pipeline Fixes**: Resolved severe Mininet single-shell concurrency errors (`AssertionError`) by moving background telemetry polling to isolated `popen` subprocesses. Fixed dataset index overwriting bugs.
- **Successful Generation**: Successfully executed a ~26-minute simulation generating a perfect **318-window GNN dataset** (exported as PyTorch Geometric JSON graphs) alongside a `tabular.csv` baseline.
- **UI Separation**: 
  - Restored and cleaned the **Mininet Control Dashboard (Flask)** to focus strictly on real-time routing, active control, and the Phase A legacy simulation loop.
  - Moved all Dataset Generation controls strictly into the **Network Monitoring Dashboard (Next.js)**.

## Phase D: Predictive GNN Development (What We Will Do Next)
Now that we have highly realistic, graph-structured, future-labeled data, we will build the AI.

1. **PyTorch Geometric Pipeline**: Write a custom PyTorch `Dataset` class that parses the `snapshots/window_*.json` files into sequential `Data` objects.
2. **Spatio-Temporal Architecture**: Design a Graph Neural Network (such as T-GCN, STGCN, or GraphSAGE + LSTM) capable of capturing both the topological relationships (which nodes are connected) and the temporal trends (how queues/bandwidth change over time).
3. **Training & Validation**: Train the GNN to predict the 15s/30s/60s prediction horizons.
4. **Baseline Comparison**: Train a LightGBM/XGBoost tabular baseline using the generated `tabular.csv` file to prove that structural graph data improves forecasting accuracy.
5. **Real-Time Integration**: Once the GNN achieves high accuracy, we will update the old Mininet Realtime Pipeline to use the new heavy-traffic simulator and feed live telemetry snapshots directly into the GNN for real-time proactive warnings.
