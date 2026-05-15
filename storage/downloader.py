import asyncio
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import aiofiles
import httpx

from core.config import get_settings

settings = get_settings()


class DownloadManager:
    def __init__(self):
        self.storage_path = Path(settings.storage.local_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.github_token = settings.storage.github_token

    async def get_download_url(self, source: str, source_url: str) -> str:
        if source == "github":
            return self._format_github_download_url(source_url)
        elif source == "gitcode":
            return self._format_gitcode_download_url(source_url)
        else:
            return source_url

    def _format_github_download_url(self, source_url: str) -> str:
        match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/tree/[^/]+/([^)]+))?", source_url)
        if match:
            owner, repo, path = match.groups()
            if path:
                return f"https://raw.githubusercontent.com/{owner}/{repo}/main/{path}"
            return f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
        return source_url

    def _format_gitcode_download_url(self, source_url: str) -> str:
        return source_url.replace("gitcode.com", "gitcode.com")

    async def download_to_local(
        self, source: str, source_url: str, skill_id: str
    ) -> Path:
        download_url = await self.get_download_url(source, source_url)
        local_path = self.storage_path / f"{skill_id}"

        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(download_url, headers=headers)
            response.raise_for_status()

            local_path.mkdir(parents=True, exist_ok=True)

            if source == "github" and "/archive/" in download_url:
                file_path = local_path / "archive.zip"
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(response.content)
                return file_path

            return local_path

    async def get_file_content(self, source: str, source_url: str) -> str:
        download_url = await self.get_download_url(source, source_url)

        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(download_url, headers=headers)
            response.raise_for_status()
            return response.text


class LocalStorage:
    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path or Path(settings.storage.local_path)

    async def save(self, skill_id: str, content: bytes | str, filename: str | None = None) -> Path:
        skill_dir = self.base_path / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)

        if filename:
            file_path = skill_dir / filename
        else:
            file_path = skill_dir / "skill_data"

        mode = "wb" if isinstance(content, bytes) else "w"
        async with aiofiles.open(file_path, mode) as f:
            await f.write(content)

        return file_path

    async def read(self, skill_id: str, filename: str) -> bytes | str | None:
        file_path = self.base_path / skill_id / filename

        if not file_path.exists():
            return None

        mode = "rb" if file_path.suffix in [".zip", ".tar", ".gz"] else "r"
        async with aiofiles.open(file_path, mode) as f:
            return await f.read()

    async def delete(self, skill_id: str) -> bool:
        import shutil
        skill_dir = self.base_path / skill_id

        if skill_dir.exists():
            shutil.rmtree(skill_dir)
            return True
        return False

    async def list_files(self, skill_id: str) -> list[str]:
        skill_dir = self.base_path / skill_id

        if not skill_dir.exists():
            return []

        return [f.name for f in skill_dir.iterdir()]
