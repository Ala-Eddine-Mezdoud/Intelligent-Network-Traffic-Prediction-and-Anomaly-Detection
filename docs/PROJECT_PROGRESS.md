# AI-SDN Integration Progress

Date: 2026-04-14

## What We Have Done So Far

- Unified the Mininet-side backend to run the end-to-end realtime loop.
- Added realtime closed-loop pipeline execution:
  - capture -> relay -> feature extraction -> inference
  - periodic execution every configurable interval (default 30s)
- Added one-step pipeline control endpoints:
  - `POST /api/pipeline/start`
  - `POST /api/pipeline/stop`
  - `GET /api/pipeline/status`
- Added realtime settings endpoints:
  - `GET /api/pipeline/settings`
  - `POST /api/pipeline/settings`
- Enabled dashboard auto-refresh (30s) in the Next.js monitoring UI.
- Added Mininet dashboard UI controls to start/stop realtime mode directly.
- Added explicit Realtime Settings panel in Mininet dashboard UI for:
  - Attack interval range (min/max)
  - Attack intensity
  - Protocol mix weights (ICMP, HTTP, DNS, DHCP, QUIC/UDP, FTP, SSH, IGMP)
- Replaced static simulation behavior with richer protocol-mix traffic generation.
- Added randomized attack scheduling with arbitrary timing windows.
- Added attack profiles aligned with IDS training classes (PortScan, DDoS, DoS variants, FTP/SSH brute-force, Web attacks, Bot, Infiltration).
- Updated capture/output paths to be repository-relative.
- Added model-backed inference loading directly from project model artifacts under `models_api/models` with fallback handling.

## Current Runtime Placement

- Models and intelligence currently run in the Mininet OS host process (same backend runtime), near the SDN simulation control plane.
- Dashboard can run on the same VM or another machine, consuming backend APIs.

## What We Will Do Next

- Move models and dashboard to a dedicated mininet-side server component that communicates with SDN services.
- Improve flow collection and relay so telemetry is sent over the network to the server (not only local file relay), then used to feed the model continuously.
- Evolve from batch-like relay toward streaming/near-streaming feature ingestion.
- Improve collector architecture for reliability and scalability:
  - queueing/buffering
  - retry and backpressure handling
  - better failure visibility
- Tighten model-to-dashboard feedback loop with richer confidence and latency metrics.
- Add SDN decision hooks for policy actions (alert-only first, then optional automated mitigation).
- Improve protocol fidelity where needed (e.g., stronger DHCP/IGMP realism with service-level emulation).
- Add evaluation and observability metrics:
  - prediction error
  - anomaly detection quality
  - false positives
  - end-to-end latency
  - throughput/scalability

## Notes

- Existing UI layout is preserved while functionality is extended behind the same interaction model.
- Realtime behavior is now configurable from the dashboard without code edits.
