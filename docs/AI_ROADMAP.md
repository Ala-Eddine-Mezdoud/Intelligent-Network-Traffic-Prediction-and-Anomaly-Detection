# AI Traffic Prediction and Anomaly Prevention Roadmap

## 1. What the current models can and cannot do

The current models were trained on CICIDS 2017. That dataset is useful for intrusion detection because it contains labeled attack traffic such as DDoS, port scanning, brute force, and web attacks. It is not a complete dataset for operational network behavior, especially things like congestion buildup, queue growth, service saturation, packet loss, or link-utilization prediction.

So the short answer is:

- Yes, you likely need new data if your goal includes operational anomalies and proactive congestion prevention.
- No, you should not delete the current models immediately.
- Keep the current models as a baseline and fallback while you build the next version.

The current CICIDS-based IDS is still valuable for security detection, but it does not fully solve anomaly prediction or congestion prevention.

## 2. What should be changed in the architecture

The current architecture is good as a simulation and data-collection lab, but it needs enhancement rather than a full replacement.

Recommended direction:

- Keep Mininet, Ryu, the dashboard, and the capture pipeline.
- Extend the telemetry layer so it collects time-window metrics, not only packet/flow snapshots.
- Add a prediction layer for congestion, service saturation, and anomaly risk.
- Add a decision engine that can take preventive actions before a problem becomes visible to the operator.

This means the project should evolve from:

`capture -> extract -> detect -> alert`

to:

`capture -> aggregate -> predict -> decide -> act -> verify`

## 3. Should you use GNN?

GNN is a strong candidate, but it should not be treated as the first and only answer.

Use cases where GNN helps:

- Topology-aware prediction.
- Congestion propagation across switches, routers, and links.
- Multi-hop effects where one overloaded node affects others.
- Modeling flows as relationships rather than isolated rows.

When GNN is better than a plain tabular model:

- You want to predict network-wide state, not just classify flows.
- You want the model to understand the topology.
- You want to estimate which link or node will become hot next.

When GNN is not enough by itself:

- You still need time-aware modeling for forecasting.
- You still need good labels for congestion and operational anomalies.
- You still need a practical decision layer that converts predictions into actions.

Best practical path:

- Start with a strong baseline forecasting model.
- Add topology features and graph-based features.
- Move to a temporal GNN once the dataset and pipeline are ready.

### 3.1 How GNN fits the project

A practical GNN design for this project is:

- Nodes: switches, routers, hosts, and optionally services.
- Edges: physical links, active flows, or aggregated communication pairs.
- Node features: interface load, queue length, packet rate, byte rate, latency, jitter, CPU or service load.
- Edge features: utilization, packet bursts, flow count, throughput, and recent trend.
- Output targets: next-window congestion risk, hot links, overloaded nodes, and anomaly probability.

Recommended training setup:

- Build a graph snapshot for each time window.
- Stack snapshots over time to capture temporal behavior.
- Start with a simple GCN or GraphSAGE baseline.
- Move to a temporal GNN or attention-based model after the baseline works.

What GNN should be used for here:

- Predict which link or node will saturate next.
- Predict whether a local anomaly will spread to neighboring parts of the topology.
- Support the decision engine with topology-aware risk scores.

## 4. Do you need to capture new data?

Yes, if you want anomaly prediction and congestion prevention.

Current CICIDS-style labels are mainly about attack detection. They do not fully cover:

- Congestion before it happens.
- CPU or service saturation.
- Queue growth on links.
- Latency and jitter spikes.
- Packet loss under load.
- Brownouts or partial failures.

You need new data that includes normal, heavy-load, and degraded operational conditions.

Suggested data categories:

- Normal traffic.
- Heavy but healthy traffic.
- Congestion-prone traffic.
- Service saturation traffic.
- Fault-injection traffic.
- Attack traffic.

## 5. Current simulation quality

The current simulation is useful but too limited if the target is realistic prediction.

What is good already:

- Multi-domain topology.
- Real Mininet environment.
- Ryu controller integration.
- Capture and flow extraction.
- Model-backed inference path.

What is weak right now:

- Limited protocol diversity.
- Too much synthetic behavior that is not close to real enterprise traffic.
- Not enough heavy continuous traffic.
- Not enough application-layer realism.
- Not enough operational failure scenarios.

