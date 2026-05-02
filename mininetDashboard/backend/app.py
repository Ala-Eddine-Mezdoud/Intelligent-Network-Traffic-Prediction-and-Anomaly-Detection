from flask import Flask
import threading
import time

from .lab import lab_pipeline
from .network_manager import manager
from .routes import register_routes


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    register_routes(app)

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    manager.start_async()

    def boot_realtime_loop():
        while True:
            net = manager.net
            if net is not None:
                try:
                    lab_pipeline.start_realtime(net, interval_seconds=30)
                    return
                except Exception:
                    # Keep retrying so realtime mode eventually starts once dependencies are ready.
                    pass
            time.sleep(1)

    threading.Thread(target=boot_realtime_loop, daemon=True).start()

    return app
