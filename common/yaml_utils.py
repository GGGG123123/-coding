from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"YAML file not found: {file_path}")
    with file_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {file_path}")
    return data


def load_yaml_list(path: str | Path) -> list[Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"YAML file not found: {file_path}")
    with file_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or []
    if not isinstance(data, list):
        raise ValueError(f"YAML root must be a list: {file_path}")
    return data


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged

