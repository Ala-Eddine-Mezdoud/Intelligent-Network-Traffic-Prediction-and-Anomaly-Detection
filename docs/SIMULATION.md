# Simulation Reference

## Network Topology

The simulation runs a multi-domain network inside Mininet kernel namespaces.

```
isp_core (switch)
    └── isp_r1 (router, 10.255.0.1)
            ├── r_ent1  (10.255.0.11) ── ent1_sw  ── Enterprise A hosts
            ├── r_ent2  (10.255.0.12) ── ent2_sw  ── Enterprise B hosts
            ├── r_home1 (10.255.0.21) ── home1_sw ── Home A hosts
            ├── r_home2 (10.255.0.22) ── home2_sw ── Home B hosts
            └── r_dc    (10.255.0.30) ── dc_sw    ── Datacenter hosts
```

All spoke routers use a default route toward `isp_r1`. `isp_r1` has explicit routes to each LAN.

### Hosts

| Zone | Router | Subnet | Hosts |
|------|--------|--------|-------|
| Enterprise A | r_ent1 | 10.10.1.0/24 | e1_pc1 (.11), e1_pc2 (.12), e1_erp (.40), e1_dns (.53), e1_dhcp (.2) |
| Enterprise B | r_ent2 | 10.20.1.0/24 | e2_pc1 (.11), e2_pc2 (.12), e2_crm (.41), e2_dns (.53), e2_dhcp (.2) |
| Home A | r_home1 | 192.168.10.0/24 | h1_pc (.11), h1_tv (.21), h1_iot (.31) |
| Home B | r_home2 | 192.168.20.0/24 | h2_pc (.11), h2_cam (.21), h2_nas (.31) |
| Datacenter | r_dc | 172.16.1.0/24 | dc_web (.20), dc_vpn (.30), dc_monitor (.40), dc_pub_dns (.53) |

### Routing path example (Enterprise A → Datacenter)

```
e1_pc1 → r_ent1 → isp_core → isp_r1 → isp_core → r_dc → dc_sw → dc_web
```

Traffic traverses `isp_core` twice (outbound to `isp_r1`, return from `isp_r1` to `r_dc`). Captures at `isp_core` interfaces therefore count each flow's bytes twice.

---

## Simulation Modes

### Normal Simulation

Started from the dashboard Overview page or via `POST /api/pipeline/start`. Spawns 14 persistent iperf3 flows covering all zones:

| Source | Destination | Protocol | Port | Target rate |
|--------|-------------|----------|------|-------------|
| e1_pc1 | dc_web | TCP | 5201 | 3 Mbps¹ |
| e1_erp | dc_web | TCP | 5202 | 5 Mbps¹ |
| e2_pc1 | dc_web | TCP | 5203 | 3 Mbps¹ |
| h1_pc | dc_web | TCP | 5204 | 2 Mbps¹ |
| h2_pc | dc_web | TCP | 5205 | 2 Mbps¹ |
| h2_nas | dc_web | TCP | 5206 | 3 Mbps¹ |
| e1_pc2 | dc_monitor | TCP | 5211 | 2 Mbps¹ |
| e2_pc2 | dc_monitor | TCP | 5212 | 2 Mbps¹ |
| e2_crm | dc_monitor | TCP | 5213 | 4 Mbps¹ |
| h1_tv | dc_monitor | UDP | 5214 | 2 Mbps |
| h2_cam | dc_monitor | UDP | 5215 | 1 Mbps |
| h1_iot | dc_monitor | UDP | 5216 | 1 Mbps |
| e1_pc1 | dc_vpn | TCP | 5221 | 1 Mbps¹ |
| e2_pc1 | dc_pub_dns | UDP | 5222 | 0.5 Mbps |

¹ **TCP `-b` rate is not enforced.** iperf3 TCP flows ignore the bandwidth hint and saturate at Mininet virtual-link speed (hundreds of Mbps). Only UDP flows respect the `-b` flag.

