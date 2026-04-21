from flask import jsonify, render_template, request

from .config import RYU_BASE_URL
from .dashboard_bridge import (
    build_alert_stats,
    build_alerts,
    build_anomalies,
    build_current_metrics,
    build_historical_traffic,
    build_predictions,
    build_protocol_distribution,
    build_system_status,
    filter_anomalies,
    model_info_payload,
    model_metrics_payload,
)
from .lab import lab_pipeline
from .network_manager import manager
from .services import (
    compute_shortest_path,
    fetch_controller_flows,
    ping_between_hosts,
    topology_payload,
)


def register_routes(app):
    # HTML entrypoint.
    @app.route("/")
    def home():
        return render_template("index.html")

    # Topology graph for D3 rendering.
    @app.route("/api/topology")
    @app.route("/topology")
    def topology():
        net = manager.net
        if net is None:
            return jsonify({"error": "Mininet is still starting"}), 503

        return jsonify(topology_payload(net))

    # Shortest path between two endpoints (host-level selection in UI).
    @app.route("/api/path", methods=["POST"])
    @app.route("/path", methods=["POST"])
    def path():
        net = manager.net
        if net is None:
            return jsonify({"error": "Mininet is still starting"}), 503

        payload = request.get_json(silent=True) or {}
        src = payload.get("src")
        dst = payload.get("dst")

        if not src or not dst:
            return jsonify({"error": "src and dst are required"}), 400

        result_path = compute_shortest_path(net, src, dst)
        if not result_path:
            return jsonify({"error": f"No path between {src} and {dst}"}), 404

        segments = []
        for index in range(len(result_path) - 1):
            segments.append(
                {
                    "source": result_path[index],
                    "target": result_path[index + 1],
                }
            )

        return jsonify({"path": result_path, "segments": segments})

    # Compatibility aliases (/path, /ping, /flows) are kept for older UI calls.
    @app.route("/api/ping", methods=["POST"])
    @app.route("/ping", methods=["POST"])
    def ping():
        net = manager.net
        if net is None:
            return "Mininet is still starting", 503

        payload = request.get_json(silent=True) or {}
        src = payload.get("src")
        dst = payload.get("dst")

        if not src or not dst:
            return "src and dst are required", 400

        try:
            return ping_between_hosts(net, src, dst)
        except Exception as exc:
            return str(exc), 500

    @app.route("/api/flows")
    @app.route("/flows")
    def flows():
        try:
            return jsonify(fetch_controller_flows(RYU_BASE_URL))
        except Exception as exc:
            return jsonify({"error": str(exc)})

    # Dataset generation controls: packet capture, synthetic traffic, and feature export.
    @app.route("/api/lab/status")
    def lab_status():
        return jsonify(lab_pipeline.status())

    @app.route("/api/lab/capture/start", methods=["POST"])
    def lab_capture_start():
        net = manager.net
        if net is None:
            return jsonify({"error": "Mininet is still starting"}), 503

        payload = request.get_json(silent=True) or {}
        label = payload.get("label", "dataset")

        try:
            return jsonify(lab_pipeline.start_capture(net, label=label))
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route("/api/lab/capture/stop", methods=["POST"])
    def lab_capture_stop():
        return jsonify(lab_pipeline.stop_capture())

    @app.route("/api/lab/traffic/start", methods=["POST"])
    def lab_traffic_start():
        net = manager.net
        if net is None:
            return jsonify({"error": "Mininet is still starting"}), 503

        payload = request.get_json(silent=True) or {}
        duration_seconds = payload.get("duration_seconds", 90)

        try:
            return jsonify(lab_pipeline.start_traffic(net, duration_seconds=duration_seconds))
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route("/api/lab/traffic/stop", methods=["POST"])
    def lab_traffic_stop():
        return jsonify(lab_pipeline.stop_traffic())

    @app.route("/api/lab/export", methods=["POST"])
    def lab_export():
        payload = request.get_json(silent=True) or {}
        capture_id = payload.get("capture_id")
        if not capture_id:
            status = lab_pipeline.status()
            capture_id = status.get("capture_id")

        if not capture_id:
            return jsonify({"error": "capture_id is required"}), 400

        try:
            return jsonify(lab_pipeline.export_features(capture_id))
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route("/api/lab/relay", methods=["POST"])
    def lab_relay():
        payload = request.get_json(silent=True) or {}
        capture_id = payload.get("capture_id")
        if not capture_id:
            status = lab_pipeline.status()
            capture_id = status.get("last_capture_id")

        if not capture_id:
            return jsonify({"error": "capture_id is required"}), 400

        try:
            return jsonify(lab_pipeline.relay_capture_to_collector(capture_id))
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route("/api/lab/infer", methods=["POST"])
    def lab_infer():
        payload = request.get_json(silent=True) or {}
        capture_id = payload.get("capture_id")
        if not capture_id:
            status = lab_pipeline.status()
            capture_id = status.get("last_capture_id")

        if not capture_id:
            return jsonify({"error": "capture_id is required"}), 400

        try:
            return jsonify(lab_pipeline.collector_extract_and_infer(capture_id))
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    # Teammate dashboard compatibility endpoints.
    @app.route("/metrics/current")
    def metrics_current():
        return jsonify(build_current_metrics(lab_pipeline))

    @app.route("/metrics/traffic/historical")
    def metrics_historical():
        return jsonify({"data": build_historical_traffic()})

    @app.route("/metrics/traffic/prediction")
    def metrics_prediction():
        pred = build_predictions()
        return jsonify(
            {
                "data": [
                    {
                        "time": item["time"],
                        "predicted": item["predicted"],
                        "upper": item["upper"],
                        "lower": item["lower"],
                    }
                    for item in pred
                ]
            }
        )

    @app.route("/metrics/protocols/distribution")
    def metrics_protocols():
        return jsonify({"data": build_protocol_distribution()})

    @app.route("/metrics/system/status")
    def metrics_system_status():
        return jsonify(build_system_status(lab_pipeline))

    @app.route("/alerts")
    def alerts():
        alerts_payload = build_alerts(lab_pipeline)
        return jsonify({"alerts": alerts_payload})

    @app.route("/alerts/stats")
    def alerts_stats():
        alerts_payload = build_alerts(lab_pipeline)
        return jsonify(build_alert_stats(alerts_payload))

    @app.route("/anomalies")
    def anomalies():
        search = request.args.get("search")
        severity = request.args.get("severity")
        result = filter_anomalies(build_anomalies(lab_pipeline), search=search, severity=severity)
        return jsonify({"anomalies": result, "total": len(result)})

    @app.route("/predictions")
    def predictions():
        return jsonify({"data": build_predictions()})

    @app.route("/predictions/model/metrics")
    def predictions_model_metrics():
        return jsonify(model_metrics_payload())

    @app.route("/predictions/model/info")
    def predictions_model_info():
        return jsonify(model_info_payload())
