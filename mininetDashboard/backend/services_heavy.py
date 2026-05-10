"""Heavy traffic service setup using iperf3 for sustained flows."""

import logging
import threading
import time
from typing import Dict, List, Set

logger = logging.getLogger(__name__)

# iperf3 server port ranges per datacenter host
IPERF_SERVERS: Dict[str, List[int]] = {
    "dc_web": list(range(5201, 5221)),
    "dc_monitor": list(range(5221, 5241)),
    "dc_vpn": list(range(5241, 5261)),
    "dc_pub_dns": list(range(5261, 5281)),
    "e1_erp": list(range(5281, 5291)),
    "e2_crm": list(range(5291, 5301)),
}

# Thread-safe port allocator
_port_lock = threading.Lock()
_allocated_ports: Dict[str, int] = {}  # dst_name -> next available port index


def _allocate_port(dst_name: str) -> int:
    """Allocate the next available iperf port for a destination host."""
    with _port_lock:
        ports = IPERF_SERVERS.get(dst_name, [5201])
        idx = _allocated_ports.get(dst_name, 0)
        port = ports[idx % len(ports)]
        _allocated_ports[dst_name] = idx + 1
        return port


def reset_port_allocations():
    """Reset port allocation counters (call between scenarios)."""
    with _port_lock:
        _allocated_ports.clear()


def start_iperf_servers(net, nodes: List[str] = None) -> Dict[str, List[int]]:
    """Start iperf3 server instances on specified nodes.

    Returns dict of node_name → list of ports with running servers.
    """
    if nodes is None:
        nodes = list(IPERF_SERVERS.keys())

    # CRITICAL: Kill ALL existing iperf3 servers ONCE at the start.
    # If we do this inside the loop, we kill the servers we just started!
    try:
        # Use the first node to run the global pkill
        first_host = net.get(nodes[0])
        first_host.cmd("pkill -f 'iperf3 -s' >/dev/null 2>&1")
        time.sleep(1)
    except Exception:
        pass

    started: Dict[str, List[int]] = {}
    for name in nodes:
        ports = IPERF_SERVERS.get(name, [5201])
        try:
            host = net.get(name)
        except Exception:
            continue

        active_ports = []
        for port in ports:
            # Use setsid and nohup to ensure the server persists after the cmd() call
            host.cmd(
                f"setsid nohup iperf3 -s -p {port} "
                f"--logfile /tmp/iperf3_{name}_{port}.log >/dev/null 2>&1 &"
            )
            active_ports.append(port)
            time.sleep(0.05) # Small stagger

        started[name] = active_ports
        logger.info(f"Started iperf3 servers on {name}: ports {active_ports}")

    return started


def stop_iperf_servers(net, nodes: List[str] = None):
    """Stop all iperf3 server instances on specified nodes."""
    if nodes is None:
        nodes = [h.name for h in net.hosts]

    for name in nodes:
        try:
            host = net.get(name)
            host.cmd("pkill -f 'iperf3 -s' >/dev/null 2>&1")
        except Exception:
            pass

    reset_port_allocations()


def run_iperf_udp(net, src: str, dst: str, bandwidth: str = "2M",
                  duration: int = 10, port: int = None):
    """Launch an iperf3 UDP client flow (background, non-blocking)."""
    try:
        src_host = net.get(src)
        dst_ip = net.get(dst).IP()
    except Exception:
        return

    if port is None:
        port = _allocate_port(dst)

    # Use setsid/nohup for clients too
    cmd = (
        f"setsid nohup iperf3 -c {dst_ip} -u -b {bandwidth} -t {duration} -p {port} "
        f"--logfile /tmp/iperf3_client_{src}_{port}.log >/dev/null 2>&1 &"
    )
    src_host.cmd(cmd)
    logger.info(f"iperf3 UDP: {src} -> {dst}({dst_ip}):{port} bw={bandwidth} dur={duration}s")


def run_iperf_tcp(net, src: str, dst: str, bandwidth: str = "10M",
                  duration: int = 10, port: int = None):
    """Launch an iperf3 TCP client flow (background, non-blocking)."""
    try:
        src_host = net.get(src)
        dst_ip = net.get(dst).IP()
    except Exception:
        return

    if port is None:
        port = _allocate_port(dst)

    cmd = (
        f"setsid nohup iperf3 -c {dst_ip} -b {bandwidth} -t {duration} -p {port} "
        f"--logfile /tmp/iperf3_client_{src}_{port}.log >/dev/null 2>&1 &"
    )
    src_host.cmd(cmd)
    logger.info(f"iperf3 TCP: {src} -> {dst}({dst_ip}):{port} bw={bandwidth} dur={duration}s")


def kill_iperf_clients(net, nodes: List[str] = None):
    """Kill all iperf3 client processes on specified nodes."""
    if nodes is None:
        nodes = [h.name for h in net.hosts]

    for name in nodes:
        try:
            host = net.get(name)
            host.cmd("pkill -f 'iperf3 -c' >/dev/null 2>&1")
        except Exception:
            pass
