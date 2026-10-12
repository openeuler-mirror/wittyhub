from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

from skillcrawler.core.git_operations import GitOperations

OPENEULER_SKILLS_URL = "https://gitcode.com/openeuler/openEuler-skills"

logger = logging.getLogger(__name__)


def sync_openEuler_skills_repo() -> Path:
    """Return the local openEuler-skills checkout, cloning it when absent."""
    from src.core.config import get_settings
    local_path = Path(get_settings().storage.local_path) / "skill-repositories" / "openEuler-skills"
    openEuler_skills_path = local_path.expanduser()
    openEuler_skills_path.parent.mkdir(parents=True, exist_ok=True)
    GitOperations().sync_catalog_repository(openEuler_skills_path, OPENEULER_SKILLS_URL)
    return openEuler_skills_path


def _iter_catalog_entries(path: Path) -> Iterator[tuple[str, str, dict[str, Any]]]:
    """Single-pass walk over the catalog, yielding ``(platform, owner, entry)``.

    ``platform`` is one of ``community`` / ``enterprise`` / ``personal`` and
    ``owner`` the directory name under it. Malformed YAML files are skipped
    with a warning instead of aborting the whole read.
    """
    for platform in ("community", "enterprise", "personal"):
        root = path / platform
        if not root.is_dir():
            continue
        for skill_file in sorted(root.glob("*/skill.yaml")):
            try:
                with skill_file.open("r", encoding="utf-8") as fh:
                    entry = yaml.safe_load(fh) or {}
            except yaml.YAMLError as exc:
                logger.warning("Skip malformed catalog file %s: %s", skill_file, exc)
                continue
            if isinstance(entry, dict):
                yield platform, skill_file.parent.name, entry


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
    for platform, owner, entry in _iter_catalog_entries(path):
        repos = entry.get("skill_repos", [])
        if not isinstance(repos, list):
            continue
        for repo in repos:
            if not isinstance(repo, dict):
                result[platform].append(repo)
                continue
            enriched = dict(repo)
            if platform == "community":
                enriched.setdefault("sig_name", owner)
            result[platform].append(enriched)
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


def _first_repo_url(entry: dict[str, Any]) -> str | None:
    """First registered git URL: skill_repos[].url, else skills[].skill_url prefix."""
    repos = entry.get("skill_repos")
    if isinstance(repos, list):
        for repo in repos:
            if isinstance(repo, dict) and isinstance(repo.get("url"), str) and repo["url"].strip():
                return repo["url"].strip()
    skills = entry.get("skills")
    if isinstance(skills, list):
        for skill in skills:
            if not isinstance(skill, dict):
                continue
            skill_url = skill.get("skill_url")
            if isinstance(skill_url, str) and skill_url.strip():
                # <host>/<owner>/<repo>/blob/<ref>/<path>/SKILL.md -> repo URL
                return skill_url.split("/blob/", 1)[0].strip()
    return None


def _extract_contributor_profile(platform: str, entry: dict[str, Any]) -> dict[str, Any]:
    """Extract contributor profile fields per platform template spec.

    git_profile 是代码托管平台主页（git_profile）；
    website是官网地址（community 的 SIG 页面 / 企业官网 / 个人网站）。

    community  (templates/community-skill-spec.yaml):  author /
               description / website（均为一级字段；无 git 主页字段）
    enterprise (templates/enterprise-skill-spec.yaml): organization /
               display_name / git_profile / website / description /
               public_email / location（均为一级字段）
    personal   (templates/personal-skill-spec.yaml):   author /
               description / git_profile / website（均为一级字段）
    """
    if platform == "community":
        return {
            "name": entry.get("author"),
            "description": entry.get("description"),
            "git_profile": None,
            "website": entry.get("website"),
        }
    if platform == "enterprise":
        return {
            "name": entry.get("display_name"),
            "description": entry.get("description"),
            "git_profile": entry.get("git_profile"),
            "website": entry.get("website"),
        }
    if platform == "personal":
        return {
            "name": entry.get("author"),
            "description": entry.get("description"),
            "git_profile": entry.get("git_profile"),
            "website": entry.get("website"),
        }
    return {"name": None, "description": None, "git_profile": None, "website": None}


def _clean_optional_str(value: Any) -> str | None:
    """Normalize yaml "null"/empty values to None."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def load_contributor_profiles(repository_path: Path | None = None) -> list[dict[str, Any]]:
    """Read contributor profiles from the openEuler-skills catalog.

    Walks ``community/<sig>/``, ``enterprise/<org>/`` and ``personal/<author>/``
    ``skill.yaml`` files and returns one profile dict per directory:
    ``source`` (git host derived from the first registered repo URL),
    ``author`` (catalog identity; the ``organization`` field for enterprise,
    the directory name otherwise), ``platform``,
    ``name`` / ``description`` / ``git_profile`` (git hosting profile) /
    ``website`` (official site) and ``repo_url`` (first registered repo URL).
    """
    from skillcrawler.core.skill_parser import derive_skill_source

    path = (repository_path or sync_openEuler_skills_repo()).expanduser()
    profiles: list[dict[str, Any]] = []
    for platform, owner, entry in _iter_catalog_entries(path):
        if platform == "enterprise":
            author = _clean_optional_str(entry.get("organization")) or owner
        else:
            author = owner
        repo_url = _first_repo_url(entry)
        source = None
        if repo_url:
            try:
                source, _ = derive_skill_source(repo_url)
            except ValueError:
                source = None
        profile = _extract_contributor_profile(platform, entry)
        profiles.append(
            {
                "source": source,
                "author": author,
                "platform": platform,
                "name": _clean_optional_str(profile["name"]),
                "description": _clean_optional_str(profile["description"]),
                "git_profile": _clean_optional_str(profile["git_profile"]),
                "website": _clean_optional_str(profile["website"]),
                "repo_url": repo_url,
            }
        )
    return profiles
