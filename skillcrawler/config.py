from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from skillcrawler.core.git_operations import GitOperations

OPENEULER_SKILLS_URL = "https://gitcode.com/openeuler/openEuler-skills"


def sync_openEuler_skills_repo() -> Path:
    """Return the local openEuler-skills checkout, cloning it when absent."""
    from src.core.config import get_settings
    local_path = Path(get_settings().storage.local_path) / "skill-repositories" / "openEuler-skills"
    openEuler_skills_path = local_path.expanduser()
    openEuler_skills_path.parent.mkdir(parents=True, exist_ok=True)
    GitOperations().sync_catalog_repository(openEuler_skills_path, OPENEULER_SKILLS_URL)
    return openEuler_skills_path


def normalize_dict_keys(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            str(key).strip(): normalize_dict_keys(value)
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [normalize_dict_keys(item) for item in data]
    return data


def load_crawler_config(repository_path: Path | None = None) -> dict[str, Any]:
    """Load crawler URLs from an openEuler-skills catalog repository.

    A directory is treated as an openEuler-skills checkout. Each
    ``community/<sig>/skill.yaml``, ``enterprise/<company>/skill.yaml`` and
    ``personal/<person>/skill.yaml`` contributes its ``skill_repos`` entries.
    YAML files are not accepted as a source.
    """
    path = (repository_path or sync_openEuler_skills_repo()).expanduser()
    if not path.is_dir():
        raise ValueError(f"Catalog path must be a repository directory: {path}")

    result: dict[str, Any] = {"community": [], "enterprise": [], "personal": []}
    for category in result:
        root = path / category
        if not root.is_dir():
            continue
        for skill_file in sorted(root.glob("*/skill.yaml")):
            with skill_file.open("r", encoding="utf-8") as fh:
                entry = yaml.safe_load(fh) or {}
            repos = entry.get("skill_repos", []) if isinstance(entry, dict) else []
            if isinstance(repos, list):
                owner_name = skill_file.parent.name
                for repo in repos:
                    if not isinstance(repo, dict):
                        result[category].append(repo)
                        continue
                    enriched = dict(repo)
                    if category == "community":
                        enriched.setdefault("sig_name", owner_name)
                    result[category].append(enriched)
    normalized = normalize_dict_keys(result)
    if not isinstance(normalized, dict):
        raise ValueError(f"Invalid config format in {path}")
    return normalized


def load_skill_categories(repository_path: Path | None = None) -> list[str]:
    """Read category names from ``templates/skill-spec.yaml`` in the catalog."""
    repo = repository_path or sync_openEuler_skills_repo()
    spec_path = repo.expanduser() / "templates" / "skill-spec.yaml"
    if not spec_path.exists():
        raise FileNotFoundError(f"Skill spec not found: {spec_path}")
    with spec_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    categories = data.get("categories", []) if isinstance(data, dict) else []
    return [str(item).strip() for item in categories if str(item).strip()] if isinstance(categories, list) else []
