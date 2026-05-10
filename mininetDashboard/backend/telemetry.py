"""Time-windowed telemetry collector for GNN training data.

Samples per-node and per-link metrics at fixed intervals to build
graph snapshots suitable for temporal GNN prediction models.
"""

import logging
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class NodeSnapshot:
    """Metrics for a single node in one time window."""

    name: str
    ip: str = ""
    zone: str = ""
    node_type: str = ""
    # Traffic counters (delta for this window)
    bytes_sent: float = 0.0
    bytes_recv: float = 0.0
    pkts_sent: float = 0.0
    pkts_recv: float = 0.0
    pkt_drops: float = 0.0
    # Latency probing
    latency_ms: float = 0.0
    jitter_ms: float = 0.0
    # Connection state
    tcp_connections: int = 0
    retransmits: int = 0
    # Queue / netem state
    queue_depth_bytes: int = 0
    queue_depth_pkts: int = 0
    bandwidth_limit_mbit: float = 0.0
    netem_delay_ms: float = 0.0
    netem_loss_pct: float = 0.0

    def feature_vector(self) -> List[float]:
        """Return ordered numeric feature vector for GNN node input."""
        return [
            self.bytes_sent,
            self.bytes_recv,
            self.pkts_sent,
            self.pkts_recv,
            self.pkt_drops,
            self.latency_ms,
            self.jitter_ms,
            float(self.tcp_connections),
            float(self.retransmits),
            float(self.queue_depth_bytes),
            float(self.queue_depth_pkts),
            self.bandwidth_limit_mbit,
            self.netem_delay_ms,
            self.netem_loss_pct,
        ]

    @staticmethod
    def feature_names() -> List[str]:
        return [
            "bytes_sent",
            "bytes_recv",
            "pkts_sent",
            "pkts_recv",
            "pkt_drops",
            "latency_ms",
            "jitter_ms",
            "tcp_connections",
            "retransmits",
            "queue_depth_bytes",
            "queue_depth_pkts",
            "bandwidth_limit_mbit",
            "netem_delay_ms",
            "netem_loss_pct",
        ]


@dataclass
class EdgeSnapshot:
    """Metrics for a single link in one time window."""

    source: str
    target: str
    # Traffic through this link
    bytes_through: float = 0.0
    utilization_pct: float = 0.0
    active_flows: int = 0
    # Protocol breakdown
    protocol_tcp_pct: float = 0.0
    protocol_udp_pct: float = 0.0
    protocol_icmp_pct: float = 0.0

    def feature_vector(self) -> List[float]:
        return [
            self.bytes_through,
            self.utilization_pct,
            float(self.active_flows),
            self.protocol_tcp_pct,
            self.protocol_udp_pct,
            self.protocol_icmp_pct,
        ]

    @staticmethod
    def feature_names() -> List[str]:
        return [
            "bytes_through",
            "utilization_pct",
            "active_flows",
            "protocol_tcp_pct",
            "protocol_udp_pct",
            "protocol_icmp_pct",
        ]


