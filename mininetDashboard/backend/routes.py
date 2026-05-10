from flask import jsonify, render_template, request

from .config import RYU_BASE_URL
from .dashboard_bridge import (
    build_alert_stats,
    build_alerts,
    build_anomalies,
    build_current_metrics,
    build_gnn_alerts,
    build_gnn_anomalies,
    build_historical_traffic,
    build_predictions,
    build_protocol_distribution_from_inference,
    build_system_status,
    filter_anomalies,
    model_info_payload,
    model_metrics_payload,
)
from .gnn_data_generator import gnn_generator
from .gnn_inference import gnn_engine
import os
from pathlib import Path
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


    # GNN Dataset Generation Endpoints
    @app.route("/api/lab/run-gnn-capture", methods=["POST"])
    def gnn_capture_start():
        net = manager.net
        if net is None:
            return jsonify({"error": "Mininet is not running"}), 503
        
        payload = request.get_json(silent=True) or {}
        scenarios = payload.get("scenarios")
        
        try:
            gnn_generator.start(net, scenarios=scenarios)
            return jsonify({"status": "started"})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route("/api/lab/gnn-capture/stop", methods=["POST"])
    def gnn_capture_stop():
        gnn_generator.stop()
        return jsonify({"status": "stopped"})

    @app.route("/api/lab/gnn-capture/status")
    def gnn_capture_status():
        return jsonify(gnn_generator.status())

    @app.route("/api/lab/gnn-datasets")
    def gnn_datasets():
        from .gnn_data_generator import GNN_DATASET_DIR
        path = Path(GNN_DATASET_DIR)
        datasets = []
        if path.exists():
            for d in path.iterdir():
                if d.is_dir():
                    datasets.append(d.name)
        return jsonify({"datasets": sorted(datasets, reverse=True)})

    # GNN Live Inference Endpoints
    @app.route("/api/gnn/inference/start", methods=["POST"])
    def gnn_inference_start():
        net = manager.net
        if net is None:
            return jsonify({"error": "Mininet is not running"}), 503
        try:
            result = gnn_engine.start(net)
            if "error" in result:
                return jsonify(result), 400
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/gnn/inference/stop", methods=["POST"])
    def gnn_inference_stop():
        return jsonify(gnn_engine.stop())

    @app.route("/api/gnn/inference/status")
    def gnn_inference_status():
        return jsonify(gnn_engine.status())

    @app.route("/api/gnn/inference/predictions")
    def gnn_inference_predictions():
        return jsonify(gnn_engine.predictions())

    @app.route("/api/gnn/inference/anomaly_history")
    def gnn_inference_anomaly_history():
        return jsonify(gnn_engine.anomaly_history())


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

    @app.route("/api/realtime/start", methods=["POST"])
    def realtime_start():
        net = manager.net
        if net is None:
            return jsonify({"error": "Mininet is still starting"}), 503

        payload = request.get_json(silent=True) or {}
        interval_seconds = payload.get("interval_seconds", 30)

        try:
            return jsonify(lab_pipeline.start_realtime(net, interval_seconds=interval_seconds))
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route("/api/realtime/stop", methods=["POST"])
    def realtime_stop():
        return jsonify(lab_pipeline.stop_realtime())

    @app.route("/api/realtime/status")
    def realtime_status():
        return jsonify(lab_pipeline.realtime_status())

    @app.route("/api/realtime/settings", methods=["GET", "POST"])
    def realtime_settings():
        if request.method == "GET":
            return jsonify(lab_pipeline.get_realtime_settings())

        payload = request.get_json(silent=True) or {}
        try:
            updated = lab_pipeline.update_realtime_settings(payload)
            return jsonify(updated)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route("/api/pipeline/start", methods=["POST"])
    def pipeline_start():
        net = manager.net
        if net is None:
            return jsonify({"error": "Mininet is still starting"}), 503

        payload = request.get_json(silent=True) or {}
        interval_seconds = payload.get("interval_seconds", 30)

        try:
            result = lab_pipeline.start_realtime(net, interval_seconds=interval_seconds)
            return jsonify(
                {
                    "pipeline": "realtime",
                    "started": result.get("started", False),
                    "interval_seconds": result.get("interval_seconds", interval_seconds),
                }
            )
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route("/api/pipeline/stop", methods=["POST"])
    def pipeline_stop():
        result = lab_pipeline.stop_realtime()
        return jsonify({"pipeline": "realtime", **result})

    @app.route("/api/pipeline/status")
    def pipeline_status():
        status = lab_pipeline.realtime_status()
        return jsonify({"pipeline": "realtime", **status})

    @app.route("/api/pipeline/settings", methods=["GET", "POST"])
    def pipeline_settings():
        if request.method == "GET":
            return jsonify({"pipeline": "realtime", **lab_pipeline.get_realtime_settings()})

        payload = request.get_json(silent=True) or {}
        try:
            updated = lab_pipeline.update_realtime_settings(payload)
            return jsonify({"pipeline": "realtime", **updated})
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
        pred = build_predictions(lab_pipeline=lab_pipeline)
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
        return jsonify({"data": build_protocol_distribution_from_inference(lab_pipeline)})

    @app.route("/metrics/system/status")
    def metrics_system_status():
        return jsonify(build_system_status(lab_pipeline))

    @app.route("/alerts")
    def alerts():
        alerts_payload = build_alerts(lab_pipeline) + build_gnn_alerts()
        return jsonify({"alerts": alerts_payload})

    @app.route("/alerts/stats")
    def alerts_stats():
        alerts_payload = build_alerts(lab_pipeline) + build_gnn_alerts()
        return jsonify(build_alert_stats(alerts_payload))

    @app.route("/anomalies")
    def anomalies():
        search = request.args.get("search")
        severity = request.args.get("severity")
        combined = build_anomalies(lab_pipeline) + build_gnn_anomalies()
        result = filter_anomalies(combined, search=search, severity=severity)
        return jsonify({"anomalies": result, "total": len(result)})

    @app.route("/predictions")
    def predictions():
        return jsonify({"data": build_predictions(lab_pipeline=lab_pipeline)})

    @app.route("/predictions/model/metrics")
    def predictions_model_metrics():
        return jsonify(model_metrics_payload())

    @app.route("/predictions/model/info")
    def predictions_model_info():
        return jsonify(model_info_payload())

    @app.route("/api/simulation/status")
    def simulation_combined_status():
        pipeline_status = lab_pipeline.realtime_status()
        normal_status = lab_pipeline.normal_sim_status()
        gnn_status = gnn_engine.status()
        gnn_preds = gnn_engine.predictions()
        return jsonify({
            "pipeline": pipeline_status,
            "normal": normal_status,
            "gnn": {
                "status": gnn_status,
                "predictions": gnn_preds if "error" not in gnn_preds else None,
            },
        })

    @app.route("/api/simulation/normal/start", methods=["POST"])
    def simulation_normal_start():
        net = manager.net
        if net is None:
            return jsonify({"error": "Mininet is still starting"}), 503
        try:
            result = lab_pipeline.start_normal_simulation(net)
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route("/api/simulation/normal/stop", methods=["POST"])
    def simulation_normal_stop():
        result = lab_pipeline.stop_normal_simulation()
        return jsonify(result)

    @app.route("/api/simulation/inject", methods=["POST"])
    def simulation_inject():
        payload = request.get_json(silent=True) or {}
        anomaly_type = payload.get("type", "")
        node = payload.get("node") or None
        duration_s = int(payload.get("duration_s", 30))
        try:
            result = lab_pipeline.inject_anomaly(anomaly_type, node=node, duration_s=duration_s)
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route("/api/simulation/anomaly_types")
    def simulation_anomaly_types():
        return jsonify(lab_pipeline.ANOMALY_TYPES)

    @app.route("/api/storage/info")
    def storage_info():
        """Return paths and file counts for all stored data."""
        import glob as _glob
        base = Path(__file__).resolve().parents[2]
        caps = base / "captures"

        def count(pattern):
            return len(_glob.glob(str(pattern)))

        def latest(pattern):
            files = sorted(_glob.glob(str(pattern)))
            return str(Path(files[-1]).name) if files else None

        gnn_inf = caps / "gnn_inference"
        return jsonify({
            "base_dir": str(base),
            "captures": {
                "path": str(caps),
                "pcap_files": count(caps / "*.pcap"),
                "latest_pcap": latest(caps / "*.pcap"),
            },
            "intelligence_out": {
                "path": str(caps / "intelligence_out"),
                "inference_files": count(caps / "intelligence_out" / "*_inference.json"),
                "latest_inference": latest(caps / "intelligence_out" / "*_inference.json"),
                "csv_files": count(caps / "intelligence_out" / "*.csv"),
            },
            "gnn_inference": {
                "path": str(gnn_inf),
                "anomaly_files": count(gnn_inf / "*_anomaly.json"),
                "latest_anomaly": latest(gnn_inf / "*_anomaly.json"),
                "has_latest": (gnn_inf / "latest_inference.json").exists(),
            },
            "gnn_datasets": {
                "path": str(caps / "gnn_datasets"),
                "dataset_count": count(caps / "gnn_datasets" / "gnn_*"),
                "latest_dataset": latest(caps / "gnn_datasets" / "gnn_*"),
            },
            "ml_models": {
                "path": str(base / "ml_training"),
                "best_model": str(base / "ml_training" / "best_model.pt"),
                "gnn_model": str(base / "ml_training" / "gnn_model_complete.pt"),
                "backend_model": str(base / "mininetDashboard" / "backend" / "models"),
            },
            "collector_inbox": {
                "path": str(caps / "collector_inbox"),
                "pending_files": count(caps / "collector_inbox" / "*"),
            },
        })
