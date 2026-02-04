"""Port utilities for finding available ports."""

import socket


def is_port_available(port: int) -> bool:
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", port))
            return True
    except OSError:
        return False


def find_available_port(start: int = 8082, range_size: int = 100) -> int:
    """
    Find an available port starting from the given port.
    Raises RuntimeError if no port is found within the range.
    """
    for port in range(start, start + range_size):
        if is_port_available(port):
            return port
    raise RuntimeError(f"No available port found in range {start}-{start + range_size}")
