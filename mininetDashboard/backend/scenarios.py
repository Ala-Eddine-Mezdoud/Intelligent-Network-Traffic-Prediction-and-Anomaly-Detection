"""Scripted scenarios with phased buildup for GNN prediction training."""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScenarioPhase:
    label: str
    duration_s: int
    actions: List[Dict[str, Any]] = field(default_factory=list)
    target_nodes: List[str] = field(default_factory=list)
    node_labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Scenario:
    name: str
    description: str
    phases: List[ScenarioPhase] = field(default_factory=list)

    def total_duration(self) -> int:
        return sum(p.duration_s for p in self.phases)


def _baseline_actions() -> List[Dict[str, Any]]:
    return [{"type": "baseline_traffic"}]


def _iperf_udp(src: str, dst: str, bw: str = "2M", duration: int = 10, port: int = 5201) -> Dict:
    return {"type": "iperf_udp", "src": src, "dst": dst, "bw": bw, "duration": duration, "port": port}


def _iperf_tcp(src: str, dst: str, bw: str = "10M", duration: int = 10, port: int = 5201) -> Dict:
    return {"type": "iperf_tcp", "src": src, "dst": dst, "bw": bw, "duration": duration, "port": port}


def _netem(node: str, delay_ms: int = 0, jitter_ms: int = 0, loss_pct: float = 0, rate: Optional[str] = None) -> Dict:
    return {"type": "netem", "node": node, "delay_ms": delay_ms, "jitter_ms": jitter_ms, "loss_pct": loss_pct, "rate": rate}


def _clear_netem(node: str) -> Dict:
    return {"type": "clear_netem", "node": node}


def _attack(profile: str, src: str, dst: str, intensity: float = 1.0) -> Dict:
    return {"type": "attack", "profile": profile, "src": src, "dst": dst, "intensity": intensity}


# ---------------------------------------------------------------------------
# Scenario library
# ---------------------------------------------------------------------------

def build_scenario_library() -> List[Scenario]:
    """Return the full set of predefined training scenarios."""
    return [
        _scenario_ddos_ramp(),
        _scenario_congestion_buildup(),
        _scenario_latency_degradation(),
        _scenario_packet_loss_cascade(),
        _scenario_portscan_exploitation(),
        _scenario_link_failure(),
        _scenario_bandwidth_saturation(),
        _scenario_service_degradation(),
        _scenario_multi_node_congestion(),
        _scenario_mixed_attack_operational(),
        _scenario_voip_quality_degradation(),
        _scenario_brute_force_escalation(),
    ]


def _scenario_ddos_ramp() -> Scenario:
    return Scenario(
        name="ddos_ramp_dc_web",
        description="DDoS attack gradually ramps up against dc_web",
        phases=[
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
            ScenarioPhase("DDOS_BUILDUP", 30,
                          _baseline_actions() + [_iperf_udp("h1_iot", "dc_web", "1M", 30), _iperf_udp("h2_cam", "dc_web", "500K", 30)],
                          ["dc_web"], {"dc_web": "DDOS_TARGET", "h1_iot": "DDOS_SOURCE", "h2_cam": "DDOS_SOURCE"}),
            ScenarioPhase("DDOS_BUILDUP", 30,
                          _baseline_actions() + [_iperf_udp("h1_iot", "dc_web", "5M", 30), _iperf_udp("h2_cam", "dc_web", "3M", 30)],
                          ["dc_web"], {"dc_web": "DDOS_TARGET", "h1_iot": "DDOS_SOURCE", "h2_cam": "DDOS_SOURCE"}),
            ScenarioPhase("DDOS_ACTIVE", 60,
                          _baseline_actions() + [_iperf_udp("h1_iot", "dc_web", "20M", 60), _iperf_udp("h2_cam", "dc_web", "15M", 60)],
                          ["dc_web"], {"dc_web": "DDOS_TARGET", "h1_iot": "DDOS_SOURCE", "h2_cam": "DDOS_SOURCE"}),
            ScenarioPhase("RECOVERY", 30, _baseline_actions()),
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
        ],
    )


