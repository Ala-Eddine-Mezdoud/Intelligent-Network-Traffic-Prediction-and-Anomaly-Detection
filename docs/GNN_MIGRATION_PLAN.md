# GNN-Powered Network Operations Platform: Technical Migration Report

**Version:** 1.0  
**Date:** April 2026  
**Classification:** Technical Architecture Document

---

## Executive Summary

This document provides a comprehensive migration plan to transform the existing Network Traffic Prediction & Anomaly Detection platform into a topology-aware Graph Neural Network (GNN) powered intelligent network operations platform. The migration leverages existing Mininet simulation infrastructure, FastAPI backend, and Next.js frontend while introducing graph-based ML pipelines for superior anomaly detection, predictive maintenance, and automated remediation.

---

## 1. Current State Assessment

### 1.1 Existing Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CURRENT ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────────┐  │
│  │   Mininet    │───▶│   Flask API  │───▶│      Next.js Dashboard       │  │
│  │ Simulation   │    │  (Dashboard)  │    │   (React + Recharts)         │  │
│  └──────────────┘    └──────────────┘    └──────────────────────────────┘  │
│         │                   │                                              │
│         │                   ▼                                              │
│         │            ┌──────────────┐                                    │
│         │            │  FastAPI ML    │                                    │
│         └───────────▶│  (models_api)  │                                    │
│                      └──────────────┘                                    │
│                           │                                               │
│                    ┌──────┴──────┐                                        │
│                    ▼              ▼                                        │
│            ┌──────────┐  ┌──────────┐                                   │
│            │ XGBoost  │  │ Sklearn  │                                   │
│            │ Forecast │  │   IDS    │                                   │
│            └──────────┘  └──────────┘                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Strengths to Preserve

| Component | Strength | Preservation Strategy |
|-----------|----------|----------------------|
| **Mininet Topology** | Realistic multi-zone ISP/Enterprise/Home/DC topology with 26 nodes | Extend with dynamic topology generator; keep RealWorldTopo as baseline |
| **Packet Capture Pipeline** | tcpdump → tshark → CSV flow features | Reuse for graph feature extraction; add temporal snapshotting |
| **API Layer** | FastAPI with Pydantic schemas, modular routing | Keep route structure; add GNN inference endpoints |
| **Dashboard** | Next.js + Recharts, dark theme, real-time updates | Extend with graph visualization using D3/Cytoscape.js |
| **Traffic Generation** | LabPipeline with benign/suspicious pattern simulation | Enhance with configurable anomaly injection engine |
| **SDN Integration** | Ryu controller integration, flow table queries | Extend for programmatic flow modification |

### 1.3 Weaknesses & Technical Debt

| Issue | Impact | Blocker Level |
|-------|--------|---------------|
| **Flat Feature Vectors** | XGBoost/sklearn operate on tabular data without topology context | **CRITICAL** - Core limitation for GNN migration |
| **Mock Data Generation** | `generate_mock_network_flows()` creates synthetic features without network correlation | **HIGH** - Breaks topology-awareness |
| **No Graph Representation** | Network topology exists only for visualization, not ML | **CRITICAL** - GNN requires graph structure |
| **Simulated Intelligence** | `IntelligencePlane` uses threshold-based rules, not learned patterns | **HIGH** - Replace with trained GNN |
| **Disconnected Pipelines** | Mininet capture → CSV export → manual model training | **MEDIUM** - Needs unified data pipeline |
| **No Temporal Modeling** | Current models are stateless; no sequence/graph dynamics | **HIGH** - Requires Temporal GNN |
| **Hardcoded Anomaly Injection** | Attacker IPs hardcoded in `lab.py` | **MEDIUM** - Needs configurable scenario engine |

### 1.4 Bottlenecks Blocking GNN Migration

1. **Data Format Mismatch**: Current flow-based CSV format loses graph connectivity
2. **Static Training**: Models trained offline on CICIDS2017; no online learning
3. **No Node Embeddings**: Missing representation learning for network devices
4. **No Edge Features**: Link characteristics (latency, bandwidth) not encoded
5. **Missing Temporal Dimension**: Graph snapshots not captured over time

---

## 2. New Target Architecture (Full GNN System)

