"""Persistent metrics server daemon management"""

import os
import signal
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


class MetricsDaemon:
    """Manages persistent metrics HTTP server as a background process"""

    def __init__(self, config: dict):
        self.config = config

        persistent_config = config.get("persistent", {})
        self.pid_file = Path(
            persistent_config.get("pid_file", "/tmp/chopsticks_metrics.pid")
        )
        self.state_file = Path(
            persistent_config.get("state_file", "/tmp/chopsticks_metrics_state.json")
        )
        self.socket_path = persistent_config.get("socket_path", "/tmp/chopsticks_metrics.sock")

        self.host = config.get("http_host", "0.0.0.0")
        self.port = config.get("http_port", 8090)

    def start(self):
        """Start metrics server as background daemon"""
        if self.is_running():
            raise RuntimeError("Metrics server already running")

        # Start server process in background
        import sys

        cmd = [
            sys.executable,
            "-m",
            "chopsticks.metrics.server_daemon",
            "--host",
            str(self.host),
            "--port",
            str(self.port),
            "--socket-path",
            str(self.socket_path),
            "--state-file",
            str(self.state_file),
        ]

        # Start detached process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Detach from parent
        )

        # Save PID
        self.pid_file.write_text(str(process.pid))

        # Save state
        state = {
            "pid": process.pid,
            "host": self.host,
            "port": self.port,
            "start_time": datetime.now().isoformat(),
        }
        self.state_file.write_text(json.dumps(state, indent=2))

        # Wait a moment and verify it started
        time.sleep(1)
        if not self.is_running():
            raise RuntimeError("Failed to start metrics server")

    def stop(self):
        """Stop the running metrics server"""
        if not self.is_running():
            raise RuntimeError("Metrics server not running")

        pid = int(self.pid_file.read_text())

        try:
            os.kill(pid, signal.SIGTERM)

            # Wait for process to stop (up to 5 seconds)
            for _ in range(50):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.1)
                except OSError:
                    break  # Process stopped

            # Clean up files
            self.pid_file.unlink(missing_ok=True)
            self.state_file.unlink(missing_ok=True)

        except OSError as e:
            raise RuntimeError(f"Failed to stop server: {e}")

    def is_running(self) -> bool:
        """Check if metrics server is currently running"""
        if not self.pid_file.exists():
            return False

        try:
            pid = int(self.pid_file.read_text())
            os.kill(pid, 0)  # Signal 0 just checks if process exists
            return True
        except (OSError, ValueError):
            # Clean up stale PID file
            self.pid_file.unlink(missing_ok=True)
            return False
    
    def cleanup_stale_files(self):
        """Clean up stale PID, state, and socket files"""
        from pathlib import Path
        
        # Remove PID file if it exists and process is not running
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text())
                try:
                    os.kill(pid, 0)
                    # Process exists, don't clean
                    return
                except OSError:
                    # Process doesn't exist, clean up
                    self.pid_file.unlink(missing_ok=True)
            except (ValueError, OSError):
                self.pid_file.unlink(missing_ok=True)
        
        # Remove state file
        self.state_file.unlink(missing_ok=True)
        
        # Remove socket file
        socket_path = Path(self.socket_path)
        socket_path.unlink(missing_ok=True)

    def get_status(self) -> Dict[str, Any]:
        """Get current server status"""
        if not self.is_running():
            return {"running": False}

        if self.state_file.exists():
            try:
                state = json.loads(self.state_file.read_text())
                state["running"] = True
                return state
            except (json.JSONDecodeError, OSError):
                pass

        # Fallback if state file missing or corrupted
        return {
            "running": True,
            "pid": int(self.pid_file.read_text()),
            "host": self.host,
            "port": self.port,
        }
