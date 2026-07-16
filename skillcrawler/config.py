from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_CRAWLER_CONFIG_PATH = Path(__file__).resolve().parent.parent / "skills" / "skill-repos.yaml"


def normalize_dict_keys(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            str(key).strip(): normalize_dict_keys(value)
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [normalize_dict_keys(item) for item in data]
    return data


def load_crawler_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or DEFAULT_CRAWLER_CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    normalized = normalize_dict_keys(data)
    if not isinstance(normalized, dict):
        raise ValueError(f"Invalid config format in {path}")
    return normalized

