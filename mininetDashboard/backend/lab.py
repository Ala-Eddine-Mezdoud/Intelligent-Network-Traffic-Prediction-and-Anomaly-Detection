import csv
import glob
import json
import os
import shutil
import statistics
import subprocess
import threading
import time
from datetime import datetime

from .intelligence import intelligence_plane


CAPTURE_DIR = "/home/mininet/mininetDashboard/captures"
COLLECTOR_INBOX_DIR = "/home/mininet/mininetDashboard/captures/collector_inbox"
INTELLIGENCE_OUT_DIR = "/home/mininet/mininetDashboard/captures/intelligence_out"
ATTACKER_IP_PREFIXES = {"192.168.10.31", "192.168.20.21"}


class LabPipeline:
    def __init__(self):
        self._lock = threading.Lock()
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
            }

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

        benign_patterns = [
            ("e1_pc1", "dc_web"),
            ("e1_pc2", "e2_crm"),
            ("e2_pc1", "dc_vpn"),
            ("h1_pc", "dc_pub_dns"),
            ("h2_pc", "dc_web"),
            ("h2_nas", "dc_monitor"),
        ]

        suspicious_patterns = [
            ("h1_iot", "dc_web"),
            ("h2_cam", "dc_web"),
        ]

        # Lightweight HTTP service to create application-layer traffic features.
        web_host = net.get("dc_web")
        web_host.cmd("pkill -f 'http.server 8080' >/dev/null 2>&1")
        web_host.cmd("nohup python3 -m http.server 8080 >/tmp/dc_web_http.log 2>&1 &")

        idx = 0
        try:
            while time.time() < end_ts and not self._traffic_stop.is_set():
                src_name, dst_name = benign_patterns[idx % len(benign_patterns)]
                self._run_ping(net, src_name, dst_name, count=3, interval=0.2)
                self._run_http_get(net, src_name, "dc_web", port=8080)

                if idx % 2 == 0:
                    self._run_udp_burst(net, "h2_nas", "dc_monitor", packets=30)

                if idx % 3 == 0:
                    atk_src, atk_dst = suspicious_patterns[(idx // 3) % len(suspicious_patterns)]
                    # Bursty ICMP profile used as a simple anomalous pattern.
                    self._run_ping_flood_like(net, atk_src, atk_dst, bursts=20)

                idx += 1
                time.sleep(0.3)
        finally:
            web_host.cmd("pkill -f 'http.server 8080' >/dev/null 2>&1")

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
