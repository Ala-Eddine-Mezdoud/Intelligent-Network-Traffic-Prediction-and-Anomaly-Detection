import csv
import glob
import json
import os
import random
import shutil
import statistics
import subprocess
import threading
import time
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from .intelligence import intelligence_plane
from .gnn_inference import gnn_engine


BASE_DIR = Path(__file__).resolve().parents[1]
CAPTURE_DIR = str(BASE_DIR / "captures")
COLLECTOR_INBOX_DIR = str(BASE_DIR / "captures" / "collector_inbox")
INTELLIGENCE_OUT_DIR = str(BASE_DIR / "captures" / "intelligence_out")
ATTACKER_IP_PREFIXES = {"192.168.10.31", "192.168.20.21"}


class LabPipeline:
    def __init__(self):
        self._lock = threading.RLock()
        self._capture_id = None
        self._capture_processes = []
        self._capture_files = []
        self._last_capture_id = None
        self._last_capture_files = []
        self._last_export_csv = None
        self._last_merged_csv = None
        self._last_relay = None
        self._last_inference = None
        self._traffic_thread = None
        self._traffic_stop = threading.Event()
        self._training_thread = None
        self._realtime_thread = None
        self._realtime_stop = threading.Event()
        self._realtime_interval_seconds = 30
        self._last_realtime_run = None
        self._last_realtime_error = None
        self._last_training_run = None
        self._last_training_error = None
        self._active_operational_anomalies = []
        self._net = None  # stored on start so inject_anomaly can use it
        self._normal_sim_thread = None
        self._normal_sim_stop = threading.Event()
        self._realtime_settings = {
            "attack_interval_min_seconds": 300,
            "attack_interval_max_seconds": 900,
            "attack_intensity": 1.5,
            "protocol_mix_weights": {
                "browser": 95,
                "streaming_http": 90,
                "rtsp_streaming": 85,
                "bulk_download": 90,
                "bulk_upload": 85,
                "api_microservices": 90,
                "dns": 95,
                "dhcp": 60,
                "quic_udp": 80,
                "mqtt_telemetry": 85,
                "voip": 80,
                "ftp": 70,
                "ssh": 75,
                "database_replication": 70,
                "icmp": 65,
                "igmp": 50,
            },
            "operational_anomaly_weights": {
                "congestion": 35,
                "latency_spike": 30,
                "packet_loss": 25,
                "jitter": 20,
                "bandwidth_throttle": 15,
                "brownout": 10,
            },
        }
        self._next_attack_epoch = None
        self._next_attack_profile = None
        self._last_attack = None
        # Separate epoch for scheduled operational anomalies (netem-based)
        # in full simulation — much rarer than protocol mix traffic.
        self._next_operational_epoch: float = 0.0
        self._op_anomaly_rotation_idx: int = 0
        self._attack_rotation_idx: int = 0
        self._attack_profiles = [
            "PortScan",
            "DDoS",
            "DoS Hulk",
            "DoS slowloris",
            "FTP-Patator",
            "SSH-Patator",
            "Web Attack - SQL Injection",
            "Web Attack - XSS",
            "Bot",
            "Infiltration",
        ]
        self._realistic_services_started = False
        # persistent anomaly history (for capture-aligned labeling)
        self._anomaly_log = []
        self._capture_host_map = {}
        self._capture_time_ranges = {}

    def status(self):
        with self._lock:
            return {
                "capture_id": self._capture_id,
                "capture_running": bool(self._capture_processes),
                "traffic_running": bool(self._traffic_thread and self._traffic_thread.is_alive()),
                "capture_files": list(self._capture_files),
                "last_capture_id": self._last_capture_id,
                "last_capture_files": list(self._last_capture_files),
                "last_export_csv": self._last_export_csv,
                "last_merged_csv": self._last_merged_csv,
                "last_relay": self._last_relay,
                "last_inference": self._last_inference,
                "realtime_running": bool(self._realtime_thread and self._realtime_thread.is_alive()),
                "realtime_interval_seconds": self._realtime_interval_seconds,
                "last_realtime_run": self._last_realtime_run,
                "last_realtime_error": self._last_realtime_error,
                "last_training_run": self._last_training_run,
                "last_training_error": self._last_training_error,
                "realtime_settings": self.get_realtime_settings(),
                "active_operational_anomalies": list(self._active_operational_anomalies),
                "next_attack_profile": self._next_attack_profile,
                "next_attack_in_seconds": self._seconds_to_next_attack(),
                "last_attack": self._last_attack,
            }

    def realtime_status(self):
        with self._lock:
            gnn_status = gnn_engine.status()
            return {
                "running": bool(self._realtime_thread and self._realtime_thread.is_alive()),
                "interval_seconds": self._realtime_interval_seconds,
                "last_realtime_run": self._last_realtime_run,
                "last_realtime_error": self._last_realtime_error,
                "last_inference": self._last_inference,
                "last_training_run": self._last_training_run,
                "last_training_error": self._last_training_error,
                "realtime_settings": self.get_realtime_settings(),
                "active_operational_anomalies": list(self._active_operational_anomalies),
                "next_attack_profile": self._next_attack_profile,
                "next_attack_in_seconds": self._seconds_to_next_attack(),
                "last_attack": self._last_attack,
                "gnn_inference": {
                    "running": gnn_status.get("running", False),
                    "predictions_made": gnn_status.get("predictions_made", 0),
                    "window_state": gnn_status.get("window_state"),
                    "anomaly_count": gnn_status.get("anomaly_count", 0),
                },
            }

    def get_realtime_settings(self):
        with self._lock:
            mix = dict(self._realtime_settings.get("protocol_mix_weights", {}))
            operational = dict(self._realtime_settings.get("operational_anomaly_weights", {}))
            return {
                "attack_interval_min_seconds": int(self._realtime_settings.get("attack_interval_min_seconds", 60)),
                "attack_interval_max_seconds": int(self._realtime_settings.get("attack_interval_max_seconds", 300)),
                "attack_intensity": float(self._realtime_settings.get("attack_intensity", 1.0)),
                "protocol_mix_weights": mix,
                "operational_anomaly_weights": operational,
            }

    def update_realtime_settings(self, payload):
        payload = payload or {}
        current = self.get_realtime_settings()

        min_s = int(payload.get("attack_interval_min_seconds", current["attack_interval_min_seconds"]))
        max_s = int(payload.get("attack_interval_max_seconds", current["attack_interval_max_seconds"]))
        if min_s < 10 or max_s < 10:
            raise RuntimeError("Attack interval min/max must be at least 10 seconds")
        if min_s > max_s:
            raise RuntimeError("attack_interval_min_seconds must be <= attack_interval_max_seconds")

        intensity = float(payload.get("attack_intensity", current["attack_intensity"]))
        if intensity < 0.2 or intensity > 5.0:
            raise RuntimeError("attack_intensity must be between 0.2 and 5.0")

        incoming_mix = payload.get("protocol_mix_weights") or {}
        next_mix = dict(current["protocol_mix_weights"])
        for key, value in incoming_mix.items():
            if key not in next_mix:
                continue
            ivalue = int(value)
            if ivalue < 0 or ivalue > 100:
                raise RuntimeError(f"protocol_mix_weights.{key} must be in range 0..100")
            next_mix[key] = ivalue

        incoming_operational = payload.get("operational_anomaly_weights") or {}
        next_operational = dict(current.get("operational_anomaly_weights", {}))
        for key, value in incoming_operational.items():
            if key not in next_operational:
                continue
            ivalue = int(value)
            if ivalue < 0 or ivalue > 100:
                raise RuntimeError(f"operational_anomaly_weights.{key} must be in range 0..100")
            next_operational[key] = ivalue

        with self._lock:
            self._realtime_settings["attack_interval_min_seconds"] = min_s
            self._realtime_settings["attack_interval_max_seconds"] = max_s
            self._realtime_settings["attack_intensity"] = intensity
            self._realtime_settings["protocol_mix_weights"] = next_mix
            self._realtime_settings["operational_anomaly_weights"] = next_operational

            if self._realtime_thread and self._realtime_thread.is_alive():
                self._schedule_next_attack()

        return self.get_realtime_settings()

    def _seconds_to_next_attack(self):
        if self._next_attack_epoch is None:
            return None
        return max(0, int(self._next_attack_epoch - time.time()))

    def _schedule_next_attack(self, min_seconds=None, max_seconds=None):
        settings = self.get_realtime_settings()
        min_seconds = int(min_seconds or settings["attack_interval_min_seconds"])
        max_seconds = int(max_seconds or settings["attack_interval_max_seconds"])
        self._next_attack_epoch = time.time() + random.randint(min_seconds, max_seconds)
        self._next_attack_profile = random.choice(self._attack_profiles)

    def _ensure_attack_schedule(self):
        if self._next_attack_epoch is None or self._next_attack_profile is None:
            self._schedule_next_attack()

    # ------------------------------------------------------------------
    # Normal simulation mode — steady baseline traffic, no auto-attacks
    # ------------------------------------------------------------------

    def start_normal_simulation(self, net):
        """Start steady-state normal traffic matching GNN training conditions."""
        with self._lock:
            if self._normal_sim_thread and self._normal_sim_thread.is_alive():
                raise RuntimeError("Normal simulation already running")
            if self._realtime_thread and self._realtime_thread.is_alive():
                raise RuntimeError("Stop realtime simulation first")
            self._net = net
            self._normal_sim_stop.clear()
            thread = threading.Thread(
                target=self._normal_sim_worker,
                args=(net,),
                daemon=True,
            )
            self._normal_sim_thread = thread
            thread.start()

        if gnn_engine._loaded and not gnn_engine._running:
            try:
                gnn_engine.start(net)
            except Exception:
                pass

        return {"started": True, "mode": "normal", "gnn_inference": gnn_engine._running}

    def stop_normal_simulation(self):
        self._normal_sim_stop.set()
        if gnn_engine._running:
            try:
                gnn_engine.stop()
            except Exception:
                pass
        with self._lock:
            thread = self._normal_sim_thread
        if thread and thread.is_alive():
            thread.join(timeout=5)
        self._net = None
        return {"stopped": True}

    def normal_sim_status(self):
        return {
            "running": bool(self._normal_sim_thread and self._normal_sim_thread.is_alive()),
            "mode": "normal",
            "active_operational_anomalies": list(self._active_operational_anomalies),
        }

    def _normal_sim_worker(self, net):
        # Each iperf3 server handles ONE client at a time. When we tried to
        # restart clients before the old ones finished, the server rejected the
        # new connection and we got a 40-second zero-traffic window.
        #
        # Fix: each source host runs a persistent bash loop that restarts
        # iperf3 immediately after each run finishes (1-second gap maximum).
        # This keeps traffic continuous regardless of flow duration.
        #
        # Flows: (src, dst, bandwidth_str, proto, server_port)
        FLOWS = [
            # DC-web receives from 6 sources → 6 server instances (ports 5201-5206)
            ("e1_pc1", "dc_web",     "3M",   "tcp", 5201),
            ("e1_erp", "dc_web",     "5M",   "tcp", 5202),
            ("e2_pc1", "dc_web",     "3M",   "tcp", 5203),
            ("h1_pc",  "dc_web",     "2M",   "tcp", 5204),
            ("h2_pc",  "dc_web",     "2M",   "tcp", 5205),
            ("h2_nas", "dc_web",     "3M",   "tcp", 5206),
            # DC-monitor receives from 6 sources → ports 5211-5216
            ("e1_pc2", "dc_monitor", "2M",   "tcp", 5211),
            ("e2_pc2", "dc_monitor", "2M",   "tcp", 5212),
            ("e2_crm", "dc_monitor", "4M",   "tcp", 5213),
            ("h1_tv",  "dc_monitor", "2M",   "udp", 5214),
            ("h2_cam", "dc_monitor", "1M",   "udp", 5215),
            ("h1_iot", "dc_monitor", "1M",   "udp", 5216),
            # Additional DC services for broader node coverage
            ("e1_pc1", "dc_vpn",     "1M",   "tcp", 5221),
            ("e2_pc1", "dc_pub_dns", "500K", "udp", 5222),
        ]
        FLOW_DURATION = 35  # each iperf3 run; loop restarts immediately after

        # Collect unique (dst, port) pairs for server startup
        dst_ports: dict = {}
        for _, dst, _, _, port in FLOWS:
            dst_ports.setdefault(dst, [])
            if port not in dst_ports[dst]:
                dst_ports[dst].append(port)

        # Kill old iperf3 servers on target hosts before starting fresh ones.
        # Do NOT call _ensure_http_media_service — its pkill kills all iperf3.
        for dst_name in dst_ports:
            try:
                net.get(dst_name).cmd("pkill -f 'iperf3 -s' >/dev/null 2>&1 || true")
            except Exception:
                pass

        time.sleep(1)

        for dst_name, ports in dst_ports.items():
            try:
                h = net.get(dst_name)
                for port in ports:
                    h.cmd(
                        f"nohup iperf3 -s -p {port} "
                        f"--logfile /tmp/iperf3_{dst_name}_{port}.log >/dev/null 2>&1 &"
                    )
                    time.sleep(0.05)
                logger.info(f"Normal sim: started iperf3 servers on {dst_name}: {ports}")
            except Exception as exc:
                logger.warning(f"iperf3 server start error on {dst_name}: {exc}")

        time.sleep(2)  # let servers bind before first client connects

        # Launch a self-restarting client loop on every source host.
        # The loop exits only when iperf3 itself is killed (on simulation stop).
        for src, dst, bw, proto, port in FLOWS:
            try:
                src_host = net.get(src)
                dst_ip   = net.get(dst).IP()
                udp_flag = "-u" if proto == "udp" else ""
                # The bash loop restarts iperf3 immediately after each run,
                # giving at most a 1-second gap between consecutive flows.
                src_host.cmd(
                    f"nohup bash -c '"
                    f"while true; do "
                    f"iperf3 -c {dst_ip} {udp_flag} -b {bw} -t {FLOW_DURATION} -p {port} "
                    f">/tmp/iperf3_c_{src}_{port}.log 2>&1 || true; "
                    f"sleep 0.5; "
                    f"done' >/dev/null 2>&1 &"
                )
            except Exception as exc:
                logger.debug(f"Normal sim flow error {src}->{dst}:{port}: {exc}")

        logger.info("Normal sim: all persistent client loops started")

        # Allow flows to ramp up before the first IDS snapshot
        self._normal_sim_stop.wait(15)

        last_ids_ts = 0.0
        IDS_INTERVAL = 90  # seconds between lightweight pcap snapshots

        try:
            # Main loop — prune anomaly state and run periodic IDS snapshots
            while not self._normal_sim_stop.is_set():
                with self._lock:
                    expired_nodes = self._prune_expired_operational_anomalies()
                for _node_name in expired_nodes:
                    self._clear_node_netem(net, _node_name)

                now = time.time()
                if now - last_ids_ts >= IDS_INTERVAL:
                    try:
                        self._run_normal_sim_ids_check(net)
                    except Exception as exc:
                        logger.debug("Normal sim IDS check error: %s", exc)
                    last_ids_ts = time.time()

                self._normal_sim_stop.wait(10)
        finally:
            self._clear_operational_anomalies(net)
            # Kill all iperf3 processes on source and destination hosts.
            # The bash loops will also die once iperf3 is gone.
            all_hosts = set(src for src, *_ in FLOWS) | set(dst_ports.keys())
            for host_name in all_hosts:
                try:
                    net.get(host_name).cmd("pkill -9 -f 'iperf3' >/dev/null 2>&1 || true")
                except Exception:
                    pass
            with self._lock:
                self._active_operational_anomalies = []

    # ------------------------------------------------------------------
    # Manual anomaly injection (works in both normal and realtime mode)
    # ------------------------------------------------------------------

    ANOMALY_TYPES = {
        "congestion": {
            "description": "Rate-limit a node to simulate link saturation",
            "default_nodes": ["e1_pc1", "e2_pc1", "h2_nas"],
        },
        "latency": {
            "description": "Add high latency to simulate WAN degradation",
            "default_nodes": ["h1_pc", "e2_pc1", "dc_monitor"],
        },
        "packet_loss": {
            "description": "Inject random packet drops",
            "default_nodes": ["dc_web", "dc_monitor", "h2_pc"],
        },
        "jitter": {
            "description": "Add variable delay to simulate unstable link",
            "default_nodes": ["h1_tv", "h2_cam", "h1_iot"],
        },
        "brownout": {
            "description": "Combined degradation — rate limit + high latency + some loss",
            "default_nodes": ["dc_web", "dc_monitor", "h1_pc"],
        },
        "ddos": {
            "description": "Flood dc_web with high-bandwidth UDP traffic",
            "default_nodes": ["dc_web"],
        },
        "portscan": {
            "description": "Rapid port scan from IoT device toward datacenter",
            "default_nodes": ["dc_web", "dc_vpn"],
        },
        "brute_force": {
            "description": "SSH brute-force attempts toward datacenter VPN",
            "default_nodes": ["dc_vpn"],
        },
    }

    def inject_anomaly(self, anomaly_type: str, node: str = None, duration_s: int = 30):
        """Inject a specific anomaly immediately into the running network."""
        net = self._net
        if net is None:
            raise RuntimeError("No simulation running — start normal or realtime simulation first")

        if anomaly_type not in self.ANOMALY_TYPES:
            raise RuntimeError(f"Unknown anomaly type '{anomaly_type}'. Valid: {list(self.ANOMALY_TYPES)}")

        duration_s = max(10, min(300, int(duration_s)))

        if anomaly_type == "congestion":
            target = node or random.choice(self.ANOMALY_TYPES["congestion"]["default_nodes"])
            self._inject_operational_anomaly(
                net, target, "congestion",
                delay_ms=60, jitter_ms=15, loss_pct=0.0, rate="4mbit",
                duration_seconds=duration_s,
            )
            gnn_engine.set_active_injection("congestion", duration_s, target_nodes=[target])

        elif anomaly_type == "latency":
            target = node or random.choice(self.ANOMALY_TYPES["latency"]["default_nodes"])
            self._inject_operational_anomaly(
                net, target, "latency_spike",
                delay_ms=300, jitter_ms=80, loss_pct=0.0, rate=None,
                duration_seconds=duration_s,
            )
            gnn_engine.set_active_injection("latency", duration_s, target_nodes=[target])

        elif anomaly_type == "packet_loss":
            target = node or random.choice(self.ANOMALY_TYPES["packet_loss"]["default_nodes"])
            self._inject_operational_anomaly(
                net, target, "packet_loss",
                delay_ms=15, jitter_ms=5, loss_pct=8.0, rate=None,
                duration_seconds=duration_s,
            )
            gnn_engine.set_active_injection("packet_loss", duration_s, target_nodes=[target])

        elif anomaly_type == "jitter":
            target = node or random.choice(self.ANOMALY_TYPES["jitter"]["default_nodes"])
            self._inject_operational_anomaly(
                net, target, "jitter",
                delay_ms=80, jitter_ms=60, loss_pct=0.0, rate="10mbit",
                duration_seconds=duration_s,
            )
            gnn_engine.set_active_injection("jitter", duration_s, target_nodes=[target])

        elif anomaly_type == "brownout":
            target = node or random.choice(self.ANOMALY_TYPES["brownout"]["default_nodes"])
            self._inject_operational_anomaly(
                net, target, "brownout",
                delay_ms=200, jitter_ms=80, loss_pct=5.0, rate="1mbit",
                duration_seconds=duration_s,
            )
            gnn_engine.set_active_injection("brownout", duration_s, target_nodes=[target])

        elif anomaly_type == "ddos":
            # High-volume flood matching training DDOS scenario
            from .services_heavy import run_iperf_udp
            gnn_engine.set_active_injection(
                "ddos", duration_s,
                target_nodes=["h1_iot", "h2_cam", "e2_pc2", "dc_web"],
            )
            run_iperf_udp(net, "h1_iot",  "dc_web", bandwidth="20M", duration=duration_s)
            run_iperf_udp(net, "h2_cam",  "dc_web", bandwidth="15M", duration=duration_s)
            run_iperf_udp(net, "e2_pc2",  "dc_web", bandwidth="15M", duration=duration_s)
            return {"injected": True, "type": anomaly_type, "target": "dc_web", "duration_s": duration_s}

        elif anomaly_type == "portscan":
            scan_target = node or "dc_web"
            target_ip = net.get(scan_target).IP()
            src = net.get("h1_iot")
            src.cmd(
                f"bash -c 'for i in $(seq 1 {duration_s * 2}); do "
                f"for p in 21 22 23 25 53 80 110 443 3306 3389 5900 8080; do "
                f"nc -z -w1 {target_ip} $p 2>/dev/null; done; sleep 0.5; done' &"
            )
            gnn_engine.set_active_injection(
                "portscan", duration_s,
                target_nodes=["h1_iot", scan_target],
            )
            return {"injected": True, "type": anomaly_type, "target": scan_target, "duration_s": duration_s}

        elif anomaly_type == "brute_force":
            bf_target = node or "dc_vpn"
            target_ip = net.get(bf_target).IP()
            src = net.get("h2_cam")
            src.cmd(
                f"bash -c 'for i in $(seq 1 {duration_s * 4}); do "
                f"nc -z -w1 {target_ip} 22 2>/dev/null; sleep 0.25; done' &"
            )
            gnn_engine.set_active_injection(
                "brute_force", duration_s,
                target_nodes=["h2_cam", bf_target],
            )
            return {"injected": True, "type": anomaly_type, "target": bf_target, "duration_s": duration_s}

        target = node or "unknown"
        return {"injected": True, "type": anomaly_type, "target": target, "duration_s": duration_s}

    def start_realtime(self, net, interval_seconds=30):
        interval_seconds = int(interval_seconds)
        if interval_seconds < 10:
            raise RuntimeError("interval_seconds must be at least 10")

        if not self._command_exists("tcpdump"):
            raise RuntimeError("tcpdump not found. Install tcpdump before starting realtime mode")
        if not self._command_exists("tshark"):
            raise RuntimeError("tshark not found. Install tshark before starting realtime mode")
        if not self._command_exists("tc"):
            raise RuntimeError("tc not found. Install iproute2 before starting realtime mode")

        with self._lock:
            if self._realtime_thread and self._realtime_thread.is_alive():
                raise RuntimeError("Realtime loop already running")
            if self._normal_sim_thread and self._normal_sim_thread.is_alive():
                raise RuntimeError("Stop normal simulation first")
            if self._capture_processes:
                raise RuntimeError("Cannot start realtime loop while manual capture is running")
            self._net = net

            self._ensure_realistic_services(net)

            self._realtime_interval_seconds = interval_seconds
            self._last_realtime_error = None
            self._schedule_next_attack()
            self._next_operational_epoch = 0.0  # will be scheduled on first cycle
            self._op_anomaly_rotation_idx = 0
            self._attack_rotation_idx = 0
            self._realtime_stop.clear()
            thread = threading.Thread(
                target=self._realtime_worker,
                args=(net, interval_seconds),
                daemon=True,
            )
            self._realtime_thread = thread
            thread.start()

            # Auto-start GNN inference alongside realtime pipeline
            if gnn_engine._loaded and not gnn_engine._running:
                try:
                    logger.info("Auto-starting GNN Inference Engine...")
                    gnn_engine.start(net)
                except Exception as gnn_exc:
                    logger.error(f"Failed to auto-start GNN Engine: {gnn_exc}")
                    pass  # GNN is optional — don't block realtime

        return {
            "started": True,
            "interval_seconds": interval_seconds,
            "gnn_inference": gnn_engine._running,
        }

    def stop_realtime(self):
        self._realtime_stop.set()

        # Stop GNN inference alongside realtime pipeline
        if gnn_engine._running:
            try:
                gnn_engine.stop()
            except Exception:
                pass

        with self._lock:
            thread = self._realtime_thread

        if thread and thread.is_alive():
            thread.join(timeout=5)

        if self.status().get("capture_running"):
            self.stop_capture()

        self._net = None
        return {"stopped": True, "gnn_stopped": not gnn_engine._running}

    def start_capture(self, net, label="session"):
        if not self._command_exists("tcpdump"):
            raise RuntimeError("tcpdump not found. Install tcpdump before starting capture")

        with self._lock:
            if self._capture_processes:
                raise RuntimeError("Capture already running")

            os.makedirs(CAPTURE_DIR, exist_ok=True)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            capture_id = f"{label}_{timestamp}"
            capture_start = time.time()

            host_map = {}
            for host in net.hosts:
                try:
                    host_map[host.name] = host.IP()
                except Exception:
                    continue

            interfaces = self._capture_interfaces(net)
            processes = []
            capture_files = []

            for intf_name in interfaces:
                safe_name = intf_name.replace("/", "_")
                pcap_path = os.path.join(CAPTURE_DIR, f"{capture_id}_{safe_name}.pcap")
                # Capture at switch interfaces to emulate SDN-wide visibility.
                proc = subprocess.Popen(
                    [
                        "tcpdump",
                        "-i",
                        intf_name,
                        "-n",
                        "-s",
                        "0",
                        "-U",
                        "-w",
                        pcap_path,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                processes.append(proc)
                capture_files.append(pcap_path)

            self._capture_id = capture_id
            self._capture_processes = processes
            self._capture_files = capture_files
            self._last_capture_id = capture_id
            self._last_capture_files = list(capture_files)
            self._capture_host_map[capture_id] = host_map
            self._capture_time_ranges[capture_id] = {"start_ts": capture_start}

            return {
                "capture_id": capture_id,
                "interfaces": interfaces,
                "capture_files": capture_files,
            }

    def stop_capture(self):
        with self._lock:
            if not self._capture_processes:
                return {"stopped": False, "reason": "No capture running"}

            procs = list(self._capture_processes)
            capture_id = self._capture_id
            capture_files = list(self._capture_files)

            self._capture_processes = []
            self._capture_id = None
            self._capture_files = []
            self._last_capture_id = capture_id
            self._last_capture_files = list(capture_files)
            if capture_id:
                entry = self._capture_time_ranges.get(capture_id, {})
                entry["end_ts"] = time.time()
                self._capture_time_ranges[capture_id] = entry

        for proc in procs:
            proc.terminate()
        for proc in procs:
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

        return {
            "stopped": True,
            "capture_id": capture_id,
            "capture_files": capture_files,
        }

    def start_traffic(self, net, duration_seconds=90):
        if not self._command_exists("tc"):
            raise RuntimeError("tc not found. Install iproute2 before starting traffic generation")

        with self._lock:
            if self._traffic_thread and self._traffic_thread.is_alive():
                raise RuntimeError("Traffic generator already running")

            self._ensure_realistic_services(net)

            self._traffic_stop.clear()
            thread = threading.Thread(
                target=self._traffic_worker,
                args=(net, int(duration_seconds)),
                daemon=True,
            )
            self._traffic_thread = thread
            self._schedule_next_attack()
            thread.start()

        return {"started": True, "duration_seconds": int(duration_seconds)}

    def stop_traffic(self):
        self._traffic_stop.set()
        with self._lock:
            thread = self._traffic_thread

        if thread and thread.is_alive():
            thread.join(timeout=3)

        return {"stopped": True}

    def run_training_capture(self, net, duration_seconds=90, include_labels=True, include_anomaly_labels=True):
        if not self._command_exists("tcpdump"):
            raise RuntimeError("tcpdump not found. Install tcpdump before starting training capture")
        if not self._command_exists("tshark"):
            raise RuntimeError("tshark not found. Install tshark before starting training capture")
        if not self._command_exists("tc"):
            raise RuntimeError("tc not found. Install iproute2 before starting training capture")

        duration_seconds = max(10, int(duration_seconds))

        with self._lock:
            if self._training_thread and self._training_thread.is_alive():
                raise RuntimeError("Training capture already running")
            if self._capture_processes:
                raise RuntimeError("Cannot start training capture while manual capture is running")
            if self._traffic_thread and self._traffic_thread.is_alive():
                raise RuntimeError("Cannot start training capture while traffic generator is running")
            if self._realtime_thread and self._realtime_thread.is_alive():
                raise RuntimeError("Cannot start training capture while realtime loop is running")

            self._last_training_error = None
            self._last_training_run = None
            thread = threading.Thread(
                target=self._training_worker,
                args=(net, duration_seconds, include_labels, include_anomaly_labels),
                daemon=True,
            )
            self._training_thread = thread
            thread.start()

        return {
            "started": True,
            "duration_seconds": duration_seconds,
            "include_labels": bool(include_labels),
            "include_anomaly_labels": bool(include_anomaly_labels),
        }

    def export_features(self, capture_id):
        if not self._command_exists("tshark"):
            raise RuntimeError("tshark not found. Install tshark to export CICIDS-like flow features")

        pcap_files = sorted(glob.glob(os.path.join(CAPTURE_DIR, f"{capture_id}_*.pcap")))
        if not pcap_files:
            raise RuntimeError(f"No pcap files found for capture_id={capture_id}")

        rows = []
        for pcap_path in pcap_files:
            rows.extend(self._read_packets_with_tshark(pcap_path))

        if not rows:
            raise RuntimeError("No packets decoded from pcap files")

        flow_features = self._build_flow_features(rows)
        out_path = os.path.join(CAPTURE_DIR, f"{capture_id}_flows.csv")
        self._write_flow_csv(flow_features, out_path)

        with self._lock:
            self._last_export_csv = out_path

        return {
            "capture_id": capture_id,
            "flow_count": len(flow_features),
            "csv_path": out_path,
        }

    def relay_capture_to_collector(self, capture_id):
        pcap_files = sorted(glob.glob(os.path.join(CAPTURE_DIR, f"{capture_id}_*.pcap")))
        if not pcap_files:
            raise RuntimeError(f"No pcap files found for capture_id={capture_id}")

        inbox_path = os.path.join(COLLECTOR_INBOX_DIR, capture_id)
        os.makedirs(inbox_path, exist_ok=True)

        relayed_files = []
        for source in pcap_files:
            destination = os.path.join(inbox_path, os.path.basename(source))
            shutil.copy2(source, destination)
            relayed_files.append(destination)

        manifest = {
            "capture_id": capture_id,
            "relayed_files": relayed_files,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        manifest_path = os.path.join(inbox_path, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as manifest_file:
            json.dump(manifest, manifest_file, indent=2)

        result = {
            "capture_id": capture_id,
            "collector_inbox": inbox_path,
            "relayed_files": relayed_files,
            "manifest": manifest_path,
        }

        with self._lock:
            self._last_relay = result

        return result

    def collector_extract_and_infer(self, capture_id, attack_hint=None):
        inbox_path = os.path.join(COLLECTOR_INBOX_DIR, capture_id)
        pcap_files = sorted(glob.glob(os.path.join(inbox_path, f"{capture_id}_*.pcap")))
        if not pcap_files:
            raise RuntimeError(
                "No relayed pcap files found in collector inbox. Run relay step first."
            )

        rows = []
        for pcap_path in pcap_files:
            rows.extend(self._read_packets_with_tshark(pcap_path))

        if not rows:
            raise RuntimeError("Collector decoded zero packets from relayed traces")

        flow_features = self._build_flow_features(rows)
        os.makedirs(INTELLIGENCE_OUT_DIR, exist_ok=True)
        collector_csv = os.path.join(INTELLIGENCE_OUT_DIR, f"{capture_id}_collector_flows.csv")
        self._write_flow_csv(flow_features, collector_csv)

        # produce merged/annotated CSV for training when requested; keep original collector CSV
        try:
            merged = self.merge_and_annotate_capture(capture_id, collector_csv)
            merged_path = merged.get("merged_csv") if merged else None
        except Exception:
            merged_path = None

        inference = intelligence_plane.infer(
            flow_features, capture_id, attack_hint=attack_hint, window_seconds=30.0
        )
        inference_report = {
            "capture_id": capture_id,
            "collector_csv": collector_csv,
            "collector_flow_count": len(flow_features),
            "inference": inference,
        }

        inference_path = os.path.join(INTELLIGENCE_OUT_DIR, f"{capture_id}_inference.json")
        with open(inference_path, "w", encoding="utf-8") as report_file:
            json.dump(inference_report, report_file, indent=2)

        inference_report["inference_path"] = inference_path

        with self._lock:
            self._last_inference = inference_report

        return inference_report

    def _training_worker(self, net, duration_seconds, include_labels, include_anomaly_labels):
        capture_id = None
        try:
            cap = self.start_capture(net, label="training")
            capture_id = cap["capture_id"]

            self.start_traffic(net, duration_seconds=duration_seconds)
            end_ts = time.time() + duration_seconds
            while time.time() < end_ts and self._traffic_thread and self._traffic_thread.is_alive():
                time.sleep(1)

            try:
                self.stop_traffic()
            except Exception:
                pass

            self.stop_capture()
            try:
                self.export_features(capture_id)
            except Exception:
                pass

            self.relay_capture_to_collector(capture_id)
            self.merge_and_annotate_capture(
                capture_id,
                include_anomaly_labels=include_anomaly_labels,
                include_label_column=include_labels,
            )

            with self._lock:
                self._last_training_run = datetime.utcnow().isoformat() + "Z"
                self._last_training_error = None
        except Exception as exc:
            try:
                if self.status().get("capture_running"):
                    self.stop_capture()
            except Exception:
                pass
            try:
                self.stop_traffic()
            except Exception:
                pass

            with self._lock:
                self._last_training_run = datetime.utcnow().isoformat() + "Z"
                self._last_training_error = str(exc)

    def merge_and_annotate_capture(
        self,
        capture_id,
        collector_csv_path=None,
        output_path=None,
        include_anomaly_labels=True,
        include_label_column=True,
    ):
        """
        Merge per-interface flow CSVs and annotate with operational anomaly labels from the anomaly log.
        If include_anomaly_labels is False, do not add anomaly columns.
        If include_label_column is False, omit the base Label column.
        Returns dict with merged_csv path and counts.
        """
        pcap_csv = os.path.join(CAPTURE_DIR, f"{capture_id}_flows.csv")
        candidate_files = []
        if os.path.exists(pcap_csv):
            candidate_files.append(pcap_csv)
        if collector_csv_path and os.path.exists(collector_csv_path):
            candidate_files.append(collector_csv_path)

        # include any intelligence out CSVs matching pattern
        for f in glob.glob(os.path.join(INTELLIGENCE_OUT_DIR, f"{capture_id}_*_flows.csv")):
            if f not in candidate_files:
                candidate_files.append(f)

        if not candidate_files:
            raise RuntimeError(f"No flow CSVs found to merge for capture_id={capture_id}")

        merged_rows = []
        seen_flow_ids = set()
        for csv_file in candidate_files:
            with open(csv_file, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    fid = row.get("Flow ID") or f"{row.get('Src IP')}-{row.get('Dst IP')}-{row.get('Src Port')}-{row.get('Dst Port')}-{row.get('Protocol')}"
                    if fid in seen_flow_ids:
                        continue
                    seen_flow_ids.add(fid)
                    merged_rows.append(row)

        # annotate rows by checking anomaly log timestamps and affected nodes
        annotated = []
        anomalies = list(self._anomaly_log)
        host_map = self._capture_host_map.get(capture_id, {})
        capture_time = self._capture_time_ranges.get(capture_id, {})
        capture_start = capture_time.get("start_ts")
        capture_end = capture_time.get("end_ts")
        for row in merged_rows:
            if not include_label_column:
                row.pop("Label", None)

            if include_anomaly_labels:
                matched = False
                for a in anomalies:
                    if a.get("capture_id") != capture_id:
                        continue

                    node = a.get("node")
                    profile = a.get("profile")
                    node_ip = host_map.get(node)

                    if node_ip and node_ip not in (row.get("Src IP"), row.get("Dst IP")):
                        continue

                    flow_start = row.get("Flow Start")
                    flow_end = row.get("Flow End")
                    flow_start = float(flow_start) if flow_start else None
                    flow_end = float(flow_end) if flow_end else None

                    anomaly_start = a.get("start_ts")
                    anomaly_end = a.get("expires_at")

                    overlaps = True
                    if flow_start and flow_end:
                        overlaps = not (flow_end < anomaly_start or flow_start > anomaly_end)
                    elif capture_start and capture_end:
                        overlaps = not (capture_end < anomaly_start or capture_start > anomaly_end)

                    if overlaps:
                        row["Anomaly Label"] = profile
                        row["Anomaly Start"] = anomaly_start
                        row["Anomaly End"] = anomaly_end
                        row["Anomaly Node"] = node
                        matched = True
                        break

                if not matched:
                    row["Anomaly Label"] = "NONE"

            annotated.append(row)

        # write merged CSV
        os.makedirs(INTELLIGENCE_OUT_DIR, exist_ok=True)
        out_path = output_path or os.path.join(INTELLIGENCE_OUT_DIR, f"{capture_id}_merged_training.csv")

        # compute header union
        header_fields = []
        for r in annotated:
            for k in r.keys():
                if k not in header_fields:
                    header_fields.append(k)

        with open(out_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=header_fields)
            writer.writeheader()
            for r in annotated:
                writer.writerow(r)

        with self._lock:
            self._last_merged_csv = out_path

        return {"merged_csv": out_path, "rows": len(annotated)}

    def _start_realtime_baseline(self, net):
        """Persistent iperf3 flows for full simulation baseline traffic.

        Uses ports 5301-5308 (separate from the protocol-mix server on 5201)
        so multiple concurrent clients don't compete for the same server slot.
        Provides continuous non-zero traffic so the GNN never measures 0 Mbps
        between protocol-mix cycles.
        """
        BASELINE_FLOWS = [
            ("e1_pc1", "dc_web",     "4M",  "tcp", 5301),
            ("e1_erp", "dc_web",     "6M",  "tcp", 5302),
            ("e2_pc1", "dc_web",     "4M",  "tcp", 5303),
            ("h1_pc",  "dc_web",     "3M",  "tcp", 5304),
            ("e2_pc2", "dc_monitor", "3M",  "tcp", 5305),
            ("e2_crm", "dc_monitor", "5M",  "tcp", 5306),
            ("h1_tv",  "dc_monitor", "2M",  "udp", 5307),
            ("h2_cam", "dc_monitor", "1M",  "udp", 5308),
        ]
        FLOW_DURATION = 30  # each iperf3 run; loop restarts immediately after

        # Start a dedicated iperf3 server for each port
        for dst_name, ports in [
            ("dc_web",     [5301, 5302, 5303, 5304]),
            ("dc_monitor", [5305, 5306, 5307, 5308]),
        ]:
            h = net.get(dst_name)
            for port in ports:
                h.cmd(
                    f"nohup iperf3 -s -p {port} "
                    f"--logfile /tmp/iperf3_rt_{dst_name}_{port}.log "
                    f">/dev/null 2>&1 &"
                )
                time.sleep(0.05)

        time.sleep(1)  # let servers bind before first client connects

        for src, dst, bw, proto, port in BASELINE_FLOWS:
            try:
                src_host = net.get(src)
                dst_ip   = net.get(dst).IP()
                udp_flag = "-u" if proto == "udp" else ""
                src_host.cmd(
                    f"nohup bash -c '"
                    f"while true; do "
                    f"iperf3 -c {dst_ip} {udp_flag} -b {bw} -t {FLOW_DURATION} -p {port} "
                    f">/tmp/iperf3_rt_c_{src}_{port}.log 2>&1 || true; "
                    f"sleep 0.5; "
                    f"done' >/dev/null 2>&1 &"
                )
            except Exception as exc:
                logger.debug(f"Baseline flow error {src}→{dst}:{port}: {exc}")

        logger.info("Full sim: baseline iperf3 flows started on ports 5301-5308")

    def _realtime_worker(self, net, interval_seconds):
        self._start_realtime_baseline(net)
        while not self._realtime_stop.is_set():
            capture_id = None
            cycle_start = time.time()

            try:
                cap = self.start_capture(net, label="realtime")
                capture_id = cap["capture_id"]

                while (time.time() - cycle_start) < interval_seconds and not self._realtime_stop.is_set():
                    self._run_realtime_traffic_cycle(net)
                    time.sleep(1) # Reduced from 2s to 1s for more density

                self.stop_capture()
                self.relay_capture_to_collector(capture_id)
                
                # Get current attack profile for better labeling
                current_attack = self._next_attack_profile if (self._next_attack_epoch and time.time() >= self._next_attack_epoch) else None
                if not current_attack and self._last_attack:
                    # Check if last attack is still "fresh" (within last 60s)
                    last_ts = datetime.fromisoformat(self._last_attack["timestamp"].replace("Z", ""))
                    if (datetime.utcnow() - last_ts).total_seconds() < 60:
                        current_attack = self._last_attack["name"]

                self.collector_extract_and_infer(capture_id, attack_hint=current_attack)

                with self._lock:
                    self._last_realtime_run = datetime.utcnow().isoformat() + "Z"
                    self._last_realtime_error = None

            except Exception as exc:
                if self.status().get("capture_running"):
                    try:
                        self.stop_capture()
                    except Exception:
                        pass

                with self._lock:
                    self._last_realtime_run = datetime.utcnow().isoformat() + "Z"
                    self._last_realtime_error = str(exc)

                time.sleep(2)

        self._clear_operational_anomalies(net)
        net.get("dc_web").cmd("pkill -f 'python3 -m http.server 8080' >/dev/null 2>&1")
        net.get("dc_monitor").cmd("pkill -f 'python3 -m http.server 8080' >/dev/null 2>&1")
        net.get("dc_monitor").cmd("pkill -f 'tcp sink 9000' >/dev/null 2>&1")
        # Kill all iperf3 processes (baseline loops + protocol-mix sessions)
        for host_name in [
            "e1_pc1", "e1_erp", "e2_pc1", "h1_pc",
            "e2_pc2", "e2_crm", "h1_tv", "h2_cam",
            "dc_web", "dc_monitor",
        ]:
            try:
                net.get(host_name).cmd("pkill -9 -f 'iperf3' >/dev/null 2>&1 || true")
            except Exception:
                pass
        with self._lock:
            self._realistic_services_started = False

    def _run_realtime_traffic_cycle(self, net):
        self._run_protocol_mix_cycle(net)
        self._maybe_inject_operational_anomaly(net)
        self._maybe_run_scheduled_attack(net)

    def _run_normal_sim_ids_check(self, net):
        """Run a short pcap capture and IDS inference during normal simulation.

        This gives the IDS real flow-level features to analyse even when the
        full pcap pipeline is not running.  The snapshot lasts IDS_CAP_SECS
        seconds on two switch interfaces, then feeds the extracted flows to
        intelligence_plane.infer() and stores the result as _last_inference so
        the /anomalies endpoint can return flow-based IDS alerts.
        """
        IDS_CAP_SECS = 10

        interfaces = self._capture_interfaces(net)[:2]  # two interfaces is enough
        if not interfaces:
            return

        capture_id = f"normsim_ids_{int(time.time())}"
        pcap_paths = []
        procs = []

        for intf in interfaces:
            safe = intf.replace("/", "_")
            path = os.path.join(CAPTURE_DIR, f"{capture_id}_{safe}.pcap")
            proc = subprocess.Popen(
                ["tcpdump", "-i", intf, "-n", "-s", "0", "-U", "-w", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            procs.append(proc)
            pcap_paths.append(path)

        self._normal_sim_stop.wait(IDS_CAP_SECS)  # sleep without blocking stop event

        for p in procs:
            try:
                p.terminate()
                p.wait(timeout=3)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

        rows = []
        for path in pcap_paths:
            try:
                rows.extend(self._read_packets_with_tshark(path))
            except Exception:
                pass
            finally:
                try:
                    os.remove(path)
                except Exception:
                    pass

        if not rows:
            return

        flow_features = self._build_flow_features(rows)
        if not flow_features:
            return

        inference = intelligence_plane.infer(
            flow_features,
            capture_id,
            window_seconds=float(IDS_CAP_SECS),
        )
        with self._lock:
            self._last_inference = {
                "capture_id": capture_id,
                "collector_flow_count": len(flow_features),
                "inference": inference,
            }
        logger.debug(
            "Normal sim IDS check: %d flows, %d suspicious",
            len(flow_features),
            inference.get("suspicious_flows", 0),
        )

    def _capture_interfaces(self, net):
        # Capture points are distribution/access switches instead of edge hosts.
        switch_names = ["isp_core", "ent1_sw", "ent2_sw", "home1_sw", "home2_sw", "dc_sw"]
        interfaces = []

        for switch_name in switch_names:
            sw = net.get(switch_name)
            for intf in sw.intfList():
                if intf.name == "lo":
                    continue
                interfaces.append(intf.name)

        # Keep unique order and avoid very noisy duplicates from accidental repeats
        seen = set()
        unique_interfaces = []
        for name in interfaces:
            if name in seen:
                continue
            seen.add(name)
            unique_interfaces.append(name)

        return unique_interfaces

    def _traffic_worker(self, net, duration_seconds):
        end_ts = time.time() + max(10, duration_seconds)

        try:
            while time.time() < end_ts and not self._traffic_stop.is_set():
                self._run_realtime_traffic_cycle(net)
                time.sleep(1.0)
        finally:
            self._clear_operational_anomalies(net)
            net.get("dc_web").cmd("pkill -f 'python3 -m http.server 8080' >/dev/null 2>&1")
            net.get("dc_monitor").cmd("pkill -f 'python3 -m http.server 8080' >/dev/null 2>&1")
            net.get("dc_monitor").cmd("pkill -f 'tcp sink 9000' >/dev/null 2>&1")
            with self._lock:
                self._realistic_services_started = False
                self._active_operational_anomalies = []

    def _run_protocol_mix_cycle(self, net):
        self._run_real_world_mix_cycle(net)

    def _run_real_world_mix_cycle(self, net):
        try:
            mix = self.get_realtime_settings().get("protocol_mix_weights", {})
            self._ensure_realistic_services(net)

            # --- Browsing Traffic ---
            if random.randint(1, 100) <= int(mix.get("browser", 75)):
                srcs = ["e1_pc1", "h2_pc", "h1_pc", "e2_pc1"]
                for src in random.sample(srcs, 2):
                    self._run_http_get(net, src, "dc_web", port=8080, path="/")

            # --- Streaming Traffic ---
            if random.randint(1, 100) <= int(mix.get("streaming_http", 80)):
                srcs = ["h1_pc", "e2_pc2", "h1_tv"]
                for src in random.sample(srcs, 1):
                    self._run_streaming_download(net, src, "dc_web", path="/assets/stream.bin", port=8080)

            # --- RTSP / IoT Traffic ---
            if random.randint(1, 100) <= int(mix.get("rtsp_streaming", 70)):
                self._run_rtsp_like_session(net, "h1_tv", "dc_monitor")
                self._run_rtsp_like_session(net, "h2_cam", "dc_monitor")

            # --- Bulk Transfers ---
            if random.randint(1, 100) <= int(mix.get("bulk_download", 70)):
                self._run_bulk_download(net, "e1_pc2", "dc_web", path="/assets/backup.bin", port=8080, rounds=1)
                self._run_bulk_download(net, "h2_nas", "dc_web", path="/assets/backup.bin", port=8080, rounds=1)

            # --- API / Microservices ---
            if random.randint(1, 100) <= int(mix.get("api_microservices", 70)):
                self._run_http_get(net, "e1_pc1", "dc_monitor", port=8080, path="/api/health")

            # --- Heavy Background Traffic (iperf3) ---
            if random.randint(1, 100) <= 85: # High probability for background load
                self._run_iperf_session(net, "e1_pc1", "dc_web", bandwidth="5M", duration=8)
                self._run_iperf_session(net, "h2_pc", "dc_monitor", bandwidth="3M", duration=8)
                self._run_iperf_session(net, "e1_erp", "dc_web", bandwidth="15M", duration=12)
                self._run_iperf_session(net, "e2_crm", "dc_monitor", bandwidth="12M", duration=12)

            # --- DNS Traffic ---
            if random.randint(1, 100) <= int(mix.get("dns", 80)):
                self._run_udp_burst_port(net, "h1_pc", "dc_pub_dns", port=53, packets=15, payload_prefix="dns_query")
                self._run_udp_burst_port(net, "e2_pc2", "dc_pub_dns", port=53, packets=15, payload_prefix="dns_query")

        except Exception as e:
            logger.error(f"Error in traffic mix cycle: {e}")

        # --- Protocol Specific Bursts ---
        if random.randint(1, 100) <= int(mix.get("quic_udp", 65)):
            self._run_udp_burst_port(net, "e2_pc1", "dc_web", port=443, packets=30, payload_prefix="quic")

        if random.randint(1, 100) <= int(mix.get("mqtt_telemetry", 55)):
            self._run_udp_burst_port(net, "h1_iot", "dc_monitor", port=1883, packets=35, payload_prefix="mqtt")
            self._run_udp_burst_port(net, "h2_cam", "dc_monitor", port=1883, packets=35, payload_prefix="mqtt")

        if random.randint(1, 100) <= int(mix.get("voip", 45)):
            self._run_udp_burst_port(net, "h1_tv", "dc_monitor", port=5060, packets=30, payload_prefix="sip_rtp")
            self._run_udp_burst_port(net, "h2_cam", "dc_monitor", port=5060, packets=30, payload_prefix="sip_rtp")

        if random.randint(1, 100) <= int(mix.get("ftp", 35)):
            self._run_tcp_connect_burst(net, "e2_pc2", "dc_monitor", port=21, attempts=8)
            self._run_tcp_connect_burst(net, "h1_pc", "dc_monitor", port=21, attempts=8)

        if random.randint(1, 100) <= int(mix.get("ssh", 45)):
            self._run_tcp_connect_burst(net, "e2_pc1", "dc_vpn", port=22, attempts=8)
            self._run_tcp_connect_burst(net, "h2_pc", "dc_vpn", port=22, attempts=8)

        if random.randint(1, 100) <= int(mix.get("database_replication", 40)):
            self._run_tcp_connect_burst(net, "dc_monitor", "dc_web", port=5432, attempts=12)
            self._run_tcp_connect_burst(net, "dc_web", "dc_monitor", port=3306, attempts=12)

        if random.randint(1, 100) <= int(mix.get("icmp", 35)):
            self._run_ping(net, "e1_pc1", "dc_web", count=4, interval=0.15)
            self._run_ping(net, "h2_pc", "dc_monitor", count=4, interval=0.15)

        if random.randint(1, 100) <= int(mix.get("igmp", 25)):
            self._run_udp_burst_port(net, "h1_tv", "224.0.0.22", port=1900, packets=10, payload_prefix="igmp_like")

    def _schedule_next_operational_anomaly(self):
        """Schedule the next automatic operational anomaly 3-8 minutes from now."""
        interval = random.randint(180, 480)
        self._next_operational_epoch = time.time() + interval
        logger.info(f"Full sim: next operational anomaly in {interval}s")

    def _maybe_inject_operational_anomaly(self, net):
        """Inject a netem-based operational anomaly on a timed schedule (3-8 min apart).

        Also prunes expired anomalies every call so netem state is always clean.
        Called once per second from _run_realtime_traffic_cycle.
        """
        with self._lock:
            expired_nodes = self._prune_expired_operational_anomalies()
        for _node_name in expired_nodes:
            self._clear_node_netem(net, _node_name)

        # Initialize schedule on first call
        if self._next_operational_epoch == 0.0:
            self._schedule_next_operational_anomaly()
            return

        if time.time() < self._next_operational_epoch:
            return

        # Time to inject the next operational anomaly
        rotation = [
            "congestion", "latency_spike", "packet_loss",
            "jitter", "bandwidth_throttle", "brownout",
        ]
        profile = rotation[self._op_anomaly_rotation_idx % len(rotation)]
        self._op_anomaly_rotation_idx += 1

        duration = random.randint(45, 90)  # 45-90 second window — long enough for GNN to capture
        target = None

        if profile == "congestion":
            target = random.choice(["h2_nas", "h1_pc"])
            self._inject_operational_anomaly(
                net, target, "congestion",
                delay_ms=75, jitter_ms=20, loss_pct=0.0, rate="5mbit",
                duration_seconds=duration,
            )
            gnn_engine.set_active_injection("congestion", duration, target_nodes=[target])

        elif profile == "latency_spike":
            target = random.choice(["e1_pc1", "e2_pc1"])
            self._inject_operational_anomaly(
                net, target, "latency_spike",
                delay_ms=280, jitter_ms=60, loss_pct=0.0, rate=None,
                duration_seconds=duration,
            )
            gnn_engine.set_active_injection("latency", duration, target_nodes=[target])

        elif profile == "packet_loss":
            target = random.choice(["dc_web", "dc_monitor"])
            self._inject_operational_anomaly(
                net, target, "packet_loss",
                delay_ms=20, jitter_ms=5, loss_pct=6.0, rate=None,
                duration_seconds=duration,
            )
            gnn_engine.set_active_injection("packet_loss", duration, target_nodes=[target])

        elif profile == "jitter":
            target = random.choice(["h1_tv", "h2_pc"])
            self._inject_operational_anomaly(
                net, target, "jitter",
                delay_ms=100, jitter_ms=45, loss_pct=0.0, rate="12mbit",
                duration_seconds=duration,
            )
            gnn_engine.set_active_injection("jitter", duration, target_nodes=[target])

        elif profile == "bandwidth_throttle":
            target = random.choice(["e1_erp", "dc_web"])
            self._inject_operational_anomaly(
                net, target, "bandwidth_throttle",
                delay_ms=25, jitter_ms=8, loss_pct=0.0, rate="2mbit",
                duration_seconds=duration,
            )
            gnn_engine.set_active_injection("congestion", duration, target_nodes=[target])

        elif profile == "brownout":
            target = random.choice(["dc_web", "h1_iot"])
            self._inject_operational_anomaly(
                net, target, "brownout",
                delay_ms=160, jitter_ms=50, loss_pct=4.0, rate="1mbit",
                duration_seconds=duration,
            )
            gnn_engine.set_active_injection("brownout", duration, target_nodes=[target])

        if target:
            logger.info(f"Full sim: auto operational anomaly '{profile}' on {target} for {duration}s")

        self._schedule_next_operational_anomaly()

    def _inject_operational_anomaly(self, net, node_name, profile, delay_ms, jitter_ms, loss_pct, rate, duration_seconds):
        start_ts = time.time()
        expires_at = start_ts + max(4, int(duration_seconds))
        qdisc = self._build_netem_command(delay_ms=delay_ms, jitter_ms=jitter_ms, loss_pct=loss_pct, rate=rate)

        self._clear_node_netem(net, node_name)
        node = net.get(node_name)
        node.cmd(f"tc qdisc replace dev {self._primary_host_interface(node)} root {qdisc}")

        anomaly = {
            "node": node_name,
            "profile": profile,
            "delay_ms": delay_ms,
            "jitter_ms": jitter_ms,
            "loss_pct": loss_pct,
            "rate": rate,
            "start_ts": start_ts,
            "expires_at": expires_at,
            "duration_seconds": int(max(4, int(duration_seconds))),
            "capture_id": self._capture_id,
        }

        with self._lock:
            self._active_operational_anomalies = [
                item for item in self._active_operational_anomalies if item.get("node") != node_name
            ]
            self._active_operational_anomalies.append(anomaly)
            # keep a persistent history for later capture-aligned labeling
            try:
                self._anomaly_log.append(dict(anomaly))
            except Exception:
                pass

    def _clear_operational_anomalies(self, net):
        with self._lock:
            active = list(self._active_operational_anomalies)
            self._active_operational_anomalies = []

        for item in active:
            self._clear_node_netem(net, item.get("node"))

    def _prune_expired_operational_anomalies(self) -> list:
        """Remove expired anomalies from the list and return their node names.

        Does NOT perform any network operations so it is safe to call while
        holding self._lock.  Callers must clear netem on returned nodes outside
        the lock to avoid blocking status() and API routes.
        """
        now = time.time()
        kept = []
        expired_nodes = []
        for item in list(self._active_operational_anomalies):
            if item.get("expires_at", 0) > now:
                kept.append(item)
            else:
                expired_nodes.append(item.get("node"))
        self._active_operational_anomalies = kept
        return expired_nodes

    @staticmethod
    def _primary_host_interface(node):
        return f"{node.name}-eth0"

    @staticmethod
    def _build_netem_command(delay_ms=0, jitter_ms=0, loss_pct=0.0, rate=None):
        parts = ["netem"]
        if delay_ms:
            if jitter_ms:
                parts.append(f"delay {int(delay_ms)}ms {int(jitter_ms)}ms")
            else:
                parts.append(f"delay {int(delay_ms)}ms")
        if loss_pct:
            parts.append(f"loss {float(loss_pct)}%")
        if rate:
            parts.append(f"rate {rate}")
        return " ".join(parts)

    @staticmethod
    def _clear_node_netem(net, node_name):
        if not node_name:
            return
        try:
            node = net.get(node_name)
        except Exception:
            return

        intf = f"{node.name}-eth0"
        node.cmd(f"tc qdisc del dev {intf} root >/dev/null 2>&1 || true")

    def _ensure_realistic_services(self, net):
        if self._realistic_services_started:
            return

        self._ensure_http_media_service(net)
        self._ensure_service_hub(net)
        self._realistic_services_started = True

    def _ensure_http_media_service(self, net):
        web_host = net.get("dc_web")
        web_host.cmd("mkdir -p /tmp/ai_sdn_web/assets")
        web_host.cmd(
            "bash -lc '"
            "if [[ ! -f /tmp/ai_sdn_web/assets/stream.bin ]]; then dd if=/dev/zero of=/tmp/ai_sdn_web/assets/stream.bin bs=1M count=24 status=none; fi; "
            "if [[ ! -f /tmp/ai_sdn_web/assets/backup.bin ]]; then dd if=/dev/zero of=/tmp/ai_sdn_web/assets/backup.bin bs=1M count=64 status=none; fi; "
            "cat > /tmp/ai_sdn_web/index.html <<\"EOF\"\n"
            "<html><body><h1>AI SDN Lab</h1><p>Streaming and bulk transfer test content.</p></body></html>\n"
            "EOF'"
        )
        web_host.cmd("pkill -f 'python3 -m http.server 8080' >/dev/null 2>&1")
        web_host.cmd("cd /tmp/ai_sdn_web && nohup python3 -m http.server 8080 >/tmp/dc_web_http.log 2>&1 &")
        # iperf3 server for bulk traffic generation (port 5201)
        web_host.cmd("pkill -f 'iperf3 -s' >/dev/null 2>&1")
        web_host.cmd("nohup iperf3 -s >/tmp/dc_web_iperf3.log 2>&1 &")

        monitor_host = net.get("dc_monitor")
        monitor_host.cmd("mkdir -p /tmp/ai_sdn_monitor")
        monitor_host.cmd(
            "bash -lc '"
            "cat > /tmp/ai_sdn_monitor/health.json <<\"EOF\"\n"
            "{\"status\": \"ok\", \"service\": \"monitor\"}\n"
            "EOF'"
        )
        monitor_host.cmd("pkill -f 'python3 -m http.server 8080' >/dev/null 2>&1")
        monitor_host.cmd("cd /tmp/ai_sdn_monitor && nohup python3 -m http.server 8080 >/tmp/dc_monitor_http.log 2>&1 &")
        # iperf3 server for bulk traffic generation (port 5201)
        monitor_host.cmd("pkill -f 'iperf3 -s' >/dev/null 2>&1")
        monitor_host.cmd("nohup iperf3 -s >/tmp/dc_monitor_iperf3.log 2>&1 &")

    def _ensure_service_hub(self, net):
        sink_host = net.get("dc_monitor")
        sink_host.cmd("pkill -f 'ai_sdn service hub' >/dev/null 2>&1")
        sink_host.cmd(
            "nohup python3 -u -c \"import select,socket,time\n"
            "tcp_ports=[1883,3306,5432,554,9000,443]\n"
            "udp_ports=[5060,10000,514,5683,1900]\n"
            "tcp=[]; udp=[]\n"
            "for port in tcp_ports:\n"
            "    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)\n"
            "    s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)\n"
            "    s.bind(('0.0.0.0',port)); s.listen(64); tcp.append(s)\n"
            "for port in udp_ports:\n"
            "    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)\n"
            "    s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)\n"
            "    s.bind(('0.0.0.0',port)); udp.append(s)\n"
            "print('ai_sdn service hub ready', flush=True)\n"
            "while True:\n"
            "    ready,_,_=select.select(tcp+udp,[],[],1.0)\n"
            "    for sock in ready:\n"
            "        if sock in tcp:\n"
            "            conn,_=sock.accept()\n"
            "            try:\n"
            "                conn.settimeout(0.3)\n"
            "                while conn.recv(65536):\n"
            "                    pass\n"
            "            except Exception:\n"
            "                pass\n"
            "            finally:\n"
            "                conn.close()\n"
            "        else:\n"
            "            try:\n"
            "                sock.recvfrom(65536)\n"
            "            except Exception:\n"
            "                pass\" >/tmp/dc_monitor_sink.log 2>&1 &"
        )

    @staticmethod
    def _host_command_exists(host, command):
        return host.cmd(f"command -v {command} >/dev/null 2>&1; echo $?\n").strip() == "0"

    @staticmethod
    def _host_process_running(host, pattern):
        return host.cmd(f"pgrep -f '{pattern}' >/dev/null 2>&1; echo $?\n").strip() == "0"

    @staticmethod
    def _host_shell_command(host, command):
        host.cmd(f"bash -lc '{command}'")

    @staticmethod
    def _run_rtsp_like_session(net, src_name, dst_name):
        src = net.get(src_name)
        dst_ip = net.get(dst_name).IP()

        if src.cmd("command -v curl >/dev/null 2>&1; echo $?\n").strip() == "0":
            src.cmd(f"curl -m 3 -s rtsp://{dst_ip}:554/stream >/dev/null 2>&1 || true")

        if src.cmd("command -v nc >/dev/null 2>&1; echo $?\n").strip() == "0":
            src.cmd(
                "bash -lc '"
                + f"printf \"OPTIONS rtsp://{dst_ip}:554/stream RTSP/1.0\\r\\nCSeq: 1\\r\\n\\r\\nDESCRIBE rtsp://{dst_ip}:554/stream RTSP/1.0\\r\\nCSeq: 2\\r\\n\\r\\n\" | nc -w2 {dst_ip} 554 >/dev/null 2>&1 || true"
                + "'"
            )

        src.cmd(f"nc -u -w1 {dst_ip} 10000 >/dev/null 2>&1 <<<'RTP_FRAME' || true")

    def _maybe_run_scheduled_attack(self, net):
        self._ensure_attack_schedule()
        if time.time() < self._next_attack_epoch:
            return

        profiles = [
            "PortScan", "DDoS", "DoS Hulk", "DoS slowloris",
            "FTP-Patator", "SSH-Patator", "Web Attack - SQL Injection", "Web Attack - XSS",
        ]
        profile = profiles[self._attack_rotation_idx % len(profiles)]
        self._attack_rotation_idx += 1

        self._execute_attack_profile(net, profile)

        # Tell GNN what attack is happening so it uses the correct label.
        _ATTACK_TO_GNN = {
            "PortScan":                   ("portscan",     ["h1_iot", "dc_web"]),
            "DDoS":                       ("ddos",         ["h1_iot", "h2_cam", "e2_pc2", "dc_web"]),
            "DoS Hulk":                   ("ddos",         ["h1_iot", "dc_web"]),
            "DoS slowloris":              ("ddos",         ["h2_cam", "dc_web"]),
            "FTP-Patator":                ("brute_force",  ["e2_pc2", "dc_monitor"]),
            "SSH-Patator":                ("brute_force",  ["e2_pc2", "dc_vpn"]),
            "Web Attack - SQL Injection": ("portscan",     ["h1_iot", "dc_web"]),
            "Web Attack - XSS":           ("portscan",     ["h2_cam", "dc_web"]),
        }
        gnn_type, targets = _ATTACK_TO_GNN.get(profile, ("portscan", []))
        gnn_engine.set_active_injection(gnn_type, duration_s=60, target_nodes=targets)

        self._last_attack = {
            "name": profile,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        logger.info(f"Full sim: scheduled cyber attack '{profile}' → GNN label '{gnn_type}'")
        self._schedule_next_attack()

    def _execute_attack_profile(self, net, profile):
        intensity = float(self.get_realtime_settings().get("attack_intensity", 1.0))
        burst = lambda n: max(1, int(n * intensity))

        if profile == "PortScan":
            self._run_port_scan(net, "h1_iot", "dc_web", ports=[21, 22, 23, 25, 53, 80, 443, 8080, 3306, 3389, 5900])
            return

        if profile == "DDoS":
            # Use iperf3 for high-volume UDP flood
            self._run_iperf_session(net, "h1_iot", "dc_web", bandwidth="40M", duration=12)
            self._run_iperf_session(net, "h2_cam", "dc_web", bandwidth="40M", duration=12)
            self._run_iperf_session(net, "e2_pc2", "dc_web", bandwidth="40M", duration=12)
            return

        if profile == "DoS Hulk":
            self._run_http_flood(net, "h1_iot", "dc_web", port=8080, requests=burst(150))
            return

        if profile == "DoS slowloris":
            self._run_slow_http_like(net, "h2_cam", "dc_web", port=8080, sockets=burst(48))
            return

        if profile == "FTP-Patator":
            self._run_tcp_connect_burst(net, "h1_iot", "dc_monitor", port=21, attempts=burst(80))
            return

        if profile == "SSH-Patator":
            self._run_tcp_connect_burst(net, "h2_cam", "dc_vpn", port=22, attempts=burst(80))
            return

        if profile == "Web Attack - SQL Injection":
            self._run_http_payload_attack(
                net,
                "h1_iot",
                "dc_web",
                payload="id=1%20OR%201=1--",
                port=8080,
                requests=burst(30),
            )
            return

        if profile == "Web Attack - XSS":
            self._run_http_payload_attack(
                net,
                "h2_cam",
                "dc_web",
                payload="q=%3Cscript%3Ealert(1)%3C/script%3E",
                port=8080,
                requests=burst(30),
            )
            return

        if profile == "Bot":
            self._run_udp_burst_port(net, "h1_iot", "dc_monitor", port=6667, packets=burst(80), payload_prefix="bot_c2")
            return

        if profile == "Infiltration":
            self._run_tcp_connect_burst(net, "h2_cam", "dc_vpn", port=22, attempts=burst(18))
            self._run_udp_burst_port(net, "h2_cam", "dc_pub_dns", port=53, packets=burst(90), payload_prefix="dns_tunnel")
            return

    @staticmethod
    def _run_ping(net, src_name, dst_name, count=3, interval=0.2):
        src = net.get(src_name)
        dst_ip = net.get(dst_name).IP()
        src.cmd(f"ping -c {count} -i {interval} -W 1 {dst_ip} >/dev/null 2>&1")

    @staticmethod
    def _run_ping_flood_like(net, src_name, dst_name, bursts=20):
        src = net.get(src_name)
        dst_ip = net.get(dst_name).IP()
        src.cmd(
            f"bash -c 'for i in $(seq 1 {bursts}); do ping -c 1 -W 1 {dst_ip} >/dev/null 2>&1; done'"
        )

    @staticmethod
    def _run_iperf_session(net, src_name, dst_name, bandwidth="10M", duration=5):
        src = net.get(src_name)
        dst_ip = net.get(dst_name).IP()
        # Run iperf3 client in non-blocking mode
        src.cmd(f"iperf3 -c {dst_ip} -b {bandwidth} -t {duration} >/dev/null 2>&1 &")

    @staticmethod
    def _run_http_get(net, src_name, dst_name, port=8080, path="/"):
        src = net.get(src_name)
        dst_ip = net.get(dst_name).IP()

        if src.cmd("command -v curl >/dev/null 2>&1; echo $?\n").strip() == "0":
            src.cmd(f"curl -m 3 -s http://{dst_ip}:{port}{path} >/dev/null 2>&1")
            return

        if src.cmd("command -v wget >/dev/null 2>&1; echo $?\n").strip() == "0":
            src.cmd(f"wget -T 3 -q -O /dev/null http://{dst_ip}:{port}{path} >/dev/null 2>&1")

    @staticmethod
    def _run_streaming_download(net, src_name, dst_name, path="/assets/stream.bin", port=8080):
        src = net.get(src_name)
        dst_ip = net.get(dst_name).IP()

        if src.cmd("command -v curl >/dev/null 2>&1; echo $?\n").strip() == "0":
            src.cmd(
                f"curl --limit-rate 2m --max-time 8 -s http://{dst_ip}:{port}{path} >/dev/null 2>&1"
            )
            return

        if src.cmd("command -v wget >/dev/null 2>&1; echo $?\n").strip() == "0":
            src.cmd(
                f"wget --limit-rate=2m -T 8 -q -O /dev/null http://{dst_ip}:{port}{path} >/dev/null 2>&1"
            )

    @staticmethod
    def _run_bulk_download(net, src_name, dst_name, path="/assets/backup.bin", port=8080, rounds=1):
        src = net.get(src_name)
        dst_ip = net.get(dst_name).IP()

        if src.cmd("command -v curl >/dev/null 2>&1; echo $?\n").strip() == "0":
            src.cmd(
                "bash -lc '"
                + f"for i in $(seq 1 {rounds}); do curl -m 12 -s http://{dst_ip}:{port}{path} >/dev/null 2>&1 || true; done"
                + "'"
            )
            return

        if src.cmd("command -v wget >/dev/null 2>&1; echo $?\n").strip() == "0":
            src.cmd(
                "bash -lc '"
                + f"for i in $(seq 1 {rounds}); do wget -T 12 -q -O /dev/null http://{dst_ip}:{port}{path} >/dev/null 2>&1 || true; done"
                + "'"
            )

    @staticmethod
    def _run_bulk_upload(net, src_name, dst_name, port=9000, bytes_count=8_000_000):
        src = net.get(src_name)
        dst_ip = net.get(dst_name).IP()

        if src.cmd("command -v nc >/dev/null 2>&1; echo $?\n").strip() != "0":
            return

        src.cmd(
            "bash -lc '"
            + f"head -c {bytes_count} /dev/zero | tr '\\0' 'A' | nc -w3 {dst_ip} {port} >/dev/null 2>&1 || true"
            + "'"
        )

    @staticmethod
    def _run_http_flood(net, src_name, dst_name, port=8080, requests=60):
        src = net.get(src_name)
        dst_ip = net.get(dst_name).IP()
        src.cmd(
            "bash -lc '"
            + f"for i in $(seq 1 {requests}); do curl -m 1 -s http://{dst_ip}:{port}/ >/dev/null 2>&1 || true; done"
            + "'"
        )

    @staticmethod
    def _run_http_payload_attack(net, src_name, dst_name, payload, port=8080, requests=20):
        src = net.get(src_name)
        dst_ip = net.get(dst_name).IP()
        src.cmd(
            "bash -lc '"
            + f"for i in $(seq 1 {requests}); do curl -m 1 -s \"http://{dst_ip}:{port}/?{payload}\" >/dev/null 2>&1 || true; done"
            + "'"
        )

    @staticmethod
    def _run_slow_http_like(net, src_name, dst_name, port=8080, sockets=20):
        src = net.get(src_name)
        dst_ip = net.get(dst_name).IP()
        src.cmd(
            "bash -lc '"
            + f"for i in $(seq 1 {sockets}); do (printf \"GET / HTTP/1.1\\r\\nHost: x\\r\\n\"; sleep 0.4) | nc -w2 {dst_ip} {port} >/dev/null 2>&1; done"
            + "'"
        )

    @staticmethod
    def _run_udp_burst(net, src_name, dst_name, packets=30):
        src = net.get(src_name)
        dst_ip = net.get(dst_name).IP()

        if src.cmd("command -v nc >/dev/null 2>&1; echo $?\n").strip() != "0":
            return

        src.cmd(
            "bash -lc '"
            + f"for i in $(seq 1 {packets}); do echo udp_sample_$i | nc -u -w1 {dst_ip} 9999 >/dev/null 2>&1; done"
            + "'"
        )

    @staticmethod
    def _run_udp_burst_port(net, src_name, dst_name_or_ip, port=9999, packets=20, payload_prefix="udp"):
        src = net.get(src_name)
        if src.cmd("command -v nc >/dev/null 2>&1; echo $?\n").strip() != "0":
            return

        if dst_name_or_ip.count(".") == 3:
            dst_ip = dst_name_or_ip
        else:
            dst_ip = net.get(dst_name_or_ip).IP()

        src.cmd(
            "bash -lc '"
            + f"for i in $(seq 1 {packets}); do echo {payload_prefix}_$i | nc -u -w1 {dst_ip} {port} >/dev/null 2>&1; done"
            + "'"
        )

    @staticmethod
    def _run_tcp_connect_burst(net, src_name, dst_name_or_ip, port=22, attempts=10):
        src = net.get(src_name)
        if src.cmd("command -v nc >/dev/null 2>&1; echo $?\n").strip() != "0":
            return

        if dst_name_or_ip.count(".") == 3:
            dst_ip = dst_name_or_ip
        else:
            dst_ip = net.get(dst_name_or_ip).IP()

        src.cmd(
            "bash -lc '"
            + f"for i in $(seq 1 {attempts}); do nc -z -w1 {dst_ip} {port} >/dev/null 2>&1 || true; done"
            + "'"
        )

    @staticmethod
    def _run_port_scan(net, src_name, dst_name, ports):
        src = net.get(src_name)
        dst_ip = net.get(dst_name).IP()

        if src.cmd("command -v nc >/dev/null 2>&1; echo $?\n").strip() != "0":
            return

        port_list = " ".join(str(port) for port in ports)
        src.cmd(
            "bash -lc '"
            + f"for p in {port_list}; do nc -z -w1 {dst_ip} $p >/dev/null 2>&1 || true; done"
            + "'"
        )

    @staticmethod
    def _run_dns_like(net, src_name, dst_name):
        src = net.get(src_name)
        dst_ip = net.get(dst_name).IP()

        if src.cmd("command -v dig >/dev/null 2>&1; echo $?\n").strip() == "0":
            src.cmd(f"dig @{dst_ip} example.com +short >/dev/null 2>&1")
            return

        if src.cmd("command -v nslookup >/dev/null 2>&1; echo $?\n").strip() == "0":
            src.cmd(f"nslookup example.com {dst_ip} >/dev/null 2>&1")
            return

        if src.cmd("command -v nc >/dev/null 2>&1; echo $?\n").strip() == "0":
            src.cmd(f"echo dns_query | nc -u -w1 {dst_ip} 53 >/dev/null 2>&1")

    @staticmethod
    def _command_exists(command):
        return subprocess.call(
            ["bash", "-lc", f"command -v {command} >/dev/null 2>&1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ) == 0

    @staticmethod
    def _read_packets_with_tshark(pcap_path):
        # Export a minimal packet schema required to derive CICIDS-style flow stats.
        cmd = [
            "tshark",
            "-r",
            pcap_path,
            "-T",
            "fields",
            "-E",
            "separator=,",
            "-e",
            "frame.time_epoch",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "tcp.srcport",
            "-e",
            "tcp.dstport",
            "-e",
            "udp.srcport",
            "-e",
            "udp.dstport",
            "-e",
            "ip.proto",
            "-e",
            "frame.len",
        ]

        try:
            output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        except FileNotFoundError as exc:
            raise RuntimeError("tshark not found. Install wireshark/tshark to extract CICIDS-like features") from exc

        packets = []
        for line in output.splitlines():
            cols = line.strip().split(",")
            if len(cols) < 9:
                continue
            if not cols[1] or not cols[2]:
                continue

            ts = float(cols[0]) if cols[0] else 0.0
            src_ip = cols[1]
            dst_ip = cols[2]
            src_port = cols[3] or cols[5] or "0"
            dst_port = cols[4] or cols[6] or "0"
            proto = cols[7] or "0"
            pkt_len = int(cols[8]) if cols[8] else 0

            packets.append(
                {
                    "ts": ts,
                    "src_ip": src_ip,
                    "dst_ip": dst_ip,
                    "src_port": src_port,
                    "dst_port": dst_port,
                    "proto": proto,
                    "length": pkt_len,
                }
            )

        return packets

    @staticmethod
    def _build_flow_features(packets):
        # Bidirectional flow aggregation by 5-tuple with reverse-direction matching.
        flows = {}

        for pkt in packets:
            key = (
                pkt["src_ip"],
                pkt["dst_ip"],
                pkt["src_port"],
                pkt["dst_port"],
                pkt["proto"],
            )
            rev_key = (
                pkt["dst_ip"],
                pkt["src_ip"],
                pkt["dst_port"],
                pkt["src_port"],
                pkt["proto"],
            )

            if key in flows:
                flow_key = key
                direction = "fwd"
            elif rev_key in flows:
                flow_key = rev_key
                direction = "bwd"
            else:
                flow_key = key
                direction = "fwd"
                flows[flow_key] = {
                    "timestamps": [],
                    "lengths": [],
                    "fwd_pkts": 0,
                    "bwd_pkts": 0,
                    "fwd_bytes": 0,
                    "bwd_bytes": 0,
                }

            flow = flows[flow_key]
            flow["timestamps"].append(pkt["ts"])
            flow["lengths"].append(pkt["length"])

            if direction == "fwd":
                flow["fwd_pkts"] += 1
                flow["fwd_bytes"] += pkt["length"]
            else:
                flow["bwd_pkts"] += 1
                flow["bwd_bytes"] += pkt["length"]

        rows = []
        for flow_key, data in flows.items():
            src_ip, dst_ip, src_port, dst_port, proto = flow_key
            times = sorted(data["timestamps"])
            lengths = data["lengths"]

            duration = max(0.0, times[-1] - times[0]) if len(times) > 1 else 0.0
            total_packets = data["fwd_pkts"] + data["bwd_pkts"]
            total_bytes = data["fwd_bytes"] + data["bwd_bytes"]
            flow_start = times[0] if times else 0.0
            flow_end = times[-1] if times else 0.0

            iats = []
            for idx in range(1, len(times)):
                iats.append(times[idx] - times[idx - 1])

            active_periods = []
            idle_periods = []
            if times:
                active_start = times[0]
                prev = times[0]
                for ts in times[1:]:
                    gap = ts - prev
                    if gap > 1.0:
                        active_periods.append(prev - active_start)
                        idle_periods.append(gap)
                        active_start = ts
                    prev = ts
                active_periods.append(prev - active_start)

            pkt_len_mean = statistics.mean(lengths) if lengths else 0.0
            pkt_len_std = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0

            flow_byts_s = (total_bytes / duration) if duration > 0 else float(total_bytes)
            flow_pkts_s = (total_packets / duration) if duration > 0 else float(total_packets)

            label = "MALICIOUS_SIM" if src_ip in ATTACKER_IP_PREFIXES else "BENIGN"

            rows.append(
                {
                    "Flow ID": f"{src_ip}-{dst_ip}-{src_port}-{dst_port}-{proto}",
                    "Src IP": src_ip,
                    "Dst IP": dst_ip,
                    "Src Port": src_port,
                    "Dst Port": dst_port,
                    "Protocol": proto,
                    "Flow Start": round(flow_start, 6),
                    "Flow End": round(flow_end, 6),
                    "Flow Duration": round(duration, 6),
                    "Tot Fwd Pkts": data["fwd_pkts"],
                    "Tot Bwd Pkts": data["bwd_pkts"],
                    "TotLen Fwd Pkts": data["fwd_bytes"],
                    "TotLen Bwd Pkts": data["bwd_bytes"],
                    "Pkt Len Mean": round(pkt_len_mean, 6),
                    "Pkt Len Max": max(lengths) if lengths else 0,
                    "Pkt Len Std": round(pkt_len_std, 6),
                    "Flow Byts/s": round(flow_byts_s, 6),
                    "Flow Pkts/s": round(flow_pkts_s, 6),
                    "Flow IAT Mean": round(statistics.mean(iats), 6) if iats else 0.0,
                    "Flow IAT Std": round(statistics.pstdev(iats), 6) if len(iats) > 1 else 0.0,
                    "Flow IAT Max": round(max(iats), 6) if iats else 0.0,
                    "Active Mean": round(statistics.mean(active_periods), 6) if active_periods else 0.0,
                    "Active Std": round(statistics.pstdev(active_periods), 6) if len(active_periods) > 1 else 0.0,
                    "Idle Mean": round(statistics.mean(idle_periods), 6) if idle_periods else 0.0,
                    "Idle Std": round(statistics.pstdev(idle_periods), 6) if len(idle_periods) > 1 else 0.0,
                    "Label": label,
                }
            )

        return rows

    @staticmethod
    def _write_flow_csv(flow_features, out_path):
        header = [
            "Flow ID",
            "Src IP",
            "Dst IP",
            "Src Port",
            "Dst Port",
            "Protocol",
            "Flow Start",
            "Flow End",
            "Flow Duration",
            "Tot Fwd Pkts",
            "Tot Bwd Pkts",
            "TotLen Fwd Pkts",
            "TotLen Bwd Pkts",
            "Pkt Len Mean",
            "Pkt Len Max",
            "Pkt Len Std",
            "Flow Byts/s",
            "Flow Pkts/s",
            "Flow IAT Mean",
            "Flow IAT Std",
            "Flow IAT Max",
            "Active Mean",
            "Active Std",
            "Idle Mean",
            "Idle Std",
            "Label",
        ]

        with open(out_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=header)
            writer.writeheader()
            for row in flow_features:
                writer.writerow(row)


lab_pipeline = LabPipeline()
