# Intelligent Network Traffic Prediction & Anomaly Detection — Simulation Report

## System Architecture Overview

The simulation runs on top of **Mininet**, a network emulator that creates virtual hosts, switches, and routers inside a single Linux kernel. The dashboard is a Next.js frontend communicating with a Flask backend that orchestrates the simulation.

```
Next.js Dashboard (port 3000)
        │ HTTP polling every 30 s
        ▼
Flask Backend (port 5000)
        │
        ├── GNN Inference Engine   ← live telemetry every 8 seconds
        ├── IDS Intelligence Plane ← pcap-based IDS every 90 seconds (normal sim)
        └── Lab Pipeline           ← Mininet network control
                │
                ▼
        Mininet Network (kernel namespaces)
        ┌────────────────────────────────────────────────┐
        │ isp_core ── isp_r1                             │
        │    ├── r_ent1 ── ent1_sw ── e1_pc1, e1_erp ... │
        │    ├── r_ent2 ── ent2_sw ── e2_pc1, e2_crm ... │
        │    ├── r_home1 ── home1_sw ── h1_pc, h1_tv ... │
        │    ├── r_home2 ── home2_sw ── h2_pc, h2_cam .. │
        │    └── r_dc   ── dc_sw   ── dc_web, dc_monitor │
        └────────────────────────────────────────────────┘
```

---

## Network Topology

| Segment | Router | Subnet | Hosts |
|---------|--------|--------|-------|
| Enterprise 1 | r_ent1 | 10.10.1.0/24 | e1_pc1 (.11), e1_pc2 (.12), e1_erp (.40), e1_dns (.53), e1_dhcp (.2) |
| Enterprise 2 | r_ent2 | 10.20.1.0/24 | e2_pc1 (.11), e2_pc2 (.12), e2_crm (.41), e2_dns (.53), e2_dhcp (.2) |
| Home 1 | r_home1 | 192.168.10.0/24 | h1_pc (.11), h1_tv (.21), h1_iot (.31) |
| Home 2 | r_home2 | 192.168.20.0/24 | h2_pc (.11), h2_cam (.21), h2_nas (.31) |
| Datacenter | r_dc | 172.16.1.0/24 | dc_web (.20), dc_vpn (.30), dc_monitor (.40), dc_pub_dns (.53) |
| ISP Transit | isp_r1 | 10.255.0.0/24 | All routers (isp_r1=.1, r_ent1=.11, r_ent2=.12, r_home1=.21, r_home2=.22, r_dc=.30) |

**Routing path (enterprise → DC):**  
`e1_pc1 → r_ent1 → isp_core → isp_r1 → isp_core → r_dc → dc_sw → dc_web`

> Note: Traffic passes through isp_core **twice** (once to isp_r1, once from isp_r1 to r_dc).
> This causes packet duplication at isp_core capture points — capturing there inflates measurements.

---

## Simulation Modes

### 1. Normal Simulation (Baseline Traffic)

Started with **"Start Simulation"** on the dashboard. Runs 14 persistent iperf3 flows:

| Source | Destination | Protocol | Port | Rate target |
|--------|-------------|----------|------|-------------|
| e1_pc1 | dc_web | TCP | 5201 | 3 Mbps* |
| e1_erp | dc_web | TCP | 5202 | 5 Mbps* |
| e2_pc1 | dc_web | TCP | 5203 | 3 Mbps* |
| h1_pc  | dc_web | TCP | 5204 | 2 Mbps* |
| h2_pc  | dc_web | TCP | 5205 | 2 Mbps* |
| h2_nas | dc_web | TCP | 5206 | 3 Mbps* |
| e1_pc2 | dc_monitor | TCP | 5211 | 2 Mbps* |
| e2_pc2 | dc_monitor | TCP | 5212 | 2 Mbps* |
| e2_crm | dc_monitor | TCP | 5213 | 4 Mbps* |
| h1_tv  | dc_monitor | UDP | 5214 | 2 Mbps |
| h2_cam | dc_monitor | UDP | 5215 | 1 Mbps |
| h1_iot | dc_monitor | UDP | 5216 | 1 Mbps |
| e1_pc1 | dc_vpn | TCP | 5221 | 1 Mbps* |
| e2_pc1 | dc_pub_dns | UDP | 5222 | 0.5 Mbps |

