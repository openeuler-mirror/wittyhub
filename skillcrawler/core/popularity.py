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

# Weights used to estimate a skill's download count from repository
# popularity metrics. Watchers typically mirror stars on GitHub, so its
# weight is kept low to avoid double-counting.
POPULARITY_DOWNLOAD_WEIGHTS = {"stars": 2.0, "forks": 1.0, "watchers": 0.5}


def estimate_download_count(stars: int, forks: int, watchers: int) -> int:
    """Estimate a skill's download count from repo popularity metrics."""
    estimated = (
        stars * POPULARITY_DOWNLOAD_WEIGHTS["stars"]
        + forks * POPULARITY_DOWNLOAD_WEIGHTS["forks"]
        + watchers * POPULARITY_DOWNLOAD_WEIGHTS["watchers"]
    )
    return int(round(estimated))


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

    def _parse_repo_list(self, config_path: Path | None) -> list[str]:
        """Extract unique repo URLs from the crawler config file."""
        from skillcrawler.config import load_crawler_config

        config = load_crawler_config(config_path)
        urls: list[str] = []
        seen: set[str] = set()
        for key in ("openeuler_repos", "personal_repos", "enterprise_repos"):
            for item in config.get(key, []) or []:
                url = item.get("url") if isinstance(item, dict) else None
                if isinstance(url, str) and url.strip() and url.strip() not in seen:
                    seen.add(url.strip())
                    urls.append(url.strip())
        return urls

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
        urls = self._parse_repo_list(config_path)
        if only:
            urls = [u for u in urls if self._source_for_url(u) == only]
        if not urls:
            return []

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_FETCHES)

        async def _fetch_one(repo_url: str) -> RepoPopularity:
            async with semaphore:
                source = self._source_for_url(repo_url)
                try:
                    return await self.fetcher.fetch(repo_url, source)
                except PopularityError as exc:
                    _logger.warning("Failed to collect popularity for %s: %s", repo_url, exc)
                    return RepoPopularity(url=repo_url, source=source)

        results = await asyncio.gather(*(_fetch_one(u) for u in urls))
        return list(results)
