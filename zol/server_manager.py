"""Server process management for cc-zol."""

import os
import sys
import signal
import subprocess
import time
from typing import Optional

from .config import LocalConfig
from .port_utils import find_available_port, is_port_available


class ServerManager:
    """Manages the background uvicorn server process."""

    def __init__(self):
        self.config = LocalConfig.load()

    def is_running(self) -> bool:
        """Check if the server is currently running."""
        pid = self.config.get_server_pid()
        if pid is None:
            return False

        try:
            # Check if process exists
            os.kill(pid, 0)
            # Also verify the port is in use (process might be zombie)
            port = self.config.get_server_port()
            if port and is_port_available(port):
                # Port is available but PID exists - stale state
                self._cleanup()
                return False
            return True
        except OSError:
            # Process doesn't exist
            self._cleanup()
            return False

    def _cleanup(self) -> None:
        """Clean up stale PID/port files."""
        self.config.clear_server_pid()
        self.config.clear_server_port()

    def get_port(self) -> Optional[int]:
        """Get the port the server is running on."""
        return self.config.get_server_port()

    def start(self, port: Optional[int] = None, provider_config: Optional[dict] = None) -> int:
        """
        Start the server in the background.
        Returns the port number.

        Args:
            port: Optional port to use (auto-finds available if not specified)
            provider_config: Provider configuration from auth server (api_key, base_url, model).
                           Passed as environment variables - never written to disk.
        """
        if self.is_running():
            return self.get_port()

        # Find available port
        if port is None:
            port = find_available_port()

        # Ensure config directory exists
        self.config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Start uvicorn as background process
        log_file = open(self.config.SERVER_LOG_FILE, "w")

        # Build environment - pass provider config securely (in memory only)
        env = os.environ.copy()
        if provider_config:
            env["PROVIDER_API_KEY"] = provider_config.get("provider_api_key", "")
            env["PROVIDER_BASE_URL"] = provider_config.get("provider_base_url", "")
            env["MODEL"] = provider_config.get("model", "")

        # Use api.app:app directly (works when installed as package)
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "api.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            stdout=log_file,
            stderr=log_file,
            env=env,
            start_new_session=True,  # Detach from terminal
        )

        # Save PID and port
        self.config.save_server_pid(process.pid)
        self.config.save_server_port(port)

        # Wait for server to be ready
        self._wait_for_server(port)

        return port

    def _wait_for_server(self, port: int, timeout: float = 10.0) -> None:
        """Wait for the server to be ready to accept connections."""
        import socket

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    s.connect(("127.0.0.1", port))
                    return  # Server is ready
            except (socket.error, OSError):
                time.sleep(0.1)

        raise RuntimeError(f"Server failed to start on port {port} within {timeout}s")

    def stop(self) -> bool:
        """
        Stop the running server.
        Returns True if server was stopped, False if not running.
        """
        pid = self.config.get_server_pid()
        if pid is None:
            return False

        try:
            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)

            # Wait for process to exit
            for _ in range(50):  # 5 seconds max
                try:
                    os.kill(pid, 0)
                    time.sleep(0.1)
                except OSError:
                    break
            else:
                # Force kill if still running
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass

            self._cleanup()
            return True

        except OSError:
            self._cleanup()
            return False
