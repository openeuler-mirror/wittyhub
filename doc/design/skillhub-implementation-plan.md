# SkillHub 平台实施计划

**项目状态：** 核心功能已完成，部分高级功能待开发

**Architecture:**
- REST API 层：FastAPI
- 数据层：PostgreSQL 单数据库 (tsvector 全文搜索)
- 前端：Vue.js + TypeScript + Tailwind CSS
- CLI：Python Typer 框架

**Tech Stack:**
- Python FastAPI, SQLAlchemy, Pydantic
- PostgreSQL 15 (tsvector 全文搜索)
- Vue.js 3, TypeScript, Tailwind CSS
- Python Typer (CLI), httpx
- Docker, Docker Compose

---

## 已完成功能清单

### Chunk 1-8: 全部完成 ✅

| Chunk | 模块 | 状态 | 说明 |
|--------|------|------|------|
| 1 | 项目初始化 | ✅ | 目录结构、配置文件、Docker |
| 2 | 数据库层 | ✅ | SQLAlchemy模型、Repository |
| 3 | API层 | ✅ | FastAPI路由、CRUD操作 |
| 4 | 搜索功能 | ✅ | PostgreSQL tsvector + pgvector 全文+向量搜索 |
| 5 | 搜索服务 | ✅ | SearchService 封装 + 混合搜索 |
| 6 | Embedding服务 | ✅ | src/ai/embedding.py |
| 6 | CLI工具 | ✅ | 7个命令 (list/search/get/download/install/audit/reindex) |
| 7 | Web前端 | ✅ | 5个页面 (Home/Search/SkillDetail/Category/Leaderboard) |
| 8 | 数据库迁移 | ✅ | Alembic迁移脚本 |

---

## 项目结构

```
skillhub/
├── src/                           # 后端源代码
│   ├── api/
│   │   ├── main.py              # FastAPI 应用入口
│   │   ├── models/
│   │   │   ├── models.py        # Skill, Agent, SecurityAudit, DownloadHistory
│   │   │   └── repository.py    # SkillRepository, AgentRepository
│   │   ├── routes/
│   │   │   ├── skills.py        # GET/POST/DELETE /skills/*
│   │   │   ├── agents.py        # GET /agents/*
│   │   │   ├── index.py         # search, reindex, stats, categories
│   │   │   └── health.py        # GET /health
│   │   ├── schemas/
│   │   │   └── skill.py         # Pydantic schemas
│   │   └── services/
│   │       └── security.py
│   ├── core/
│   │   ├── config.py            # YAML配置加载
│   │   └── database.py          # 异步SQLAlchemy引擎
│   ├── indexer/
│   │   └── search.py            # PostgreSQL tsvector + pgvector 混合搜索
│   ├── ai/
│   │   └── embedding.py       # Embedding 服务
│   ├── security/
│   │   └── detector.py          # Socket.dev + 静态分析
│   ├── storage/
│   │   └── downloader.py        # GitHub/GitCode/Gitee下载
│   └── migrations/
│       ├── 001_initial_schema.sql
│       └── 002_add_audit_version_columns.sql
│
├── web/                           # Vue.js 前端
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts        # Axios API客户端
│   │   │   └── types.ts         # TypeScript类型
│   │   ├── components/
│   │   │   ├── AppHeader.vue
│   │   │   ├── AppFooter.vue
│   │   │   ├── SearchBar.vue
│   │   │   ├── CategoryNav.vue
│   │   │   ├── SkillCard.vue
│   │   │   └── SecurityBadge.vue
│   │   ├── pages/
│   │   │   ├── Home.vue
│   │   │   ├── Search.vue
│   │   │   ├── SkillDetail.vue
│   │   │   ├── Category.vue
│   │   │   └── Leaderboard.vue
│   │   ├── router.ts
│   │   ├── App.vue
│   │   └── main.ts
│   └── package.json
│
├── cli/                           # CLI工具
│   ├── main.py                  # Typer命令 (list/search/get/download/install/audit/reindex)
│   └── client.py                # 同步/异步API客户端
│
├── tests/                        # 测试
│   ├── conftest.py
│   ├── test_api.py
│   └── test_skill_repository.py
│
├── scripts/                      # 工具脚本
│   ├── generate_test_data.py
│   ├── import_skills.py
│   └── ...
│
├── deploy/docker/               # Docker部署
│   ├── Dockerfile
│   ├── docker-compose.yaml
│   ├── nginx.conf
│   ├── config.yaml
│   └── init.sql                # PostgreSQL 扩展初始化
│
├── alembic.ini
├── config.yaml
├── pyproject.toml
└── README.md
```

---

## PostgreSQL 搜索设计

### 技术方案

```
PostgreSQL 单数据库:
├── tsvector     ──► 全文搜索 (to_tsvector + plainto_tsquery)
├── pgvector     ──► 向量搜索 (语义相似度)
├── JSONB        ──► 灵活元数据存储
└── ARRAY        ──► 标签数组
```

### 搜索模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `text` | 纯全文搜索 | 精确关键词匹配 |
| `semantic` | 纯向量搜索 | 语义理解查询 |
| `hybrid` | 混合搜索 (RRF) | 兼顾关键词和语义 |