def _scenario_congestion_buildup() -> Scenario:
    return Scenario(
        name="congestion_buildup_ent1",
        description="Enterprise A link gradually saturates",
        phases=[
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
            ScenarioPhase("CONGESTION_BUILDUP", 30,
                          _baseline_actions() + [_iperf_tcp("e1_pc1", "dc_web", "15M", 30), _iperf_tcp("e1_pc2", "dc_web", "10M", 30)],
                          ["e1_pc1", "e1_pc2"], {"e1_pc1": "CONGESTION_BUILDUP", "e1_pc2": "CONGESTION_BUILDUP"}),
            ScenarioPhase("CONGESTION_BUILDUP", 30,
                          _baseline_actions() + [_iperf_tcp("e1_pc1", "dc_web", "30M", 30), _iperf_tcp("e1_pc2", "dc_web", "25M", 30), _iperf_tcp("e1_erp", "dc_monitor", "20M", 30)],
                          ["e1_pc1", "e1_pc2", "e1_erp"], {"e1_pc1": "CONGESTION_BUILDUP", "e1_pc2": "CONGESTION_BUILDUP", "e1_erp": "CONGESTION_BUILDUP"}),
            ScenarioPhase("CONGESTION_ACTIVE", 60,
                          _baseline_actions() + [_iperf_tcp("e1_pc1", "dc_web", "40M", 60), _iperf_tcp("e1_pc2", "dc_web", "35M", 60), _iperf_tcp("e1_erp", "dc_monitor", "30M", 60)],
                          ["e1_pc1", "e1_pc2", "e1_erp"], {"e1_pc1": "CONGESTION_ACTIVE", "e1_pc2": "CONGESTION_ACTIVE", "e1_erp": "CONGESTION_ACTIVE"}),
            ScenarioPhase("RECOVERY", 30, _baseline_actions()),
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
        ],
    )


def _scenario_latency_degradation() -> Scenario:
    return Scenario(
        name="latency_degradation_home1",
        description="Progressive latency degradation on Home A network",
        phases=[
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
            ScenarioPhase("LATENCY_DEGRADING", 30,
                          _baseline_actions() + [_netem("h1_pc", delay_ms=50, jitter_ms=10)],
                          ["h1_pc"], {"h1_pc": "LATENCY_DEGRADING"}),
            ScenarioPhase("LATENCY_DEGRADING", 30,
                          _baseline_actions() + [_netem("h1_pc", delay_ms=150, jitter_ms=30), _netem("h1_tv", delay_ms=80, jitter_ms=15)],
                          ["h1_pc", "h1_tv"], {"h1_pc": "LATENCY_DEGRADING", "h1_tv": "LATENCY_DEGRADING"}),
            ScenarioPhase("LATENCY_CRITICAL", 60,
                          _baseline_actions() + [_netem("h1_pc", delay_ms=300, jitter_ms=60), _netem("h1_tv", delay_ms=200, jitter_ms=40), _netem("h1_iot", delay_ms=150, jitter_ms=30)],
                          ["h1_pc", "h1_tv", "h1_iot"], {"h1_pc": "LATENCY_CRITICAL", "h1_tv": "LATENCY_CRITICAL", "h1_iot": "LATENCY_CRITICAL"}),
            ScenarioPhase("RECOVERY", 30, [_clear_netem("h1_pc"), _clear_netem("h1_tv"), _clear_netem("h1_iot")] + _baseline_actions()),
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
        ],
    )


def _scenario_packet_loss_cascade() -> Scenario:
    return Scenario(
        name="packet_loss_cascade_dc",
        description="Packet loss on datacenter nodes causes retransmission cascade",
        phases=[
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
            ScenarioPhase("PACKET_LOSS_MILD", 30,
                          _baseline_actions() + [_netem("dc_web", delay_ms=10, loss_pct=1.0)],
                          ["dc_web"], {"dc_web": "PACKET_LOSS_MILD"}),
            ScenarioPhase("PACKET_LOSS_MILD", 30,
                          _baseline_actions() + [_netem("dc_web", delay_ms=15, loss_pct=3.0), _netem("dc_monitor", delay_ms=10, loss_pct=1.5)],
                          ["dc_web", "dc_monitor"], {"dc_web": "PACKET_LOSS_MILD", "dc_monitor": "PACKET_LOSS_MILD"}),
            ScenarioPhase("PACKET_LOSS_SEVERE", 60,
                          _baseline_actions() + [_netem("dc_web", delay_ms=25, loss_pct=8.0), _netem("dc_monitor", delay_ms=20, loss_pct=5.0)],
                          ["dc_web", "dc_monitor"], {"dc_web": "PACKET_LOSS_SEVERE", "dc_monitor": "PACKET_LOSS_SEVERE"}),
            ScenarioPhase("RECOVERY", 30, [_clear_netem("dc_web"), _clear_netem("dc_monitor")] + _baseline_actions()),
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
        ],
    )


