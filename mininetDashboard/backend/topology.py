from mininet.node import Node
from mininet.topo import Topo


class LinuxRouter(Node):
    def config(self, **params):
        super().config(**params)
        # Routers must forward packets between LAN and transit networks.
        self.cmd("sysctl -w net.ipv4.ip_forward=1")

    def terminate(self):
        self.cmd("sysctl -w net.ipv4.ip_forward=0")
        super().terminate()


class RealWorldTopo(Topo):
    def build(self):
        # Explicit DPIDs are required because switch names are not canonical (s1, s2...).
        isp_core = self.addSwitch("isp_core", dpid="0000000000000001")
        ent1_sw = self.addSwitch("ent1_sw", dpid="0000000000000002")
        ent2_sw = self.addSwitch("ent2_sw", dpid="0000000000000003")
        home1_sw = self.addSwitch("home1_sw", dpid="0000000000000004")
        home2_sw = self.addSwitch("home2_sw", dpid="0000000000000005")
        dc_sw = self.addSwitch("dc_sw", dpid="0000000000000006")

        isp_r1 = self.addNode("isp_r1", cls=LinuxRouter)
        r_ent1 = self.addNode("r_ent1", cls=LinuxRouter)
        r_ent2 = self.addNode("r_ent2", cls=LinuxRouter)
        r_home1 = self.addNode("r_home1", cls=LinuxRouter)
        r_home2 = self.addNode("r_home2", cls=LinuxRouter)
        r_dc = self.addNode("r_dc", cls=LinuxRouter)

        # Enterprise A
        self.addHost("e1_pc1")
        self.addHost("e1_pc2")
        self.addHost("e1_dns")
        self.addHost("e1_dhcp")
        self.addHost("e1_erp")

        # Enterprise B
        self.addHost("e2_pc1")
        self.addHost("e2_pc2")
        self.addHost("e2_dns")
        self.addHost("e2_dhcp")
        self.addHost("e2_crm")

        # Home A
        self.addHost("h1_pc")
        self.addHost("h1_tv")
        self.addHost("h1_iot")

        # Home B
        self.addHost("h2_pc")
        self.addHost("h2_cam")
        self.addHost("h2_nas")

        # Datacenter / shared services
        self.addHost("dc_pub_dns")
        self.addHost("dc_web")
        self.addHost("dc_vpn")
        self.addHost("dc_monitor")

        # Transit links (first link on each spoke router is transit side)
        self.addLink(isp_r1, isp_core)
        self.addLink(r_ent1, isp_core)
        self.addLink(r_ent2, isp_core)
        self.addLink(r_home1, isp_core)
        self.addLink(r_home2, isp_core)
        self.addLink(r_dc, isp_core)

        # Access links (second link on each spoke router is LAN side)
        self.addLink(r_ent1, ent1_sw)
        self.addLink(r_ent2, ent2_sw)
        self.addLink(r_home1, home1_sw)
        self.addLink(r_home2, home2_sw)
        self.addLink(r_dc, dc_sw)

        # LAN memberships
        for host in ["e1_pc1", "e1_pc2", "e1_dns", "e1_dhcp", "e1_erp"]:
            self.addLink(host, ent1_sw)

        for host in ["e2_pc1", "e2_pc2", "e2_dns", "e2_dhcp", "e2_crm"]:
            self.addLink(host, ent2_sw)

        for host in ["h1_pc", "h1_tv", "h1_iot"]:
            self.addLink(host, home1_sw)

        for host in ["h2_pc", "h2_cam", "h2_nas"]:
            self.addLink(host, home2_sw)

        for host in ["dc_pub_dns", "dc_web", "dc_vpn", "dc_monitor"]:
            self.addLink(host, dc_sw)