@dataclass
class GraphSnapshot:
    """Complete graph state for one time window."""

    timestamp: float = 0.0
    window_index: int = 0
    node_snapshots: Dict[str, NodeSnapshot] = field(default_factory=dict)
    edge_snapshots: List[EdgeSnapshot] = field(default_factory=list)
    # Labels set later by labeling module
    current_label: str = "NORMAL"
    node_labels: Dict[str, str] = field(default_factory=dict)
    prediction_labels: Dict[str, Any] = field(default_factory=dict)
    # Metadata
    phase_name: str = ""
    scenario_name: str = ""
    active_anomalies: List[Dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsing helpers — extract metrics from Mininet host command output
# ---------------------------------------------------------------------------

def safe_cmd(node, cmd_str: str) -> str:
    """Run a command safely without interfering with node.cmd() shell.
    Uses popen to execute in a separate process within the node's namespace,
    avoiding the AssertionError: assert self.shell and not self.waiting.
    """
    try:
        proc = node.popen(cmd_str, shell=True)
        stdout, stderr = proc.communicate(timeout=5)
        result = stdout.decode('utf-8', errors='ignore')
        if not result.strip() and stderr:
            err = stderr.decode('utf-8', errors='ignore').strip()
            if err:
                logger.debug(f"safe_cmd '{cmd_str}' on {node.name}: stderr={err}")
        return result
    except Exception as e:
        logger.debug(f"safe_cmd '{cmd_str}' on {node.name}: exception={e}")
        return ""


def _read_sys_stat(node, intf: str, stat_name: str) -> int:
    """Read a single interface statistic from /sys/class/net/.
    This is the most reliable fallback for Mininet network namespaces.
    """
    try:
        raw = safe_cmd(node, f"cat /sys/class/net/{intf}/statistics/{stat_name} 2>/dev/null")
        return int(raw.strip()) if raw.strip() else 0
    except (ValueError, Exception):
        return 0


def _read_interface_counters_sysfs(node, intf: str) -> Tuple[int, int, int, int, int, int]:
    """Read interface counters via /sys/class/net/ files.
    Returns (rx_bytes, rx_pkts, rx_drops, tx_bytes, tx_pkts, tx_drops).
    """
    rx_bytes = _read_sys_stat(node, intf, "rx_bytes")
    rx_pkts = _read_sys_stat(node, intf, "rx_packets")
    rx_drops = _read_sys_stat(node, intf, "rx_dropped")
    tx_bytes = _read_sys_stat(node, intf, "tx_bytes")
    tx_pkts = _read_sys_stat(node, intf, "tx_packets")
    tx_drops = _read_sys_stat(node, intf, "tx_dropped")
    return rx_bytes, rx_pkts, rx_drops, tx_bytes, tx_pkts, tx_drops


# Regex for ip -s link show — two-line format:
#   RX: bytes  packets  errors  dropped overrun mcast
#       12345  678      0       0       0       0
_RX_TX_RE = re.compile(
    r"(RX|TX):\s+bytes\s+packets\s+errors\s+dropped.*?\n\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
    re.DOTALL,
)

_NETEM_DELAY_RE = re.compile(r"delay\s+([\d.]+)ms")
_NETEM_LOSS_RE = re.compile(r"loss\s+([\d.]+)%")
_RATE_RE = re.compile(r"rate\s+([\d.]+)([KkMmGg]?)bit")
_BACKLOG_RE = re.compile(r"backlog\s+(\d+)b\s+(\d+)p")
_PING_RTT_RE = re.compile(r"rtt\s+min/avg/max/mdev\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)")
_TCP_ESTAB_RE = re.compile(r"TCP:\s+(\d+)\s+\(estab\s+(\d+),", re.IGNORECASE)


def _parse_link_stats(output: str) -> Tuple[int, int, int, int, int, int]:
    """Parse `ip -s link show <intf>` output.

    Returns (rx_bytes, rx_pkts, rx_drops, tx_bytes, tx_pkts, tx_drops).
    """
    rx_bytes = rx_pkts = rx_drops = 0
    tx_bytes = tx_pkts = tx_drops = 0
    for match in _RX_TX_RE.finditer(output):
        direction = match.group(1)
        if direction == "RX":
            rx_bytes = int(match.group(2))
            rx_pkts = int(match.group(3))
            rx_drops = int(match.group(5))  # dropped is column 4 (index 5)
        else:
            tx_bytes = int(match.group(2))
            tx_pkts = int(match.group(3))
            tx_drops = int(match.group(5))
    return rx_bytes, rx_pkts, rx_drops, tx_bytes, tx_pkts, tx_drops


def _parse_qdisc(output: str) -> Dict[str, float]:
    """Parse `tc -s qdisc show dev <intf>` output."""
    result: Dict[str, float] = {
        "delay_ms": 0.0,
        "loss_pct": 0.0,
        "rate_mbit": 0.0,
        "backlog_bytes": 0,
        "backlog_pkts": 0,
    }
    m = _NETEM_DELAY_RE.search(output)
    if m:
        result["delay_ms"] = float(m.group(1))
    m = _NETEM_LOSS_RE.search(output)
    if m:
        result["loss_pct"] = float(m.group(1))
    m = _RATE_RE.search(output)
    if m:
        val = float(m.group(1))
        unit = m.group(2).upper()
        if unit == "K":
            val /= 1000.0
        elif unit == "G":
            val *= 1000.0
        result["rate_mbit"] = val
    m = _BACKLOG_RE.search(output)
    if m:
        result["backlog_bytes"] = int(m.group(1))
        result["backlog_pkts"] = int(m.group(2))
    return result


def _parse_ping(output: str) -> Tuple[float, float]:
    """Parse `ping -c 2 -W 1` output → (avg_rtt_ms, mdev_ms)."""
    m = _PING_RTT_RE.search(output)
    if m:
        return float(m.group(2)), float(m.group(4))
    return 0.0, 0.0


def _parse_tcp_connections(output: str) -> int:
    """Parse `ss -s` output → established TCP count."""
    m = _TCP_ESTAB_RE.search(output)
    if m:
        return int(m.group(2))
    # Fallback: count lines from ss -t
    lines = [line for line in output.strip().splitlines() if line.strip() and not line.startswith("State")]
    return len(lines)


# ---------------------------------------------------------------------------
# Telemetry collector
# ---------------------------------------------------------------------------

class TelemetryCollector:
    """Collects per-node and per-link metrics at fixed intervals.

    Usage::

        collector = TelemetryCollector(net, window_seconds=5)
        collector.start()
        # ... run scenarios ...
        collector.stop()
        snapshots = collector.snapshots
    """

    # Assumed link capacity for utilization calculation (Mininet default veth)
    LINK_CAPACITY_MBPS = 100.0

    def __init__(self, net, window_seconds: int = 5):
        self._net = net
        self._window_seconds = max(2, int(window_seconds))
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._snapshots: List[GraphSnapshot] = []
        self._lock = threading.Lock()
        self._window_index = 0

        # Build topology metadata
        self._host_names: List[str] = [h.name for h in net.hosts]
        self._switch_names: List[str] = [s.name for s in net.switches]
        self._all_nodes: List[str] = self._host_names + self._switch_names
        self._edges: List[Tuple[str, str]] = []
        for link in net.links:
            self._edges.append((link.intf1.node.name, link.intf2.node.name))

        # Previous counter values for computing deltas
        self._prev_counters: Dict[str, Tuple[int, int, int, int, int, int]] = {}

        # Build node→IP mapping
        self._node_ips: Dict[str, str] = {}
        for host in net.hosts:
            try:
                self._node_ips[host.name] = host.IP()
            except Exception:
                pass

        # Build node→gateway mapping for latency probes
        self._node_gateways: Dict[str, str] = {}
        from .topology import get_node_zone
        for name in self._host_names:
            zone = get_node_zone(name)
            # Each zone's router LAN IP is the gateway
            gw_map = {
                "enterprise-a": "10.10.1.1",
                "enterprise-b": "10.20.1.1",
                "home-a": "192.168.10.1",
                "home-b": "192.168.20.1",
                "datacenter": "172.16.1.1",
            }
            self._node_gateways[name] = gw_map.get(zone, "10.255.0.1")

    @property
    def snapshots(self) -> List[GraphSnapshot]:
        with self._lock:
            return list(self._snapshots)

    @property
    def window_seconds(self) -> int:
        return self._window_seconds

    def start(self):
        """Begin collecting telemetry in background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._window_index = 0
        self._prev_counters.clear()
        with self._lock:
            self._snapshots.clear()
        # Take an initial counter reading so first delta is meaningful
        self._read_all_counters()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop telemetry collection and wait for thread to finish."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self._window_seconds + 5)

    def _worker(self):
        while not self._stop_event.is_set():
            cycle_start = time.time()
            try:
                snapshot = self._collect_snapshot()
                with self._lock:
                    self._snapshots.append(snapshot)
                self._window_index += 1
            except Exception:
                pass
            # Sleep for remaining window time
            elapsed = time.time() - cycle_start
            remaining = max(0.1, self._window_seconds - elapsed)
            self._stop_event.wait(timeout=remaining)

    def _collect_snapshot(self) -> GraphSnapshot:
        ts = time.time()
        snap = GraphSnapshot(
            timestamp=ts,
            window_index=self._window_index,
        )

        from concurrent.futures import ThreadPoolExecutor
        
        # Collect node metrics in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self._collect_node_metrics, name): name for name in self._host_names}
            for future in futures:
                node_snap = future.result()
                snap.node_snapshots[node_snap.name] = node_snap

        # Collect edge metrics (derived from endpoint interface counters)
        for src, dst in self._edges:
            edge_snap = self._collect_edge_metrics(src, dst, snap)
            snap.edge_snapshots.append(edge_snap)

        return snap

    def _collect_node_metrics(self, name: str) -> NodeSnapshot:
        from .topology import get_node_type, get_node_zone
        net = self._net
        try:
            node = net.get(name)
        except Exception:
            return NodeSnapshot(name=name)

        intf = f"{name}-eth0"
        ns = NodeSnapshot(
            name=name,
            ip=self._node_ips.get(name, ""),
            zone=get_node_zone(name),
            node_type=get_node_type(name, set(self._switch_names)),
        )

        # --- Interface counters (delta) ---
        # Read counters from ALL interfaces on this node, not just eth0
        try:
            # List all interfaces for this node
            intf_list_raw = safe_cmd(node, "ls /sys/class/net/ 2>/dev/null")
            intfs = [i.strip() for i in intf_list_raw.split() if i.strip() and i.strip() != "lo"]
            if not intfs:
                intfs = [intf]  # fallback to {name}-eth0
            
            total_rx_b = total_rx_p = total_rx_d = 0
            total_tx_b = total_tx_p = total_tx_d = 0
            
            for iface in intfs:
                # Try sysfs first (most reliable), then ip -s link show
                irx_b, irx_p, irx_d, itx_b, itx_p, itx_d = _read_interface_counters_sysfs(node, iface)
                if irx_b == 0 and itx_b == 0:
                    raw = safe_cmd(node, f"ip -s link show {iface} 2>/dev/null")
                    irx_b, irx_p, irx_d, itx_b, itx_p, itx_d = _parse_link_stats(raw)
                total_rx_b += irx_b
                total_rx_p += irx_p
                total_rx_d += irx_d
                total_tx_b += itx_b
                total_tx_p += itx_p
                total_tx_d += itx_d
            
            prev = self._prev_counters.get(name)
            if prev is None:
                prev = (total_rx_b, total_rx_p, total_rx_d, total_tx_b, total_tx_p, total_tx_d)

            ns.bytes_recv = max(0, total_rx_b - prev[0])
            ns.pkts_recv = max(0, total_rx_p - prev[1])
            ns.bytes_sent = max(0, total_tx_b - prev[3])
            ns.pkts_sent = max(0, total_tx_p - prev[4])
            ns.pkt_drops = max(0, (total_rx_d + total_tx_d) - (prev[2] + prev[5]))
            self._prev_counters[name] = (total_rx_b, total_rx_p, total_rx_d, total_tx_b, total_tx_p, total_tx_d)
        except Exception as e:
            logger.debug(f"Interface counter error for {name}: {e}")

        # --- Qdisc / netem state ---
        try:
            qdisc_raw = safe_cmd(node, f"tc -s qdisc show dev {intf} 2>/dev/null")
            qdisc = _parse_qdisc(qdisc_raw)
            ns.netem_delay_ms = qdisc["delay_ms"]
            ns.netem_loss_pct = qdisc["loss_pct"]
            ns.bandwidth_limit_mbit = qdisc["rate_mbit"]
            ns.queue_depth_bytes = int(qdisc["backlog_bytes"])
            ns.queue_depth_pkts = int(qdisc["backlog_pkts"])
        except Exception:
            pass

        # --- TCP connections ---
        try:
            ss_raw = safe_cmd(node, "ss -s 2>/dev/null")
            ns.tcp_connections = _parse_tcp_connections(ss_raw)
            # Fallback: count ESTABLISHED lines from ss -t
            if ns.tcp_connections == 0:
                ss_t = safe_cmd(node, "ss -t state established 2>/dev/null")
                lines = [l for l in ss_t.strip().splitlines() if l.strip() and not l.startswith('State')]
                ns.tcp_connections = len(lines)
        except Exception as e:
            logger.debug(f"TCP connection error for {name}: {e}")

        # --- Latency probe (ping gateway, fast) ---
        gw = self._node_gateways.get(name)
        if gw:
            try:
                ping_raw = safe_cmd(node, f"ping -c 2 -W 1 -i 0.2 {gw} 2>/dev/null")
                avg_rtt, mdev = _parse_ping(ping_raw)
                ns.latency_ms = avg_rtt
                ns.jitter_ms = mdev
            except Exception:
                pass

        return ns

    def _collect_edge_metrics(self, src: str, dst: str, snap: GraphSnapshot) -> EdgeSnapshot:
        edge = EdgeSnapshot(source=src, target=dst)

        # Use endpoint node metrics to estimate edge traffic
        src_snap = snap.node_snapshots.get(src)
        dst_snap = snap.node_snapshots.get(dst)
        if src_snap and dst_snap:
            # Approximate bytes through this link as the average of
            # src bytes_sent and dst bytes_recv (imperfect but reasonable)
            edge.bytes_through = (src_snap.bytes_sent + dst_snap.bytes_recv) / 2.0

            # Utilization = bytes_through / (capacity_bytes_per_window)
            capacity_bytes = (self.LINK_CAPACITY_MBPS * 1_000_000.0 / 8.0) * self._window_seconds
            if capacity_bytes > 0:
                edge.utilization_pct = min(100.0, (edge.bytes_through / capacity_bytes) * 100.0)

        return edge

    def _read_all_counters(self):
        """Read initial counter values so first delta is meaningful."""
        net = self._net
        for name in self._host_names:
            try:
                node = net.get(name)
                intf = f"{name}-eth0"
                
                # Read counters from ALL interfaces (consistent with _collect_node_metrics)
                intf_list_raw = safe_cmd(node, "ls /sys/class/net/ 2>/dev/null")
                intfs = [i.strip() for i in intf_list_raw.split() if i.strip() and i.strip() != "lo"]
                if not intfs:
                    intfs = [intf]
                
                total_rx_b = total_rx_p = total_rx_d = 0
                total_tx_b = total_tx_p = total_tx_d = 0
                
                for iface in intfs:
                    irx_b, irx_p, irx_d, itx_b, itx_p, itx_d = _read_interface_counters_sysfs(node, iface)
                    if irx_b == 0 and itx_b == 0:
                        raw = safe_cmd(node, f"ip -s link show {iface} 2>/dev/null")
                        irx_b, irx_p, irx_d, itx_b, itx_p, itx_d = _parse_link_stats(raw)
                    total_rx_b += irx_b
                    total_rx_p += irx_p
                    total_rx_d += irx_d
                    total_tx_b += itx_b
                    total_tx_p += itx_p
                    total_tx_d += itx_d
                
                counters = (total_rx_b, total_rx_p, total_rx_d, total_tx_b, total_tx_p, total_tx_d)
                self._prev_counters[name] = counters
                if counters[0] > 0 or counters[3] > 0:
                    logger.info(f"Initial counters for {name}: rx_bytes={counters[0]}, tx_bytes={counters[3]}, intfs={intfs}")
            except Exception:
                self._prev_counters[name] = (0, 0, 0, 0, 0, 0)

    def get_topology_info(self) -> Dict[str, Any]:
        """Return topology metadata for dataset export."""
        node_index = OrderedDict()
        for idx, name in enumerate(self._host_names):
            node_index[name] = idx

        edge_list = []
        for src, dst in self._edges:
            if src in node_index and dst in node_index:
                edge_list.append([node_index[src], node_index[dst]])
                edge_list.append([node_index[dst], node_index[src]])

        return {
            "node_names": list(node_index.keys()),
            "node_index": dict(node_index),
            "node_ips": dict(self._node_ips),
            "edges": self._edges,
            "edge_index": edge_list,
            "node_feature_names": NodeSnapshot.feature_names(),
            "edge_feature_names": EdgeSnapshot.feature_names(),
        }
