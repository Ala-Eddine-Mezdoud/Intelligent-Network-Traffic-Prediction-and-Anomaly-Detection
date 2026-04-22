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
from datetime import datetime

from .intelligence import intelligence_plane


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
        self._last_relay = None
        self._last_inference = None
        self._traffic_thread = None
        self._traffic_stop = threading.Event()
        self._realtime_thread = None
        self._realtime_stop = threading.Event()
        self._realtime_interval_seconds = 30
        self._last_realtime_run = None
        self._last_realtime_error = None
        self._realtime_settings = {
            "attack_interval_min_seconds": 60,
            "attack_interval_max_seconds": 300,
            "attack_intensity": 1.0,
            "protocol_mix_weights": {
                "icmp": 55,
                "http": 75,
                "dns": 65,
                "dhcp": 40,
                "quic_udp": 60,
                "ftp": 35,
                "ssh": 45,
                "igmp": 25,
            },
        }
        self._next_attack_epoch = None
        self._next_attack_profile = None
        self._last_attack = None
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
                "last_relay": self._last_relay,
                "last_inference": self._last_inference,
                "realtime_running": bool(self._realtime_thread and self._realtime_thread.is_alive()),
                "realtime_interval_seconds": self._realtime_interval_seconds,
                "last_realtime_run": self._last_realtime_run,
                "last_realtime_error": self._last_realtime_error,
                "realtime_settings": self.get_realtime_settings(),
                "next_attack_profile": self._next_attack_profile,
                "next_attack_in_seconds": self._seconds_to_next_attack(),
                "last_attack": self._last_attack,
            }

    def realtime_status(self):
        with self._lock:
            return {
                "running": bool(self._realtime_thread and self._realtime_thread.is_alive()),
                "interval_seconds": self._realtime_interval_seconds,
                "last_realtime_run": self._last_realtime_run,
                "last_realtime_error": self._last_realtime_error,
                "last_inference": self._last_inference,
                "realtime_settings": self.get_realtime_settings(),
                "next_attack_profile": self._next_attack_profile,
                "next_attack_in_seconds": self._seconds_to_next_attack(),
                "last_attack": self._last_attack,
            }

    def get_realtime_settings(self):
        with self._lock:
            mix = dict(self._realtime_settings.get("protocol_mix_weights", {}))
            return {
                "attack_interval_min_seconds": int(self._realtime_settings.get("attack_interval_min_seconds", 60)),
                "attack_interval_max_seconds": int(self._realtime_settings.get("attack_interval_max_seconds", 300)),
                "attack_intensity": float(self._realtime_settings.get("attack_intensity", 1.0)),
                "protocol_mix_weights": mix,
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

        with self._lock:
            self._realtime_settings["attack_interval_min_seconds"] = min_s
            self._realtime_settings["attack_interval_max_seconds"] = max_s
            self._realtime_settings["attack_intensity"] = intensity
            self._realtime_settings["protocol_mix_weights"] = next_mix

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

    def start_realtime(self, net, interval_seconds=30):
        interval_seconds = int(interval_seconds)
        if interval_seconds < 10:
            raise RuntimeError("interval_seconds must be at least 10")

        if not self._command_exists("tcpdump"):
            raise RuntimeError("tcpdump not found. Install tcpdump before starting realtime mode")
        if not self._command_exists("tshark"):
            raise RuntimeError("tshark not found. Install tshark before starting realtime mode")

        with self._lock:
            if self._realtime_thread and self._realtime_thread.is_alive():
                raise RuntimeError("Realtime loop already running")
            if self._capture_processes:
                raise RuntimeError("Cannot start realtime loop while manual capture is running")

            self._realtime_interval_seconds = interval_seconds
            self._last_realtime_error = None
            self._schedule_next_attack()
            self._realtime_stop.clear()
            thread = threading.Thread(
                target=self._realtime_worker,
                args=(net, interval_seconds),
                daemon=True,
            )
            self._realtime_thread = thread
            thread.start()

        return {
            "started": True,
            "interval_seconds": interval_seconds,
        }

    def stop_realtime(self):
        self._realtime_stop.set()

        with self._lock:
            thread = self._realtime_thread

        if thread and thread.is_alive():
            thread.join(timeout=5)

        if self.status().get("capture_running"):
            self.stop_capture()

        return {"stopped": True}

    def start_capture(self, net, label="session"):
        if not self._command_exists("tcpdump"):
            raise RuntimeError("tcpdump not found. Install tcpdump before starting capture")

        with self._lock:
            if self._capture_processes:
                raise RuntimeError("Capture already running")

            os.makedirs(CAPTURE_DIR, exist_ok=True)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            capture_id = f"{label}_{timestamp}"

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
        with self._lock:
            if self._traffic_thread and self._traffic_thread.is_alive():
                raise RuntimeError("Traffic generator already running")

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

    def collector_extract_and_infer(self, capture_id):
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

        inference = intelligence_plane.infer(flow_features, capture_id)
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

    def _realtime_worker(self, net, interval_seconds):
        while not self._realtime_stop.is_set():
            capture_id = None
            cycle_start = time.time()

            try:
                cap = self.start_capture(net, label="realtime")
                capture_id = cap["capture_id"]

                while (time.time() - cycle_start) < interval_seconds and not self._realtime_stop.is_set():
                    self._run_realtime_traffic_cycle(net)
                    time.sleep(2)

                self.stop_capture()
                self.relay_capture_to_collector(capture_id)
                self.collector_extract_and_infer(capture_id)

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

    def _run_realtime_traffic_cycle(self, net):
        self._run_protocol_mix_cycle(net)
        self._maybe_run_scheduled_attack(net)

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
                self._run_protocol_mix_cycle(net)
                self._maybe_run_scheduled_attack(net)
                time.sleep(1.0)
        finally:
            net.get("dc_web").cmd("pkill -f 'http.server 8080' >/dev/null 2>&1")

    def _run_protocol_mix_cycle(self, net):
        mix = self.get_realtime_settings().get("protocol_mix_weights", {})

        # Lightweight HTTP service to generate web traffic features.
        web_host = net.get("dc_web")
        web_host.cmd("pkill -f 'http.server 8080' >/dev/null 2>&1")
        web_host.cmd("nohup python3 -m http.server 8080 >/tmp/dc_web_http.log 2>&1 &")

        if random.randint(1, 100) <= int(mix.get("icmp", 50)):
            self._run_ping(net, "e1_pc1", "dc_web", count=2, interval=0.2)

        if random.randint(1, 100) <= int(mix.get("http", 70)):
            self._run_http_get(net, "e1_pc1", "dc_web", port=8080)
            self._run_http_get(net, "h2_pc", "dc_web", port=8080)

        if random.randint(1, 100) <= int(mix.get("dns", 60)):
            self._run_dns_like(net, "e1_pc2", "dc_pub_dns")
            self._run_dns_like(net, "h1_pc", "dc_pub_dns")

        if random.randint(1, 100) <= int(mix.get("dhcp", 35)):
            self._run_udp_burst_port(net, "e1_pc1", "e1_dhcp", port=67, packets=8, payload_prefix="dhcp_discover")
            self._run_udp_burst_port(net, "e1_dhcp", "e1_pc1", port=68, packets=8, payload_prefix="dhcp_offer")

        if random.randint(1, 100) <= int(mix.get("quic_udp", 55)):
            self._run_udp_burst_port(net, "h2_nas", "dc_web", port=443, packets=20, payload_prefix="quic")

        if random.randint(1, 100) <= int(mix.get("ftp", 30)):
            self._run_tcp_connect_burst(net, "e2_pc2", "dc_monitor", port=21, attempts=6)

        if random.randint(1, 100) <= int(mix.get("ssh", 40)):
            self._run_tcp_connect_burst(net, "e2_pc1", "dc_vpn", port=22, attempts=6)

        if random.randint(1, 100) <= int(mix.get("igmp", 20)):
            self._run_udp_burst_port(net, "h1_tv", "224.0.0.22", port=1900, packets=6, payload_prefix="igmp_like")

    def _maybe_run_scheduled_attack(self, net):
        self._ensure_attack_schedule()
        if time.time() < self._next_attack_epoch:
            return

        profile = self._next_attack_profile
        self._execute_attack_profile(net, profile)
        self._last_attack = {
            "name": profile,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        self._schedule_next_attack()

    def _execute_attack_profile(self, net, profile):
        intensity = float(self.get_realtime_settings().get("attack_intensity", 1.0))
        burst = lambda n: max(1, int(n * intensity))

        if profile == "PortScan":
            self._run_port_scan(net, "h1_iot", "dc_web", ports=[21, 22, 23, 53, 80, 443, 8080, 3306, 3389])
            return

        if profile == "DDoS":
            self._run_udp_burst_port(net, "h1_iot", "dc_web", port=443, packets=burst(120), payload_prefix="ddos_quic")
            self._run_udp_burst_port(net, "h2_cam", "dc_web", port=443, packets=burst(120), payload_prefix="ddos_quic")
            return

        if profile == "DoS Hulk":
            self._run_http_flood(net, "h1_iot", "dc_web", port=8080, requests=burst(80))
            return

        if profile == "DoS slowloris":
            self._run_slow_http_like(net, "h2_cam", "dc_web", port=8080, sockets=burst(24))
            return

        if profile == "FTP-Patator":
            self._run_tcp_connect_burst(net, "h1_iot", "dc_monitor", port=21, attempts=burst(40))
            return

        if profile == "SSH-Patator":
            self._run_tcp_connect_burst(net, "h2_cam", "dc_vpn", port=22, attempts=burst(40))
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
    def _run_http_get(net, src_name, dst_name, port=8080):
        src = net.get(src_name)
        dst_ip = net.get(dst_name).IP()

        if src.cmd("command -v curl >/dev/null 2>&1; echo $?\n").strip() == "0":
            src.cmd(f"curl -m 2 -s http://{dst_ip}:{port}/ >/dev/null 2>&1")
            return

        if src.cmd("command -v wget >/dev/null 2>&1; echo $?\n").strip() == "0":
            src.cmd(f"wget -T 2 -q -O /dev/null http://{dst_ip}:{port}/ >/dev/null 2>&1")

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
