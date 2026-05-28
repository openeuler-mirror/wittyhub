# SkillHub 平台需求设计说明书

## 文档信息

| 项目 | 内容 |
|------|------|
| 项目名称 | SkillHub - Agent/Skill 检索与下载平台 |
| 文档版本 | v2.0 |
| 创建日期 | 2026-05-15 |
| 更新日期 | 2026-05-28 |
| 文档状态 | 进行中 |

---

## 1. 项目概述

### 1.1 项目背景

随着AI Agent和Skill生态的快速发展，开发者需要在一个集中的平台上发现、评估和获取可复用的Skill。当前存在多个Skill分发渠道（如skills.sh、clawhub.ai等），但缺乏统一的标准和本地化支持。本项目旨在构建一个去中心化的SkillHub平台，支持CLI/API访问，本地只存储索引，Skill内容存储在GitHub/GitCode等外部仓库。

### 1.2 项目目标

- **核心功能**：为Agent和Skill提供统一的检索、发现、下载和安全检测服务
- **访问方式**：支持CLI工具和REST API访问
- **数据管理**：去中心化存储，数据存储在GitHub/GitCode，本地只存储索引
- **安全优先**：提供多级安全检测和风险评分
- **扩展能力**：模块化架构，支持后续扩展Agent等资源类型

### 1.3 核心设计原则

| 原则 | 说明 |
|------|------|
| 去中心化 | Skill内容存储在外部仓库，本地只存储索引，避免审查风险 |
| 平台无关 | Skill本身与Agent平台无关，由下载工具自行适配 |
| 最小元数据 | 采用最小必需+可选扩展的元数据模型 |
| 安全优先 | 多级安全检测，提供风险评分和检测报告 |
| 模块化设计 | 核心模块与资源类型模块分离，资源类型安全检测独立 |

---

## 2. 需求汇总

### 2.1 功能需求清单

| 编号 | 需求项 | 优先级 | 状态 | 说明 |
|------|--------|--------|------|------|
| R-01 | CLI/API检索下载 | P0 | 已实现 | 支持关键词、分类、标签搜索 |
| R-02 | 多级安全检测 | P0 | 已实现 | Socket.dev API + 静态分析，提供风险评分 |
| R-03 | 分类标签系统 | P1 | 已实现 | 顶层大类 + 标签筛选 |
| R-04 | Web浏览功能 | P1 | 已实现 | 首页、搜索结果、详情、分类浏览、排行榜 |
| R-05 | 数据库索引存储 | P0 | 已实现 | PostgreSQL存储索引，不存储Skill内容 |
| R-06 | 全文搜索引擎 | P0 | 已实现 | PostgreSQL tsvector 全文检索 |
| R-07 | CLI工具 | P0 | 已实现 | search, list, get, install, download, audit命令 |
| R-08 | Web前端 | P1 | 已实现 | Vue.js + TypeScript + Tailwind CSS |
| R-09 | Docker部署 | P0 | 已实现 | Docker Compose一键部署 |
| R-10 | 多版本支持 | P1 | 已实现 | Skill版本管理，历史版本查询 |
| R-11 | 爬虫自动发现 | P1 | 待开发 | 主动扫描+配置仓库触发+用户提交 |
| R-12 | AI语义搜索 | P2 | 已实现 | pgvector向量检索 + 混合搜索 |
| R-13 | 排行榜功能 | P2 | 已实现 | 下载量排行榜 |
| R-14 | 开发者页 | P2 | 待开发 | 开发者信息页 |
| R-15 | 标签页浏览 | P2 | 待开发 | 同标签Skill列表页 |

### 2.2 非功能需求

| 编号 | 需求项 | 说明 |
|------|--------|------|
| N-01 | 无用户系统 | 暂不做用户系统，无个人收藏功能 |
| N-02 | 参考openEuler风格 | 前端UI参考openEuler蓝色调简洁风格 |
| N-03 | 中国区优化 | 考虑GitCode/Gitee等国内平台支持 |
| N-04 | 离线索引 | CLI支持离线使用本地缓存索引（待开发） |

---

## 3. 上下文视图

