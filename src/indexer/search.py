from collections import defaultdict
import re

from sqlalchemy import desc, func, literal_column, select, text, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from src.api.services.categories import category_label
from src.models.orm import Skill


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

    def _apply_skill_filters(
        self,
        query,
        *,
        category: list[str] | None = None,
        platform: str | None = None,
        tags: list[str] | None = None,
        security_level: list[str] | None = None,
    ):
        # 全局规则：排除未检测（risk_score 为空）的 Skill，不进入搜索
        query = query.where(Skill.risk_score.is_not(None))
        if category:
            conditions = []
            normal_cats = []
            for c in category:
                if c.lower() == "others":
                    conditions.append(
                        or_(
                            Skill.category.is_(None),
                            Skill.category == "",
                            func.lower(Skill.category).in_(["others", "other"]),
                        )
                    )
                else:
                    normal_cats.append(c)
            if normal_cats:
                conditions.append(Skill.category.in_(normal_cats))
            if conditions:
                query = query.where(or_(*conditions))
        if platform:
            platforms = [p for p in platform.split(",") if p] if isinstance(platform, str) else platform
            query = query.where(Skill.platform.in_(platforms))
        if tags:
            query = query.where(Skill.tags.contains(tags))
        if security_level:
            conditions = []
            for level in security_level:
                if level == "安全":
                    conditions.append(Skill.risk_score <= 20)
                elif level == "低风险":
                    conditions.append(Skill.risk_score.between(21, 50))
                elif level == "中风险":
                    conditions.append(Skill.risk_score.between(51, 80))
                elif level == "高风险":
                    conditions.append(Skill.risk_score >= 81)
            if conditions:
                query = query.where(or_(*conditions))
        return query

    def _item_version_sort_key(self, item: dict[str, Any]) -> tuple[int, tuple[int, ...], int, str, str, str]:
        version = str(item.get("version") or "").strip()
        if version.lower() == "latest":
            return (
                2,
                tuple(),
                0,
                "",
                str(item.get("updated_at") or ""),
                str(item.get("created_at") or ""),
            )
        match = re.fullmatch(
            r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-([0-9A-Za-z.-]+))?",
            version,
            flags=re.IGNORECASE,
        )
        if match:
            major = int(match.group(1) or 0)
            minor = int(match.group(2) or 0)
            patch = int(match.group(3) or 0)
            prerelease = (match.group(4) or "").lower()
            is_stable = 1 if not prerelease else 0
            return (
                1,
                (major, minor, patch),
                is_stable,
                prerelease,
                str(item.get("updated_at") or ""),
                str(item.get("created_at") or ""),
            )
        return (
            0,
            tuple(),
            0,
            "",
            str(item.get("updated_at") or ""),
            str(item.get("created_at") or ""),
        )

    def _dedupe_skill_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}

        for index, item in enumerate(results):
            dedupe_key = str(item.get("skill_id") or "").strip().lower()
            if not dedupe_key:
                continue

            existing = grouped.get(dedupe_key)
            if existing is None:
                grouped[dedupe_key] = {
                    "first_index": index,
                    "representative": item,
                }
                continue

            existing_item = existing["representative"]
            if self._item_version_sort_key(item) > self._item_version_sort_key(existing_item):
                existing["representative"] = item

        ordered = sorted(grouped.values(), key=lambda entry: entry["first_index"])
        return [entry["representative"] for entry in ordered]

    async def search_skills(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        category: list[str] | None = None,
        platform: str | None = None,
        tags: list[str] | None = None,
        security_level: list[str] | None = None,
        embedding: list[float] | None = None,
        mode: str = "hybrid",
        scope: str = "summary",
    ) -> dict[str, Any]:
        if embedding and mode == "semantic":
            return await self._vector_search(
                embedding=embedding,
                limit=limit,
                offset=offset,
                category=category,
                platform=platform,
                tags=tags,
                security_level=security_level,
            )

        is_hybrid = bool(embedding and mode == "hybrid")
        text_results = await self._text_search(
            query=query,
            limit=limit * 2 if is_hybrid else limit,
            offset=0 if is_hybrid else offset,
            category=category,
            platform=platform,
            tags=tags,
            scope=scope,
            security_level=security_level,
        )

        if is_hybrid:
            vector_results = await self._vector_search(
                embedding=embedding,
                limit=limit * 2,
                offset=0,
                category=category,
                platform=platform,
                tags=tags,
                security_level=security_level,
            )
            combined = reciprocal_rank_fusion(
                text_results.get("results", []),
                vector_results.get("results", []),
            )
            deduped = self._dedupe_skill_results(combined)
            return {
                "results": deduped[offset:offset + limit],
                "total": text_results["total"],
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
                security_level=security_level,
            )
        else:
            # _text_search 已在 SQL 层完成 limit/offset 分页（见上方 limit/offset 传参），
            # 这里不能再按 offset 二次切片，否则第 2 页（offset>0）会得到空列表。
            deduped = self._dedupe_skill_results(text_results["results"])
            return {
                "results": deduped,
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
        category: list[str] | None = None,
        platform: str | None = None,
        tags: list[str] | None = None,
        scope: str = "summary",
        security_level: list[str] | None = None,
    ) -> dict[str, Any]:
        # Keep these expressions in sync with migrations 009 and 010.
        # String concatenation (||) is immutable in PostgreSQL and can be indexed,
        # unlike concat(), which is only STABLE.
        search_text = (
            func.coalesce(Skill.name, "") + " "
            + func.coalesce(Skill.description, "")
        )
        if scope == "full":
            search_text = search_text + " " + func.coalesce(Skill.content, "")
        search_config = literal_column("'zhcfg'::regconfig")

        rank_expression = func.ts_rank(
            func.to_tsvector(search_config, search_text),
            func.plainto_tsquery(search_config, query),
        )

        ts_query = func.plainto_tsquery(search_config, query)
        search_predicate = (
            (func.to_tsvector(search_config, search_text).op("@@")(ts_query)) |
            (Skill.name.ilike(f"%{query}%")) |
            (Skill.description.ilike(f"%{query}%"))
        )
        # Select only fields returned by the API. Loading content, metadata,
        # and the 768-dimensional embedding for every candidate makes common
        # queries such as "code" unnecessarily expensive.
        base_query = select(
            Skill.id,
            Skill.skill_id,
            Skill.name,
            Skill.description,
            Skill.version,
            Skill.author,
            Skill.source,
            Skill.source_url,
            Skill.category,
            Skill.tags,
            Skill.platform,
            Skill.risk_score,
            Skill.download_count,
            Skill.rating,
            Skill.created_at,
            Skill.updated_at,
            rank_expression.label("rank"),
        ).where(search_predicate)

        base_query = self._apply_skill_filters(
            base_query,
            category=category,
            platform=platform,
            tags=tags,
            security_level=security_level,
        )

        # skills.skill_id is unique; DISTINCT adds sorting/hash work without
        # changing the result.
        count_query = select(func.count(Skill.id)).where(
            search_predicate
        )
        count_query = self._apply_skill_filters(
            count_query,
            category=category,
            platform=platform,
            tags=tags,
            security_level=security_level,
        )
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # skills.skill_id is unique, so fetch only the requested page. The old
        # 10x candidate overfetch loaded up to 240 rows for a 12-card page.
        candidate_query = (
            base_query
            .order_by(rank_expression.desc(), Skill.download_count.desc(), desc(Skill.updated_at), desc(Skill.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(candidate_query)
        rows = result.mappings().all()

        results = []
        for row in rows:
            results.append({
                "id": str(row["id"]),
                "skill_id": row["skill_id"],
                "name": row["name"],
                "description": row["description"],
                "version": row["version"],
                "author": row["author"],
                "source": row["source"],
                "source_url": row["source_url"],
                "category": row["category"],
                "category_label": category_label(row["category"]),
                "tags": row["tags"] or [],
                "platform": row["platform"],
                "risk_score": row["risk_score"],
                "download_count": row["download_count"],
                "rating": row["rating"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                "text_rank": float(row["rank"]) if row["rank"] else 0,
            })

        return {"results": results, "total": total}

    async def _vector_search(
        self,
        embedding: list[float],
        limit: int = 20,
        offset: int = 0,
        category: list[str] | None = None,
        platform: str | None = None,
        tags: list[str] | None = None,
        security_level: list[str] | None = None,
        min_similarity: float = 0.47,
    ) -> dict[str, Any]:
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        where_clauses = ["embedding IS NOT NULL", "risk_score IS NOT NULL"]
        params: dict[str, Any] = {"limit": limit, "offset": offset, "embedding": embedding_str}

        if category:
            placeholders = []
            for idx, c in enumerate(category):
                key = f"cat_{idx}"
                placeholders.append(f":{key}")
                params[key] = c
            where_clauses.append(f"category IN ({', '.join(placeholders)})")
        if platform:
            platforms = [p for p in platform.split(",") if p] if isinstance(platform, str) else [platform]
            placeholders = []
            for idx, p in enumerate(platforms):
                key = f"plat_{idx}"
                placeholders.append(f":{key}")
                params[key] = p
            where_clauses.append(f"platform IN ({', '.join(placeholders)})")
        if tags:
            where_clauses.append("tags @> :tags")
            params["tags"] = tags
        if security_level:
            sl_conditions = []
            for idx, level in enumerate(security_level):
                if level == "安全":
                    sl_conditions.append(f"risk_score <= :sl_{idx}")
                    params[f"sl_{idx}"] = 20
                elif level == "低风险":
                    sl_conditions.append(f"(risk_score >= :sl_low_{idx} AND risk_score <= :sl_high_{idx})")
                    params[f"sl_low_{idx}"] = 21
                    params[f"sl_high_{idx}"] = 50
                elif level == "中风险":
                    sl_conditions.append(f"(risk_score >= :sl_low_{idx} AND risk_score <= :sl_high_{idx})")
                    params[f"sl_low_{idx}"] = 51
                    params[f"sl_high_{idx}"] = 80
                elif level == "高风险":
                    sl_conditions.append(f"risk_score >= :sl_{idx}")
                    params[f"sl_{idx}"] = 81
            if sl_conditions:
                where_clauses.append("(" + " OR ".join(sl_conditions) + ")")

        where_sql = " AND ".join(where_clauses)

        sql = text(f"""
            SELECT id, skill_id, name, description, version, author, source,
                   source_url, category, tags, platform,
                   risk_score, download_count, rating, created_at, updated_at,
                   embedding <-> CAST(:embedding AS vector) AS distance
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
                "category_label": category_label(row.category),
                "tags": row.tags or [],
                "platform": row.platform,
                "risk_score": row.risk_score,
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
        from src.models.orm import Agent

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
                "risk_score": agent.risk_score,
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