### 2.1 High-Level System Design

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                    GNN-POWERED INTELLIGENT NETWORK OPERATIONS PLATFORM                        │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                           SIMULATION & DATA LAYER                                    │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │ │
│  │  │   Mininet    │  │   Topology   │  │   Anomaly    │  │   Traffic    │            │ │
│  │  │   Network    │──▶│   Graph      │──▶│   Injection  │──▶│   Generator  │            │ │
│  │  │   (RealWorld │  │   Extractor  │  │   Engine     │  │   (iPerf3/   │            │ │
│  │  │    Topo+)    │  │              │  │              │  │   Scapy)     │            │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘            │ │
│  │         │                 │                                                            │ │
│  │         ▼                 ▼                                                            │ │
│  │  ┌──────────────────────────────────────────────────────────────────────────────┐   │ │
│  │  │                    REAL-TIME TELEMETRY COLLECTOR                              │   │ │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │   │ │
│  │  │  │tcpdump   │  │sFlow/    │  │OpenFlow  │  │SNMP      │  │Router    │      │   │ │
│  │  │  │Capture   │  │NetFlow   │  │Stats     │  │Polling   │  │CLI Stats │      │   │ │
│  │  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │   │ │
│  │  │       └─────────────┴─────────────┴─────────────┴─────────────┘            │   │ │
│  │  │                              │                                               │   │ │
│  │  │                              ▼                                               │   │ │
│  │  │                    ┌──────────────────┐                                    │   │ │
│  │  │                    │  Graph Dataset   │                                    │   │ │
│  │  │                    │  Generator       │                                    │   │ │
│  │  │                    │  (PyG/PyTorch)   │                                    │   │ │
│  │  │                    └────────┬─────────┘                                    │   │ │
│  │  └───────────────────────────────┼──────────────────────────────────────────────┘   │ │
│  └──────────────────────────────────┼────────────────────────────────────────────────────┘ │
│                                     │                                                      │
│  ┌──────────────────────────────────┼────────────────────────────────────────────────────┐ │
│  │                         AI/ML ENGINE LAYER                                          │ │
│  │                              │                                                     │ │
│  │  ┌───────────────────────────┴───────────────────────────┐                           │ │
│  │  │              GNN TRAINING PIPELINE                   │                           │ │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  │                           │ │
│  │  │  │GraphSAGE   │  │    GAT     │  │  STGNN     │  │                           │ │
│  │  │  │Node/Edge   │  │  Attention │  │ (Temporal) │  │                           │ │
│  │  │  │Classifier  │  │  Network   │  │            │  │                           │ │
│  │  │  └────────────┘  └────────────┘  └────────────┘  │                           │ │
│  │  │       │                 │                │       │                           │ │
│  │  │       └─────────────────┴────────────────┘       │                           │ │
│  │  │                       │                          │                           │ │
│  │  │                       ▼                          │                           │ │
│  │  │              ┌──────────────────┐               │                           │ │
│  │  │              │  Model Registry  │               │                           │ │
│  │  │              │  (MLflow/Local)  │               │                           │ │
│  │  │              └──────────────────┘               │                           │ │
│  │  └──────────────────────────────────────────────────┘                           │ │
│  │                              │                                                 │ │
│  │                              ▼                                                 │ │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                    LIVE INFERENCE ENGINE                                  │ │ │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐        │ │ │
│  │  │  │  Sliding   │  │  Graph     │  │  GNN       │  │  Anomaly   │        │ │ │
│  │  │  │  Window    │──▶│  Builder   │──▶│  Encoder   │──▶│  Scoring   │        │ │ │
│  │  │  │  (T=60s)   │  │  (PyG)     │  │  (GPU)     │  │  (Softmax) │        │ │ │
│  │  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘        │ │ │
│  │  └────────────────────────────────────────────────────────────────────────────┘ │ │
│  │                              │                                                 │ │
│  │                              ▼                                                 │ │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │              PREDICTIVE MAINTENANCE ENGINE                                  │ │ │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐        │ │ │
│  │  │  │  Link      │  │  Capacity  │  │  Route     │  │  Failure   │        │ │ │
│  │  │  │  Failure   │  │  Exhaustion│  │  Instability│  │  Risk Score│        │ │ │
│  │  │  │  Predictor │  │  Predictor │  │  Predictor │  │  (Ensemble)│        │ │ │
│  │  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘        │ │ │
│  │  └────────────────────────────────────────────────────────────────────────────┘ │ │
│  │                              │                                                 │ │
│  │                              ▼                                                 │ │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │              INTELLIGENT DECISION ENGINE                                    │ │ │
│  │  │                                                                             │ │ │
│  │  │   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐       │ │ │
│  │  │   │  Rule-Based     │    │  Reinforcement  │    │  Hybrid Policy  │       │ │ │
│  │  │   │  Expert System  │◄──►│  Learning Agent │◄──►│  Executor       │       │ │ │
│  │  │   │  (IF-THEN-ELSE) │    │  (PPO/SAC)      │    │  (Priority      │       │ │ │
│  │  │   │                 │    │                 │    │  Arbitration)   │       │ │ │
│  │  │   └─────────────────┘    └─────────────────┘    └─────────────────┘       │ │ │
│  │  │                              │                                              │ │ │
│  │  │                              ▼                                              │ │ │
│  │  │   ┌────────────────────────────────────────────────────────────────────┐   │ │ │
│  │  │   │                    ACTION CANDIDATES                                │   │ │ │
│  │  │   │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │   │ │ │
│  │  │   │  │Reroute │ │Isolate │ │Throttle│ │Load    │ │Priority│ │Trigger │ │   │ │ │
│  │  │   │  │Traffic │ │Node    │ │Flow    │ │Balance │ │QoS     │ │Alert   │ │   │ │ │
│  │  │   │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ │   │ │ │
│  │  │   └────────────────────────────────────────────────────────────────────┘   │ │ │
│  │  │                              │                                              │ │ │
│  │  │                              ▼                                              │ │ │
│  │  │   ┌────────────────────────────────────────────────────────────────────┐   │ │ │
│  │  │   │                 AUTO-REMEDIATION / SELF-HEALING                       │   │ │ │
│  │  │   │                                                                             │ │ │
│  │  │   │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐     │   │ │ │
│  │  │   │  │  OpenFlow   │  │  BGP/OSPF   │  │  Linux TC   │  │  Node      │     │   │ │ │
│  │  │   │  │  Flow Mods  │  │  Route      │  │  (Traffic   │  │  Quarantine│     │   │ │ │
│  │  │   │  │  (Add/Del)  │  │  Injection  │  │  Shaping)   │  │  (ebtables)│     │   │ │ │
│  │  │   │  └────────────┘  └────────────┘  └────────────┘  └────────────┘     │   │ │ │
│  │  │   └────────────────────────────────────────────────────────────────────┘   │ │ │
│  │  └────────────────────────────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                                   │
│  ┌──────────────────────────────────┼────────────────────────────────────────────────┐ │
│  │                         API & PRESENTATION LAYER                                   │ │
│  │                              │                                                     │ │
│  │  ┌───────────────────────────┴───────────────────────────┐                         │ │
│  │  │              BACKEND APIs (FastAPI)                   │                         │ │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐      │                         │ │
│  │  │  │ /gnn/      │  │ /predictive│  │ /actions/  │      │                         │ │
│  │  │  │ inference  │  │ /maintenance│  │ execute  │      │                         │ │
│  │  │  │ /topology  │  │ /decisions │  │ /remediate │      │                         │ │
│  │  │  │ /anomalies │  │ /risk      │  │ /explain   │      │                         │ │
│  │  │  └────────────┘  └────────────┘  └────────────┘      │                         │ │
│  │  └────────────────────────────────────────────────────────┘                         │ │
│  │                              │                                                       │ │
│  │                              ▼                                                       │ │
│  │  ┌────────────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                    FRONTEND DASHBOARD (Next.js + D3.js)                         │ │ │
│  │  │                                                                                 │ │ │
│  │  │   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐          │ │ │
│  │  │   │  Network    │  │  GNN        │  │  Anomaly   │  │  Decision   │          │ │ │
│  │  │   │  Topology   │  │  Embedding  │  │  Heatmap   │  │  Timeline   │          │ │ │
│  │  │   │  Graph      │  │  Visualizer │  │            │  │            │          │ │ │
│  │  │   │  (Cytoscape)│  │  (t-SNE)    │  │            │  │            │          │ │ │
│  │  │   └────────────┘  └────────────┘  └────────────┘  └────────────┘          │ │ │
│  │  │                                                                                 │ │ │
│  │  │   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐          │ │ │
│  │  │   │  Traffic   │  │  Predictive│  │  Action    │  │  Model     │          │ │ │
│  │  │   │  Forecast  │  │  Alerts    │  │  Recommend │  │  Performance│          │ │ │
│  │  │   │            │  │            │  │            │  │            │          │ │ │
│  │  │   └────────────┘  └────────────┘  └────────────┘  └────────────┘          │ │ │
│  │  └────────────────────────────────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                           │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                           STORAGE LAYER                                               │ │
│  │                                                                                       │ │
│  │   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐   │ │
│  │   │  Graph     │  │  Time-Series│  │  Model     │  │  Event     │  │  Action    │   │ │
│  │   │  Database  │  │  Database   │  │  Registry  │  │  Log       │  │  Log       │   │ │
│  │   │  (Neo4j/   │  │  (InfluxDB/ │  │  (MLflow/  │  │  (PostgreSQL│  │  (Redis/   │   │ │
│  │   │  NetworkX) │  │  TimescaleDB│  │  SQLite)   │  │  /Timescale)│  │  Kafka)    │   │ │
│  │   └────────────┘  └────────────┘  └────────────┘  └────────────┘  └────────────┘   │ │
│  └──────────────────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Specifications

#### 2.2.1 Mininet + SDN Simulation Layer

**Capabilities:**
- Multi-tier topology (ISP Core, Enterprise, Home, Datacenter)
- SDN controller (Ryu) with OpenFlow 1.3
- Router emulation with Linux namespaces
- Programmable traffic generation

**GNN Extensions:**
```python
# New: Dynamic topology generator with graph export
class GNNEnabledTopo(RealWorldTopo):
    def export_graph_snapshot(self, timestamp: float) -> dict:
        """Export topology as graph for GNN processing."""
        return {
            "timestamp": timestamp,
            "nodes": self._get_node_features(),  # CPU, memory, interfaces
            "edges": self._get_edge_features(),  # bandwidth, latency, utilization
            "adjacency": self._get_adjacency_matrix(),
            "flows": self._get_active_flows(),
        }
```

#### 2.2.2 Topology Graph Extraction Pipeline

**Input:** Live Mininet network state  
**Output:** PyTorch Geometric `Data` objects

```
Raw Network State
       │
       ▼
┌──────────────────┐
│ Node Feature     │  → CPU load, memory, interface stats
│ Extractor        │  → Role encoding (router/switch/host)
└────────┬─────────┘
         │
┌────────▼─────────┐
│ Edge Feature     │  → Bandwidth, latency, packet loss
│ Extractor        │  → Error rates, queue depth
└────────┬─────────┘
         │
┌────────▼─────────┐
│ Graph Builder    │  → PyG Data object
│ (PyTorch Geo)    │  → Adjacency + Features
└────────┬─────────┘
         │
┌────────▼─────────┐
│ Temporal         │  → DynamicGraphTemporalSignal
│ Snapshot Store   │  → Sequence of graph states
└──────────────────┘
```

**Node Features (dim=32):**
| Feature | Type | Description |
|---------|------|-------------|
| `node_type` | One-hot(6) | router, switch, host, controller, dns, iot |
| `zone` | One-hot(6) | enterprise-a, enterprise-b, home-a, home-b, dc, backbone |
| `cpu_load` | Float | Current CPU utilization (0-1) |
| `memory_usage` | Float | Memory utilization (0-1) |
| `interface_count` | Int | Number of active interfaces |
| `packet_rate` | Float | Packets per second |
| `byte_rate` | Float | Bytes per second |
| `error_rate` | Float | Packet errors per second |
| `flow_count` | Int | Number of active flows |
| `degree` | Int | Graph degree (number of neighbors) |
| `betweenness` | Float | Betweenness centrality (precomputed) |

**Edge Features (dim=16):**
| Feature | Type | Description |
|---------|------|-------------|
| `bandwidth_mbps` | Float | Link capacity |
| `utilization` | Float | Current utilization (0-1) |
| `latency_ms` | Float | Measured RTT |
| `packet_loss` | Float | Loss rate (0-1) |
| `queue_depth` | Int | Current queue length |
| `errors` | Int | Error count |
| `flow_count` | Int | Number of flows using this link |

**Global Features (dim=8):**
| Feature | Description |
|---------|-------------|
| `timestamp` | Unix timestamp |
| `total_nodes` | Number of nodes |
| `total_edges` | Number of edges |
| `avg_utilization` | Network-wide average |
| `anomaly_score` | Current global anomaly level |

#### 2.2.3 Real-Time Telemetry Collectors

| Collector | Source | Frequency | Output |
|-----------|--------|-----------|--------|
| `SwitchStatsCollector` | Ryu REST API | 5s | Flow tables, port stats |
| `RouterStatsCollector` | Linux `/proc`, `ss` | 10s | Interface counters, routes |
| `HostStatsCollector` | Mininet `host.cmd()` | 10s | Process stats, connections |
| `LinkStatsCollector` | Custom ping/iperf | 30s | Latency, bandwidth |
| `PacketCaptureCollector` | tcpdump | Event-driven | PCAP for deep inspection |

#### 2.2.4 Graph Dataset Generation Engine

**Dataset Structure:**
```
gnn_dataset/
├── snapshots/
│   ├── snapshot_000001.pt        # PyG Data object
│   ├── snapshot_000002.pt
│   └── ...
├── labels/
│   ├── node_labels.json          # Node-level anomalies
│   ├── edge_labels.json          # Link-level anomalies
│   └── graph_labels.json         # Global events
├── metadata/
│   ├── topology_config.yaml      # Mininet config
│   └── feature_schema.json       # Feature definitions
└── processed/
    ├── train.pt                  # Training split
    ├── val.pt                    # Validation split
    └── test.pt                   # Test split
```

**Label Taxonomy:**
```json
{
  "node_labels": {
    "normal": 0,
    "congested": 1,
    "failing": 2,
    "attacked": 3,
    "misconfigured": 4
  },
  "edge_labels": {
    "normal": 0,
    "congested": 1,
    "high_latency": 2,
    "flapping": 3,
    "failed": 4
  },
  "graph_labels": {
    "normal": 0,
    "ddos_attack": 1,
    "broadcast_storm": 2,
    "route_instability": 3,
    "cascading_failure": 4
  }
}
```

---

## 3. Data Generation Strategy (Mininet)

### 3.1 Realistic Enterprise Network Topologies

**Topology Hierarchy:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ISP BACKBONE                                    │
│                    ┌─────────────────┐                                  │
│                    │   isp_core (S1) │                                  │
│                    │   10.255.0.0/24  │                                  │
│                    └────────┬────────┘                                  │
│                             │                                           │
│           ┌─────────────────┼─────────────────┐                         │
│           │                 │                 │                         │
│           ▼                 ▼                 ▼                         │
│    ┌──────────┐      ┌──────────┐      ┌──────────┐                    │
│    │ isp_r1   │      │ r_ent1   │      │ r_ent2   │                    │
│    │ Router   │      │ Enterprise│      │ Enterprise│                    │
│    │ Backbone │      │ Router A  │      │ Router B  │                    │
│    └────┬─────┘      └────┬─────┘      └────┬─────┘                    │
│         │                  │                  │                          │
│         │                  ▼                  ▼                          │
│         │           ┌──────────┐      ┌──────────┐                     │
│         │           │ ent1_sw  │      │ ent2_sw  │                     │
│         │           │ Access   │      │ Access   │                     │
│         │           │ Switch   │      │ Switch   │                     │
│         │           └────┬─────┘      └────┬─────┘                     │
│         │                │                 │                           │
│         │     ┌──────────┼──────────┐     │                           │
│         │     │          │          │     │                           │
│         │     ▼          ▼          ▼     ▼                           │
│         │  ┌────┐    ┌────┐    ┌────┐  ┌────┐                        │
│         │  │PC1 │    │DNS │    │ERP │  │CRM │                        │
│         │  └────┘    └────┘    └────┘  └────┘                        │
│         │                                                             │
│         │                  HOME NETWORKS                                │
│         │           ┌──────────┐      ┌──────────┐                    │
│         └──────────▶│ r_home1  │      │ r_home2  │                    │
│                     │ Home Router A   │ Home Router B   │                    │
│                     └────┬─────┘      └────┬─────┘                    │
│                          │                  │                          │
│                          ▼                  ▼                          │
│                    ┌──────────┐      ┌──────────┐                     │
│                    │ home1_sw │      │ home2_sw │                     │
│                    └────┬─────┘      └────┬─────┘                     │
│                         │                  │                          │
│                    ┌────┴────┐        ┌────┴────┐                       │
│                    │PC │ IoT│ │TV │  │PC │ Cam│ │NAS│                       │
│                    └────┴────┘        └────┴────┘                       │
│                                                                         │
│                    DATACENTER                                           │
│                    ┌──────────┐                                          │
│                    │ r_dc     │                                          │
│                    │ DC Router│                                          │
│                    └────┬─────┘                                          │
│                         │                                               │
│                         ▼                                               │
│                    ┌──────────┐                                          │
│                    │ dc_sw    │                                          │
│                    └────┬─────┘                                          │
│                         │                                               │
│               ┌─────────┼─────────┐                                     │
│               ▼         ▼         ▼                                     │
│            ┌────┐   ┌────┐   ┌────┐                                     │
│            │Web │   │VPN │   │Mon │                                     │
│            └────┘   └────┘   └────┘                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Normal Traffic Generation Patterns

| Pattern | Source → Destination | Protocol | Rate | Schedule |
|-----------|---------------------|----------|------|----------|
| Web Browsing | e1_pc* → dc_web | HTTP/HTTPS | 10-50 req/min | Business hours |
| DNS Queries | All hosts → dc_pub_dns | UDP/53 | 5-20 qps | Continuous |
| ERP Access | e1_erp ↔ e2_crm | TCP/443 | 100-500 KB/s | 9AM-6PM |
| File Transfer | h2_nas → dc_web | SMB/NFS | 1-10 MB/s | Off-peak |
| IoT Telemetry | h1_iot → dc_monitor | MQTT | 1 msg/min | Continuous |
| VPN Traffic | e2_pc* → dc_vpn | IPsec | 500 KB/s-2 MB/s | Variable |
| Video Streaming | h1_tv → dc_web | HTTP/DASH | 5-15 Mbps | Evening |
| Backup Sync | h2_nas → dc_monitor | rsync/SSH | Burst | 2AM nightly |

### 3.3 Anomaly Injection Scenarios

**Scenario A: DDoS Attack**
```python
# Injection parameters
ddos_config = {
    "type": "volumetric_ddos",
    "target": "dc_web",
    "attackers": ["h1_iot", "h2_cam"],
    "duration_seconds": 300,
    "attack_rate": "10_mbps_per_attacker",
    "protocol": "udp_flood",
    "label": "DDoS"
}
```

**Scenario B: Route Instability**
```python
route_flap_config = {
    "type": "bgp_route_flap",
    "target_router": "r_ent1",
    "flap_count": 20,
    "interval_seconds": 30,
    "affected_prefixes": ["10.10.1.0/24"],
    "label": "RouteInstability"
}
```

**Scenario C: Link Congestion**
```python
congestion_config = {
    "type": "link_congestion",
    "link": ("ent1_sw", "r_ent1"),
    "duration_seconds": 600,
    "utilization_target": 0.95,
    "background_traffic_multiplier": 5,
    "label": "Congestion"
}
```

### 3.4 Dataset Storage Format

**PyTorch Geometric Dataset:**
```python
from torch_geometric.data import Dataset, Data

class NetworkGraphDataset(Dataset):
    """Temporal network graph dataset for GNN training."""
    
    def get(self, idx):
        snapshot = torch.load(self.processed_paths[idx])
        return Data(
            x=snapshot['node_features'],           # [num_nodes, 32]
            edge_index=snapshot['edge_index'],    # [2, num_edges]
            edge_attr=snapshot['edge_features'],   # [num_edges, 16]
            y_node=snapshot['node_labels'],        # [num_nodes]
            y_edge=snapshot['edge_labels'],        # [num_edges]
            y_graph=snapshot['graph_label'],       # scalar
            timestamp=snapshot['timestamp'],
            global_attr=snapshot['global_features'] # [8]
        )
```

**Storage Format:**
- Raw: `snapshots/{timestamp}.pt` (individual PyG Data objects)
- Training: `processed/train.pt` (concatenated batch)
- Metadata: `metadata/dataset_info.json`

---

## 4. Anomalies To Detect

### 4.1 Security Anomalies

| Anomaly | GNN Task | Detection Features | Severity |
|---------|----------|---------------------|----------|
| **DDoS Attack** | Node classification | Sudden traffic spike, many sources → one target | Critical |
| **Port Scan** | Edge classification | Sequential connection attempts, low bytes/flow | Medium |
| **Brute Force** | Node classification | High auth attempt rate, single src → single dst | High |
| **Data Exfiltration** | Edge classification | Sustained high outbound, unusual dst | Critical |
| **Lateral Movement** | Graph classification | Path traversing multiple zones, unusual hops | High |
| **Man-in-the-Middle** | Edge classification | ARP changes, duplicate MACs | Critical |
| **Botnet C&C** | Node classification | Periodic beaconing, DGA DNS patterns | High |
| **Zero-day Exploit** | Graph classification | Anomalous subgraph pattern | Critical |

### 4.2 Operational Anomalies

| Anomaly | GNN Task | Detection Features | Severity |
|---------|----------|---------------------|----------|
| **Link Congestion** | Edge classification | Utilization > 90%, queue buildup | Medium |
| **High Latency** | Edge classification | RTT deviation from baseline | Medium |
| **Link Failure** | Edge classification | Zero utilization, route changes | High |
| **Route Instability** | Graph classification | Frequent routing table changes | High |
| **Broadcast Storm** | Graph classification | Excessive broadcast traffic, loop | Critical |
| **Switch Overload** | Node classification | High CPU, dropped packets | High |
| **Asymmetric Routing** | Edge classification | Forward/backward path mismatch | Medium |
| **MTU Mismatch** | Edge classification | Fragmentation patterns | Low |
| **DNS Failure** | Node classification | Query timeouts, high NXDOMAIN | Medium |
| **DHCP Exhaustion** | Graph classification | Many DISCOVER, few ACK | Medium |

---

## 5. GNN Model Design

### 5.1 Model Selection Rationale

| Model | Architecture | Best For | Why |
|-------|-------------|----------|-----|
| **GraphSAGE** | Inductive, sampling | Large-scale deployment | Scalable, handles unseen nodes |
| **GAT** | Attention-based | Interpretable security | Attention weights explain decisions |
| **GCN** | Spectral | Baseline comparison | Simple, well-understood |
| **STGNN (DCRNN)** | Spatio-temporal | Predictive maintenance | Captures temporal dynamics |
| **Heterogeneous GNN** | Multiple node/edge types | Mixed infrastructure | Handles routers, switches, hosts differently |

### 5.2 Recommended Architecture: Multi-Task GNN

```
Input Graph (snapshot t)
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                 HETEROGENEOUS GNN ENCODER                      │
│                                                                 │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│   │  Router Encoder │  │  Switch Encoder │  │   Host Encoder  │ │
│   │   (MLP → GAT)   │  │   (MLP → GAT)   │  │   (MLP → GAT)   │ │
│   │   h_dim=128     │  │   h_dim=128     │  │   h_dim=128     │ │
│   └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
│            │                     │                     │        │
│            └─────────────────────┼─────────────────────┘        │
│                                  │                             │
│                         ┌────────▼────────┐                    │
│                         │  GAT Layer 1-3  │                    │
│                         │  heads=8, dropout│                    │
│                         └────────┬────────┘                    │
└──────────────────────────────────┼────────────────────────────┘
                                   │
                         ┌─────────┴─────────┐
                         ▼                   ▼
            ┌─────────────────┐    ┌─────────────────┐
            │  NODE EMBEDDINGS │    │  EDGE EMBEDDINGS │
            │   [N, 128]       │    │   [E, 128]       │
            └────────┬────────┘    └────────┬────────┘
                     │                      │
       ┌─────────────┼─────────────┐        │
       ▼             ▼             ▼        ▼
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│ NODE       │ │ GRAPH      │ │ EDGE       │ │ TEMPORAL   │
│ CLASSIFIER │ │ CLASSIFIER │ │ CLASSIFIER │ │ PREDICTOR  │
│            │ │            │ │            │ │            │
│ MLP:       │ │ Global     │ │ Edge MLP │ │ LSTM/GRU  │
│ 128→64→6   │ │ Attention  │ │ 128→64→5 │ │ on node   │
│ classes    │ │ 128→64→5   │ │ classes   │ │ sequences │
└────────────┘ └────────────┘ └────────────┘ └────────────┘
```

### 5.3 Training Targets

**Task 1: Node Classification (Anomaly Detection)**
- Input: Node embedding [N, 128]
- Output: Probability distribution over 6 classes
- Loss: CrossEntropyLoss with class weights (handle imbalance)
- Classes: normal, congested, failing, attacked, misconfigured, offline

**Task 2: Edge Classification (Link Anomalies)**
- Input: Edge embedding [E, 128]
- Output: Probability distribution over 5 classes
- Loss: CrossEntropyLoss
- Classes: normal, congested, high_latency, flapping, failed

**Task 3: Graph Classification (Global Events)**
- Input: Global attention pooling over nodes
- Output: Probability distribution over 5 classes
- Loss: CrossEntropyLoss
- Classes: normal, ddos, broadcast_storm, route_instability, cascading_failure

**Task 4: Link Prediction (Future Failures)**
- Input: Node pair embeddings
- Output: Failure probability (0-1)
- Loss: BCEWithLogitsLoss
- Ground truth: Links that fail within prediction horizon

### 5.4 Explainability Methods

| Method | Implementation | Use Case |
|--------|---------------|----------|
| **GAT Attention** | Built into GAT layers | Highlight influential neighbors |
| **GNNExplainer** | PyG implementation | Identify subgraph causing anomaly |
| **Integrated Gradients** | Captum library | Feature importance for node predictions |
| **Attention Rollout** | Custom implementation | Trace attention across layers |

---

## 6. Predictive / Preventive Maintenance

### 6.1 Prediction Modules

```
┌─────────────────────────────────────────────────────────────────────────┐
│              PREDICTIVE MAINTENANCE ENGINE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  MODULE 1: Future Congestion Risk                                  │ │
│  │  ─────────────────────────────────                                 │ │
│  │  Input:  Historical utilization time series per link               │ │
│  │  Model:  Temporal Fusion Transformer (TFT) or LSTM                │ │
│  │  Output: Risk score (0-1) per link for next 1/6/24 hours         │ │
│  │  Action: Pre-emptive rerouting if risk > 0.7                     │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  MODULE 2: Likely Failing Links                                  │ │
│  │  ─────────────────────────────────                                 │ │
│  │  Input:  Error rates, flapping history, age of equipment           │ │
│  │  Model:  Survival analysis (Cox PH) or RNN                         │ │
│  │  Output: Remaining useful life (RUL) prediction                   │ │
│  │  Action: Schedule maintenance, prepare backup paths                │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  MODULE 3: Overloaded Switches                                   │ │
│  │  ─────────────────────────────────                                 │ │
│  │  Input:  CPU, memory, flow table utilization trends                │ │
│  │  Model:  Isolation Forest + XGBoost ensemble                       │ │
│  │  Output: Overload probability + recommended action                 │ │
│  │  Action: Load balancing, flow table optimization                   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  MODULE 4: Capacity Exhaustion                                   │ │
│  │  ─────────────────────────────────                                 │ │
│  │  Input:  Growth trends, seasonality, business forecasts            │ │
│  │  Model:  Prophet + Monte Carlo simulation                          │ │
│  │  Output: Date when capacity exhausted (confidence interval)        │ │
│  │  Action: Capacity planning, upgrade scheduling                     │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  MODULE 5: Route Instability Prediction                            │ │
│  │  ─────────────────────────────────                                 │ │
│  │  Input:  BGP update frequency, route age, neighbor stability       │ │
│  │  Model:  Markov chain + GNN for topology context                   │ │
│  │  Output: Instability probability per prefix                        │ │
│  │  Action: Route dampening, alternative path pre-computation         │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Data Requirements by Module

| Module | Historical Data Needed | Feature Window | Prediction Horizon |
|--------|------------------------|----------------|-------------------|
| Congestion Risk | 30 days of utilization | 24 hours | 1/6/24 hours |
| Link Failure | 90 days of errors + failures | 7 days | 30 days |
| Switch Overload | 30 days of CPU/memory | 1 hour | 6 hours |
| Capacity Exhaustion | 1 year of traffic growth | 90 days | 1 year |
| Route Instability | 30 days of BGP updates | 24 hours | 72 hours |

---

## 7. Intelligent Decision Engine

### 7.1 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│              INTELLIGENT DECISION ENGINE                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INPUT: Anomaly Alerts + Predictive Warnings + Business Context         │
│                              │                                          │
│                              ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  PRIORITY ARBITRATION LAYER                                      │ │
│  │  ─────────────────────────                                       │ │
│  │  Score = severity × impact × urgency × confidence                │ │
│  │  Rank all alerts, process top-K simultaneously                 │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              │                                          │
│              ┌───────────────┼───────────────┐                          │
│              ▼               ▼               ▼                          │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐                 │
│  │ RULE-BASED     │ │ RL POLICY      │ │ HYBRID         │                 │
│  │ EXPERT SYSTEM  │ │ NETWORK        │ │ DECISION       │                 │
│  │                │ │                │ │ FUSION         │                 │
│  │ IF anomaly=DDOS│ │ State: Graph   │ │ Weighted vote  │                 │
│  │ THEN trigger   │ │ Action: Reroute│ │ Rule: 0.4      │                 │
│  │     rate-limit │ │ Reward: -latency│ │ RL: 0.6        │                 │
│  │ ELSE IF ...    │ │                │ │ if RL confident│                 │
│  └────────┬───────┘ └────────┬───────┘ └────────┬───────┘                 │
│           │                  │                  │                          │
│           └──────────────────┼──────────────────┘                          │
│                              │                                          │
│                              ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  ACTION SELECTION                                                 │ │
│  │  ───────────────                                                  │ │
│  │  Available actions:                                               │ │
│  │  1. Reroute traffic (source routing, MPLS, SDN flow mods)         │ │
│  │  2. Isolate faulty node (port shutdown, ACL drop)                 │ │
│  │  3. Throttle flows (rate limiting, traffic shaping)               │ │
│  │  4. Load balancing (ECMP adjustment, anycast)                   │ │
│  │  5. Prioritize services (QoS marking, queue scheduling)           │ │
│  │  6. Trigger alerts (SNMP traps, PagerDuty, Slack)                 │ │
│  │  7. Escalate to human (complex decisions, high impact)            │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                              │                                          │
│                              ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  ACTION EXECUTION (Auto-Remediation)                              │ │
│  │  ─────────────────────────────────                                │ │
│  │  • OpenFlow flow_mod via Ryu controller                          │ │
│  │  • Linux TC (traffic control) for shaping                        │ │
│  │  • iptables/nftables for filtering                               │ │
│  │  • BGP route injection (exabgp)                                  │ │
│  │  • Mininet host commands for testing                             │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Reinforcement Learning Design

**State Space:**
- Node features (normalized utilization, anomaly scores)
- Edge features (latency, loss, utilization)
- Graph topology (connectivity matrix)
- Current flow distribution
- Recent action history

**Action Space:**
| Action | Description | Parameters |
|--------|-------------|------------|
| `REROUTE_FLOW` | Move flow to alternate path | flow_id, new_path |
| `RATE_LIMIT` | Apply bandwidth limit | node_id, rate_mbps |
| `ISOLATE_NODE` | Quarantine suspicious node | node_id, duration |
| `PRIORITIZE_CLASS` | QoS mark traffic class | class, priority |
| `BALANCED_LOAD` | Adjust ECMP weights | edge_group, weights |
| `NOOP` | Take no action | - |

**Reward Function:**
```python
reward = (
    -0.5 * avg_latency_ms +              # Minimize latency
    -1.0 * max_link_utilization +          # Avoid congestion
    -10.0 * dropped_packets +              # Penalize loss
    -5.0 * anomaly_count +                 # Penalize anomalies
    +2.0 * successful_reroutes +           # Reward successful actions
    -1.0 * action_cost                      # Action overhead
)
```

**Training:**
- Algorithm: PPO (Proximal Policy Optimization) or SAC (Soft Actor-Critic)
- Environment: Mininet simulation with realistic traffic
- Episodes: 1000+ episodes, 1000 steps each
- Curriculum: Start simple, progressively add complexity

---

## 8. Migration Plan (Current → New Platform)

### 8.1 Phase 1: Quick Wins (Week 1)

**Goal:** Establish foundation while preserving existing functionality

| Task | Files/Modules | Effort | Deliverable |
|------|--------------|--------|-------------|
| Add GNN dependencies | `models_api/requirements.txt` | 2h | torch, torch-geometric, pytorch-lightning |
| Create graph data models | `models_api/app/schemas/graph.py` | 4h | Node, Edge, GraphSnapshot Pydantic models |
| Extend topology export | `mininetDashboard/backend/topology.py` | 6h | Graph export with features |
| Add GNN inference skeleton | `models_api/app/api/gnn_routes.py` | 8h | `/gnn/inference` endpoint (mock) |
| Frontend graph viz prep | `network-monitoring-dashboard/components/` | 8h | Install Cytoscape.js, create GraphView component |

**Risks:** Minimal; additive changes only

### 8.2 Phase 2: Graph Data Pipeline (Week 2)

**Goal:** Build end-to-end graph data generation

| Task | Files/Modules | Effort | Deliverable |
|------|--------------|--------|-------------|
| Telemetry collector | `gnn_engine/collectors/` | 16h | Real-time stats collection from Mininet |
| Graph builder | `gnn_engine/graph_builder.py` | 12h | Convert snapshots to PyG Data objects |
| Temporal dataset | `gnn_engine/dataset/` | 12h | DynamicGraphTemporalSignal implementation |
| Anomaly injector v2 | `gnn_engine/anomaly_injector.py` | 8h | Configurable attack scenarios |
| Dataset storage | `gnn_engine/storage/` | 8h | Parquet + PyTorch serialization |

**New Folders:**
```
gnn_engine/
├── collectors/           # Stats collection
├── dataset/             # PyG dataset classes
├── storage/             # Data persistence
├── anomaly_injector.py  # Attack scenarios
└── graph_builder.py     # Graph construction
```

**Risks:** Data volume growth; implement compression

### 8.3 Phase 3: First GNN Deployment (Week 3)

**Goal:** Train and deploy initial GNN models

| Task | Files/Modules | Effort | Deliverable |
|------|--------------|--------|-------------|
| GNN model implementation | `gnn_engine/models/` | 16h | GraphSAGE, GAT, STGNN classes |
| Training pipeline | `gnn_engine/training/` | 12h | PyTorch Lightning training loop |
| Model registry | `gnn_engine/registry/` | 8h | MLflow integration |
| Live inference engine | `gnn_engine/inference/` | 12h | Sliding window inference |
| API integration | `models_api/app/api/gnn_routes.py` | 8h | Real inference in API |

**New Folders:**
```
gnn_engine/
├── models/              # GNN architectures
│   ├── graphsage.py
│   ├── gat.py
│   └── stgnn.py
├── training/            # Training loops
│   ├── trainer.py
│   └── callbacks.py
├── registry/            # Model versioning
│   └── mlflow_client.py
└── inference/           # Live inference
    ├── engine.py
    └── batcher.py
```

**Risks:** GPU availability; have CPU fallback

### 8.4 Phase 4: Live Production Intelligence (Week 4)

**Goal:** Predictive maintenance, decision engine, auto-remediation

| Task | Files/Modules | Effort | Deliverable |
|------|--------------|--------|-------------|
| Predictive modules | `gnn_engine/predictive/` | 12h | Congestion, failure prediction |
| Decision engine | `gnn_engine/decisions/` | 16h | Rule-based + RL hybrid |
| Auto-remediation | `gnn_engine/remediation/` | 12h | OpenFlow integration |
| Frontend dashboard v2 | `network-monitoring-dashboard/app/` | 16h | Graph viz, predictions, actions |
| End-to-end testing | `tests/integration/` | 8h | Full pipeline tests |

**New Folders:**
```
gnn_engine/
├── predictive/          # Predictive maintenance
│   ├── congestion.py
│   ├── link_failure.py
│   └── switch_overload.py
├── decisions/           # Decision engine
│   ├── rule_engine.py
│   ├── rl_agent.py
│   └── hybrid.py
└── remediation/         # Auto-remediation
    ├── openflow_client.py
    ├── traffic_control.py
    └── action_executor.py
```

**Risks:** Safety of auto-remediation; implement dry-run mode

---

## 9. Team Execution Plan (4 Developers, 4 Weeks)

### 9.1 Role Assignments

| Role | Engineer | Primary Responsibilities | Week 1 | Week 2 | Week 3 | Week 4 |
|------|----------|-------------------------|--------|--------|--------|--------|
| **Network Engineer** | Dev A | Mininet, topology, traffic gen, collectors | Extend topology export | Telemetry collectors | Live inference integration | Auto-remediation |
| **ML Engineer** | Dev B | GNN models, training, predictive modules | Graph schemas | Dataset, anomaly injector | GNN training, registry | Predictive engine |
| **Backend Engineer** | Dev C | API, storage, decision engine | GNN deps, API skeleton | Graph builder, storage | Training pipeline | Decision engine, RL |
| **Frontend Engineer** | Dev D | Dashboard, visualization | Graph viz prep | Dataset viewer | GNN results display | Full dashboard v2 |

### 9.2 Daily Standup Agenda

```
1. What graph-related work did you complete?
2. Any blockers on data pipeline?
3. Model performance updates (ML eng)
4. Integration testing status
5. Demo preparation for end of week
```

### 9.3 Key Integration Points

| Integration | From | To | When | How |
|-------------|------|----|------|-----|
| Graph export | Network Eng | ML Eng | Day 3 | Shared protobuf/JSON schema |
| Dataset API | ML Eng | Backend | Day 8 | Python module interface |
| Inference API | ML Eng | Backend | Day 15 | FastAPI router integration |
| Dashboard data | Backend | Frontend | Daily | REST API + WebSocket |
| Remediation | ML Eng | Network | Day 22 | OpenFlow controller hooks |

---

## 10. Final Recommended MVP

### 10.1 MVP Scope (Minimum Viable Product)

**Core Principle:** Deliver topology-aware anomaly detection that proves GNN value while minimizing risk.

**MVP Components:**

| Component | Scope | Excluded |
|-----------|-------|----------|
| **Topology** | Single RealWorldTopo variant | Dynamic topology changes |
| **Anomalies** | 5 types: DDoS, PortScan, Congestion, LinkFail, RouteFlap | Complex multi-stage attacks |
| **GNN Model** | Single GraphSAGE for node classification | Multi-task, temporal models |
| **Predictions** | 1-hour congestion risk | Long-term, failure prediction |
| **Decisions** | Rule-based only | RL agent |
| **Remediation** | Recommendations only (dry-run) | Automatic execution |
| **Dashboard** | Topology graph + anomaly overlay | Full decision timeline |

### 10.2 MVP Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MVP GNN PLATFORM                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐      ┌────────────┐│
│  │   Mininet    │─────▶│ GraphSAGE    │─────▶│  Next.js   ││
│  │   RealWorld  │      │ Classifier   │      │  Dashboard ││
│  │   Topology   │      │ (Anomalies)  │      │  + Graph   ││
│  └──────────────┘      └──────────────┘      │  Visualizer││
│         │                     │              └────────────┘│
│         │                     │                     ▲      │
│         ▼                     ▼                     │      │
│  ┌───────────────────────────────────────────────────┐     │
│  │              FastAPI Backend                      │     │
│  │  /topology /gnn/infer /anomalies /predictions   │     │
│  └───────────────────────────────────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 10.3 MVP Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Anomaly detection accuracy | > 85% | F1-score on test set |
| Inference latency | < 500ms | End-to-end API response |
| False positive rate | < 5% | Verified anomalies only |
| Topology visualization | < 2s load | Dashboard render time |
| Training time | < 4 hours | On generated dataset (10k graphs) |

### 10.4 Post-MVP Roadmap

| Phase | Timeline | Focus |
|-------|----------|-------|
| **v1.1** | Week 5-6 | Add GAT, edge classification, attention viz |
| **v1.2** | Week 7-8 | Temporal GNN, predictive maintenance |
| **v1.3** | Week 9-10 | RL decision engine, auto-remediation |
| **v2.0** | Week 11-12 | Multi-topology, distributed training, production |

---

## Appendix A: File Structure (Target State)

```
/
├── README.md
├── docs/
│   ├── GNN_MIGRATION_PLAN.md       # This document
│   ├── ARCHITECTURE.md              # System architecture
│   └── API.md                       # API specifications
│
├── mininetDashboard/                # Existing (preserved)
│   └── backend/
│       ├── topology.py              # Extended for graph export
│       ├── network_manager.py       # Unchanged
│       └── ...
│
├── models_api/                      # Existing (extended)
│   ├── requirements.txt             # + torch, torch-geometric
│   ├── app/
│   │   ├── main.py                  # + gnn_routes
│   │   ├── api/
│   │   │   ├── gnn_routes.py        # NEW: GNN inference API
│   │   │   ├── topology_routes.py   # NEW: Graph topology API
│   │   │   └── predictive_routes.py # NEW: Predictions API
│   │   └── schemas/
│   │       └── graph.py             # NEW: Graph Pydantic models
│   └── models/                      # GNN model weights
│
├── gnn_engine/                      # NEW: Core GNN platform
│   ├── __init__.py
│   ├── config.py                    # Configuration
│   │
│   ├── collectors/                  # Telemetry collection
│   │   ├── __init__.py
│   │   ├── base.py                  # Base collector class
│   │   ├── switch_stats.py        # OpenFlow stats
│   │   ├── router_stats.py        # Linux router stats
│   │   └── link_stats.py          # Latency/bandwidth
│   │
│   ├── dataset/                     # Dataset management
│   │   ├── __init__.py
│   │   ├── network_dataset.py       # PyG Dataset
│   │   ├── temporal_dataset.py    # Dynamic graphs
│   │   └── transforms.py          # Data augmentation
│   │
│   ├── graph_builder.py             # Graph construction
│   ├── anomaly_injector.py          # Attack scenarios
│   │
│   ├── models/                      # GNN architectures
│   │   ├── __init__.py
│   │   ├── base.py                  # Base model class
│   │   ├── graphsage.py             # GraphSAGE implementation
│   │   ├── gat.py                   # GAT implementation
│   │   └── stgnn.py                 # Temporal GNN
│   │
│   ├── training/                    # Training infrastructure
│   │   ├── __init__.py
│   │   ├── trainer.py               # PyTorch Lightning trainer
│   │   ├── losses.py                # Custom loss functions
│   │   └── callbacks.py             # Training callbacks
│   │
│   ├── inference/                   # Live inference
│   │   ├── __init__.py
│   │   ├── engine.py                # Inference engine
│   │   ├── batcher.py               # Request batching
│   │   └── cache.py                 # Embedding cache
│   │
│   ├── predictive/                  # Predictive maintenance
│   │   ├── __init__.py
│   │   ├── congestion.py            # Congestion prediction
│   │   ├── link_failure.py          # Link failure prediction
│   │   └── switch_overload.py       # Switch overload prediction
│   │
│   ├── decisions/                   # Decision engine
│   │   ├── __init__.py
│   │   ├── rule_engine.py           # Rule-based decisions
│   │   ├── rl_agent.py              # RL policy
│   │   └── hybrid.py                # Hybrid decision fusion
│   │
│   ├── remediation/                 # Auto-remediation
│   │   ├── __init__.py
│   │   ├── openflow_client.py       # SDN controller client
│   │   ├── traffic_control.py       # Linux TC integration
│   │   └── action_executor.py       # Action execution
│   │
│   ├── explainability/              # Model explainability
│   │   ├── __init__.py
│   │   ├── gnnexplainer.py          # GNNExplainer wrapper
│   │   └── attention_viz.py         # Attention visualization
│   │
│   └── storage/                     # Data persistence
│       ├── __init__.py
│       ├── graph_store.py           # Graph database interface
│       └── model_registry.py        # Model versioning
│
├── network-monitoring-dashboard/    # Existing (extended)
│   ├── app/
│   │   ├── page.tsx                 # + GNN components
│   │   └── topology/
│   │       └── page.tsx             # NEW: Topology view
│   ├── components/
│   │   ├── graph-view.tsx           # NEW: Cytoscape graph
│   │   ├── anomaly-heatmap.tsx      # NEW: Anomaly overlay
│   │   └── prediction-panel.tsx     # NEW: Predictions display
│   └── lib/
│       └── gnn-api.ts               # NEW: GNN API client
│
├── ml_training/                     # Existing (extended)
│   ├── notebooks/
│   │   ├── gnn_training.ipynb       # NEW: GNN training
│   │   └── predictive_models.ipynb  # NEW: Predictive training
│   └── models/                      # Trained model weights
│
├── data/                            # NEW: Data storage
│   ├── raw/                         # Raw captures
│   ├── processed/                   # Processed datasets
│   ├── models/                      # Saved models
│   └── results/                     # Experiment results
│
├── tests/                           # NEW: Test suite
│   ├── unit/                        # Unit tests
│   ├── integration/                 # Integration tests
│   └── e2e/                         # End-to-end tests
│
├── scripts/                         # NEW: Utility scripts
│   ├── setup.sh                     # Environment setup
│   ├── train_gnn.py                 # Training script
│   └── evaluate.py                  # Evaluation script
│
├── docker/                          # NEW: Docker configs
│   ├── Dockerfile.api
│   ├── Dockerfile.gnn-engine
│   └── docker-compose.yml
│
└── infra/                           # Existing (preserved)
```

---

## Appendix B: Technology Stack

| Layer | Current | Target | Migration |
|-------|---------|--------|-----------|
| **Backend API** | FastAPI | FastAPI | No change |
| **ML Framework** | scikit-learn, XGBoost | PyTorch, PyG | Add new |
| **Graph Database** | None | Neo4j/NetworkX | New |
| **Time Series DB** | None | InfluxDB/TimescaleDB | New |
| **Frontend** | Next.js + Recharts | Next.js + D3/Cytoscape | Extend |
| **Simulation** | Mininet + Ryu | Mininet + Ryu | Extend |
| **Model Registry** | None | MLflow | New |
| **Message Queue** | None | Redis/Kafka | Optional |
| **Serving** | Uvicorn | Uvicorn + TorchServe | Extend |

---

## Appendix C: Key Dependencies

```txt
# Core ML
torch>=2.0.0
torch-geometric>=2.4.0
torch-scatter
torch-sparse
pytorch-lightning>=2.0.0

# GNN specific
dgl  # Alternative to PyG for heterogeneous graphs
ogb  # Open Graph Benchmark datasets

# Data processing
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
pyarrow  # For parquet storage

# Time series
prophet  # For capacity forecasting

# Explainability
captum  # PyTorch interpretability
torch-geometric-explainer

# RL
stable-baselines3  # For RL agent
gym  # Environment interface

# Model registry
mlflow>=2.8.0

# Storage
neo4j-python-driver
influxdb-client
redis

# Monitoring
wandb  # Experiment tracking
prometheus-client

# API (existing)
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pydantic>=2.6.0
```

---

## Conclusion

This migration plan transforms your existing network monitoring platform into a cutting-edge GNN-powered intelligent operations system. The phased approach minimizes risk while delivering incremental value:

1. **Week 1:** Foundation with preserved functionality
2. **Week 2:** Graph data pipeline enabling topology-aware ML
3. **Week 3:** First GNN deployment with live inference
4. **Week 4:** Predictive intelligence and decision automation

The MVP recommendation focuses on proving GNN value through topology-aware anomaly detection, providing a solid foundation for subsequent phases including full predictive maintenance and autonomous remediation.

**Next Steps:**
1. Review and approve plan
2. Set up development environment with GPU access
3. Begin Phase 1 implementation
4. Weekly demos to validate progress

---

*Document prepared for ENSIA Network Intelligence Project*  
*For questions or clarifications, refer to the implementation team*