### 全文搜索示例

```sql
-- 搜索 "代码调试工具"，使用中文分词配置 zhcfg
SELECT
  skill_id, name, description,
  ts_rank(
    to_tsvector('zhcfg', name || ' ' || COALESCE(description, '')),
    plainto_tsquery('zhcfg', '代码调试工具')
  ) AS rank
FROM skills
WHERE
  to_tsvector('zhcfg', name || ' ' || COALESCE(description, ''))
  @@ plainto_tsquery('zhcfg', '代码调试工具')
ORDER BY rank DESC, download_count DESC
LIMIT 20;
```

### 向量搜索示例

```sql
-- 语义搜索，查找与查询向量最相似的 skills
SELECT
  skill_id, name,
  1 / (1 + vec_l2_distance(embedding, '[0.1, 0.2, ...]'::vector)) AS similarity
FROM skills
WHERE embedding IS NOT NULL
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 20;
```

### Docker 初始化

```sql
-- init.sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "vector";

CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS zhcfg (COPY = pg_catalog.simple);
ALTER TEXT SEARCH CONFIGURATION zhcfg ALTER MAPPING FOR asciiword, word WITH unaccent, simple;
```

### 向量索引迁移

```sql
-- 添加 embedding 列
ALTER TABLE skills ADD COLUMN embedding vector(768);

-- 创建向量索引 (IVFFlat)
CREATE INDEX idx_skills_embedding ON skills USING ivfflat (embedding vector_l2_ops);

-- 或使用 HNSW 索引 (更好的性能)
-- CREATE INDEX idx_skills_embedding_hnsw ON skills USING hnsw (embedding vector_l2_ops);
```

---

## API 端点清单

### Skills API (`src/api/routes/skills.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/skills/` | 列表技能（分页、过滤） |
| POST | `/api/v1/skills/` | 创建技能 |
| GET | `/api/v1/skills/{skill_id}` | 获取详情 |
| GET | `/api/v1/skills/{skill_id}/download` | 获取下载链接 |
| GET | `/api/v1/skills/{skill_id}/audit` | 获取安全审计 |
| GET | `/api/v1/skills/{repo}/{skill_name}/versions` | 版本历史 |

### Agents API (`src/api/routes/agents.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/agents/` | 列表Agents |
| GET | `/api/v1/agents/{agent_id}` | 获取详情 |

### Index API (`src/api/routes/index.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/index/search` | 全文+向量混合搜索 (mode: text/semantic/hybrid) |
| POST | `/api/v1/index/reindex` | 重置索引状态 |
| POST | `/api/v1/index/reindex/{skill_id}` | 更新单条索引状态 |
| GET | `/api/v1/index/stats` | 平台统计 |
| GET | `/api/v1/index/categories` | 分类列表 |

### System API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |

---

## CLI 命令清单

| 命令 | 文件 | 说明 |
|------|------|------|
| list | `cli/main.py:21` | 列出本地已安装Skills |
| search | `cli/main.py:58` | 搜索Skills |
| get | `cli/main.py:96` | 显示Skill详情 |
| download | `cli/main.py:128` | 获取下载链接 |
| install | `cli/main.py:147` | 安装Skill到本地 |
| audit | `cli/main.py:267` | 显示安全审计结果 |
| reindex | `cli/main.py:301` | 触发服务器重索引 |

---

## 待开发功能

### P1: 爬虫自动发现系统

```
需要实现:
- 定时扫描 GitHub/GitCode/Gitee 主题/仓库
- 配置扫描源 (scan_sources 表)
- 自动发现新的 Skills
- 用户提交入口
```

### P2: AI 语义搜索 ✅ 已完成

```
已实现:
- Embedding 服务 (src/ai/embedding.py)
- 向量存储 (pgvector)
- 混合搜索 (RRF 算法)
- 三种搜索模式: text / semantic / hybrid
```

### P2: 标签页浏览

```
需要实现:
- GET /tags 端点
- /skills/tags/:tag 页面
```

### P2: 开发者页

```
需要实现:
- developer 数据聚合
- /developers/:name 页面
```

---

## 验证检查清单

完成部署后，验证以下内容：

- [ ] `docker-compose up -d` 能成功启动所有服务
- [ ] API 能正常访问 `http://localhost:8081/api/v1/health`
- [ ] API 文档可访问 `http://localhost:8081/docs`
- [ ] Web 前端能正常访问 `http://localhost:8080`
- [ ] 数据库表已创建 (`skills`, `agents`, `security_audits`, `download_history`)
- [ ] PostgreSQL 扩展已启用 (`pg_trgm`, `uuid-ossp`, `vector`)
- [ ] 中文分词配置已创建 (`zhcfg`)
- [ ] 向量列已添加 (`ALTER TABLE skills ADD COLUMN embedding vector(768)`)
- [ ] CLI 工具能正常执行 `python -m cli.main --help`
- [ ] `skillhub search "测试"` 能返回搜索结果
- [ ] `skillhub install` 能成功安装 Skill

---

*计划版本: v3.0 | 创建日期: 2026-05-15 | 更新日期: 2026-05-28*