> \* **TCP `-b` rate hint is NOT a hard limit.** iperf3 TCP flows saturate at Mininet wire speed
> (veth pairs can handle GBps). Actual throughput is typically **20–50 Mbps per TCP flow** in
> Mininet. The `-b` flag is respected for UDP flows.

**Persistent loop**: each TCP source runs `while true; do iperf3 ...; sleep 0.5; done`, ensuring
continuous traffic with at most 0.5 s gaps between flow restarts.

**IDS snapshot**: every 90 seconds, a 10-second tcpdump capture runs on dc_sw interfaces. The
captured flows are processed by the IDS pipeline and stored as `_last_inference`.

### 2. Realtime Simulation (Full PCAP Pipeline)

Not currently the default. Runs a pcap capture every ~30 seconds, processes flows through tshark,
builds CICIDS-style flow features, and runs the full IDS + forecast pipeline.

### 3. Anomaly Injection (Manual)

Available while any simulation is running. Injected via tc/netem on a target host's interface:

| Type | Effect | Detection method |
|------|--------|-----------------|
| `congestion` | 60 ms delay, 15 ms jitter, 4 Mbit rate cap | GNN netem check |
| `latency` | 300 ms delay, 80 ms jitter | GNN netem check |
| `packet_loss` | 15 ms delay, 8% random loss | GNN netem check |
| `jitter` | 80 ms delay, 60 ms jitter, 10 Mbit rate cap | GNN netem check |
| `brownout` | 200 ms delay, 5% loss, 1 Mbit rate cap | GNN netem check |
| `ddos` | UDP flood from h1_iot + h2_cam to dc_web | GNN + IDS P1/P2 |
| `portscan` | nmap port scan from attacker | IDS P5 + GNN |
| `brute_force` | SSH brute force from attacker | IDS P6 + GNN |

---

## GNN Inference Engine

**Model**: TemporalGAT — a Temporal Graph Attention Network combining LSTM temporal encoding
with 3-layer GAT for spatial graph reasoning.

**Inputs** (per node, per 8-second window): 14 features — bytes_sent, bytes_recv, pkts_sent,
pkts_recv, pkt_drops, latency_ms, jitter_ms, tcp_connections, retransmits, queue_depth_bytes,
queue_depth_pkts, bandwidth_limit_mbit, netem_delay_ms, netem_loss_pct.

**Sequence**: 5 windows (40 seconds of history) before the first prediction.

**Classes** (9 merged): NORMAL, CONGESTION, LATENCY, PACKET_LOSS, JITTER, BANDWIDTH,
INFRA_FAILURE, DDOS, SCANNING.

**Ground-truth overrides** (in priority order):
1. **Netem check**: reads unscaled raw features for delay_ms > 100, loss_pct > 2 → overrides model
2. **Active injection**: when `inject_anomaly()` was called, pins the correct label for the duration
3. **SCANNING / BRUTE_FORCE suppression**: always false-positive in normal sim (tcp_connections
   distribution mismatch: training had mean ≈ 1, normal sim has 14 persistent flows)
4. **JITTER / BANDWIDTH suppression**: always false-positive in normal sim (Mininet TCP kernel
   timing variation + uncapped TCP speed; only valid when injection is active)

**Anomaly confidence gate**: window-level ≥ 55%, node-level ≥ 50%.

---

## IDS (Intrusion Detection System) Pipeline

**Model**: `ids_pipeline.pkl` — a sklearn Pipeline (StandardScaler → RandomForestClassifier)
trained on 2420 synthetic samples across 15 attack classes (CICIDS-style features).

**Classification architecture** (P1–P9, first match wins):

| Priority | Condition | Label |
|----------|-----------|-------|
| P1 | src_ip in ATTACKER_IP_PREFIXES **and attack_hint is not None** | IDS: Simulated Attack |
| P2 | dst aggregate ≥ 50 MB/s AND per-flow > 1 MB/s AND dst_port not in iperf3 range | IDS: DDoS Multi-Source Flood |
| P3 | byte_rate > 50 MB/s AND dst_port not in iperf3 range | IDS: DDoS High Volume |
| P4 | pkt_rate > 5000 pkt/s | IDS: High Packet Rate |
| P5 | ≥ 8 distinct dst ports from same source | IDS: Port Scan |
| P6 | ≥ 5 flows to SSH/FTP/Telnet/SMTP/RDP from same source | IDS: Brute Force |
| P7 | dst_port in {80,443,8080,8443} AND pkt_rate > 200 | IDS: HTTP Flood |
| P8 | web port, duration > 10s, byte_rate < 500 B/s | IDS: Slow DoS (Slowloris) |
| P9 | ML model confidence ≥ 97% (iperf3 ports) or ≥ 90% (other) AND not BENIGN | ML-based label |