def _scenario_portscan_exploitation() -> Scenario:
    return Scenario(
        name="portscan_to_exploitation",
        description="Reconnaissance scan followed by brute force exploitation",
        phases=[
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
            ScenarioPhase("PORTSCAN_RECON", 30,
                          _baseline_actions() + [_attack("PortScan_slow", "h1_iot", "dc_web", 0.3)],
                          ["dc_web"], {"h1_iot": "PORTSCAN_RECON", "dc_web": "PORTSCAN_RECON"}),
            ScenarioPhase("PORTSCAN_RECON", 30,
                          _baseline_actions() + [_attack("PortScan", "h1_iot", "dc_web", 0.8)],
                          ["dc_web"], {"h1_iot": "PORTSCAN_RECON", "dc_web": "PORTSCAN_RECON"}),
            ScenarioPhase("BRUTE_FORCE_PROBE", 30,
                          _baseline_actions() + [_attack("SSH-Patator", "h1_iot", "dc_vpn", 0.5)],
                          ["dc_vpn"], {"h1_iot": "BRUTE_FORCE_PROBE", "dc_vpn": "BRUTE_FORCE_PROBE"}),
            ScenarioPhase("BRUTE_FORCE_ACTIVE", 60,
                          _baseline_actions() + [_attack("SSH-Patator", "h1_iot", "dc_vpn", 1.5)],
                          ["dc_vpn"], {"h1_iot": "BRUTE_FORCE_ACTIVE", "dc_vpn": "BRUTE_FORCE_ACTIVE"}),
            ScenarioPhase("RECOVERY", 30, _baseline_actions()),
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
        ],
    )


def _scenario_link_failure() -> Scenario:
    return Scenario(
        name="link_failure_brownout_home2",
        description="Home B link degrades toward failure",
        phases=[
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
            ScenarioPhase("BROWNOUT", 30,
                          _baseline_actions() + [_netem("h2_pc", delay_ms=60, jitter_ms=20, loss_pct=1.0, rate="8mbit")],
                          ["h2_pc"], {"h2_pc": "BROWNOUT"}),
            ScenarioPhase("BROWNOUT", 30,
                          _baseline_actions() + [_netem("h2_pc", delay_ms=120, jitter_ms=40, loss_pct=3.0, rate="3mbit"), _netem("h2_cam", delay_ms=80, jitter_ms=25, loss_pct=2.0, rate="4mbit")],
                          ["h2_pc", "h2_cam"], {"h2_pc": "BROWNOUT", "h2_cam": "BROWNOUT"}),
            ScenarioPhase("LINK_FAILURE", 60,
                          _baseline_actions() + [_netem("h2_pc", delay_ms=250, jitter_ms=80, loss_pct=15.0, rate="1mbit"), _netem("h2_cam", delay_ms=200, jitter_ms=60, loss_pct=10.0, rate="1mbit"), _netem("h2_nas", delay_ms=180, jitter_ms=50, loss_pct=8.0, rate="2mbit")],
                          ["h2_pc", "h2_cam", "h2_nas"], {"h2_pc": "LINK_FAILURE", "h2_cam": "LINK_FAILURE", "h2_nas": "LINK_FAILURE"}),
            ScenarioPhase("RECOVERY", 30, [_clear_netem("h2_pc"), _clear_netem("h2_cam"), _clear_netem("h2_nas")] + _baseline_actions()),
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
        ],
    )


def _scenario_bandwidth_saturation() -> Scenario:
    return Scenario(
        name="bandwidth_saturation_streaming",
        description="Multiple heavy streams saturate datacenter uplink",
        phases=[
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
            ScenarioPhase("CONGESTION_BUILDUP", 30,
                          _baseline_actions() + [_iperf_udp("h1_tv", "dc_web", "8M", 30, 5201)],
                          ["dc_web"], {"h1_tv": "NORMAL", "dc_web": "CONGESTION_BUILDUP"}),
            ScenarioPhase("CONGESTION_BUILDUP", 30,
                          _baseline_actions() + [_iperf_udp("h1_tv", "dc_web", "8M", 30, 5201), _iperf_udp("h2_cam", "dc_web", "6M", 30, 5202), _iperf_tcp("e1_pc1", "dc_web", "15M", 30, 5203)],
                          ["dc_web"], {"dc_web": "CONGESTION_BUILDUP"}),
            ScenarioPhase("CONGESTION_ACTIVE", 60,
                          _baseline_actions() + [_iperf_udp("h1_tv", "dc_web", "12M", 60, 5201), _iperf_udp("h2_cam", "dc_web", "10M", 60, 5202), _iperf_tcp("e1_pc1", "dc_web", "25M", 60, 5203), _iperf_tcp("e2_pc1", "dc_web", "20M", 60, 5204), _iperf_tcp("h2_nas", "dc_web", "15M", 60, 5205)],
                          ["dc_web"], {"dc_web": "CONGESTION_ACTIVE"}),
            ScenarioPhase("RECOVERY", 30, _baseline_actions()),
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
        ],
    )