### 3.1 系统边界

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    SkillHub Platform                                   │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                         Web UI (Vue.js + TypeScript + Tailwind CSS)              │   │
│  │                                                                                 │   │
│  │   ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │   │
│  │   │   首页    │  │  搜索页   │  │  详情页   │  │  分类页   │  │ 排行榜   │   │   │
│  │   └───────────┘  └───────────┘  └───────────┘  └───────────┘  └───────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                            REST API Layer (FastAPI)                               │   │
│  │                                                                                 │   │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │   │
│  │  │                   Skills API (/api/v1/skills/*)                          │  │   │
│  │  │   list    detail   download   audit   versions                          │  │   │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                                 │   │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │   │
│  │  │                   Agents API (/api/v1/agents/*)                           │  │   │
│  │  │   list    detail                                                         │  │   │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                                 │   │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │   │
│  │  │                   Index API (/api/v1/index/*)                            │  │   │
│  │  │   search   reindex   stats   categories                                  │  │   │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           Core Services Layer (src/)                            │   │
│  │                                                                                 │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │   │
│  │   │  Search     │  │  Security   │  │  Storage    │  │   Config    │            │   │
│  │   │  (Indexer)  │  │  (detector) │  │ (downloader)│  │   (YAML)    │            │   │
│  │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘            │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           Data Layer (PostgreSQL 单数据库)                       │   │
│  │                                                                                 │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │   │
│  │   │   Skills   │  │   Agents    │  │  tsvector   │  │    Audit    │           │   │
│  │   │   Table    │  │   Table     │  │ 全文搜索    │  │   Records   │           │   │
│  │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘           │   │
│  │   ┌─────────────┐  ┌─────────────┐                                                       │   │
│  │   │  pgvector  │  │   JSONB     │                                                       │   │
│  │   │ 向量检索   │  │  灵活元数据  │                                                       │   │
│  │   └─────────────┘  └─────────────┘                                                       │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                               │
           ┌───────────────────────────────────┼───────────────────────────────────┐
           │                                   │                                   │
           ▼                                   ▼                                   ▼
┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐
│       Users             │     │   External Services     │     │     Data Storage        │
│                         │     │                         │     │                         │
│  ┌───────────────────┐ │     │  ┌─────────────────┐  │     │  ┌─────────────────┐  │
│  │   CLI Users       │ │     │  │  GitCode API   │  │     │  │  PostgreSQL     │  │
│  │   - skill search  │ │     │  │  - 下载仓库     │  │     │  │  - tsvector    │  │
│  │   - skill install │ │     │  └─────────────────┘  │     │  └─────────────────┘  │
│  │   - skill audit   │ │     │                        │     │                        │
│  └───────────────────┘ │     │  ┌─────────────────┐  │     │                        │
│                         │     │  │  Gitee API     │  │     │                        │
│  ┌───────────────────┐ │     │  │  - 下载仓库     │  │     │                        │
│  │   System Admin    │ │     │  └─────────────────┘  │     │                        │
│  │   - 触发重索引    │ │     │                        │     │                        │
│  │   - 查看统计       │ │     │  ┌─────────────────┐  │     │                        │
│  └───────────────────┘ │     │  │ Socket.dev API │  │     │                        │
│                         │     │  │  - 安全检测    │  │     │                        │
└─────────────────────────┘     │  └─────────────────┘  │     └─────────────────────────┘
                                 │                        │
                                 │  ┌─────────────────┐  │
                                 │  │ Local Storage   │  │
                                 │  │ ~/.agents/skills│  │
                                 │  └─────────────────┘  │
                                 └─────────────────────────┘
```

### 3.2 模块边界说明

| 模块 | 目录 | 说明 |
|------|------|------|
| Web UI | `web/` | Vue.js + TypeScript + Tailwind CSS 前端界面 |
| REST API | `src/api/` | FastAPI 路由层，统一入口 |
| Skills Module | `src/api/` | Skills 数据模型、业务逻辑 |
| Agents Module | `src/api/` | Agents 数据模型、业务逻辑 |
| Core Services | `src/` | 配置、数据库、搜索、安全、存储等通用能力 |
| Data Storage | PostgreSQL 单数据库 | 关系数据 + 全文搜索 + JSONB |

**关键设计：**
- Security 检测归属 Core 层 (`src/security/`)
- 不同资源类型（Skill、Agent）共享安全检测能力
- Core 层提供配置管理、数据库连接、搜索索引、文件下载等通用能力

### 3.3 数据流关系

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    数据流总览                                           │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  1. 搜索发现流程 (Search & Discovery)                                                   │
│     ┌──────────┐      ┌─────────────┐      ┌──────────────┐      ┌───────────────┐    │
│     │   User   │ ───► │   Search    │ ───► │   Embedding   │ ───► │  混合排序     │    │
│     │   Query  │      │   Handler   │      │   Service     │      │   (RRF)      │    │
│     └──────────┘      └─────────────┘      └──────────────┘      └───────────────┘    │
│                                    │                  │                                   │
│                          ┌─────────┴─────────┐      │                                   │
│                          │ PostgreSQL        │      │                                   │
│                          │ tsvector + pgvector│ ◄────┘                                   │
│                          └───────────────────┘                                           │
│                                                                                         │
│  2. Skill详情获取流程 (Detail Retrieval)                                                │
│     ┌──────────┐      ┌─────────────┐      ┌──────────────┐      ┌───────────────┐     │
│     │   User   │ ───► │   REST API │ ───► │  PostgreSQL  │ ───► │   Skill JSON  │     │
│     │          │      │             │      │              │      │               │     │
│     └──────────┘      └─────────────┘      └──────────────┘      └───────────────┘     │
│                                                                                         │
│  3. 安全检测流程 (Security Scanning)                                                    │
│     ┌──────────┐      ┌─────────────┐      ┌──────────────┐      ┌───────────────┐     │
│     │  New/    │ ───► │   Security  │ ───► │  Socket.dev  │ ───► │ Risk Score &  │     │
│     │  Update  │      │   Detector  │      │  API/Static  │      │ Alert Report  │     │
│     └──────────┘      └─────────────┘      └──────────────┘      └───────────────┘     │
│                                                                                         │
│  4. 下载流程 (Download)                                                                 │
│     ┌──────────┐      ┌─────────────┐      ┌──────────────┐      ┌───────────────┐     │
│     │   CLI/   │ ───► │  Download   │ ───► │   Source     │ ───► │   GitHub/     │     │
│     │   Web    │      │   Manager   │      │   Formatter  │      │   GitCode     │     │
│     └──────────┘      └─────────────┘      └──────────────┘      └───────────────┘     │
│                                                                                         │
│  5. 全文索引流程 (Full-text Index)                                                     │
│     ┌──────────┐      ┌─────────────┐      ┌──────────────┐      ┌───────────────┐     │
│     │ Database │ ───► │  tsvector   │ ───► │ PostgreSQL   │ ───► │ Search Index  │     │
│     │          │      │             │      │  索引        │      │               │     │
│     └──────────┘      └─────────────┘      └──────────────┘      └───────────────┘     │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 外部系统接口

| 外部系统 | 接口类型 | 用途 | 数据格式 |
|----------|----------|------|----------|
| GitHub API | REST API | 下载仓库存档、获取文件内容 | JSON |
| GitCode API | REST API | 下载仓库存档（国内镜像） | JSON |
| Gitee API | REST API | 下载仓库存档（国内平台） | JSON |
| Socket.dev API | REST API | npm包安全检测、风险评分 | JSON |
| Local Storage | 文件系统 | CLI安装的Skill本地存储 | 目录/文件 |

---

## 4. 用例视图

### 4.1 参与者定义

| 参与者 | 说明 | 角色 |
|--------|------|------|
| Web User | 通过浏览器访问平台的用户 | 搜索、浏览、查看安全报告 |
| CLI User | 使用命令行工具的用户 | 搜索、安装、更新Skill、查看安全审计 |
| System Admin | 系统运维管理人员 | 触发重索引、查看统计 |
| Skill Developer | Skill开发者 | 通过CLI安装和管理本地Skills |

### 4.2 用例汇总

| 用例ID | 用例名称 | 参与者 | 状态 | 描述 |
|--------|----------|--------|------|------|
| UC-1 | 搜索Skill | Web User | 已实现 | 通过关键词、分类、标签搜索Skill |
| UC-2 | 浏览Skill详情 | Web User | 已实现 | 查看Skill完整信息和统计 |
| UC-3 | 查看安全报告 | Web User | 已实现 | 查看多级安全检测报告和风险评分 |
| UC-4 | 浏览分类和标签 | Web User | 已实现 | 按分类浏览Skill列表 |
| UC-5 | 查看排行榜 | Web User | 已实现 | 查看下载量排行榜 |
| UC-6 | CLI搜索Skill | CLI User | 已实现 | 通过CLI搜索Skill |
| UC-7 | CLI安装Skill | CLI User | 已实现 | 安装Skill到本地 `~/.agents/skills/` |
| UC-8 | CLI查看Skill详情 | CLI User | 已实现 | 显示Skill详细信息 |
| UC-9 | CLI下载Skill | CLI User | 已实现 | 获取Skill下载链接 |
| UC-10 | CLI安全审计 | CLI User | 已实现 | 查看Skill安全审计结果 |
| UC-11 | CLI重索引 | CLI User | 已实现 | 触发服务器重索引 |
| UC-12 | 手动触发扫描 | System Admin | 待开发 | 手动触发立即扫描 |
| UC-13 | 查看系统状态 | System Admin | 已实现 | 查看系统运行状态和统计 |
| UC-14 | 多版本管理 | CLI User | 已实现 | 查看Skill版本历史 |

---

## 5. 技术架构

### 5.1 技术栈选型

| 层级 | 技术选型 | 选型理由 |
|------|----------|----------|
| 后端框架 | Python FastAPI | 高性能、自动化API文档、类型安全 |
| 数据库 | PostgreSQL | 成熟稳定、JSONB支持、tsvector全文搜索、pgvector向量搜索 |
| 全文搜索 | PostgreSQL tsvector | 内置全文搜索、中文分词支持 |
| 向量搜索 | PostgreSQL pgvector | 内置向量存储和相似度搜索 |
| Embedding | bge-base-zh-v1.5 | 中文效果好、开源可自部署 |
| 前端框架 | Vue.js 3 + TypeScript | 响应式开发、类型安全、IDE支持 |
| 样式 | Tailwind CSS | 原子化CSS，蓝色主调 |
| CLI框架 | Typer | Python类型安全的CLI框架 |
| HTTP客户端 | httpx | 同步/异步HTTP客户端 |
| 容器化 | Docker Compose | 快速部署、一键启动 |
| 安全检测 | Socket.dev API + 自研规则引擎 | 专业供应链安全检测、多级防护 |
| 配置管理 | YAML | 集中配置，环境分离 |

### 5.2 项目目录结构

```
skillhub/
├── src/                           # 后端源代码
│   ├── __init__.py
│   ├── api/                      # FastAPI 应用
│   │   ├── __init__.py
│   │   ├── main.py              # 应用入口
│   │   ├── models/              # 数据模型
│   │   │   ├── models.py       # Skill, Agent, SecurityAudit, DownloadHistory
│   │   │   └── repository.py   # 数据库操作类
│   │   ├── routes/             # API 路由
│   │   │   ├── skills.py       # Skills CRUD + 下载 + 审计
│   │   │   ├── agents.py       # Agents CRUD
│   │   │   ├── index.py        # 搜索 + 索引 + 统计
│   │   │   └── health.py       # 健康检查
│   │   ├── schemas/            # Pydantic Schemas
│   │   │   └── skill.py
│   │   └── services/           # 业务服务
│   │       └── security.py
│   ├── core/                    # 核心模块
│   │   ├── config.py          # YAML 配置加载
│   │   └── database.py        # 数据库连接
│   ├── indexer/               # 搜索引擎
│   │   └── search.py          # PostgreSQL tsvector 搜索
│   ├── security/              # 安全检测
│   │   └── detector.py        # Socket.dev + 静态分析
│   ├── storage/               # 文件存储
│   │   └── downloader.py      # 下载管理
│   └── migrations/            # 数据库迁移
│       ├── 001_initial_schema.sql
│       └── 002_add_audit_version_columns.sql
│
├── web/                        # Vue.js 前端
│   ├── src/
│   │   ├── api/              # API 调用
│   │   │   ├── client.ts    # Axios 客户端
│   │   │   └── types.ts     # TypeScript 类型
│   │   ├── components/       # 公共组件
│   │   │   ├── AppHeader.vue
│   │   │   ├── AppFooter.vue
│   │   │   ├── SearchBar.vue
│   │   │   ├── CategoryNav.vue
│   │   │   ├── SkillCard.vue
│   │   │   └── SecurityBadge.vue
│   │   ├── pages/           # 页面组件
│   │   │   ├── Home.vue
│   │   │   ├── Search.vue
│   │   │   ├── SkillDetail.vue
│   │   │   ├── Category.vue
│   │   │   └── Leaderboard.vue
│   │   ├── router.ts       # Vue Router 配置
│   │   ├── App.vue
│   │   └── main.ts
│   ├── package.json
│   └── vite.config.ts
│
├── cli/                        # CLI 工具
│   ├── main.py               # Typer CLI 主入口
│   └── client.py             # API 客户端
│
├── tests/                     # 测试
│   ├── conftest.py
│   ├── test_api.py
│   └── test_skill_repository.py
│
├── scripts/                   # 工具脚本
│   ├── generate_test_data.py
│   ├── import_skills.py
│   └── ...
│
├── deploy/docker/            # Docker 部署
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

### 5.3 模块职责

| 模块 | 职责 | 关键类/函数 |
|------|------|-------------|
| `src/api/routes/skills.py` | Skills CRUD, 下载, 审计 | `GET /skills/`, `GET /skills/{id}`, `POST /skills/`, `GET /skills/{id}/download`, `GET /skills/{id}/audit` |
| `src/api/routes/agents.py` | Agents CRUD | `GET /agents/`, `GET /agents/{id}` |
| `src/api/routes/index.py` | 搜索, 索引, 统计 | `GET /index/search`, `POST /index/reindex`, `GET /index/stats`, `GET /index/categories` |
| `src/api/models/models.py` | SQLAlchemy 模型 | `Skill`, `Agent`, `SecurityAudit`, `DownloadHistory` |
| `src/api/models/repository.py` | 数据库操作 | `SkillRepository`, `AgentRepository`, `SecurityAuditRepository` |
| `src/indexer/search.py` | PostgreSQL tsvector + pgvector 混合搜索 | `SearchService.search_skills()` |
| `src/ai/embedding.py` | Embedding 服务 | `generate_embeddings()` |
| `src/security/detector.py` | 安全检测 | `SecurityDetector`, `StaticSecurityAnalyzer` |
| `src/storage/downloader.py` | 下载管理 | `DownloadManager.get_download_url()` |
| `src/core/config.py` | 配置管理 | `Settings` (从 YAML 加载) |
| `cli/main.py` | CLI 命令 | `list`, `search`, `get`, `install`, `download`, `audit`, `reindex` |

---

## 6. CLI 工具设计

### 6.1 CLI 功能概览

```
skillhub - Agent/Skill 检索与下载平台 CLI

用法:
  skillhub [选项] 命令 [参数]

命令:
  list       列出已安装的 Skills
  search     搜索 Skill
  get        显示 Skill 详细信息
  download   获取 Skill 下载链接
  install    安装 Skill 到本地
  audit      显示 Skill 安全审计结果
  reindex    触发服务器重新索引

选项:
  --version  显示版本号
  --help     显示帮助信息
```

### 6.2 命令详解

#### 6.2.1 search - 搜索命令

```
skillhub search [关键词] [选项]

选项:
  --limit, -l <数量>         返回结果数量 (默认 20)

示例:
  skillhub search "代码调试"
  skillhub search --limit 10
```

#### 6.2.2 install - 安装命令

```
skillhub install <skill-id> [选项]

参数:
  <skill-id>                 Skill 的唯一标识 (如 vercel-labs/skills/find-skills)

选项:
  --target, -t <目录>        安装目标目录 (默认 ~/.agents/skills)

示例:
  skillhub install vercel-labs/skills/find-skills
  skillhub install anthropics/skills/frontend-design --target ./my-skills
```

#### 6.2.3 其他命令

| 命令 | 说明 |
|------|------|
| `list` | 列出本地已安装的 Skills |
| `get <skill-id>` | 显示 Skill 详细信息 |
| `download <skill-id>` | 获取 Skill 下载链接 |
| `audit <skill-id>` | 显示 Skill 安全审计结果 |
| `reindex` | 触发服务器重新索引所有 Skills |

### 6.3 CLI 本地存储

```
~/.agents/skills/
├── vercel-labs__skills__find-skills/
│   ├── skill.json           # Skill 元数据
│   ├── content/            # Skill 内容目录
│   └── versions/          # 版本历史
└── anthropics__skills__frontend-design/
    └── ...
```

---

## 7. Web 前端设计

### 7.1 页面结构

| 页面 | 路由 | 功能描述 |
|------|------|----------|
| 首页 | `/` | Hero区、搜索框、分类入口、热门Skill、统计 |
| 搜索页 | `/skills/search` | 关键词/分类/标签过滤、分页 |
| Skill详情 | `/skills/:repo/:name` | 元数据、版本选择、下载、安装命令、安全报告 |
| 分类页 | `/skills/categories/:category` | 分类下的Skill列表 |
| 排行榜 | `/skills/leaderboard` | 下载量排序 |

### 7.2 组件库

| 组件 | 说明 |
|------|------|
| SkillCard | Skill卡片，显示名称、描述、分类、安全等级 |
| SearchBar | 搜索栏，支持关键词输入 |
| CategoryNav | 分类导航，带图标 |
| SecurityBadge | 安全等级徽章（基于分数） |
| AppHeader | 顶部导航，含暗色模式切换 |
| AppFooter | 页脚 |

### 7.3 技术栈

| 组件 | 技术选型 |
|------|----------|
| 框架 | Vue 3 + Composition API + TypeScript |
| 构建工具 | Vite |
| 样式 | Tailwind CSS |
| HTTP | Axios |
| 路由 | Vue Router 4 |
| Markdown渲染 | marked |

---

## 8. 数据库设计

### 8.1 核心表结构

#### skills 索引表

```sql
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id VARCHAR(255) UNIQUE NOT NULL,  -- 唯一标识，如 "vercel-labs/skills/find-skills"
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- 版本信息
    version VARCHAR(50),
    commit_id VARCHAR(40),

    -- 作者信息
    author VARCHAR(255),

    -- 来源信息
    source VARCHAR(50) NOT NULL,           -- github, gitcode, gitee, local, clawhub
    source_url TEXT NOT NULL,

    -- 分类和标签
    category VARCHAR(100),
    tags TEXT[],
    platform VARCHAR(100),

    -- 扩展元数据
    extra_metadata JSONB,

    -- Skill内容
    content TEXT,                          -- skill.md 内容

    -- 统计信息
    security_score INTEGER,
    download_count INTEGER DEFAULT 0,
    rating DECIMAL(3,2),

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_indexed_at TIMESTAMPTZ
);

CREATE INDEX idx_skills_category ON skills(category);
CREATE INDEX idx_skills_platform ON skills(platform);
CREATE INDEX idx_skills_source ON skills(source);
CREATE INDEX idx_skills_tags ON skills USING GIN(tags);
CREATE INDEX idx_skills_created_at ON skills(created_at DESC);
```

#### agents 表

```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    author VARCHAR(255),
    source VARCHAR(50) NOT NULL,
    source_url TEXT NOT NULL,
    category VARCHAR(100),
    platform VARCHAR(100),
    extra_metadata JSONB,
    download_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### security_audits 表

```sql
CREATE TABLE security_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(20) NOT NULL,     -- 'skill' or 'agent'
    resource_id UUID NOT NULL,
    version VARCHAR(50),
    commit_id VARCHAR(40),
    audit_type VARCHAR(50) NOT NULL,        -- 'socket.dev', 'static'
    risk_level VARCHAR(20) NOT NULL,        -- critical, high, medium, low, unknown
    risk_signals JSONB DEFAULT '[]',
    details JSONB DEFAULT '{}',
    audited_at TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY (resource_id) REFERENCES skills(id) ON DELETE CASCADE
);
```

#### download_history 表

```sql
CREATE TABLE download_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(20) NOT NULL,
    resource_id UUID NOT NULL,
    ip_address INET,
    user_agent TEXT,
    downloaded_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 9. API接口设计

### 9.1 基础信息

| 项目 | 内容 |
|------|------|
| 基础路径 | `/api/v1` |
| 数据格式 | JSON |
| 认证方式 | 暂不需要认证（公开API） |

### 9.2 接口列表

#### Skills API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/skills/` | 列表技能（分页、过滤） |
| POST | `/skills/` | 创建技能（触发安全审计） |
| GET | `/skills/{skill_id}` | 获取技能详情 |
| DELETE | `/skills/{skill_id}` | 删除技能 |
| GET | `/skills/{skill_id}/download` | 获取下载链接 |
| GET | `/skills/{skill_id}/audit` | 获取安全审计结果 |
| GET | `/skills/{repo}/{skill_name}/versions` | 获取版本历史 |

#### Agents API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/agents/` | 列表Agent |
| GET | `/agents/{agent_id}` | 获取Agent详情 |

#### Index API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/index/search` | 全文搜索 |
| POST | `/index/reindex` | 全量重索引 |
| POST | `/index/reindex/{skill_id}` | 单条重索引 |
| GET | `/index/stats` | 平台统计 |
| GET | `/index/categories` | 分类列表 |

#### System API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查 |

### 9.3 搜索接口详细

```
GET /api/v1/index/search

Query Parameters:
  - q: 关键词搜索
  - category: 分类筛选
  - platform: 平台筛选
  - tags: 标签筛选
  - limit: 返回数量 (默认 20)
  - offset: 偏移量

Response:
{
  "total": 1234,
  "limit": 20,
  "offset": 0,
  "results": [
    {
      "id": "uuid",
      "skill_id": "vercel-labs/skills/find-skills",
      "name": "find-skills",
      "description": "...",
      "category": "DevTools",
      "tags": ["search", "discovery"],
      "source": "github",
      "security_score": 95,
      "download_count": 1500000
    }
  ]
}
```

### 9.4 列表接口详细

```
GET /api/v1/skills/

Query Parameters:
  - category: 分类筛选
  - platform: 平台筛选
  - tags: 标签筛选 (逗号分隔)
  - page: 页码 (默认 1)
  - size: 每页数量 (默认 20, 最大 100)

Response:
{
  "total": 1234,
  "page": 1,
  "size": 20,
  "results": [...]
}
```

---

## 10. 部署架构

### 10.1 Docker Compose架构

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://skillhub:skillhub@postgres:5432/skillhub

  web:
    build: ./web
    ports:
      - "3000:3000"

  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./deploy/docker/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - api
      - web
```

### 10.2 配置管理

```yaml
# config.yaml
database:
  host: "localhost"
  port: 5432
  user: "skillhub"
  password: "skillhub_secret"
  dbname: "skillhub"

storage:
  local_path: ~/.agents/skills
  github_token: ""

security:
  socket_api_key: ""
  enable_audit: true

app:
  host: 0.0.0.0
  port: 8000
  cors_origins:
    - "*"
```

---

## 11. 后续扩展规划

### 11.1 短期扩展

- [ ] 爬虫自动发现系统
- [ ] 标签页浏览功能
- [ ] 开发者页

### 11.2 中期扩展

- [ ] AI语义搜索（Embedding模型）
- [ ] 多维度排行榜（热门飙升、评分）
- [ ] 用户系统

### 11.3 长期扩展

- [ ] 企业级功能（私有仓库、权限管理）
- [ ] Kubernetes部署支持
- [ ] 更多AI能力集成

---

## 附录

### A. 参考资料

- [FastAPI](https://fastapi.tiangolo.com/)
- [PostgreSQL](https://www.postgresql.org/)
- [pgvector](https://github.com/pgvector/pgvector)
- [BGE Embedding](https://github.com/FlagOpen/FlagEmbedding)
- [Vue.js](https://vuejs.org/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Typer](https://typer.tiangolo.com/)
- [Socket.dev](https://socket.dev/)

### B. 术语表

| 术语 | 说明 |
|------|------|
| Skill | 可复用的AI Agent能力模块 |
| Agent | AI代理/智能体 |
| skill_id | Skill的唯一标识符，格式为 `owner/repo/skill-name` |
| tsvector | PostgreSQL 内置全文搜索向量类型 |
| pgvector | PostgreSQL 向量搜索扩展 |
| Embedding | 文本向量表示，用于语义相似度计算 |
| RRF | Reciprocal Rank Fusion，混合搜索排序融合算法 |
| Socket.dev | npm包安全检测服务 |

---

*文档版本: v2.0 | 创建日期: 2026-05-15 | 更新日期: 2026-05-28 | 状态: 进行中*
