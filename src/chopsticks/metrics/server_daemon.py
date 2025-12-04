"""Standalone metrics HTTP server that runs as a daemon"""

import argparse
import signal
import sys
from pathlib import Path
from chopsticks.metrics.http_server import MetricsHTTPServer


def main():
    parser = argparse.ArgumentParser(
        description="Run Chopsticks metrics HTTP server as a daemon"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8090, help="Port to bind to")
    parser.add_argument(
        "--socket-path", default="/tmp/chopsticks_metrics.sock", help="Unix socket path for IPC"
    )
    parser.add_argument(
        "--state-file", type=Path, required=True, help="Path to state file"
    )
    args = parser.parse_args()

    # Create and start server
    server = MetricsHTTPServer(host=args.host, port=args.port, socket_path=args.socket_path)

    # Handle shutdown signals
    def signal_handler(sig, frame):
        print("Shutting down metrics server...", file=sys.stderr)
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Start server (this blocks)
    server.start()


if __name__ == "__main__":
    main()