def _scenario_service_degradation() -> Scenario:
    return Scenario(
        name="service_degradation_dc_monitor",
        description="dc_monitor service degrades causing slow responses and timeouts",
        phases=[
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
            ScenarioPhase("LATENCY_DEGRADING", 30,
                          _baseline_actions() + [_netem("dc_monitor", delay_ms=100, jitter_ms=30)],
                          ["dc_monitor"], {"dc_monitor": "LATENCY_DEGRADING"}),
            ScenarioPhase("LATENCY_CRITICAL", 30,
                          _baseline_actions() + [_netem("dc_monitor", delay_ms=400, jitter_ms=80, loss_pct=2.0)],
                          ["dc_monitor"], {"dc_monitor": "LATENCY_CRITICAL"}),
            ScenarioPhase("BROWNOUT", 60,
                          _baseline_actions() + [_netem("dc_monitor", delay_ms=800, jitter_ms=150, loss_pct=8.0, rate="1mbit")],
                          ["dc_monitor"], {"dc_monitor": "BROWNOUT"}),
            ScenarioPhase("RECOVERY", 30, [_clear_netem("dc_monitor")] + _baseline_actions()),
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
        ],
    )


def _scenario_multi_node_congestion() -> Scenario:
    return Scenario(
        name="multi_node_congestion_spread",
        description="Congestion starts at one node and propagates to neighbors",
        phases=[
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
            ScenarioPhase("CONGESTION_BUILDUP", 30,
                          _baseline_actions() + [_iperf_tcp("e1_pc1", "dc_web", "30M", 30)],
                          ["e1_pc1"], {"e1_pc1": "CONGESTION_BUILDUP"}),
            ScenarioPhase("CONGESTION_ACTIVE", 30,
                          _baseline_actions() + [_iperf_tcp("e1_pc1", "dc_web", "40M", 30), _iperf_tcp("e1_pc2", "dc_web", "30M", 30)],
                          ["e1_pc1", "e1_pc2"], {"e1_pc1": "CONGESTION_ACTIVE", "e1_pc2": "CONGESTION_BUILDUP"}),
            ScenarioPhase("CONGESTION_ACTIVE", 60,
                          _baseline_actions() + [_iperf_tcp("e1_pc1", "dc_web", "40M", 60), _iperf_tcp("e1_pc2", "dc_web", "35M", 60), _iperf_tcp("e1_erp", "dc_monitor", "25M", 60)],
                          ["e1_pc1", "e1_pc2", "e1_erp"], {"e1_pc1": "CONGESTION_ACTIVE", "e1_pc2": "CONGESTION_ACTIVE", "e1_erp": "CONGESTION_ACTIVE"}),
            ScenarioPhase("RECOVERY", 30, _baseline_actions()),
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
        ],
    )


def _scenario_mixed_attack_operational() -> Scenario:
    return Scenario(
        name="mixed_ddos_during_congestion",
        description="DDoS attack happens while network is already congested",
        phases=[
            ScenarioPhase("NORMAL", 45, _baseline_actions()),
            ScenarioPhase("CONGESTION_BUILDUP", 30,
                          _baseline_actions() + [_iperf_tcp("e2_pc1", "dc_web", "25M", 30), _iperf_tcp("e2_pc2", "dc_web", "20M", 30)],
                          ["dc_web"], {"dc_web": "CONGESTION_BUILDUP", "e2_pc1": "CONGESTION_BUILDUP"}),
            ScenarioPhase("CONGESTION_ACTIVE", 30,
                          _baseline_actions() + [_iperf_tcp("e2_pc1", "dc_web", "35M", 30), _iperf_tcp("e2_pc2", "dc_web", "30M", 30)],
                          ["dc_web"], {"dc_web": "CONGESTION_ACTIVE"}),
            ScenarioPhase("DDOS_BUILDUP", 30,
                          _baseline_actions() + [_iperf_tcp("e2_pc1", "dc_web", "35M", 30), _iperf_udp("h1_iot", "dc_web", "5M", 30), _iperf_udp("h2_cam", "dc_web", "3M", 30)],
                          ["dc_web"], {"dc_web": "DDOS_BUILDUP", "h1_iot": "DDOS_SOURCE", "h2_cam": "DDOS_SOURCE"}),
            ScenarioPhase("DDOS_ACTIVE", 45,
                          _baseline_actions() + [_iperf_udp("h1_iot", "dc_web", "20M", 45), _iperf_udp("h2_cam", "dc_web", "15M", 45)],
                          ["dc_web"], {"dc_web": "DDOS_TARGET", "h1_iot": "DDOS_SOURCE", "h2_cam": "DDOS_SOURCE"}),
            ScenarioPhase("RECOVERY", 30, _baseline_actions()),
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
        ],
    )


