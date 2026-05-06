"""End-to-end GNN data generation orchestrator.

Coordinates: service startup → telemetry collection → scenario execution
→ label application → dataset export.
"""

import logging
import os
import random
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .graph_export import export_gnn_dataset
from .labeling import apply_predictive_labels, apply_scenario_labels
from .scenarios import Scenario, ScenarioPhase, build_scenario_library
from .services_heavy import (
    kill_iperf_clients,
    run_iperf_tcp,
    run_iperf_udp,
    start_iperf_servers,
    stop_iperf_servers,
)
from .telemetry import TelemetryCollector

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
GNN_DATASET_DIR = str(BASE_DIR / "captures" / "gnn_datasets")


class GNNDataGenerator:
    """Orchestrates GNN training data generation."""

    def __init__(self):
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._status: Dict[str, Any] = {
            "running": False,
            "current_scenario": None,
            "current_phase": None,
            "progress_pct": 0,
            "last_run": None,
            "last_error": None,
            "last_result": None,
        }

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._status)

    def start(self, net, scenarios: List[str] = None,
              window_seconds: int = 5,
              prediction_horizons: List[int] = None,
              random_seed: int = None) -> Dict[str, Any]:
        """Start a GNN data generation run.

        Args:
            net: Mininet network object.
            scenarios: List of scenario names to run (None = all).
            window_seconds: Telemetry sampling interval.
            prediction_horizons: Look-ahead horizons in seconds.
            random_seed: Seed for reproducibility.
        """
        if prediction_horizons is None:
            prediction_horizons = [15, 30, 60]

        with self._lock:
            if self._thread and self._thread.is_alive():
                raise RuntimeError("GNN data generation already running")
            self._stop_event.clear()
            self._status.update({
                "running": True,
                "current_scenario": None,
                "current_phase": None,
                "progress_pct": 0,
                "last_error": None,
            })

        self._thread = threading.Thread(
            target=self._run_worker,
            args=(net, scenarios, window_seconds, prediction_horizons, random_seed),
            daemon=True,
        )
        self._thread.start()

        return {"started": True, "window_seconds": window_seconds,
                "prediction_horizons": prediction_horizons}

    def stop(self):
        self._stop_event.set()
        with self._lock:
            thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=15)
        return {"stopped": True}

    def _run_worker(self, net, scenario_names, window_seconds,
                    prediction_horizons, random_seed):
        if random_seed is not None:
            random.seed(random_seed)

        try:
            library = build_scenario_library()
            if scenario_names:
                library = [s for s in library if s.name in scenario_names]

            if not library:
                raise RuntimeError("No matching scenarios found")

            run_id = datetime.utcnow().strftime("gnn_%Y%m%d_%H%M%S")
            os.makedirs(GNN_DATASET_DIR, exist_ok=True)

            # Get topology info and node names
            host_names = [h.name for h in net.hosts]

            # Start iperf3 servers
            self._update_status(current_scenario="setup", current_phase="starting_services")
            start_iperf_servers(net)

            # Ensure basic services (HTTP media, service hub)
            self._ensure_baseline_services(net)

            all_snapshots = []
            total_scenarios = len(library)

            for sc_idx, scenario in enumerate(library):
                if self._stop_event.is_set():
                    break

                self._update_status(
                    current_scenario=scenario.name,
                    current_phase="starting",
                    progress_pct=int((sc_idx / total_scenarios) * 100),
                )

                snapshots, phase_timeline = self._run_scenario(
                    net, scenario, window_seconds, host_names
                )

                # Apply current-state labels from scenario phases
                apply_scenario_labels(snapshots, phase_timeline, host_names)

                # Set scenario name on each snapshot
                for snap in snapshots:
                    snap.scenario_name = scenario.name

                all_snapshots.extend(snapshots)

            if self._stop_event.is_set():
                logger.info("GNN data generation stopped by user")

            # Apply predictive labels across all snapshots
            self._update_status(current_phase="applying_predictive_labels")
            apply_predictive_labels(
                all_snapshots, prediction_horizons, window_seconds, host_names
            )

            # Build topology info from collector
            collector = TelemetryCollector(net, window_seconds)
            topo_info = collector.get_topology_info()

            # Export
            self._update_status(current_phase="exporting_dataset")
            result = export_gnn_dataset(
                snapshots=all_snapshots,
                topology_info=topo_info,
                scenario_name="multi_scenario" if len(library) > 1 else library[0].name,
                run_id=run_id,
                output_base=GNN_DATASET_DIR,
                metadata_extra={
                    "prediction_horizons": prediction_horizons,
                    "scenarios_run": [s.name for s in library if not self._stop_event.is_set()],
                },
            )

            # Clean up
            stop_iperf_servers(net)
            kill_iperf_clients(net)

            with self._lock:
                self._status.update({
                    "running": False,
                    "current_scenario": None,
                    "current_phase": None,
                    "progress_pct": 100,
                    "last_run": datetime.utcnow().isoformat() + "Z",
                    "last_error": None,
                    "last_result": result,
                })

        except Exception as exc:
            logger.exception("GNN data generation failed")
            try:
                stop_iperf_servers(net)
                kill_iperf_clients(net)
            except Exception:
                pass

            with self._lock:
                self._status.update({
                    "running": False,
                    "last_run": datetime.utcnow().isoformat() + "Z",
                    "last_error": str(exc),
                })

    def _run_scenario(self, net, scenario: Scenario, window_seconds: int,
                      host_names: List[str]):
        """Execute a single scenario and collect telemetry."""
        collector = TelemetryCollector(net, window_seconds)
        collector.start()

        phase_timeline = []
        scenario_start = time.time()

        try:
            for phase in scenario.phases:
                if self._stop_event.is_set():
                    break

                self._update_status(current_phase=phase.label)
                phase_start = time.time()

                # Execute phase actions
                self._execute_phase_actions(net, phase)

                # Record phase timing for labeling
                phase_entry = {
                    "start_ts": phase_start,
                    "end_ts": phase_start + phase.duration_s,
                    "label": phase.label,
                    "phase_name": phase.label,
                    "node_labels": dict(phase.node_labels),
                }
                phase_timeline.append(phase_entry)

                # Wait for phase duration (checking stop event every second)
                elapsed = time.time() - phase_start
                while elapsed < phase.duration_s and not self._stop_event.is_set():
                    # Run baseline traffic during wait
                    self._run_baseline_traffic_tick(net)
                    time.sleep(min(2.0, phase.duration_s - elapsed))
                    elapsed = time.time() - phase_start

                # Clean up phase-specific netem at end
                self._cleanup_phase(net, phase)

        finally:
            collector.stop()
            # Kill any leftover iperf clients from this scenario
            kill_iperf_clients(net)
            # Clear all netem
            for name in host_names:
                self._clear_node_netem(net, name)

        return collector.snapshots, phase_timeline

    def _execute_phase_actions(self, net, phase: ScenarioPhase):
        """Execute all actions defined in a scenario phase."""
        for action in phase.actions:
            if self._stop_event.is_set():
                return

            atype = action.get("type")

            if atype == "baseline_traffic":
                # Baseline is run continuously in the wait loop
                continue

            elif atype == "iperf_udp":
                run_iperf_udp(
                    net, action["src"], action["dst"],
                    bandwidth=action.get("bw", "2M"),
                    duration=action.get("duration", 10),
                    port=action.get("port", 5201),
                )

            elif atype == "iperf_tcp":
                run_iperf_tcp(
                    net, action["src"], action["dst"],
                    bandwidth=action.get("bw", "10M"),
                    duration=action.get("duration", 10),
                    port=action.get("port", 5201),
                )

            elif atype == "netem":
                node = action["node"]
                self._apply_netem(
                    net, node,
                    delay_ms=action.get("delay_ms", 0),
                    jitter_ms=action.get("jitter_ms", 0),
                    loss_pct=action.get("loss_pct", 0),
                    rate=action.get("rate"),
                )

            elif atype == "clear_netem":
                self._clear_node_netem(net, action["node"])

            elif atype == "attack":
                self._execute_attack(
                    net, action["profile"],
                    action["src"], action["dst"],
                    action.get("intensity", 1.0),
                )

    def _cleanup_phase(self, net, phase: ScenarioPhase):
        """Clean up netem applied during a phase (but not if next phase also uses netem)."""
        for action in phase.actions:
            if action.get("type") == "netem":
                # Don't auto-clear — next phase might want different netem
                pass

    def _run_baseline_traffic_tick(self, net):
        """Run a quick burst of baseline traffic (lightweight, called every 2s)."""
        try:
            pairs = [
                ("e1_pc1", "dc_web"), ("h2_pc", "dc_web"),
                ("e2_pc1", "dc_monitor"), ("h1_pc", "dc_pub_dns"),
            ]
            pair = random.choice(pairs)
            src = net.get(pair[0])
            dst_ip = net.get(pair[1]).IP()

            # Quick HTTP GET or ping
            if random.random() < 0.6:
                src.cmd(f"curl -m 2 -s http://{dst_ip}:8080/ >/dev/null 2>&1 &")
            else:
                src.cmd(f"ping -c 1 -W 1 {dst_ip} >/dev/null 2>&1 &")

            # Occasional DNS
            if random.random() < 0.3:
                dns_src = net.get(random.choice(["e1_pc2", "h1_pc", "h2_nas"]))
                dns_ip = net.get("dc_pub_dns").IP()
                dns_src.cmd(f"echo dns_q | nc -u -w1 {dns_ip} 53 >/dev/null 2>&1 &")

            # Occasional MQTT-like
            if random.random() < 0.2:
                iot = net.get(random.choice(["h1_iot", "h2_cam"]))
                mon_ip = net.get("dc_monitor").IP()
                iot.cmd(f"echo mqtt_t | nc -u -w1 {mon_ip} 1883 >/dev/null 2>&1 &")

        except Exception:
            pass

    def _execute_attack(self, net, profile: str, src: str, dst: str,
                        intensity: float):
        """Execute an attack profile (reuses lab.py patterns)."""
        try:
            src_host = net.get(src)
            dst_ip = net.get(dst).IP()
        except Exception:
            return

        burst = lambda n: max(1, int(n * intensity))

        if profile == "PortScan_slow":
            ports = [22, 80, 443]
            for p in ports:
                src_host.cmd(f"nc -z -w1 {dst_ip} {p} >/dev/null 2>&1 &")
                time.sleep(0.5)

        elif profile == "PortScan":
            ports = [21, 22, 23, 53, 80, 443, 8080, 3306, 3389]
            pl = " ".join(str(p) for p in ports)
            src_host.cmd(
                f"bash -lc 'for p in {pl}; do nc -z -w1 {dst_ip} $p >/dev/null 2>&1; done' &"
            )

        elif profile == "SSH-Patator":
            src_host.cmd(
                f"bash -lc 'for i in $(seq 1 {burst(30)}); do "
                f"nc -z -w1 {dst_ip} 22 >/dev/null 2>&1; done' &"
            )

        elif profile == "FTP-Patator":
            src_host.cmd(
                f"bash -lc 'for i in $(seq 1 {burst(30)}); do "
                f"nc -z -w1 {dst_ip} 21 >/dev/null 2>&1; done' &"
            )

        elif profile == "Infiltration":
            src_host.cmd(
                f"bash -lc 'for i in $(seq 1 {burst(15)}); do "
                f"nc -z -w1 {dst_ip} 22 >/dev/null 2>&1; done' &"
            )
            src_host.cmd(
                f"bash -lc 'for i in $(seq 1 {burst(60)}); do "
                f"echo dns_tunnel_$i | nc -u -w1 {dst_ip} 53 >/dev/null 2>&1; done' &"
            )

    @staticmethod
    def _apply_netem(net, node_name: str, delay_ms=0, jitter_ms=0,
                     loss_pct=0.0, rate=None):
        try:
            node = net.get(node_name)
        except Exception:
            return
        intf = f"{node_name}-eth0"
        parts = ["netem"]
        if delay_ms:
            parts.append(f"delay {int(delay_ms)}ms" + (f" {int(jitter_ms)}ms" if jitter_ms else ""))
        if loss_pct:
            parts.append(f"loss {float(loss_pct)}%")
        if rate:
            parts.append(f"rate {rate}")
        node.cmd(f"tc qdisc replace dev {intf} root {' '.join(parts)}")

    @staticmethod
    def _clear_node_netem(net, node_name: str):
        try:
            node = net.get(node_name)
            node.cmd(f"tc qdisc del dev {node_name}-eth0 root >/dev/null 2>&1 || true")
        except Exception:
            pass

    def _ensure_baseline_services(self, net):
        """Start HTTP servers on dc_web and dc_monitor if not running."""
        try:
            web = net.get("dc_web")
            web.cmd("mkdir -p /tmp/ai_sdn_web/assets")
            web.cmd(
                "bash -lc '"
                "if [[ ! -f /tmp/ai_sdn_web/assets/stream.bin ]]; then "
                "dd if=/dev/zero of=/tmp/ai_sdn_web/assets/stream.bin bs=1M count=24 status=none; fi'"
            )
            web.cmd("pkill -f 'python3 -m http.server 8080' >/dev/null 2>&1")
            web.cmd("cd /tmp/ai_sdn_web && nohup python3 -m http.server 8080 >/dev/null 2>&1 &")

            mon = net.get("dc_monitor")
            mon.cmd("mkdir -p /tmp/ai_sdn_monitor")
            mon.cmd("pkill -f 'python3 -m http.server 8080' >/dev/null 2>&1")
            mon.cmd("cd /tmp/ai_sdn_monitor && nohup python3 -m http.server 8080 >/dev/null 2>&1 &")
        except Exception:
            pass

    def _update_status(self, **kwargs):
        with self._lock:
            self._status.update(kwargs)


gnn_generator = GNNDataGenerator()
