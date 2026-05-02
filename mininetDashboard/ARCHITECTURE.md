# SDN Dashboard Architecture and Data Pipeline

## 1. What This Project Builds

This project provides a simulation-first SDN lab that combines:

- Multi-domain Mininet topology (enterprise, home, datacenter, ISP backbone)
- Flask backend APIs for topology, control, and data generation
- D3.js dashboard for interactive network visualization
- Packet capture and feature extraction pipeline for CICIDS-like flow datasets

The design goal is to bridge offline ML training and near-real-time inference by producing structured flow features from controlled network simulations.

## 2. Code Structure

- Entry point: `sdn_dashboard.py`
- Backend package: `backend/`
- UI template: `templates/index.html`
- Static assets: `static/css/dashboard.css`, `static/js/dashboard.js`
- Capture output: `captures/`

### Backend modules

- `backend/app.py`: Creates Flask app and starts Mininet bootstrap in background
- `backend/network_manager.py`: Owns Mininet lifecycle and thread-safe net object access
- `backend/topology.py`: Defines topology graph, router behavior, addressing, routes, and node classification
- `backend/services.py`: Stateless helpers for topology serialization, path computation, ping, and controller flow reads
- `backend/routes.py`: HTTP API layer; validates input and delegates to service modules
- `backend/lab.py`: Dataset lab pipeline (capture, traffic generation, feature extraction/export)
- `backend/intelligence.py`: Baseline IDS and forecasting logic; future home for graph-based prediction adapters

## 3. Topology Model

The topology emulates multiple administrative domains:

- ISP/backbone:
  - `isp_core` switch
  - `isp_r1` router

- Enterprise A:
  - `r_ent1`, `ent1_sw`
  - `e1_pc1`, `e1_pc2`, `e1_dns`, `e1_dhcp`, `e1_erp`

- Enterprise B:
  - `r_ent2`, `ent2_sw`
  - `e2_pc1`, `e2_pc2`, `e2_dns`, `e2_dhcp`, `e2_crm`

- Home A:
  - `r_home1`, `home1_sw`
  - `h1_pc`, `h1_tv`, `h1_iot`

- Home B:
  - `r_home2`, `home2_sw`
  - `h2_pc`, `h2_cam`, `h2_nas`

- Datacenter:
  - `r_dc`, `dc_sw`
  - `dc_pub_dns`, `dc_web`, `dc_vpn`, `dc_monitor`

### Addressing and routing

- Transit network: `10.255.0.0/24`
- Enterprise A: `10.10.1.0/24`
- Enterprise B: `10.20.1.0/24`
- Home A: `192.168.10.0/24`
- Home B: `192.168.20.0/24`
- Datacenter: `172.16.1.0/24`

Spoke routers use default route to `isp_r1`. `isp_r1` has explicit routes to each spoke LAN.

## 4. Backend Runtime Flow

1. `sdn_dashboard.py` calls `create_app()`.
2. `backend/app.py` registers routes and triggers `NetworkManager.start_async()`.
3. `backend/network_manager.py` launches Mininet in a background thread:
   - Executes `mn -c`
   - Builds topology
   - Starts switches/controllers
   - Applies IPs/routes/resolver config via `configure_network()`
4. APIs become available immediately; topology/lab endpoints return startup errors until Mininet is ready.

## 6. Planned Predictive Layer

The current backend already supports reactive anomaly detection and traffic forecasting. The next enhancement is a graph-aware predictive layer that uses topology and flow relationships to forecast congestion and operational anomalies before they become visible to the operator.

Recommended flow:

1. Capture traffic and extract flow/window features.
2. Build a topology-aware graph snapshot from nodes, links, and active flows.
3. Run a GNN or graph-temporal model to predict congestion and anomaly risk.
4. Feed the output to a decision engine for reroute, throttle, or priority actions.
5. Expose the prediction and action status through the same dashboard APIs.

## 5. API Endpoints

### Core dashboard APIs

- `GET /api/topology`: node/link graph payload (type + zone metadata)
- `POST /api/path`: shortest path between two nodes (BFS)
- `POST /api/ping`: connectivity test from selected source to destination
- `GET /api/flows`: flow tables from Ryu OFCTL REST API

Compatibility aliases are also exposed (`/topology`, `/path`, `/ping`, `/flows`).

### Dataset lab APIs

- `GET /api/lab/status`: capture/traffic/export state
- `POST /api/lab/capture/start`: starts tcpdump on switch interfaces
- `POST /api/lab/capture/stop`: stops active capture processes
- `POST /api/lab/traffic/start`: starts synthetic mixed traffic thread
- `POST /api/lab/traffic/stop`: stops traffic thread
- `POST /api/lab/export`: parses PCAPs and writes CICIDS-like flow CSV

## 6. UI Runtime Flow

1. Browser loads `templates/index.html`.
2. `static/js/dashboard.js` calls `/api/topology` and renders force graph.
3. User selects two endpoint nodes for path/ping operations.
4. Lab controls call capture/traffic/export endpoints and render status/output.
5. Lab status is polled every 4 seconds for near-real-time feedback.

## 7. Dataset Generation Pipeline

### Capture strategy

- Capture points: switch interfaces (global SDN vantage point)
- Tool: `tcpdump`
- Output: one PCAP per monitored interface under `captures/`

### Traffic simulation

`backend/lab.py` generates mixed traffic:

- Benign patterns:
  - ICMP pings across enterprise/home/datacenter hosts
  - HTTP requests to `dc_web`
  - UDP bursts for non-ICMP variation
- Suspicious pattern:
  - Bursty ICMP traffic from IoT-like sources

### Feature extraction

- Tool: `tshark`
- Extracted packet fields:
  - timestamp, src/dst IP, src/dst ports (TCP/UDP), protocol, frame length
- Flow construction:
  - bidirectional 5-tuple aggregation with reverse-flow matching
- Derived CICIDS-like statistics:
  - duration, fwd/bwd packets and bytes
  - packet length mean/max/std
  - flow bytes/s and packets/s
  - flow IAT mean/std/max
  - active/idle mean/std
  - label (`BENIGN` or `MALICIOUS_SIM`)

Output CSV path format:

- `captures/<capture_id>_flows.csv`

## 8. Required Runtime Dependencies

- Mininet + Open vSwitch
- Ryu controller with `ryu.app.simple_switch_13` and `ryu.app.ofctl_rest`
- `tcpdump` for packet capture
- `tshark` for packet decoding and flow feature generation

## 9. Typical Lab Run Sequence

1. Start OVS service.
2. Start Ryu controller.
3. Launch app with root privileges.
4. In dashboard:
   - Start Capture
   - Run Traffic
   - Stop Traffic
   - Stop Capture
   - Export CICIDS-Like CSV

## 10. Notes on Scope

- Current labels are simulation labels, not ground-truth IDS classes.
- Feature set is aligned with CICIDS-style flow statistics but is intentionally lightweight.
- This pipeline is intended for controlled experimentation and prototyping, not direct production deployment.
