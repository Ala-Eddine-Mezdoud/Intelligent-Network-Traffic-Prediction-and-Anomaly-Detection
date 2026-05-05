import sys
import re

with open("mininetDashboard/backend/routes.py", "r") as f:
    content = f.read()

# Add import
import_stmt = "from .gnn_data_generator import gnn_generator\nimport os\nfrom pathlib import Path\n"
if "from .gnn_data_generator import gnn_generator" not in content:
    content = content.replace("from .lab import lab_pipeline", import_stmt + "from .lab import lab_pipeline")

# Add routes
routes_code = """
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

"""

if "gnn_capture_start" not in content:
    content = content.replace("    # Dataset generation controls", routes_code + "\n    # Dataset generation controls")

with open("mininetDashboard/backend/routes.py", "w") as f:
    f.write(content)

print("Patch applied successfully.")
