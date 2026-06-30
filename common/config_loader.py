from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from common.yaml_utils import load_yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_env_config(env: str) -> dict[str, Any]:
    config_path = PROJECT_ROOT / "config" / f"{env}.yaml"
    config = load_yaml(config_path)
    config["_project_root"] = str(PROJECT_ROOT)
    config["_config_path"] = str(config_path)

    env_base_url = os.getenv("XSENSE_BASE_URL")
    env_admin_url = os.getenv("XSENSE_ADMIN_URL")
    if env_base_url:
        config["base_url"] = env_base_url
    if env_admin_url:
        config["admin_url"] = env_admin_url

    return config


def load_data_file(name: str) -> dict[str, Any]:
    return load_yaml(PROJECT_ROOT / "data" / name)

