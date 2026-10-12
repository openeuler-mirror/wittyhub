from collections import defaultdict
from datetime import datetime, timedelta, timezone
import re

from sqlalchemy import desc, func, literal_column, select, text, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from src.api.services.categories import category_label
from src.models.orm import DownloadHistory, Skill


# Hybrid search ranks a stable, bounded candidate pool so total and pagination
# do not change as the caller moves between pages.
HYBRID_CANDIDATE_LIMIT = 200


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
        translated_query: str | None = None,
        translated_embedding: list[float] | None = None,
        sort_by: str = "relevance",
        sort_period: str | None = None,
    ) -> dict[str, Any]:
        # 显式排序（热门/最新）时先取无分页候选集，再统一排序分页；
        # 默认 relevance 保持各模式现有相关度排序与分页行为不变。
        has_sort = sort_by in ("updated_at", "download_count")

        if embedding and mode == "semantic":
            vector_results = await self._vector_search(
                embedding=embedding,
                limit=HYBRID_CANDIDATE_LIMIT if has_sort else limit,
                offset=0 if has_sort else offset,
                category=category,
                platform=platform,
                tags=tags,
                security_level=security_level,
            )
            if not has_sort:
                return vector_results
            return await self._sorted_search_response(
                vector_results.get("results", []),
                query=query, mode="semantic", offset=offset, limit=limit,
                sort_by=sort_by, sort_period=sort_period,
            )

        is_hybrid = bool(embedding and mode == "hybrid")
        text_results = await self._text_search(
            query=query,
            limit=HYBRID_CANDIDATE_LIMIT if (is_hybrid or has_sort) else limit,
            offset=0 if (is_hybrid or has_sort) else offset,
            category=category,
            platform=platform,
            tags=tags,
            scope=scope,
            security_level=security_level,
        )

        if is_hybrid:
            vector_results = await self._vector_search(
                embedding=embedding,
                limit=HYBRID_CANDIDATE_LIMIT,
                offset=0,
                category=category,
                platform=platform,
                tags=tags,
                security_level=security_level,
            )
            ranked_lists = [text_results.get("results", []), vector_results.get("results", [])]
            if translated_query:
                translated_text = await self._text_search(
                    query=translated_query, limit=HYBRID_CANDIDATE_LIMIT,
                    category=category, platform=platform, tags=tags,
                    scope=scope, security_level=security_level,
                )
                ranked_lists.append(translated_text.get("results", []))
            if translated_embedding:
                translated_vector = await self._vector_search(
                    embedding=translated_embedding, limit=HYBRID_CANDIDATE_LIMIT,
                    offset=0, category=category, platform=platform, tags=tags,
                    security_level=security_level,
                )
                ranked_lists.append(translated_vector.get("results", []))
            combined = reciprocal_rank_fusion(*ranked_lists)
            deduped = self._dedupe_skill_results(combined)
            if has_sort:
                return await self._sorted_search_response(
                    deduped,
                    query=query, mode="hybrid", offset=offset, limit=limit,
                    sort_by=sort_by, sort_period=sort_period,
                )
            return {
                "results": deduped[offset:offset + limit],
                "total": len(deduped),
                "query": query,
                "skip": offset,
                "limit": limit,
                "mode": "hybrid",
            }
        elif has_sort:
            # 纯文本模式 + 显式排序：候选集为无分页取回的相关度 Top N
            deduped = self._dedupe_skill_results(text_results["results"])
            return await self._sorted_search_response(
                deduped,
                query=query, mode="text", offset=offset, limit=limit,
                sort_by=sort_by, sort_period=sort_period,
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

    async def _sorted_search_response(
        self,
        candidates: list[dict[str, Any]],
        *,
        query: str,
        mode: str,
        offset: int,
        limit: int,
        sort_by: str,
        sort_period: str | None,
    ) -> dict[str, Any]:
        """在搜索候选集内应用显式排序，语义与列表端点一致。

        - 热门-本周/本月：inner join download_history 周期聚合，仅保留周期内
          有下载的结果并按周期下载量排序（total 同口径）；结果附 period_downloads。
        - 其他排序：直接按候选字段排序，total 为候选总数。
        """
        if sort_period in ("week", "month"):
            ordered, total = await self._order_candidates_by_period(candidates, sort_period)
        else:
            ordered = self._sort_candidates(candidates, sort_by)
            total = len(ordered)
        return {
            "results": ordered[offset:offset + limit],
            "total": total,
            "query": query,
            "skip": offset,
            "limit": limit,
            "mode": mode,
        }

    @staticmethod
    def _sort_candidates(
        candidates: list[dict[str, Any]], sort_by: str
    ) -> list[dict[str, Any]]:
        if sort_by == "download_count":
            return sorted(
                candidates,
                key=lambda c: (
                    c.get("download_count") or 0,
                    c.get("updated_at") or "",
                    c.get("created_at") or "",
                ),
                reverse=True,
            )
        return sorted(
            candidates,
            key=lambda c: (c.get("updated_at") or "", c.get("created_at") or ""),
            reverse=True,
        )

    async def _order_candidates_by_period(
        self, candidates: list[dict[str, Any]], sort_period: str
    ) -> tuple[list[dict[str, Any]], int]:
        # cutoff 口径与 SkillRepository.list 一致（UTC 周一 00:00 / 月初 00:00）
        now = datetime.now(timezone.utc)
        if sort_period == "week":
            cutoff = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            cutoff = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        dl_subquery = (
            select(
                DownloadHistory.resource_id,
                func.count(DownloadHistory.id).label("period_downloads"),
            )
            .where(DownloadHistory.resource_type == "skill")
            .where(DownloadHistory.downloaded_at >= cutoff)
            .group_by(DownloadHistory.resource_id)
            .subquery()
        )
        id_list = [c["id"] for c in candidates]
        if not id_list:
            return [], 0

        rows = (
            await self.session.execute(
                select(Skill.id, dl_subquery.c.period_downloads)
                .join(dl_subquery, Skill.id == dl_subquery.c.resource_id)
                .where(Skill.id.in_(id_list))
                .order_by(
                    desc(dl_subquery.c.period_downloads),
                    desc(Skill.updated_at),
                    desc(Skill.created_at),
                )
            )
        ).all()

        by_id = {c["id"]: c for c in candidates}
        ordered: list[dict[str, Any]] = []
        for skill_id, period_downloads in rows:
            item = dict(by_id.get(str(skill_id), {}))
            if not item:
                continue
            item["period_downloads"] = int(period_downloads or 0)
            ordered.append(item)
        return ordered, len(ordered)

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
            distance = float(row.distance)
            similarity = 1 / (1 + distance)
            if similarity < min_similarity:
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
                "distance": distance,
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
