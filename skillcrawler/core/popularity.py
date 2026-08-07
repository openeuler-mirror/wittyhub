"""Popularity collection: fetch star/fork/watcher counts for skill repos.

The collector reads the configured repo list (skills/skill-repos.yaml by
default) and queries each hosting platform's public REST API for repository
popularity metrics (stars, forks, watchers). Results are stored on the
``skill_repos`` table via :class:`SkillRepoRepository`.

Supported platforms:
- GitHub  : https://api.github.com/repos/{owner}/{repo}
- GitCode : https://api.gitcode.com/api/v5/repos/{owner}/{repo}
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from skillcrawler.core.skill_parser import derive_skill_source, extract_owner_repo
from src.core.config import get_settings

_logger = logging.getLogger(__name__)
settings = get_settings()

GITHUB_API_BASE = "https://api.github.com"
GITCODE_API_BASE = "https://api.gitcode.com/api/v5"

GITHUB_TIMEOUT_SECONDS = 20.0
GITCODE_TIMEOUT_SECONDS = 20.0

# Max concurrent API requests per collect run.
MAX_CONCURRENT_FETCHES = 5

# Retry with backoff when the platform rate-limits us (HTTP 429).
MAX_RATE_LIMIT_RETRIES = 2
RATE_LIMIT_RETRY_BASE_SECONDS = 30

# Download-conversion weights per repository type. Different repo types
# (openeuler community / enterprise / personal) convert popularity metrics
# into downloads at different rates: enterprise repos are trusted more,
# personal repos convert the least.
REPO_TYPE_WEIGHTS: dict[str, dict[str, float]] = {
    "enterprise": {"stars": 3.0, "forks": 1.5, "watchers": 1.0},
    "openeuler": {"stars": 2.0, "forks": 1.2, "watchers": 0.8},
    "personal": {"stars": 1.0, "forks": 0.5, "watchers": 0.3},
}
DEFAULT_REPO_TYPE = "openeuler"

# Relative popularity of each skill category. Skills in more popular
# categories get a larger share of the repository's total downloads.
CATEGORY_WEIGHTS: dict[str, float] = {
    "AI": 1.8,
    "Security": 1.6,
    "Data": 1.5,
    "Frontend": 1.3,
    "Backend": 1.3,
    "Database": 1.3,
    "DevOps": 1.2,
    "Cloud": 1.2,
    "Mobile": 1.1,
    "Design": 1.0,
    "Networking": 1.0,
    "others": 1.0,
}
DEFAULT_CATEGORY = "others"

# Risk penalty: skills with higher risk scores are downloaded less.
RISK_WEIGHT_MIN = 0.4
RISK_WEIGHT_MAX = 1.0


def repo_type_weights(repo_type: str) -> dict[str, float]:
    """Return download weights for a repository type (fallback to default)."""
    return REPO_TYPE_WEIGHTS.get(repo_type, REPO_TYPE_WEIGHTS[DEFAULT_REPO_TYPE])


def estimate_repo_downloads(
    stars: int,
    forks: int,
    watchers: int,
    repo_type: str,
) -> int:
    """Estimate total downloads for a repository from its popularity metrics."""
    weights = repo_type_weights(repo_type)
    estimated = (
        stars * weights["stars"]
        + forks * weights["forks"]
        + watchers * weights["watchers"]
    )
    return int(round(estimated))


def category_weight(category: str | None) -> float:
    return CATEGORY_WEIGHTS.get(category, CATEGORY_WEIGHTS[DEFAULT_CATEGORY])


def risk_weight(risk_score: int | None) -> float:
    """Lower risk scores convert to more downloads."""
    if risk_score is None:
        return RISK_WEIGHT_MAX
    # risk_score is roughly 0..100; scale linearly into [MIN, MAX].
    return max(RISK_WEIGHT_MIN, RISK_WEIGHT_MAX - (risk_score / 100.0) * (RISK_WEIGHT_MAX - RISK_WEIGHT_MIN))


def allocate_skill_downloads(
    repo_total_downloads: int,
    skills: list[Any],
) -> dict[str, int]:
    """Distribute a repository's total downloads across its skills.

    Each skill gets a share proportional to ``category_weight * risk_weight``
    so that more popular categories and lower-risk skills receive more
    downloads. Returns a mapping of skill_id -> download_count.
    """
    if not skills:
        return {}

    weights: dict[str, float] = {}
    for skill in skills:
        skill_id = getattr(skill, "skill_id", None)
        if not skill_id:
            continue
        weights[skill_id] = category_weight(getattr(skill, "category", None)) * risk_weight(
            getattr(skill, "risk_score", None)
        )

    total_weight = sum(weights.values()) or 1.0
    allocations: dict[str, int] = {}
    remaining = repo_total_downloads
    items = list(weights.items())

    for index, (skill_id, weight) in enumerate(items):
        # Largest remainder method keeps the sum exact across allocations.
        if index == len(items) - 1:
            allocations[skill_id] = remaining
        else:
            allocation = int(repo_total_downloads * weight / total_weight)
            allocations[skill_id] = allocation
            remaining -= allocation
    return allocations


class PopularityError(Exception):
    """Raised when a repository's popularity cannot be fetched."""


@dataclass(slots=True)
class RepoPopularity:
    """Popularity metrics for a single repository."""

    url: str
    source: str
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    repo_type: str = DEFAULT_REPO_TYPE


