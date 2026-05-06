"""Heavy traffic service setup using iperf3 for sustained flows."""

from typing import Dict, List, Set


# iperf3 server port ranges per datacenter host
IPERF_SERVERS: Dict[str, List[int]] = {
    "dc_web": list(range(5201, 5211)),
    "dc_monitor": list(range(5211, 5221)),
    "dc_vpn": list(range(5221, 5231)),
}


def start_iperf_servers(net, nodes: List[str] = None) -> Dict[str, List[int]]:
    """Start iperf3 server instances on specified nodes.

    Returns dict of node_name → list of ports with running servers.
    """
    if nodes is None:
        nodes = list(IPERF_SERVERS.keys())

    started: Dict[str, List[int]] = {}
    for name in nodes:
        ports = IPERF_SERVERS.get(name, [5201])
        try:
            host = net.get(name)
        except Exception:
            continue

        # Kill any existing iperf3 servers on this host
        host.cmd("pkill -f 'iperf3 -s' >/dev/null 2>&1")

        active_ports = []
        for port in ports:
            host.cmd(
                f"nohup iperf3 -s -p {port} -D "
                f"--logfile /tmp/iperf3_{name}_{port}.log >/dev/null 2>&1"
            )
            active_ports.append(port)

        started[name] = active_ports

    return started


def stop_iperf_servers(net, nodes: List[str] = None):
    """Stop all iperf3 server instances on specified nodes."""
    if nodes is None:
        nodes = list(IPERF_SERVERS.keys())

    for name in nodes:
        try:
            host = net.get(name)
            host.cmd("pkill -f 'iperf3 -s' >/dev/null 2>&1")
        except Exception:
            pass


def run_iperf_udp(net, src: str, dst: str, bandwidth: str = "2M",
                  duration: int = 10, port: int = 5201):
    """Launch an iperf3 UDP client flow (background, non-blocking)."""
    try:
        src_host = net.get(src)
        dst_ip = net.get(dst).IP()
    except Exception:
        return

    src_host.cmd(
        f"nohup iperf3 -c {dst_ip} -u -b {bandwidth} -t {duration} -p {port} "
        f">/dev/null 2>&1 &"
    )


def run_iperf_tcp(net, src: str, dst: str, bandwidth: str = "10M",
                  duration: int = 10, port: int = 5201):
    """Launch an iperf3 TCP client flow (background, non-blocking)."""
    try:
        src_host = net.get(src)
        dst_ip = net.get(dst).IP()
    except Exception:
        return

    src_host.cmd(
        f"nohup iperf3 -c {dst_ip} -b {bandwidth} -t {duration} -p {port} "
        f">/dev/null 2>&1 &"
    )


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