def configure_network(net):
    # Router interfaces use eth0 for transit and eth1 for local LAN links.
    routers = {
        "isp_r1": ("10.255.0.1/24", None),
        "r_ent1": ("10.255.0.11/24", "10.10.1.1/24"),
        "r_ent2": ("10.255.0.12/24", "10.20.1.1/24"),
        "r_home1": ("10.255.0.21/24", "192.168.10.1/24"),
        "r_home2": ("10.255.0.22/24", "192.168.20.1/24"),
        "r_dc": ("10.255.0.30/24", "172.16.1.1/24"),
    }

    for router_name, (transit_ip, lan_ip) in routers.items():
        router = net.get(router_name)
        router.setIP(transit_ip, intf=f"{router_name}-eth0")
        if lan_ip:
            router.setIP(lan_ip, intf=f"{router_name}-eth1")

    host_config = {
        "e1_pc1": ("10.10.1.11/24", "10.10.1.1"),
        "e1_pc2": ("10.10.1.12/24", "10.10.1.1"),
        "e1_dns": ("10.10.1.53/24", "10.10.1.1"),
        "e1_dhcp": ("10.10.1.2/24", "10.10.1.1"),
        "e1_erp": ("10.10.1.40/24", "10.10.1.1"),
        "e2_pc1": ("10.20.1.11/24", "10.20.1.1"),
        "e2_pc2": ("10.20.1.12/24", "10.20.1.1"),
        "e2_dns": ("10.20.1.53/24", "10.20.1.1"),
        "e2_dhcp": ("10.20.1.2/24", "10.20.1.1"),
        "e2_crm": ("10.20.1.41/24", "10.20.1.1"),
        "h1_pc": ("192.168.10.11/24", "192.168.10.1"),
        "h1_tv": ("192.168.10.21/24", "192.168.10.1"),
        "h1_iot": ("192.168.10.31/24", "192.168.10.1"),
        "h2_pc": ("192.168.20.11/24", "192.168.20.1"),
        "h2_cam": ("192.168.20.21/24", "192.168.20.1"),
        "h2_nas": ("192.168.20.31/24", "192.168.20.1"),
        "dc_pub_dns": ("172.16.1.53/24", "172.16.1.1"),
        "dc_web": ("172.16.1.20/24", "172.16.1.1"),
        "dc_vpn": ("172.16.1.30/24", "172.16.1.1"),
        "dc_monitor": ("172.16.1.40/24", "172.16.1.1"),
    }

    for host_name, (ip_cidr, gateway) in host_config.items():
        host = net.get(host_name)
        host.setIP(ip_cidr, intf=f"{host_name}-eth0")
        host.cmd(f"ip route replace default via {gateway}")

    # Default route from spokes to ISP router
    for router_name in ["r_ent1", "r_ent2", "r_home1", "r_home2", "r_dc"]:
        net.get(router_name).cmd("ip route replace default via 10.255.0.1")

    # ISP router knows every LAN
    isp = net.get("isp_r1")
    isp.cmd("ip route replace 10.10.1.0/24 via 10.255.0.11")
    isp.cmd("ip route replace 10.20.1.0/24 via 10.255.0.12")
    isp.cmd("ip route replace 192.168.10.0/24 via 10.255.0.21")
    isp.cmd("ip route replace 192.168.20.0/24 via 10.255.0.22")
    isp.cmd("ip route replace 172.16.1.0/24 via 10.255.0.30")

    # Basic DNS placement to simulate realistic resolution
    for host_name in host_config:
        host = net.get(host_name)
        if host_name.startswith("e1_"):
            resolver = "10.10.1.53"
        elif host_name.startswith("e2_"):
            resolver = "10.20.1.53"
        else:
            resolver = "172.16.1.53"

        host.cmd(f'printf "nameserver {resolver}\\n" > /etc/resolv.conf')


def get_node_type(node_name, switch_names):
    if node_name in switch_names:
        return "switch"
    if node_name.startswith("isp_r") or node_name.startswith("r_"):
        return "router"
    if "dns" in node_name:
        return "dns"
    if "dhcp" in node_name:
        return "dhcp"
    if "iot" in node_name or "tv" in node_name or "cam" in node_name:
        return "iot"
    if "monitor" in node_name:
        return "security"
    if node_name.startswith("e"):
        return "enterprise"
    if node_name.startswith("h"):
        return "home"
    return "server"


def get_node_zone(node_name):
    if node_name.startswith("e1_") or node_name == "ent1_sw" or node_name == "r_ent1":
        return "enterprise-a"
    if node_name.startswith("e2_") or node_name == "ent2_sw" or node_name == "r_ent2":
        return "enterprise-b"
    if node_name.startswith("h1_") or node_name == "home1_sw" or node_name == "r_home1":
        return "home-a"
    if node_name.startswith("h2_") or node_name == "home2_sw" or node_name == "r_home2":
        return "home-b"
    if node_name.startswith("dc_") or node_name == "dc_sw" or node_name == "r_dc":
        return "datacenter"
    return "backbone"
