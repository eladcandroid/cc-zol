"""Local configuration management for cc-zol."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


DEFAULT_MODEL = "moonshotai/kimi-k2.5"
GITHUB_REPO = "eladcandroid/cc-zol"

# Remote auth server URL (for email verification & token retrieval)
# Users login against this server, then run local proxy
AUTH_SERVER_URL = "http://localhost:8083"  # Change to your hosted URL for production


@dataclass
class LocalConfig:
    """Local configuration stored in ~/.cc-zol/."""

    CONFIG_DIR = Path.home() / ".cc-zol"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    SERVER_PID_FILE = CONFIG_DIR / "server.pid"
    SERVER_PORT_FILE = CONFIG_DIR / "server.port"
    SERVER_LOG_FILE = CONFIG_DIR / "server.log"

    email: Optional[str] = None
    token: Optional[str] = None
    model: Optional[str] = None

    @classmethod
    def load(cls) -> "LocalConfig":
        """Load configuration from disk."""
        config = cls()
        if cls.CONFIG_FILE.exists():
            try:
                data = json.loads(cls.CONFIG_FILE.read_text())
                config.email = data.get("email")
                config.token = data.get("token")
                config.model = data.get("model")
            except (json.JSONDecodeError, OSError):
                pass
        return config

    def is_logged_in(self) -> bool:
        """Check if user is logged in."""
        return bool(self.email and self.token)

    def get_model(self) -> str:
        """Get selected model or default."""
        return self.model or DEFAULT_MODEL

    def save(self, email: str, token: str, model: Optional[str] = None) -> None:
        """Save credentials to disk with secure permissions."""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.email = email
        self.token = token
        if model:
            self.model = model
        data = {"email": email, "token": token}
        if self.model:
            data["model"] = self.model
        self.CONFIG_FILE.write_text(json.dumps(data))
        # Set file permissions to owner read/write only
        os.chmod(self.CONFIG_FILE, 0o600)

    def save_model(self, model: str) -> None:
        """Save only the model selection."""
        self.model = model
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {}
        if self.CONFIG_FILE.exists():
            try:
                data = json.loads(self.CONFIG_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        data["model"] = model
        self.CONFIG_FILE.write_text(json.dumps(data))
        os.chmod(self.CONFIG_FILE, 0o600)

    def clear(self) -> None:
        """Clear saved credentials."""
        self.email = None
        self.token = None
        self.model = None
        if self.CONFIG_FILE.exists():
            self.CONFIG_FILE.unlink()

    def save_server_pid(self, pid: int) -> None:
        """Save server PID."""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.SERVER_PID_FILE.write_text(str(pid))

    def get_server_pid(self) -> Optional[int]:
        """Get saved server PID."""
        if self.SERVER_PID_FILE.exists():
            try:
                return int(self.SERVER_PID_FILE.read_text().strip())
            except (ValueError, OSError):
                pass
        return None

    def clear_server_pid(self) -> None:
        """Clear saved server PID."""
        if self.SERVER_PID_FILE.exists():
            self.SERVER_PID_FILE.unlink()

    def save_server_port(self, port: int) -> None:
        """Save server port."""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.SERVER_PORT_FILE.write_text(str(port))

    def get_server_port(self) -> Optional[int]:
        """Get saved server port."""
        if self.SERVER_PORT_FILE.exists():
            try:
                return int(self.SERVER_PORT_FILE.read_text().strip())
            except (ValueError, OSError):
                pass
        return None

    def clear_server_port(self) -> None:
        """Clear saved server port."""
        if self.SERVER_PORT_FILE.exists():
            self.SERVER_PORT_FILE.unlink()

    def save_update_info(self, commit_sha: str) -> None:
        """Save update info (commit SHA and timestamp)."""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {}
        if self.CONFIG_FILE.exists():
            try:
                data = json.loads(self.CONFIG_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        data["last_update_commit"] = commit_sha
        data["last_update_time"] = datetime.now().isoformat()
        self.CONFIG_FILE.write_text(json.dumps(data))
        os.chmod(self.CONFIG_FILE, 0o600)

    def get_update_info(self) -> tuple[Optional[str], Optional[str]]:
        """Get last update info (commit_sha, timestamp)."""
        if self.CONFIG_FILE.exists():
            try:
                data = json.loads(self.CONFIG_FILE.read_text())
                return data.get("last_update_commit"), data.get("last_update_time")
            except (json.JSONDecodeError, OSError):
                pass
        return None, None