**IPERF3_PORTS** = {5200–5330} — flows to these ports never trigger P2/P3 since TCP iperf3
runs at uncapped wire speed in Mininet.

**ATTACKER_IP_PREFIXES** = {192.168.10.31 (h1_iot), 192.168.20.21 (h2_cam)} — reserved for
attack simulations. P1 only activates when `attack_hint` is set (realtime simulation + explicit
attack injection). In normal simulation snapshots, `attack_hint=None`, so P1 is skipped even
when these hosts send legitimate iperf3 traffic.

---

## Traffic Forecast (Traffic Prediction Chart)

**Data source**: GNN engine's `traffic_series` list, which combines:
- **Historical** (left side of chart): real GNN telemetry from 8-second windows, stored as
  `{time, historical: Mbps, predicted: null}`
- **Future** (right side of chart): trend extrapolation from `_forecast_base × multiplier^(idx/4) × (1 + sin(idx×0.5)×0.04)`, where the multiplier reflects the current network state (DDOS=1.15, CONGESTION=0.85, INFRA_FAILURE=0.60, NORMAL=1.0)

**When shown**: Only when the GNN engine is actively running (simulation is live). Returns empty `[]` when no simulation is running → frontend shows "No simulation running".

**Why `forecasting_benign.pkl` is NOT used here**: The pkl model was trained on pcap-derived byte
rates (actual per-flow rates of 2–5 Mbps). The GNN measures interface counters at full Mininet speed
(both-endpoint counting, 400+ Mbps). Feeding pkl predictions into a GNN-scale chart would produce
near-zero predictions next to 400+ Mbps historical values, making the chart unreadable. The pkl
model IS used internally by `intelligence_plane._build_predictions()` for the IDS pipeline context
(where both history and predictions are in the same pcap-scale).

---

## Anomaly Detection Page

**Data sources** (combined and de-duplicated):
1. **IDS pipeline** (`build_anomalies`): real pcap-derived flows classified by the IDS heuristics + ML
2. **GNN anomaly nodes** (`build_gnn_anomalies`): per-node detections from the TemporalGAT model

**When empty**: normal simulation with no attack injection → IDS sees only iperf3 flows (all excluded from DDoS checks, all on safe ports) and GNN sees NORMAL state → no anomalies displayed.

**When populated**:
- Injection of `ddos`, `portscan`, `brute_force` → IDS heuristics P2–P6 + GNN active injection
- Injection of `latency`, `congestion`, `packet_loss`, `jitter`, `brownout` → GNN netem detection

---

## Known Limitations

| Limitation | Cause | Impact |
|-----------|-------|--------|
| Traffic shows 180–220 Mbps | Both-endpoint byte counting + fast Mininet TCP | Cosmetic only; real flows are ~20–35 Mbps each |
| GNN `_last_prediction` persists after stop | No reset on simulation stop | Old data shown briefly after stop; fixed by gating on `gnn_engine._running` |
| Forecast uses sinusoidal extrapolation | pkl model trained on different scale | Predictions are trend-based but in correct traffic scale |
| GNN needs 5×8=40s warm-up | Must buffer 5 snapshots before prediction | Brief "no data" period after simulation start |
| IDS snapshot every 90s | Performance tradeoff | Attack detection latency up to 90s in normal sim |
| TCP iperf3 ignores `-b` hint | iperf3 behavior for TCP | Flows run at wire speed; `-b` only respected for UDP |

---

## Dashboard Pages Reference

| Page | URL | Data source | Refresh |
|------|-----|-------------|---------|
| Main Dashboard | / | GNN + IDS | 30 s |
| Traffic Prediction | /traffic-prediction | GNN traffic_series | 30 s |
| Anomaly Detection | /anomaly-detection | IDS + GNN anomaly_nodes | 30 s |
| Alerts | /alerts | IDS risk score + GNN anomaly events | 30 s |
| Simulation Control | /simulation | Lab pipeline status | on-demand |
| Data Generation | /data-generation | GNN data capture status | on-demand |