def _int_value(data: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = data.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return 0


class PopularityFetcher:
    """Fetches popularity metrics from GitHub / GitCode public APIs."""

    def __init__(self) -> None:
        self.github_token = settings.crawler.github_token or None
        self.gitcode_token = settings.crawler.gitcode_token or None

    def _github_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "wittyhub-popularity-collector",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    def _gitcode_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "wittyhub-popularity-collector",
        }
        if self.gitcode_token:
            headers["PRIVATE-TOKEN"] = self.gitcode_token
        return headers

    async def fetch(self, repo_url: str, source: str) -> RepoPopularity:
        """Fetch popularity for one repository URL."""
        if source == "github":
            return await self._fetch_github(repo_url)
        if source == "gitcode":
            return await self._fetch_gitcode(repo_url)
        raise PopularityError(f"Unsupported popularity source: {source}")

    async def _fetch_github(self, repo_url: str) -> RepoPopularity:
        owner_repo = extract_owner_repo(repo_url)
        url = f"{GITHUB_API_BASE}/repos/{owner_repo}"
        try:
            async with httpx.AsyncClient(
                timeout=GITHUB_TIMEOUT_SECONDS,
                headers=self._github_headers(),
            ) as client:
                resp = await client.get(url)
        except httpx.RequestError as exc:
            raise PopularityError(f"GitHub API request failed: {exc}") from exc

        if resp.status_code == 404:
            raise PopularityError(f"GitHub repo not found: {owner_repo}")
        if resp.status_code == 429:
            raise PopularityError(
                f"GitHub API rate-limited (429) for {owner_repo}; "
                "configure crawler.github_token to raise the limit"
            )
        if resp.status_code != 200:
            raise PopularityError(
                f"GitHub API returned {resp.status_code}: {resp.text[:200]}"
            )

        data = resp.json()
        return RepoPopularity(
            url=repo_url,
            source="github",
            stars=_int_value(data, "stargazers_count", "stars_count"),
            forks=_int_value(data, "forks_count"),
            watchers=_int_value(data, "watchers_count"),
        )

    async def _fetch_gitcode(self, repo_url: str) -> RepoPopularity:
        owner_repo = extract_owner_repo(repo_url)
        url = f"{GITCODE_API_BASE}/repos/{owner_repo}"
        try:
            async with httpx.AsyncClient(
                timeout=GITCODE_TIMEOUT_SECONDS,
                headers=self._gitcode_headers(),
            ) as client:
                resp = await client.get(url)
        except httpx.RequestError as exc:
            raise PopularityError(f"GitCode API request failed: {exc}") from exc

        if resp.status_code == 404:
            raise PopularityError(f"GitCode repo not found: {owner_repo}")
        if resp.status_code != 200:
            raise PopularityError(
                f"GitCode API returned {resp.status_code}: {resp.text[:200]}"
            )

        data = resp.json()
        return RepoPopularity(
            url=repo_url,
            source="gitcode",
            stars=_int_value(data, "star_count", "stargazers_count"),
            forks=_int_value(data, "forks_count"),
            watchers=_int_value(data, "watch_count", "watchers_count"),
        )


class PopularityCollector:
    """Collects popularity for all repositories in the configured repo list."""

    def __init__(self, fetcher: PopularityFetcher | None = None) -> None:
        self.fetcher = fetcher or PopularityFetcher()

    def _parse_repo_list(self, config_path: Path | None) -> list[tuple[str, str]]:
        """Extract (repo_url, repo_type) pairs from the crawler config file.

        The repo type is derived from the config section the URL appears in:
        ``openeuler_repos`` -> "openeuler", ``enterprise_repos`` -> "enterprise",
        ``personal_repos`` -> "personal".
        """
        from skillcrawler.config import load_crawler_config

        config = load_crawler_config(config_path)
        repos: list[tuple[str, str]] = []
        seen: set[str] = set()
        for key in ("openeuler_repos", "personal_repos", "enterprise_repos"):
            repo_type = key.removesuffix("_repos")
            for item in config.get(key, []) or []:
                url = item.get("url") if isinstance(item, dict) else None
                if isinstance(url, str) and url.strip() and url.strip() not in seen:
                    seen.add(url.strip())
                    repos.append((url.strip(), repo_type))
        return repos

    @staticmethod
    def _source_for_url(repo_url: str) -> str:
        parsed = urlparse(repo_url.strip())
        host = parsed.netloc.lower()
        if host == "github.com":
            return "github"
        if host == "gitcode.com":
            return "gitcode"
        try:
            source, _ = derive_skill_source(repo_url)
            return source
        except ValueError:
            raise PopularityError(f"Cannot determine source for URL: {repo_url}")

    async def collect(
        self,
        config_path: Path | None = None,
        *,
        only: str | None = None,
    ) -> list[RepoPopularity]:
        """Collect popularity for configured repos, with bounded concurrency."""
        repos = self._parse_repo_list(config_path)
        if only:
            repos = [(url, repo_type) for url, repo_type in repos if self._source_for_url(url) == only]
        if not repos:
            return []

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_FETCHES)

        async def _fetch_one(repo_url: str, repo_type: str) -> RepoPopularity:
            async with semaphore:
                source = self._source_for_url(repo_url)
                try:
                    result = await self.fetcher.fetch(repo_url, source)
                    result.repo_type = repo_type
                    return result
                except PopularityError as exc:
                    _logger.warning("Failed to collect popularity for %s: %s", repo_url, exc)
                    return RepoPopularity(url=repo_url, source=source, repo_type=repo_type)

        results = await asyncio.gather(*(_fetch_one(url, repo_type) for url, repo_type in repos))
        return list(results)
