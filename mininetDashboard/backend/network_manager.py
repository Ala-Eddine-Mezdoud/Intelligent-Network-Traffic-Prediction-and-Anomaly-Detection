import os
import threading
from functools import partial

from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController

from .config import MININET_CONTROLLER_IP
from .topology import RealWorldTopo, configure_network


class NetworkManager:
    def __init__(self):
        self._net = None
        self._lock = threading.Lock()
        self._started = False

    @property
    def net(self):
        with self._lock:
            return self._net

    def start_async(self):
        with self._lock:
            if self._started:
                return
            self._started = True

        # Bootstrap Mininet in a background thread so Flask can start immediately.
        thread = threading.Thread(target=self._start_net, daemon=True)
        thread.start()

    def _start_net(self):
        # Clean stale interfaces/namespaces from earlier runs.
        os.system("mn -c")

        topo = RealWorldTopo()
        net = Mininet(
            topo=topo,
            controller=lambda name: RemoteController(name, ip=MININET_CONTROLLER_IP),
            # Ryu app simple_switch_13 requires OpenFlow 1.3 datapaths.
            switch=partial(OVSSwitch, protocols="OpenFlow13"),
        )

        net.start()
        # Apply L3 addressing, routes, and resolver config after topology boot.
        configure_network(net)

        with self._lock:
            self._net = net


manager = NetworkManager()
