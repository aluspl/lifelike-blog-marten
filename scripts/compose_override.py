"""Generate a minimal docker-compose override YAML string.

This module deliberately avoids a YAML dependency for generation and returns a
small string suitable for writing to a file when needed.
"""
from __future__ import annotations
from typing import Mapping
import tempfile
import os


def generate_override(mapping: Mapping | None = None) -> str:
    """Write a minimal docker-compose override YAML to a temp file and return its path.

    mapping: {service_name: {"container_port": int, "host_port": int}}
    """
    services_block = ""
    if mapping:
        parts = ["services:"]
        for svc, cfg in mapping.items():
            cont = cfg.get("container_port")
            host = cfg.get("host_port")
            parts.append(f"  {svc}:")
            parts.append(f"    ports:")
            parts.append(f"      - \"{host}:{cont}\"")
        services_block = "\n".join(parts) + "\n"
    content = f"version: '3'\n{services_block}"
    fd, path = tempfile.mkstemp(suffix=".yml", prefix="tester-override-")
    os.close(fd)
    with open(path, "w", encoding="utf8") as fh:
        fh.write(content)
    return path
