from collections import defaultdict

from sqlalchemy import func, select, text, String, cast, column
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
        def concat_fields(*args):
            return func.concat(*args)

        search_text = concat_fields(
            Skill.name, " ",
            func.coalesce(Skill.description, ""), " ",
            func.coalesce(Skill.content, "")
        )

        base_query = select(
            Skill,
            func.ts_rank(
                func.to_tsvector("zhcfg", search_text),
                func.plainto_tsquery("zhcfg", query)
            ).label("rank")
        )

        ts_query = func.plainto_tsquery("zhcfg", query)
        base_query = base_query.where(
            (func.to_tsvector("zhcfg", search_text).op("@@")(ts_query)) |
            (Skill.name.ilike(f"%{query}%")) |
            (Skill.description.ilike(f"%{query}%"))
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
        min_similarity: float = 0.47,
    ) -> dict[str, Any]:
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        where_clauses = ["embedding IS NOT NULL"]
        params = {"limit": limit, "offset": offset}

        if category:
            where_clauses.append("category = :category")
            params["category"] = category
        if platform:
            where_clauses.append("platform = :platform")
            params["platform"] = platform
        if tags:
            where_clauses.append("tags @> :tags")
            params["tags"] = tags

        where_sql = " AND ".join(where_clauses)

        sql = text(f"""
            SELECT id, skill_id, name, description, version, commit_id, author, source,
                   source_url, category, tags, platform, extra_metadata, content,
                   security_score, download_count, rating, created_at, updated_at,
                   l2_distance(embedding::vector, '{embedding_str}'::vector) AS distance
            FROM skills
            WHERE {where_sql}
            ORDER BY distance ASC
            LIMIT :limit OFFSET :offset
        """)

        result = await self.session.execute(sql, params)
        rows = result.fetchall()

        results = []
        for row in rows:
            similarity = 1 / (1 + float(row.distance)) if row.distance else None
            if similarity and similarity < min_similarity:
                continue
            results.append({
                "id": str(row.id),
                "skill_id": row.skill_id,
                "name": row.name,
                "description": row.description,
                "version": row.version,
                "author": row.author,
                "source": row.source,
                "source_url": row.source_url,
                "category": row.category,
                "tags": row.tags or [],
                "platform": row.platform,
                "security_score": row.security_score,
                "download_count": row.download_count,
                "rating": row.rating,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "distance": float(row.distance) if row.distance else None,
                "similarity": similarity,
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

        agent_search_text = func.concat(
            Agent.name, " ",
            func.coalesce(Agent.description, "")
        )

        search_query = select(
            Agent,
            func.ts_rank(
                func.to_tsvector("zhcfg", agent_search_text),
                func.plainto_tsquery("zhcfg", query)
            ).label("rank")
        )

        ts_query = func.plainto_tsquery("zhcfg", query)
        search_query = search_query.where(
            func.to_tsvector("zhcfg", agent_search_text).op("@@")(ts_query)
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
