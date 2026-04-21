import statistics


class IntelligencePlane:
    """Simple AI-plane placeholder for simulation-time inference behavior."""

    def infer(self, flow_rows, capture_id):
        total = len(flow_rows)
        if total == 0:
            return {
                "capture_id": capture_id,
                "total_flows": 0,
                "suspicious_flows": 0,
                "risk_score": 0.0,
                "severity": "low",
                "reasons": ["No flows decoded"],
            }

        suspicious = []
        for row in flow_rows:
            pkt_rate = float(row.get("Flow Pkts/s", 0.0) or 0.0)
            byte_rate = float(row.get("Flow Byts/s", 0.0) or 0.0)
            label = str(row.get("Label", "")).strip()

            if label == "MALICIOUS_SIM" or pkt_rate > 220.0 or byte_rate > 800000.0:
                suspicious.append(row)

        risk_score = round(len(suspicious) / total, 4)

        if risk_score >= 0.25:
            severity = "high"
        elif risk_score >= 0.08:
            severity = "medium"
        else:
            severity = "low"

        pkt_rates = [float(row.get("Flow Pkts/s", 0.0) or 0.0) for row in flow_rows]
        byte_rates = [float(row.get("Flow Byts/s", 0.0) or 0.0) for row in flow_rows]

        reasons = [
            f"mean_pkt_rate={round(statistics.mean(pkt_rates), 3) if pkt_rates else 0}",
            f"mean_byte_rate={round(statistics.mean(byte_rates), 3) if byte_rates else 0}",
        ]

        return {
            "capture_id": capture_id,
            "total_flows": total,
            "suspicious_flows": len(suspicious),
            "risk_score": risk_score,
            "severity": severity,
            "reasons": reasons,
        }


intelligence_plane = IntelligencePlane()