So the simulation should be enhanced, not replaced immediately.

## 6. Heavy and more realistic traffic to add

Add these traffic classes to the simulation tasks:

- Video streaming traffic.
- Audio streaming and VoIP traffic.
- Large HTTPS downloads.
- File upload and backup traffic.
- Web browsing bursts.
- Cloud synchronization traffic.
- DNS-heavy bursts.
- MQTT or IoT telemetry.
- SSH and remote administration traffic.
- Database replication traffic.
- VPN or encrypted tunnel traffic.
- API microservice traffic.
- Real-time messaging traffic.

Useful tooling and services for simulation:

- `iperf3` for sustained bandwidth load.
- `wrk` or `ab` for HTTP stress.
- `curl` and `wget` for client bursts.
- `ffmpeg` or local HLS/DASH serving for streaming-like traffic.
- `mosquitto` for MQTT-style telemetry.
- `rtsp-simple-server` or similar for streaming control-plane tests.
- `nc`, `socat`, or custom Python clients for protocol diversity.

## 7. Detailed tasks to achieve the target system

### Phase A: Define the target problem clearly ✅ DONE

- ✅ Separate security anomaly detection from operational anomaly prediction.
- ✅ Define what counts as congestion, failure, and saturation — see label taxonomy in `DATA_GENERATION.md`.
- ✅ Decide the prediction horizon — multi-horizon: 15s, 30s, 60s.
- Define success metrics for each task.

### Phase B: Build the right dataset ✅ DONE

- ✅ Keep the current CICIDS 2017-trained IDS as a benchmark.
- ✅ Capture new traffic in Mininet with realistic heavy workloads — `services_heavy.py` (iperf3).
- ✅ Introduce operational anomalies intentionally — 12 scenarios in `scenarios.py`.
- ✅ Label data for normal, congested, degraded, and attack states — `labeling.py`.
- ✅ Record link load, latency, jitter, queue length, packet loss — `telemetry.py` (14 node + 6 edge features).
- ✅ Save time-windowed telemetry — `graph_export.py` (PyG JSON + tabular CSV).

### Phase C: Improve the simulation environment ✅ DONE

- ✅ Expand traffic generation — 16+ protocol types in baseline mix.
- ✅ Add realistic service emulation — HTTP, RTSP, MQTT, VoIP via iperf3 sustained flows.
- ✅ Increase background traffic variety — continuous baseline traffic during all scenarios.
- ✅ Add burst traffic and long-lived flows — iperf3 TCP/UDP with configurable duration.
- ✅ Inject link failures, bandwidth throttling, latency changes — netem-based injection in scenarios.

### Phase D: Improve feature engineering ✅ DONE

- ✅ Build sliding-window features over time — 5s window telemetry collection.
- ✅ Add topology-aware features for nodes and links — per-node and per-edge feature vectors.
- ✅ Extract flow rate, byte rate, packet burstiness — differential counters per window.
- ✅ Add queue and utilization metrics — tc qdisc stats.
- ✅ Add lagged features for forecasting — multi-horizon predictive labels (15s, 30s, 60s).

### Phase E: Train predictive models

- Keep the current IDS model for attack detection.
- Train a forecasting model for traffic load and congestion.
- Train a separate operational anomaly predictor.
- Evaluate a tabular baseline before moving to GNN.
- Move to temporal GNN when graph data and labels are ready.

### Phase F: Add a decision engine

- Create a rule-based decision engine first.
- Trigger preventive actions when predicted congestion crosses thresholds.
- Add rerouting, rate limiting, or priority changes.
- Add rollback logic so actions can be undone safely.
- Log every decision and its outcome.

### Phase G: Integrate with SDN control

- Expose controller actions through backend APIs.
- Send flow mods or policy updates to Ryu.
- Verify that the action reduced load or avoided congestion.
- Add policy safety checks so the controller does not overreact.

### Phase H: Improve observability and evaluation

- Add confusion matrix, precision, recall, and F1 for attacks.
- Add MAE and RMSE for traffic prediction.
- Add congestion prediction lead time.
- Measure false positives and false negatives.
- Measure end-to-end latency from capture to decision.
- Measure system throughput and stability under load.