Each TCP source runs in a `while true; do iperf3 ...; sleep 0.5; done` loop so traffic is continuous with at most 0.5-second gaps between flow restarts.

An IDS snapshot runs every 90 seconds: a 10-second `tcpdump` capture on `dc_sw` interfaces is processed through the IDS heuristic pipeline.

### Realtime Pipeline

An alternative mode triggered via `POST /api/pipeline/start` with a shorter `interval_seconds`. Runs pcap capture → tshark feature extraction → IDS inference on a fixed cycle. The GNN inference engine runs independently on an 8-second telemetry poll regardless of pipeline mode.

### Anomaly Injection

Anomaly injection is available while any simulation is running. Each injection applies Linux `tc/netem` rules or traffic floods to the target host's interface.

| Type | Mechanism | GNN detection | IDS detection |
|------|-----------|---------------|---------------|
| `congestion` | 60 ms delay, 15 ms jitter, 4 Mbit cap | netem check → CONGESTION | — |
| `latency` | 300 ms delay, 80 ms jitter | netem check → LATENCY | — |
| `packet_loss` | 15 ms delay, 8% random loss | netem check → PACKET_LOSS | — |
| `jitter` | 80 ms delay, 60 ms jitter, 10 Mbit cap | netem check → JITTER | — |
| `brownout` | 200 ms delay, 5% loss, 1 Mbit cap | netem check → INFRA_FAILURE | — |
| `ddos` | UDP flood from h1_iot + h2_cam to dc_web | active injection label | P1 + P2 |
| `portscan` | nmap scan from attacker host | active injection label | P5 |
| `brute_force` | SSH brute force from attacker host | active injection label | P6 |

---

## GNN Inference Engine

**File:** `mininetDashboard/backend/gnn_inference.py`

**Model:** TemporalGAT — LSTM temporal encoder (bidirectional, 2 layers) feeding 3-layer Graph Attention Network with multi-head attention. Dual-head output: per-node classification and window-level classification.

**Inputs** (14 features per node, polled every 8 seconds):

| # | Feature | Source |
|---|---------|--------|
| 0–1 | bytes_sent, bytes_recv | `ip -s link` delta |
| 2–3 | pkts_sent, pkts_recv | `ip -s link` delta |
| 4 | pkt_drops | `ip -s link` delta |
| 5 | latency_ms | `ping` to gateway |
| 6 | jitter_ms | `ping` mdev |
| 7 | tcp_connections | `ss -s` |
| 8 | retransmits | `ss -s` |
| 9–10 | queue_depth_bytes, queue_depth_pkts | `tc -s qdisc` backlog |
| 11 | bandwidth_limit_mbit | `tc qdisc` rate |
| 12 | netem_delay_ms | `tc qdisc` delay |
| 13 | netem_loss_pct | `tc qdisc` loss |

**Sequence length:** 5 windows (40 seconds of history). No prediction is emitted until the buffer is full.

**Output classes** (9): `NORMAL`, `CONGESTION`, `LATENCY`, `PACKET_LOSS`, `JITTER`, `BANDWIDTH`, `INFRA_FAILURE`, `DDOS`, `SCANNING`

**Detection priority overrides** (applied after model prediction):

1. **Netem check** — if `netem_delay_ms > 100` or `netem_loss_pct > 2` on a node, overrides model output with the appropriate operational class regardless of model confidence
2. **Active injection pin** — when `inject_anomaly()` is active, the correct label is pinned for the injection duration
3. **Suppression** — `SCANNING` and `BRUTE_FORCE` are suppressed in normal simulation (TCP connection count mismatch between training distribution and Mininet persistent flows produces systematic false positives)
4. **JITTER / BANDWIDTH suppression** — suppressed unless an injection is currently active

**Confidence gate:** window-level ≥ 55%, node-level ≥ 50%

---

## IDS Pipeline

**File:** `mininetDashboard/backend/intelligence.py`

