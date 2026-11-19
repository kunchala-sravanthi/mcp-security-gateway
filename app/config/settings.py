"""Load local gateway configuration."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config.json"


@dataclass(frozen=True)
class Settings:
    upstream_command: str
    upstream_args: list[str]
    approval_timeout_seconds: int = 120


def load_settings() -> Settings:
    """Load config.json and validate required settings."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Missing {CONFIG_PATH}. Copy config.example.json to config.json first."
        )

    raw: dict[str, Any] = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    command = raw.get("upstream_command")
    args = raw.get("upstream_args", [])
    timeout = raw.get("approval_timeout_seconds", 120)

    if not isinstance(command, str) or not command.strip():
        raise ValueError("upstream_command must be a non-empty string")
    if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
        raise ValueError("upstream_args must be a list of strings")
    if not isinstance(timeout, int) or timeout < 1:
        raise ValueError("approval_timeout_seconds must be a positive integer")

    return Settings(command, args, timeout)