def _scenario_voip_quality_degradation() -> Scenario:
    return Scenario(
        name="voip_rtp_quality_degradation",
        description="VoIP/RTP quality degrades due to jitter and packet loss",
        phases=[
            ScenarioPhase("NORMAL", 60,
                          _baseline_actions() + [_iperf_udp("h1_tv", "dc_monitor", "2M", 60, 5211)]),
            ScenarioPhase("JITTER_HIGH", 30,
                          _baseline_actions() + [_iperf_udp("h1_tv", "dc_monitor", "2M", 30, 5211), _netem("h1_tv", delay_ms=40, jitter_ms=25)],
                          ["h1_tv"], {"h1_tv": "JITTER_HIGH"}),
            ScenarioPhase("JITTER_HIGH", 30,
                          _baseline_actions() + [_iperf_udp("h1_tv", "dc_monitor", "2M", 30, 5211), _netem("h1_tv", delay_ms=80, jitter_ms=50, loss_pct=1.0)],
                          ["h1_tv"], {"h1_tv": "JITTER_HIGH"}),
            ScenarioPhase("PACKET_LOSS_SEVERE", 60,
                          _baseline_actions() + [_iperf_udp("h1_tv", "dc_monitor", "2M", 60, 5211), _netem("h1_tv", delay_ms=120, jitter_ms=70, loss_pct=5.0)],
                          ["h1_tv"], {"h1_tv": "PACKET_LOSS_SEVERE"}),
            ScenarioPhase("RECOVERY", 30, [_clear_netem("h1_tv")] + _baseline_actions()),
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
        ],
    )


def _scenario_brute_force_escalation() -> Scenario:
    return Scenario(
        name="brute_force_escalation_ssh",
        description="SSH brute force starts slow and accelerates",
        phases=[
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
            ScenarioPhase("BRUTE_FORCE_PROBE", 30,
                          _baseline_actions() + [_attack("SSH-Patator", "h2_cam", "dc_vpn", 0.2)],
                          ["dc_vpn"], {"h2_cam": "BRUTE_FORCE_PROBE", "dc_vpn": "BRUTE_FORCE_PROBE"}),
            ScenarioPhase("BRUTE_FORCE_PROBE", 30,
                          _baseline_actions() + [_attack("SSH-Patator", "h2_cam", "dc_vpn", 0.6)],
                          ["dc_vpn"], {"h2_cam": "BRUTE_FORCE_PROBE", "dc_vpn": "BRUTE_FORCE_PROBE"}),
            ScenarioPhase("BRUTE_FORCE_ACTIVE", 60,
                          _baseline_actions() + [_attack("SSH-Patator", "h2_cam", "dc_vpn", 2.0), _attack("FTP-Patator", "h1_iot", "dc_monitor", 1.5)],
                          ["dc_vpn", "dc_monitor"], {"h2_cam": "BRUTE_FORCE_ACTIVE", "dc_vpn": "BRUTE_FORCE_ACTIVE", "h1_iot": "BRUTE_FORCE_ACTIVE", "dc_monitor": "BRUTE_FORCE_ACTIVE"}),
            ScenarioPhase("LATERAL_MOVEMENT", 30,
                          _baseline_actions() + [_attack("Infiltration", "h2_cam", "dc_pub_dns", 1.0)],
                          ["dc_pub_dns"], {"h2_cam": "LATERAL_MOVEMENT", "dc_pub_dns": "LATERAL_MOVEMENT"}),
            ScenarioPhase("RECOVERY", 30, _baseline_actions()),
            ScenarioPhase("NORMAL", 60, _baseline_actions()),
        ],
    )
