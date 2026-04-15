from collections import deque

import requests

from .topology import get_node_type, get_node_zone


def topology_payload(net):
    # Hosts and switches are serialized together for a single force-graph model.
    switch_names = {switch.name for switch in net.switches}

    nodes = []
    for node in net.hosts + net.switches:
        nodes.append(
            {
                "id": node.name,
                "type": get_node_type(node.name, switch_names),
                "zone": get_node_zone(node.name),
            }
        )

    links = []
    for link in net.links:
        links.append(
            {
                "source": link.intf1.node.name,
                "target": link.intf2.node.name,
                "kind": "data",
            }
        )

    # Represent the SDN controller explicitly as a control-plane node.
    controller_id = "ryu_ctrl"
    nodes.append(
        {
            "id": controller_id,
            "type": "controller",
            "zone": "control-plane",
        }
    )

    # Control-plane sessions are logical links, not forwarding links.
    for switch_name in switch_names:
        links.append(
            {
                "source": controller_id,
                "target": switch_name,
                "kind": "control",
            }
        )

    return {"nodes": nodes, "links": links}


def compute_shortest_path(net, src, dst):
    # Unweighted BFS over the current link graph.
    graph = {}

    for link in net.links:
        left = link.intf1.node.name
        right = link.intf2.node.name
        graph.setdefault(left, set()).add(right)
        graph.setdefault(right, set()).add(left)

    if src not in graph or dst not in graph:
        return []

    queue = deque([(src, [src])])
    visited = {src}

    while queue:
        current, path = queue.popleft()
        if current == dst:
            return path

        for next_hop in graph[current]:
            if next_hop in visited:
                continue
            visited.add(next_hop)
            queue.append((next_hop, path + [next_hop]))

    return []


def ping_between_hosts(net, src, dst):
    source = net.get(src)
    destination = net.get(dst)
    dst_ip = destination.IP()
    return source.cmd(f"ping -c 2 {dst_ip}")


def fetch_controller_flows(ryu_base_url):
    # Query switch list first, then pull per-switch flow tables.
    switches = requests.get(f"{ryu_base_url}/stats/switches", timeout=3).json()
    flow_data = {}

    for switch_id in switches:
        flow_data[switch_id] = requests.get(
            f"{ryu_base_url}/stats/flow/{switch_id}", timeout=3
        ).json()

    return flow_data
