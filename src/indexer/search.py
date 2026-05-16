import meilisearch
from typing import Any

from src.core.config import get_settings

settings = get_settings()


class SearchClient:
    def __init__(self):
        self.client = meilisearch.Client(
            settings.meilisearch.host,
            settings.meilisearch.api_key or None,
        )
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        try:
            self.client.create_index("skills", {"primaryKey": "id"})
        except meilisearch.errors.MeilisearchApiError:
            try:
                self.client.update_index("skills", {"primaryKey": "id"})
            except Exception:
                pass

        try:
            self.client.create_index("agents", {"primaryKey": "id"})
        except meilisearch.errors.MeilisearchApiError:
            try:
                self.client.update_index("agents", {"primaryKey": "id"})
            except Exception:
                pass

        skill_index = self.client.index("skills")
        skill_index.update_searchable_attributes([
            "name",
            "description",
            "author",
            "category",
            "tags",
            "platform",
        ])
        skill_index.update_filterable_attributes([
            "category",
            "tags",
            "platform",
            "source",
        ])
        skill_index.update_sortable_attributes([
            "download_count",
            "rating",
            "created_at",
        ])

    def index_skill(self, skill_data: dict[str, Any]) -> dict[str, Any]:
        index = self.client.index("skills")
        return index.add_documents([skill_data])

    def index_skills(self, skills_data: list[dict[str, Any]]) -> dict[str, Any]:
        index = self.client.index("skills")
        return index.add_documents(skills_data)

    def delete_skill(self, skill_id: str) -> dict[str, Any]:
        index = self.client.index("skills")
        return index.delete_document(skill_id)

    def search_skills(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        index = self.client.index("skills")

        search_params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }

        if filters:
            filter_parts = []
            if category := filters.get("category"):
                filter_parts.append(f'category = "{category}"')
            if platform := filters.get("platform"):
                filter_parts.append(f'platform = "{platform}"')
            if tags := filters.get("tags"):
                for tag in tags:
                    filter_parts.append(f'tags = "{tag}"')
            if filter_parts:
                search_params["filter"] = " AND ".join(filter_parts)

        return index.search(query, search_params)

    def index_agent(self, agent_data: dict[str, Any]) -> dict[str, Any]:
        index = self.client.index("agents")
        return index.add_documents([agent_data])

    def delete_agent(self, agent_id: str) -> dict[str, Any]:
        index = self.client.index("agents")
        return index.delete_document(agent_id)

    def search_agents(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        index = self.client.index("agents")
        return index.search(query, {"limit": limit, "offset": offset})


_search_client: SearchClient | None = None


def get_search_client() -> SearchClient:
    global _search_client
    if _search_client is None:
        _search_client = SearchClient()
    return _search_client