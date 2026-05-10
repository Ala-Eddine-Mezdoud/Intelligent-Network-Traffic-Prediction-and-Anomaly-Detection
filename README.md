# Network Traffic Prediction & Anomaly Detection (AI)

AI-powered system for analyzing network traffic, predicting future load, and detecting anomalies in real time.

---

## 🚀 Overview

This project is a full-stack AI system that:

- Predicts network traffic trends
- Detects anomalies (attacks, misconfigurations, failures)
- Provides real-time monitoring via a dashboard
- Generates alerts for suspicious activity

Built as part of a group project at ENSIA.

---

## 🧠 Core Capabilities

- **Traffic Prediction**
  - Forecast short-term and long-term network usage
  - Identify peak traffic periods
  - Support capacity planning

- **Anomaly Detection**
  - Detect abnormal traffic patterns
  - Identify potential attacks (e.g., DDoS, scanning)
  - Flag unusual system behavior or failures

- **Monitoring Dashboard**
  - Real-time traffic visualization
  - Historical data exploration
  - Alert notifications

---

## 🏗️ System Architecture (High-Level)

*(Architecture details go here)*

---

## 🛠️ Setup & Requirements

### Mininet Simulation Lab Dependencies

The Mininet SDN simulation environment uses Python alongside several system-level networking tools:

*   **System Tools:** `mininet`, `openvswitch-switch`, `tcpdump`, `tshark` (for feature extraction/PCAPs), `iperf3` (for traffic generation)
*   **Python Packages:** `Flask`, `requests`, `ryu` (Ryu SDN controller with `ryu.app.simple_switch_13` and `ryu.app.ofctl_rest`)

### Required `sudo` Commands

Because the `mininetDashboard` heavily involves `mininet` (which interacts with Linux network namespaces and virtual switches), you need `sudo` to run it and install some system tools.

**1. Installing required system tools (like iperf3):**
```bash
sudo apt-get install -y iperf3
```

**2. Running the Mininet Dashboard application:**
Because it manages network interfaces, the dashboard requires root privileges. Run the following command to execute it while preserving your user's local Python packages:
```bash
sudo -E env PYTHONPATH="$HOME/.local/lib/python3.8/site-packages" /usr/bin/python3 sdn_dashboard.py
```
*(Note: adjust `python3.8` to match your local Python version if necessary)*