**Model:** `ids_pipeline.pkl` — sklearn `Pipeline(StandardScaler → RandomForestClassifier)` trained on 2420 synthetic samples with CICIDS-style flow features.

**Classification** runs as a 9-rule priority cascade (first matching rule wins):

| Priority | Rule | Label |
|----------|------|-------|
| P1 | `src_ip` in attacker set **and** `attack_hint` is not None | Simulated Attack |
| P2 | per-destination aggregate ≥ 50 MB/s AND per-flow > 1 MB/s AND dst_port not in iperf3 range | DDoS Multi-Source Flood |
| P3 | `byte_rate` > 50 MB/s AND dst_port not in iperf3 range | DDoS High Volume |
| P4 | `pkt_rate` > 5000 pkt/s AND dst_port not in iperf3 range | High Packet Rate |
| P5 | ≥ 8 distinct dst ports from same source | Port Scan |
| P6 | ≥ 5 flows to SSH/FTP/Telnet/SMTP/RDP ports from same source | Brute Force |
| P7 | dst_port in {80, 443, 8080, 8443} AND pkt_rate > 200 | HTTP Flood |
| P8 | web port, duration > 10s, byte_rate < 500 B/s | Slow DoS (Slowloris) |
| P9 | ML confidence ≥ 97% (iperf3 ports) or ≥ 90% (other) AND class ≠ BENIGN | ML classification |

**Constants:**
- `IPERF3_PORTS` = {5200–5330} — iperf3 flows are excluded from P2/P3/P4 because Mininet TCP runs at uncapped wire speed, not the requested bandwidth
- Attacker IPs for P1 = {192.168.10.31 (h1_iot), 192.168.20.21 (h2_cam)} — P1 only fires when `attack_hint` is set by an explicit attack injection; during normal simulation `attack_hint=None` so P1 is skipped even if these hosts are active

---

## Traffic Forecast

**Source:** GNN engine's internal `traffic_series` buffer, updated every 8 seconds.

The forecast is computed from the most recent historical values using an EWMA trend model:

1. Compute an exponentially-weighted moving average (`α = 0.35`) over the last 8 historical values
2. Estimate slope from the last 5 historical values
3. Apply a damping factor (`0.92^idx`) to the slope for each future step to prevent unbounded extrapolation
4. Compute confidence bands as `± std_dev × (1 + idx × 0.08)` where `std_dev` is measured from the last 12 historical values
5. Forecast 12 steps ahead (one per 30-second bucket)

When the network state is `DDOS`, the slope is biased upward (attack traffic is growing). When the state is `CONGESTION` or `INFRA_FAILURE`, the slope is biased downward.

The chart shows historical data on the left and predicted data on the right. Only available while the simulation is running.

---

## Traffic Scale

The dashboard shows 180–530 Mbps of aggregate traffic during normal simulation. This is expected and correct for this environment for two reasons:

1. **TCP ignores `-b`** — iperf3 TCP flows run at full Mininet virtual-link speed (~20–50 Mbps each per flow). The `-b` flag is only respected for UDP.
2. **Both-endpoint counting** — the GNN reads `bytes_sent + bytes_recv` on every non-router host. Since each flow has a sender and a receiver, bytes are counted twice. A true 20 Mbps flow appears as ~40 Mbps in aggregate.

Neither effect indicates an error. The GNN model was trained on data collected under the same conditions, so its predictions are consistent with these measurements.

---

## Dashboard Pages

| Page | Path | Data source | Poll interval |
|------|------|-------------|---------------|
| Overview | `/` | GNN + IDS combined | 8 s |
| Traffic Prediction | `/traffic-prediction` | GNN traffic_series | 30 s |
| Anomaly Detection | `/anomaly-detection` | IDS + GNN anomaly nodes | 30 s |
| Alerts | `/alerts` | IDS risk score + GNN events | 30 s |
| Simulation | `/simulation` | Lab pipeline status | on-demand |
| Data Generation | `/data-generation` | GNN data capture status | on-demand |
