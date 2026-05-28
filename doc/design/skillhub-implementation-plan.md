# SkillHub 平台实施计划

**项目状态：** 核心功能已完成，部分高级功能待开发

**Architecture:**
- REST API 层：FastAPI
- 数据层：PostgreSQL + Meilisearch
- 前端：Vue.js + TypeScript + Tailwind CSS
- CLI：Python Typer 框架

**Tech Stack:**
- Python FastAPI, SQLAlchemy, Pydantic
- PostgreSQL 15, Meilisearch
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
| 4 | 爬虫/索引 | ✅ | Meilisearch全文搜索 |
| 5 | 搜索功能 | ✅ | SearchClient封装 |
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
│   │   └── search.py            # Meilisearch客户端
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
│   └── config.yaml
│
├── alembic.ini
├── config.yaml
├── pyproject.toml
└── README.md
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
| GET | `/api/v1/index/search` | 全文搜索 |
| POST | `/api/v1/index/reindex` | 全量重索引 |
| POST | `/api/v1/index/reindex/{skill_id}` | 单条重索引 |
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

### P2: AI 语义搜索

```
需要实现:
- 本地 Embedding 模型 (m3e-base)
- 文本向量化和存储
- 语义相似度搜索
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
- [ ] API 能正常访问 `http://localhost:8000/api/v1/health`
- [ ] API 文档可访问 `http://localhost:8000/docs`
- [ ] Web 前端能正常访问 `http://localhost:3000`
- [ ] 数据库表已创建 (`skills`, `agents`, `security_audits`, `download_history`)
- [ ] CLI 工具能正常执行 `python -m cli.main --help`
- [ ] `skillhub search` 能返回搜索结果
- [ ] `skillhub install` 能成功安装 Skill

---

*计划版本: v2.0 | 创建日期: 2026-05-15 | 更新日期: 2026-05-28*
