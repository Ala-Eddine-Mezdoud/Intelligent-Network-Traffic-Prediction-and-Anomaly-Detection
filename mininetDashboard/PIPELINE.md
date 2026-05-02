# AI-SDN Pipeline Guide

## 1. Purpose

This document explains the current runtime pipeline used in this project to simulate a realistic AI-assisted SDN workflow.

The pipeline combines:

- Mininet network simulation (data plane)
- Ryu SDN controller (control plane)
- Telemetry capture + feature extraction
- AI inference stage (intelligence plane)
- Web dashboard for monitoring and operations

## 2. Deployment Model (Current and Recommended)

The recommended setup for this project stage is:

- Run controller, capture pipeline, AI logic, and dashboard backend on the Linux VM OS (server near SDN).
- Use Mininet hosts only as simulated endpoints generating traffic.
- Access dashboard from Windows or other hosts using the VM bridged IP.

Important: the VM OS is the control/intelligence server. It is not a Mininet host namespace.

## 3. Pipeline Layers

### 3.1 Data Plane

- Hosts generate traffic across links, switches, and routers.
- Switches/routers forward traffic according to their configuration.

### 3.2 Telemetry Capture Layer

- `tcpdump` is launched on selected switch interfaces.
- Captures are written to PCAP files under `captures/`.

### 3.3 Collector Relay Layer

- Captured PCAP files are copied to a collector inbox folder.
- A manifest file is generated to represent a handoff event.

This simulates real-world telemetry shipping from capture agents to a collector service.

### 3.4 Feature Extraction Layer

- Collector reads relayed PCAP files.
- `tshark` decodes packet fields.
- Flow aggregation computes CICIDS-like features (duration, rates, IAT stats, packet length stats, etc.).

### 3.5 Intelligence Plane

- Extracted flow rows are passed to the AI inference stage.
- Current implementation outputs risk score, severity, suspicious flow count, and reasons.
- Inference report is saved as JSON.
- Planned extension: topology-aware graph prediction for congestion, hotspot detection, and operational anomaly forecasting.

### 3.6 Dashboard and Decision Layer

- Dashboard queries status/results through API endpoints.
- Operator sees topology, traffic status, flow exports, and AI output.
- Decision policy can then push control actions through SDN/controller integrations.

## 4. End-to-End Sequence

1. Start Mininet and controller.
2. Start capture on switch interfaces.
3. Start synthetic traffic generation.
4. Stop traffic.
5. Stop capture.
6. Relay captured traces to collector inbox.
7. Run collector extraction + AI inference.
8. Optionally export CICIDS-like CSV for training/evaluation.
9. View output and alerts on dashboard.

## 5. API Endpoints Used in Pipeline

### Core

- `GET /api/topology`
- `POST /api/path`
- `POST /api/ping`
- `GET /api/flows`

### Lab and AI Pipeline

- `GET /api/lab/status`
- `POST /api/lab/capture/start`
- `POST /api/lab/capture/stop`
- `POST /api/lab/traffic/start`
- `POST /api/lab/traffic/stop`
- `POST /api/lab/relay`
- `POST /api/lab/infer`
- `POST /api/lab/export`

## 6. Storage Paths

- Raw captures: `captures/<capture_id>_*.pcap`
- Collector inbox: `captures/collector_inbox/<capture_id>/`
- Collector flow CSV: `captures/intelligence_out/<capture_id>_collector_flows.csv`
- Inference report: `captures/intelligence_out/<capture_id>_inference.json`
- Training/export CSV: `captures/<capture_id>_flows.csv`

## 7. What Is Simulated vs. Real-World Equivalent

### Simulated now

- Capture agents and collector are on the same VM host.
- Handoff is simulated by file relay/copy.

### Real-world equivalent

- Switch telemetry/agents send data to remote collector (IPFIX/sFlow/stream bus).
- Collector extracts standardized features.
- AI service runs inference and sends decisions to controller/policy engine.

## 8. Current Strengths

- Multi-domain network simulation for varied traffic paths.
- Repeatable dataset generation flow.
- Explicit collector and intelligence stages.
- Dashboard-driven operational workflow.

## 9. Simulated vs Real-World (Detailed)

| Pipeline Step | Simulated in This Project | Typical Real-World Behavior |
|---|---|---|
| Traffic generation | Synthetic traffic from Mininet hosts | User/app traffic from real clients, servers, and services |
| Traffic visibility point | Switch interfaces (good SDN vantage point) | Switch/router telemetry exporters, taps, SPAN, packet brokers |
| Packet capture transport | Local `tcpdump` writes PCAP to local disk | Remote telemetry export over network (IPFIX/sFlow/NetFlow/stream bus) |
| Collector handoff | File relay/copy into collector inbox | Networked collector services ingest telemetry continuously |
| Feature extraction | Batch extraction from PCAP files | Streaming or micro-batch feature pipelines |
| AI inference | Triggered job run (per capture/session) | Continuous near-real-time scoring over sliding windows |
| Decision actuation | Manual/operator-driven next step | Automated policy engine pushing SDN or network actions |
| Dashboard access | Web UI served by VM server and viewed remotely | Central monitoring portal for multiple operators |

## 10. Recommended Path Forward

Use a two-phase strategy:

### Phase 1 (Current Baseline)

- Keep the current co-located simulation pipeline.
- Use it for fast iteration, model validation, and dataset generation.
- Report model accuracy and detection behavior in controlled scenarios.

### Phase 2 (Production-Like Extension)

- Separate capture agents, collector, feature service, and inference service as independent components.
- Replace file relay with network telemetry transport.
- Run continuous inference and expose a live predictions API to the dashboard.
- Add closed-loop decisions (reroute/rate-limit/block) with rollback logic.

This approach preserves development speed now and strengthens real-world credibility in final evaluation.
