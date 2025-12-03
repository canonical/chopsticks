"""HTTP server to expose Prometheus metrics"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from typing import Optional

from .prometheus_exporter import PrometheusExporter


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics endpoint"""

    exporter: Optional[PrometheusExporter] = None

    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()

            if self.exporter:
                metrics_text = self.exporter.export()
                self.wfile.write(metrics_text.encode("utf-8"))
            else:
                self.wfile.write(b"# No metrics available\n")
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = b"""
            <html>
            <head><title>Chopsticks Metrics</title></head>
            <body>
            <h1>Chopsticks Metrics Exporter</h1>
            <p><a href="/metrics">Metrics endpoint</a></p>
            </body>
            </html>
            """
            self.wfile.write(html)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


class MetricsHTTPServer:
    """HTTP server for Prometheus metrics"""

    def __init__(self, host: str = "0.0.0.0", port: int = 9090):
        self.host = host
        self.port = port
        self.exporter = PrometheusExporter()
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Start the HTTP server in a background thread"""
        MetricsHandler.exporter = self.exporter
        self.server = HTTPServer((self.host, self.port), MetricsHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        print(f"Metrics server started at http://{self.host}:{self.port}/metrics")

    def stop(self):
        """Stop the HTTP server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("Metrics server stopped")

    def get_exporter(self) -> PrometheusExporter:
        """Get the Prometheus exporter"""
        return self.exporter
