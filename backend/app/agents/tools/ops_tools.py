"""
ops_tools.py — operational health check tools for OpsPilot AI.

These give the AI the ability to check real system state:
- Docker container status
- HTTP endpoint health check
- Disk / memory usage summary
"""

import logging
import subprocess
import shutil
from typing import Optional

logger = logging.getLogger(__name__)


def check_docker_status() -> str:
    """Return a summary of all running Docker containers."""
    if not shutil.which("docker"):
        return "Docker is not installed or not in PATH on this server."

    try:
        result = subprocess.run(
            ["docker", "ps", "--format",
             "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip()
        return output if output else "No Docker containers are currently running."

    except subprocess.TimeoutExpired:
        return "Docker status check timed out."
    except Exception as exc:
        logger.error("docker ps failed: %s", exc)
        return f"Failed to query Docker: {exc}"


def check_endpoint_health(url: str) -> str:
    """
    Perform an HTTP GET to `url` and report the status.

    Args:
        url: Full URL to check, e.g. 'http://localhost:8000/health'

    Returns:
        Human-readable health report string.
    """
    try:
        import httpx
        response = httpx.get(url, timeout=5.0)
        return (
            f"Endpoint: {url}\n"
            f"Status: {response.status_code} {'✅ OK' if response.status_code < 400 else '❌ ERROR'}\n"
            f"Response time: {response.elapsed.total_seconds():.3f}s"
        )
    except Exception as exc:
        return f"Health check failed for {url}: {exc}"


def get_system_usage() -> str:
    """Return current CPU, memory, and disk usage."""
    try:
        import psutil

        cpu  = psutil.cpu_percent(interval=1)
        mem  = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return (
            f"**System Health Report**\n"
            f"- CPU usage:    {cpu}%\n"
            f"- RAM used:     {mem.used / 1e9:.1f} GB / {mem.total / 1e9:.1f} GB ({mem.percent}%)\n"
            f"- Disk used:    {disk.used / 1e9:.1f} GB / {disk.total / 1e9:.1f} GB ({disk.percent}%)"
        )
    except ImportError:
        return "psutil is not installed — add 'psutil' to requirements.txt for system stats."
    except Exception as exc:
        return f"System usage check failed: {exc}"
