import httpx
from typing import Any

from core.config import get_settings

settings = get_settings()


class APIClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = base_url or f"http://{settings.app.host}:{settings.app.port}"
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def close(self) -> None:
        self.client.close()

    def list_skills(
        self,
        skip: int = 0,
        limit: int = 20,
        category: str | None = None,
        platform: str | None = None,
    ) -> dict[str, Any]:
        params = {"skip": skip, "limit": limit}
        if category:
            params["category"] = category
        if platform:
            params["platform"] = platform

        response = self.client.get(
            f"{self.base_url}/api/v1/skills/",
            headers=self._get_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()

    def get_skill(self, skill_id: str) -> dict[str, Any]:
        response = self.client.get(
            f"{self.base_url}/api/v1/skills/{skill_id}",
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.json()

    def create_skill(self, skill_data: dict[str, Any]) -> dict[str, Any]:
        response = self.client.post(
            f"{self.base_url}/api/v1/skills/",
            headers=self._get_headers(),
            json=skill_data,
        )
        response.raise_for_status()
        return response.json()

    def delete_skill(self, skill_id: str) -> dict[str, Any]:
        response = self.client.delete(
            f"{self.base_url}/api/v1/skills/{skill_id}",
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.json()

    def search_skills(
        self,
        query: str,
        skip: int = 0,
        limit: int = 20,
        category: str | None = None,
        platform: str | None = None,
    ) -> dict[str, Any]:
        params = {"q": query, "skip": skip, "limit": limit}
        if category:
            params["category"] = category
        if platform:
            params["platform"] = platform

        response = self.client.get(
            f"{self.base_url}/api/v1/index/search",
            headers=self._get_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()

    def download_skill(self, skill_id: str) -> dict[str, Any]:
        response = self.client.get(
            f"{self.base_url}/api/v1/skills/{skill_id}/download",
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.json()

    def audit_skill(self, skill_id: str) -> dict[str, Any]:
        response = self.client.get(
            f"{self.base_url}/api/v1/skills/{skill_id}/audit",
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.json()

    def reindex(self) -> dict[str, Any]:
        response = self.client.post(
            f"{self.base_url}/api/v1/index/reindex",
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.json()


class AsyncAPIClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = base_url or f"http://{settings.app.host}:{settings.app.port}"
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def close(self) -> None:
        await self.client.aclose()

    async def list_skills(
        self,
        skip: int = 0,
        limit: int = 20,
        category: str | None = None,
    ) -> dict[str, Any]:
        params = {"skip": skip, "limit": limit}
        if category:
            params["category"] = category

        response = await self.client.get(
            f"{self.base_url}/api/v1/skills/",
            headers=self._get_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()

    async def search_skills(
        self,
        query: str,
        skip: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        params = {"q": query, "skip": skip, "limit": limit}

        response = await self.client.get(
            f"{self.base_url}/api/v1/index/search",
            headers=self._get_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()
