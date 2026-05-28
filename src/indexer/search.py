from collections import defaultdict

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from src.api.models.models import Skill


def reciprocal_rank_fusion(*ranked_lists: list[dict], k: int = 60) -> list[dict]:
    """
    合并多个排序列表，使用 RRF 算法
    """
    scores = defaultdict(float)
    item_map = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list):
            item_id = item.get("id") or item.get("skill_id")
            if item_id:
                scores[item_id] += 1 / (rank + k)
                item_map[item_id] = item

    return [
        item_map[item_id]
        for item_id, _ in sorted(scores.items(), key=lambda x: -x[1])
    ]


class SearchService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search_skills(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        category: str | None = None,
        platform: str | None = None,
        tags: list[str] | None = None,
        embedding: list[float] | None = None,
        mode: str = "hybrid",
    ) -> dict[str, Any]:
        text_results = await self._text_search(
            query=query,
            limit=limit * 2,
            offset=0,
            category=category,
            platform=platform,
            tags=tags,
        )

        if embedding and mode == "hybrid":
            vector_results = await self._vector_search(
                embedding=embedding,
                limit=limit * 2,
                offset=0,
                category=category,
                platform=platform,
                tags=tags,
            )
            combined = reciprocal_rank_fusion(
                text_results.get("results", []),
                vector_results.get("results", []),
            )
            return {
                "results": combined[offset:offset + limit],
                "total": len(combined),
                "query": query,
                "skip": offset,
                "limit": limit,
                "mode": "hybrid",
            }
        elif embedding and mode == "semantic":
            return await self._vector_search(
                embedding=embedding,
                limit=limit,
                offset=offset,
                category=category,
                platform=platform,
                tags=tags,
            )
        else:
            return {
                "results": text_results["results"][offset:offset + limit],
                "total": text_results["total"],
                "query": query,
                "skip": offset,
                "limit": limit,
                "mode": "text",
            }

    async def _text_search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        category: str | None = None,
        platform: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        base_query = select(
            Skill,
            func.ts_rank(
                func.to_tsvector(
                    "zhcfg",
                    Skill.name || " " || func.coalesce(Skill.description, "") || " " || func.coalesce(Skill.content, "")
                ),
                func.plainto_tsquery("zhcfg", query)
            ).label("rank")
        )

        ts_query = func.plainto_tsquery("zhcfg", query)
        base_query = base_query.where(
            func.to_tsvector(
                "zhcfg",
                Skill.name || " " || func.coalesce(Skill.description, "") || " " || func.coalesce(Skill.content, "")
            ).op("@@")(ts_query)
        )

        if category:
            base_query = base_query.where(Skill.category == category)
        if platform:
            base_query = base_query.where(Skill.platform == platform)
        if tags:
            base_query = base_query.where(Skill.tags.contains(tags))

        count_query = select(func.count()).select_from(
            base_query.subquery()
        )
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        base_query = base_query.order_by(text("rank desc"), Skill.download_count.desc())
        base_query = base_query.offset(offset).limit(limit)

        result = await self.session.execute(base_query)
        rows = result.all()

        results = []
        for skill, rank in rows:
            results.append({
                "id": str(skill.id),
                "skill_id": skill.skill_id,
                "name": skill.name,
                "description": skill.description,
                "version": skill.version,
                "author": skill.author,
                "source": skill.source,
                "source_url": skill.source_url,
                "category": skill.category,
                "tags": skill.tags or [],
                "platform": skill.platform,
                "security_score": skill.security_score,
                "download_count": skill.download_count,
                "rating": skill.rating,
                "created_at": skill.created_at.isoformat() if skill.created_at else None,
                "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
                "text_rank": float(rank) if rank else 0,
            })

        return {"results": results, "total": total}

    async def _vector_search(
        self,
        embedding: list[float],
        limit: int = 20,
        offset: int = 0,
        category: str | None = None,
        platform: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        base_query = select(
            Skill,
            (func.vec_l2_distance(Skill.embedding, embedding)).label("distance")
        )

        base_query = base_query.where(Skill.embedding.isnot(None))

        if category:
            base_query = base_query.where(Skill.category == category)
        if platform:
            base_query = base_query.where(Skill.platform == platform)
        if tags:
            base_query = base_query.where(Skill.tags.contains(tags))

        base_query = base_query.order_by(text("distance asc"))
        base_query = base_query.offset(offset).limit(limit)

        result = await self.session.execute(base_query)
        rows = result.all()

        results = []
        for skill, distance in rows:
            results.append({
                "id": str(skill.id),
                "skill_id": skill.skill_id,
                "name": skill.name,
                "description": skill.description,
                "version": skill.version,
                "author": skill.author,
                "source": skill.source,
                "source_url": skill.source_url,
                "category": skill.category,
                "tags": skill.tags or [],
                "platform": skill.platform,
                "security_score": skill.security_score,
                "download_count": skill.download_count,
                "rating": skill.rating,
                "created_at": skill.created_at.isoformat() if skill.created_at else None,
                "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
                "distance": float(distance) if distance else None,
                "similarity": 1 / (1 + float(distance)) if distance else None,
            })

        return {"results": results, "total": len(results), "mode": "semantic"}

    async def search_agents(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        category: str | None = None,
    ) -> dict[str, Any]:
        from src.api.models.models import Agent

        search_query = select(
            Agent,
            func.ts_rank(
                func.to_tsvector("zhcfg", Agent.name || " " || func.coalesce(Agent.description, "")),
                func.plainto_tsquery("zhcfg", query)
            ).label("rank")
        )

        ts_query = func.plainto_tsquery("zhcfg", query)
        search_query = search_query.where(
            func.to_tsvector("zhcfg", Agent.name || " " || func.coalesce(Agent.description, "")).op("@@")(ts_query)
        )

        if category:
            search_query = search_query.where(Agent.category == category)

        search_query = search_query.order_by(text("rank desc"), Agent.download_count.desc())
        search_query = search_query.offset(offset).limit(limit)

        result = await self.session.execute(search_query)
        rows = result.all()

        results = []
        for agent, rank in rows:
            results.append({
                "id": str(agent.id),
                "agent_id": agent.agent_id,
                "name": agent.name,
                "description": agent.description,
                "author": agent.author,
                "source": agent.source,
                "source_url": agent.source_url,
                "category": agent.category,
                "tags": agent.tags or [],
                "platform": agent.platform,
                "security_score": agent.security_score,
                "download_count": agent.download_count,
                "rating": agent.rating,
                "created_at": agent.created_at.isoformat() if agent.created_at else None,
                "rank": float(rank) if rank else 0,
            })

        return {
            "results": results,
            "total": len(results),
            "query": query,
            "skip": offset,
            "limit": limit,
        }


_search_service: SearchService | None = None


def get_search_service(session: AsyncSession) -> SearchService:
    return SearchService(session)
