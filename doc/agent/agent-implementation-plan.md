# Agent 功能实现方案

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档名称 | Agent 功能实现方案 |
| 文档版本 | v1.0 |
| 创建日期 | 2026-06-22 |
| 文档状态 | 进行中 |

---

## 1. 概述

### 1.1 项目背景

Agent 是基于 Universal Agent Specification (UAS) 标准的 AI Agent 配置文件。一个 Agent 以 Git 仓库形式存在，包含 `agent.yaml` 核心配置文件以及可选的 prompts、skills、subagents 等模块。

SkillHub 平台需要扩展 Agent 的前后端能力，使其与 Skills 功能对齐，支持浏览、搜索、下载等功能。

### 1.2 设计目标

- 支持 Agent 的多版本管理
- 展示 Agent 的 YAML 配置解析内容（prompt、skills、tools、subagents）
- 支持多平台兼容性展示（Claude Code、OpenCode、OpenClaw、SDK）
- 提供与其他 Git 平台类似的详情页体验

### 1.3 设计原则

| 原则 | 说明 |
|------|------|
| Agent 与 Model 解耦 | Agent 定义不含 model 配置，运行时由平台决定 |
| JSONB 存储结构 | parsed_config 使用 JSONB，与 agent.yaml 结构一致 |
| 复用现有逻辑 | 下载、安全审计等逻辑复用 Skill 实现 |
| 前端组件化 | Subagent 采用折叠面板组件 |

---

## 2. 用例视图

### 2.1 参与者

| 参与者 | 说明 |
|--------|------|
| 普通用户 | 浏览、搜索、下载 Agent |
| 开发者 | 导入、管理 Agent |
| 系统 | 爬虫自动发现、定时更新 |

### 2.2 用例列表

```
┌─────────────────────────────────────────────────────────────────┐
│                        SkillHub 平台                            │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   用户      │  │  开发者     │  │   系统      │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                 │                 │                    │
│         ▼                 ▼                 ▼                    │
│  ┌─────────────────────────────────────────────────────┐        │
│  │                    Agent 功能                        │        │
│  │                                                     │        │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │        │
│  │  │ 浏览 Agent   │  │ 搜索 Agent  │  │ 查看详情  │  │        │
│  │  └─────────────┘  └─────────────┘  └───────────┘  │        │
│  │                                                     │        │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │        │
│  │  │ 下载 Agent  │  │ 版本切换    │  │ 安全报告  │  │        │
│  │  └─────────────┘  └─────────────┘  └───────────┘  │        │
│  │                                                     │        │
│  │  ┌─────────────┐  ┌─────────────┐                   │        │
│  │  │ 导入 Agent  │  │ 删除 Agent  │                   │        │
│  │  └─────────────┘  └─────────────┘                   │        │
│  │                                                     │        │
│  └─────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 用例描述

#### UC-01: 浏览 Agent 列表

| 属性 | 内容 |
|------|------|
| 用例名称 | 浏览 Agent 列表 |
| 参与者 | 普通用户 |
| 前置条件 | 用户打开 /agents/ 页面 |
| 基本流程 | 1. 系统返回 Agent 列表（分页）<br>2. 显示名称、作者、平台标签、下载量 |
| 后置条件 | 用户看到 Agent 列表 |
| 扩展点 | 支持按分类、标签筛选 |

#### UC-02: 搜索 Agent

| 属性 | 内容 |
|------|------|
| 用例名称 | 搜索 Agent |
| 参与者 | 普通用户 |
| 前置条件 | 用户输入搜索关键词 |
| 基本流程 | 1. 用户输入关键词<br>2. 系统进行全文 + 语义搜索<br>3. 返回匹配结果 |
| 后置条件 | 用户看到搜索结果 |

#### UC-03: 查看 Agent 详情

| 属性 | 内容 |
|------|------|
| 用例名称 | 查看 Agent 详情 |
| 参与者 | 普通用户 |
| 前置条件 | 用户点击 Agent 卡片 |
| 基本流程 | 1. 显示基本信息（名称、作者、描述）<br>2. 显示 System Prompt<br>3. 显示支持平台<br>4. 显示 Skills 列表<br>5. 显示 Tools 权限<br>6. 显示 Subagents（折叠）<br>7. 显示安全报告 |
| 后置条件 | 用户看到完整 Agent 信息 |

#### UC-04: 下载 Agent

| 属性 | 内容 |
|------|------|
| 用例名称 | 下载 Agent |
| 参与者 | 普通用户 |
| 前置条件 | 用户点击下载按钮 |
| 基本流程 | 1. 用户点击下载<br>2. 系统生成下载 URL<br>3. 跳转至 Git 平台 ZIP 下载页 |
| 后置条件 | 用户下载 Agent 仓库 |

#### UC-05: 版本切换

| 属性 | 内容 |
|------|------|
| 用例名称 | 版本切换 |
| 参与者 | 普通用户 |
| 前置条件 | 用户在详情页选择版本 |
| 基本流程 | 1. 用户选择版本<br>2. 系统加载对应版本的 parsed_config<br>3. 页面更新显示新版本信息 |
| 后置条件 | 用户看到选中版本的内容 |

#### UC-06: 导入 Agent

| 属性 | 内容 |
|------|------|
| 用例名称 | 导入 Agent |
| 参与者 | 开发者 |
| 前置条件 | 开发者提供 Git 仓库地址 |
| 基本流程 | 1. 系统克隆仓库<br>2. 解析 agent.yaml<br>3. 提取 parsed_config<br>4. 保存到数据库 |
| 后置条件 | Agent 出现在列表中 |

#### UC-07: 查看安全报告

| 属性 | 内容 |
|------|------|
| 用例名称 | 查看安全报告 |
| 参与者 | 普通用户 |
| 前置条件 | 用户在详情页查看 Security Tab |
| 基本流程 | 1. 系统查询安全审计记录<br>2. 显示安全评分、风险等级、风险信号 |
| 后置条件 | 用户看到安全评估 |

---

## 3. 逻辑视图

### 3.1 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         SkillHub 平台                            │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                      Web 前端 (Vue.js)                    │   │
│  │                                                          │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐          │   │
│  │  │ AgentList │  │AgentDetail│  │  Search   │          │   │
│  │  └───────────┘  └───────────┘  └───────────┘          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    REST API (FastAPI)                   │   │
│  │                                                          │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐          │   │
│  │  │  Agents   │  │  Index    │  │  Audit    │          │   │
│  │  │  Routes   │  │  Search   │  │  Service  │          │   │
│  │  └───────────┘  └───────────┘  └───────────┘          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│         ┌────────────────────┼────────────────────┐            │
│         ▼                    ▼                    ▼            │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐  │
│  │ Repository  │      │ Downloader  │      │  Security   │  │
│  │   Layer     │      │   Manager   │      │  Detector   │  │
│  └─────────────┘      └─────────────┘      └─────────────┘  │
│                              │                    │            │
│                              ▼                    ▼            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  PostgreSQL Database                  │   │
│  │                                                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │   agents    │  │agent_versions│  │security_audits│ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Git 平台      │
                    │ GitHub/GitCode │
                    │   /Gitee       │
                    └─────────────────┘
```

### 3.2 模块设计

```
src/
├── api/
│   ├── routes/
│   │   ├── agents.py          # Agent API 路由
│   │   └── skills.py          # Skill API 路由 (复用)
│   ├── models/
│   │   ├── models.py          # Agent, AgentVersion 模型
│   │   └── repository.py      # AgentRepository
│   ├── schemas/
│   │   ├── agent.py           # Agent Pydantic 模型 (新建)
│   │   └── skill.py           # Skill Pydantic 模型 (已有)
│   └── services/
│       └── security.py        # SecurityService (复用)
│
├── storage/
│   └── downloader.py          # DownloadManager (复用)
│
└── core/
    ├── config.py              # 配置
    └── database.py            # 数据库连接

web/src/
├── api/
│   ├── client.ts              # API 客户端 (扩展)
│   └── types.ts              # Agent 类型 (扩展)
├── components/
│   ├── AgentCard.vue          # Agent 卡片 (新建)
│   ├── SubagentPanel.vue      # Subagent 折叠面板 (新建)
│   ├── PlatformBadge.vue      # 平台徽章 (新建)
│   └── SkillCard.vue          # Skill 卡片 (已有)
├── pages/
│   ├── AgentList.vue          # Agent 列表页 (新建)
│   ├── AgentDetail.vue        # Agent 详情页 (新建)
│   └── SkillDetail.vue        # Skill 详情页 (已有)
└── router.ts                 # 路由配置 (扩展)
```

### 3.3 数据模型

#### Agent 模型

```python
class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)  # owner/repo
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    commit_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # github/gitcode/gitee
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    security_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 新增字段
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    homepage_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    license: Mapped[str | None] = mapped_column(String(50), nullable=True)
    readme_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_yaml_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    supported_platforms: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    verified: Mapped[bool] = mapped_column(default=False)
    star_count: Mapped[int] = mapped_column(Integer, default=0)
    contributor_count: Mapped[int] = mapped_column(Integer, default=0)
    latest_commit_id: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # 关系
    versions: Mapped[list["AgentVersion"]] = relationship(back_populates="agent", cascade="all, delete-orphan")
    audits: Mapped[list["SecurityAudit"]] = relationship(back_populates="agent", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_agents_category", "category"),
        Index("idx_agents_tags", "tags", postgresql_using="gin"),
        Index("idx_agents_source", "source"),
        Index("idx_agents_created_at", desc("created_at")),
    )
```

#### AgentVersion 模型

```python
class AgentVersion(Base):
    __tablename__ = "agent_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    commit_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agent: Mapped["Agent"] = relationship(back_populates="versions")

    __table_args__ = (
        UniqueConstraint("agent_id", "version", "commit_id", name="idx_agent_version_unique"),
    )
```

#### parsed_config JSONB 结构

```python
{
    "prompt": {
        "system": "You are a helpful assistant...",
        "identity": {
            "role": "Senior Engineer",
            "emoji": "🤖",
            "vibe": "professional"
        },
        "workflow_file": "./prompts/workflow.md"
    },
    "tools": {
        "allowed": ["read", "bash", "grep", "edit"],
        "permission": {
            "bash": {"default": "ask", "deny": ["rm -rf *"]}
        }
    },
    "skills": [
        {"name": "tdd", "source": "./skills/tdd/SKILL.md", "when": ["TDD"]}
    ],
    "subagents": [
        {
            "name": "security-reviewer",
            "prompt": {
                "system": "You are a security engineer...",
                "identity": {"role": "Security Engineer", "emoji": "🔒"}
            },
            "tools": {"allowed": ["read", "grep", "bash"]},
            "skills": [
                {"name": "security-review", "inline": "...", "when": ["security"]}
            ]
        }
    ]
}
```

### 3.4 SecurityAudit 表扩展

```python
class SecurityAudit(Base):
    __tablename__ = "security_audits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "skill" | "agent"
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    commit_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    audit_type: Mapped[str] = mapped_column(String(50), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_signals: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    audited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    skill: Mapped["Skill"] = relationship(back_populates="audits", foreign_keys=[resource_id])
    agent: Mapped["Agent"] = relationship(back_populates="audits", foreign_keys=[resource_id])

    __table_args__ = (
        Index("idx_audits_resource", "resource_type", "resource_id"),
        Index("idx_audits_risk_level", "risk_level"),
        Index("idx_audits_audited_at", desc("audited_at")),
    )
```

---

## 4. 过程视图（时序图）

### 4.1 浏览 Agent 列表

```
┌────────┐     ┌─────────────┐     ┌─────────────┐     ┌────────────┐
│  用户   │     │  前端 Vue   │     │ FastAPI     │     │ PostgreSQL │
└───┬────┘     └──────┬──────┘     └──────┬──────┘     └─────┬──────┘
    │                │                    │                  │
    │ GET /agents/   │                    │                  │
    │───────────────>│                    │                  │
    │                │ GET /agents/       │                  │
    │                │───────────────────>│                  │
    │                │                    │ SELECT *        │
    │                │                    │─────────────────>│
    │                │                    │<─────────────────│
    │                │                    │                  │
    │                │<───────────────────│                  │
    │<───────────────│                    │                  │
    │                │                    │                  │
```

### 4.2 查看 Agent 详情

```
┌────────┐     ┌─────────────┐     ┌─────────────┐     ┌────────────┐
│  用户   │     │  前端 Vue   │     │ FastAPI     │     │ PostgreSQL │
└───┬────┘     └──────┬──────┘     └──────┬──────┘     └─────┬──────┘
    │                │                    │                  │
    │ GET /agents/:id│                    │                  │
    │───────────────>│                    │                  │
    │                │ GET /agents/:id   │                  │
    │                │───────────────────>│                  │
    │                │                    │ SELECT agent     │
    │                │                    │─────────────────>│
    │                │                    │<─────────────────│
    │                │                    │                  │
    │                │<───────────────────│                  │
    │<───────────────│                    │                  │
    │                │                    │                  │
    │ GET versions   │                    │                  │
    │───────────────>│                    │                  │
    │                │ GET /agents/:id/versions            │
    │                │───────────────────>│                  │
    │                │                    │ SELECT versions  │
    │                │                    │─────────────────>│
    │                │                    │<─────────────────│
    │                │<───────────────────│                  │
    │<───────────────│                    │                  │
```

### 4.3 版本切换

```
┌────────┐     ┌─────────────┐     ┌─────────────┐     ┌────────────┐
│  用户   │     │  前端 Vue   │     │ FastAPI     │     │ PostgreSQL │
└───┬────┘     └──────┬──────┘     └──────┬──────┘     └─────┬──────┘
    │                │                    │                  │
    │ Select v1.1.0  │                    │                  │
    │───────────────>│                    │                  │
    │                │                    │                  │
    │                │ GET /agents/:id    │                  │
    │                │?version=v1.1.0    │                  │
    │                │───────────────────>│                  │
    │                │                    │ SELECT by version│
    │                │                    │─────────────────>│
    │                │                    │<─────────────────│
    │                │                    │                  │
    │                │<───────────────────│                  │
    │<───────────────│                    │                  │
    │                │                    │                  │
```

### 4.4 下载 Agent

```
┌────────┐     ┌─────────────┐     ┌─────────────┐     ┌────────────┐
│  用户   │     │  前端 Vue   │     │ FastAPI     │     │   Git      │
└───┬────┘     └──────┬──────┘     └──────┬──────┘     │  平台      │
    │                │                    │         └─────┬──────┘
    │                │                    │                  │
    │ GET /agents/:id/download            │                  │
    │───────────────>│                    │                  │
    │                │ GET /download      │                  │
    │                │───────────────────>│                  │
    │                │                    │                  │
    │                │                    │ format URL        │
    │                │                    │ (gitcode.com/...)│
    │                │                    │                  │
    │                │<───────────────────│                  │
    │<───────────────│                    │                  │
    │                │                    │                  │
    │ Redirect to download URL            │                  │
    │────────────────────────────────────────────────────────>
    │                │                    │                  │
```

### 4.5 导入 Agent（开发者）

```
┌────────┐     ┌─────────────┐     ┌─────────────┐     ┌────────────┐
│ 开发者  │     │ FastAPI     │     │  GitClone  │     │ PostgreSQL │
└───┬────┘     └──────┬──────┘     └──────┬──────┘     └─────┬──────┘
    │                │                    │                  │
    │ POST /agents/  │                    │                  │
    │ source_url=... │                    │                  │
    │───────────────>│                    │                  │
    │                │                    │                  │
    │                │ clone repository   │                  │
    │                │───────────────────>│                  │
    │                │                    │                  │
    │                │ read agent.yaml    │                  │
    │                │<───────────────────│                  │
    │                │                    │                  │
    │                │ parse YAML        │                  │
    │                │ extract config    │                  │
    │                │                    │                  │
    │                │ INSERT agent      │                  │
    │                │───────────────────>│                  │
    │                │                    │                  │
    │<───────────────│                    │                  │
    │ 201 Created    │                    │                  │
```

---

## 5. 开发视图

### 5.1 目录结构

```
skillhub/
├── src/
│   └── api/
│       ├── routes/
│       │   ├── agents.py          # [修改] 扩展端点
│       │   └── skills.py          # [已有]
│       ├── models/
│       │   ├── models.py          # [修改] Agent 模型扩展
│       │   └── repository.py      # [修改] AgentRepository 扩展
│       ├── schemas/
│       │   ├── agent.py           # [新建] Agent Pydantic 模型
│       │   └── skill.py           # [已有]
│       └── services/
│           └── security.py        # [已有] 复用
├── web/
│   └── src/
│       ├── api/
│       │   ├── client.ts          # [修改] 添加 Agent API 方法
│       │   └── types.ts          # [修改] 添加 Agent 类型
│       ├── components/
│       │   ├── AgentCard.vue      # [新建]
│       │   ├── SubagentPanel.vue  # [新建]
│       │   └── PlatformBadge.vue  # [新建]
│       ├── pages/
│       │   ├── AgentList.vue      # [新建]
│       │   └── AgentDetail.vue     # [新建]
│       └── router.ts             # [修改] 添加 Agent 路由
└── tests/
    ├── test_agents_api.py        # [新建]
    └── test_repository.py         # [修改] 添加 Agent 测试
```

### 5.2 API 端点设计

| 方法 | 端点 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| GET | `/api/v1/agents/` | query: skip, limit, category, tags | AgentListResponse | 列表查询 |
| GET | `/api/v1/agents/{agent_id}` | - | AgentResponse | 详情 |
| GET | `/api/v1/agents/{agent_id}/versions` | - | AgentVersionsResponse | 版本列表 |
| GET | `/api/v1/agents/{agent_id}/download` | - | DownloadResponse | 下载链接 |
| GET | `/api/v1/agents/{agent_id}/audit` | - | SecurityAuditResponse | 安全报告 |
| POST | `/api/v1/agents/` | AgentCreate | AgentResponse | 创建 |
| DELETE | `/api/v1/agents/{agent_id}` | - | {message} | 删除 |

### 5.3 请求/响应模型

#### AgentResponse

```python
class AgentResponse(BaseModel):
    id: str
    agent_id: str
    name: str
    description: str | None
    version: str | None
    commit_id: str | None
    author: str | None
    source: str
    source_url: str
    category: str | None
    tags: list[str] | None
    logo_url: str | None
    homepage_url: str | None
    license: str | None
    readme_content: str | None
    agent_yaml_content: str | None
    parsed_config: dict[str, Any]
    supported_platforms: list[str] | None
    verified: bool
    star_count: int
    contributor_count: int
    security_score: int | None
    download_count: int
    rating: str | None
    latest_commit_id: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

#### AgentListResponse

```python
class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int
    skip: int
    limit: int
```

#### AgentVersionsResponse

```python
class AgentVersionResponse(BaseModel):
    version: str
    commit_id: str | None
    author: str | None
    message: str | None
    released_at: datetime | None
    download_count: int

    class Config:
        from_attributes = True

class AgentVersionsResponse(BaseModel):
    agent_id: str
    versions: list[AgentVersionResponse]
```

### 5.4 前端类型定义

```typescript
// web/src/api/types.ts

export interface Agent {
  id: string
  agent_id: string
  name: string
  description: string | null
  version: string | null
  commit_id: string | null
  author: string | null
  source: string
  source_url: string
  category: string | null
  tags: string[] | null
  logo_url: string | null
  homepage_url: string | null
  license: string | null
  readme_content: string | null
  agent_yaml_content: string | null
  parsed_config: ParsedAgentConfig | null
  supported_platforms: string[] | null
  verified: boolean
  star_count: number
  contributor_count: number
  security_score: number | null
  download_count: number
  rating: string | null
  latest_commit_id: string | null
  created_at: string
  updated_at: string
}

export interface ParsedAgentConfig {
  prompt?: {
    system?: string
    identity?: {
      role?: string
      emoji?: string
      vibe?: string
    }
    workflow_file?: string
  }
  tools?: {
    allowed?: string[]
    permission?: Record<string, any>
  }
  skills?: AgentSkillRef[]
  subagents?: Subagent[]
}

export interface AgentSkillRef {
  name: string
  source?: string
  inline?: string
  installed?: string
  when?: string[]
}

export interface Subagent {
  name: string
  prompt: {
    system?: string
    identity?: {
      role?: string
      emoji?: string
      vibe?: string
    }
  }
  tools?: {
    allowed?: string[]
  }
  skills?: AgentSkillRef[]
}

export interface AgentVersion {
  version: string
  commit_id: string | null
  author: string | null
  message: string | null
  released_at: string | null
  download_count: number
}

export interface AgentListResponse {
  agents: Agent[]
  total: number
  skip: number
  limit: number
}
```

---

## 6. 部署视图

### 6.1 部署架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Compose                            │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │    Nginx    │  │   FastAPI   │  │ PostgreSQL  │            │
│  │  (Port 80)  │  │ (Port 8080) │  │ (Port 5432) │            │
│  │  静态文件    │  │  业务逻辑    │  │ + pgvector  │            │
│  │  API代理     │  │  数据访问    │  │             │            │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘            │
│         │                │                                     │
│         │                │                                     │
│         │                ▼                                     │
│         │         ┌─────────────┐                             │
│         │         │ Embedding   │                             │
│         │         │   Service   │                             │
│         │         │ (向量模型)   │                             │
│         │         └─────────────┘                             │
│         │                                                       │
│         │              (后续扩展)                                │
│         │                │                                     │
│         │                ▼                                     │
│         │         ┌─────────────┐                             │
│         │         │  Security   │                             │
│         │         │   Scanner   │                             │
│         │         │ (安全扫描)   │                             │
│         │         └─────────────┘                             │
└─────────┼───────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────┐
│   Git 平台      │
│ GitHub/GitCode │
│   /Gitee       │
└─────────────────┘
```

**访问路径**：
```
前端 ──► Nginx ──► FastAPI ──► PostgreSQL
         (静态文件)  (API代理)   (数据存储)
```

**组件说明**：

| 组件 | 说明 | 状态 |
|------|------|------|
| Nginx | 静态文件服务 + API 反向代理 | 已有 |
| FastAPI | 后端业务逻辑 + 数据访问 | 已有 |
| PostgreSQL | 数据库 + pgvector 语义搜索 | 已有 |
| Embedding Service | 向量嵌入服务 | 已有 |
| Security Scanner | 安全扫描服务 | 后续扩展 |

### 6.2 环境变量

```yaml
# .env
DATABASE_URL=postgresql+asyncpg://skillhub:skillhub_secret@db:5432/skillhub

STORAGE_TYPE=local
STORAGE_LOCAL_PATH=/data/skills

GITHUB_TOKEN=your_github_token

SECURITY_ENABLE_AUDIT=true
```

### 6.3 Agent 导入接口说明

**重要**：Agent 导入接口为内部接口，不对外部开放。

| 接口 | 访问方式 | 说明 |
|------|----------|------|
| POST `/api/v1/agents/` | 内部调用 | 仅限系统/管理员导入 Agent |
| GET `/api/v1/agents/` | 公开 | 用户浏览 Agent 列表 |
| GET `/api/v1/agents/{agent_id}` | 公开 | 用户查看 Agent 详情 |

导入方式：
1. **爬虫自动发现**：系统定时扫描配置的 Git 仓库
2. **管理员手动导入**：通过管理后台或 CLI 工具导入

### 6.4 数据库迁移

```bash
# 生成迁移
alembic revision --autogenerate -m "add agent tables"

# 执行迁移
alembic upgrade head
```

### 6.5 前端构建

```bash
cd web
npm install
npm run build
```

---

## 7. 实现任务

### 7.1 后端任务

| 任务 | 优先级 | 文件 | 说明 |
|------|--------|------|------|
| T1 | P0 | `src/api/models/models.py` | 扩展 Agent 模型（添加新字段） |
| T2 | P0 | `src/api/models/models.py` | 新增 AgentVersion 模型 |
| T3 | P0 | `src/api/models/repository.py` | 扩展 AgentRepository（版本查询） |
| T4 | P0 | `src/api/schemas/agent.py` | 新建 AgentSchema |
| T5 | P0 | `src/api/routes/agents.py` | 扩展 API 端点 |
| T6 | P1 | `src/storage/downloader.py` | 支持 Agent 下载 URL 生成 |
| T7 | P2 | `scripts/import_agents.py` | 新建 Agent 导入脚本 |

### 7.2 前端任务

| 任务 | 优先级 | 文件 | 说明 |
|------|--------|------|------|
| T8 | P0 | `web/src/api/types.ts` | 添加 Agent 类型定义 |
| T9 | P0 | `web/src/api/client.ts` | 添加 Agent API 方法 |
| T10 | P0 | `web/src/router.ts` | 添加 Agent 路由 |
| T11 | P0 | `web/src/components/AgentCard.vue` | 新建 AgentCard 组件 |
| T12 | P0 | `web/src/pages/AgentList.vue` | 新建 AgentList 页面 |
| T13 | P0 | `web/src/pages/AgentDetail.vue` | 新建 AgentDetail 页面 |
| T14 | P1 | `web/src/components/SubagentPanel.vue` | 新建 SubagentPanel 组件 |
| T15 | P1 | `web/src/components/PlatformBadge.vue` | 新建 PlatformBadge 组件 |

### 7.3 测试任务

| 任务 | 优先级 | 文件 | 说明 |
|------|--------|------|------|
| T16 | P0 | `tests/test_agents_api.py` | 新建 Agent API 测试 |
| T17 | P1 | `tests/test_repository.py` | 扩展 Repository 测试 |

---

## 8. 详细实现步骤

### Task T1: 扩展 Agent 模型

**修改文件**: `src/api/models/models.py`

```python
# 在 Agent 类中添加新字段（在 extra_metadata 后）

# 新增字段
logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
homepage_url: Mapped[str | None] = mapped_column(Text, nullable=True)
license: Mapped[str | None] = mapped_column(String(50), nullable=True)
readme_content: Mapped[str | None] = mapped_column(Text, nullable=True)
agent_yaml_content: Mapped[str | None] = mapped_column(Text, nullable=True)
parsed_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
supported_platforms: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
verified: Mapped[bool] = mapped_column(default=False)
star_count: Mapped[int] = mapped_column(Integer, default=0)
contributor_count: Mapped[int] = mapped_column(Integer, default=0)
latest_commit_id: Mapped[str | None] = mapped_column(String(40), nullable=True)

# 添加关系
versions: Mapped[list["AgentVersion"]] = relationship(back_populates="agent", cascade="all, delete-orphan")
audits: Mapped[list["SecurityAudit"]] = relationship(back_populates="agent", cascade="all, delete-orphan")
```

### Task T2: 新增 AgentVersion 模型

**修改文件**: `src/api/models/models.py`

```python
class AgentVersion(Base):
    __tablename__ = "agent_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    commit_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agent: Mapped["Agent"] = relationship(back_populates="versions")

    __table_args__ = (
        UniqueConstraint("agent_id", "version", "commit_id", name="idx_agent_version_unique"),
    )
```

### Task T3: 扩展 AgentRepository

**修改文件**: `src/api/models/repository.py`

新增方法：

```python
# AgentVersion 查询
async def get_versions(self, agent_id: uuid.UUID) -> list[AgentVersion]:
    result = await self.session.execute(
        select(AgentVersion)
        .where(AgentVersion.agent_id == agent_id)
        .order_by(AgentVersion.released_at.desc())
    )
    return list(result.scalars().all())

# Agent 下载次数增加
async def increment_download(self, agent_id: uuid.UUID) -> None:
    await self.session.execute(
        update(Agent)
        .where(Agent.id == agent_id)
        .values(download_count=Agent.download_count + 1)
    )
    await self.session.flush()
```

### Task T4: 新建 AgentSchema

**新建文件**: `src/api/schemas/agent.py`

```python
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class AgentBase(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    version: str | None = Field(None, max_length=50)
    author: str | None = Field(None, max_length=255)
    source: str = Field(..., max_length=50)
    source_url: str = Field(..., min_length=1)
    category: str | None = Field(None, max_length=100)
    tags: list[str] | None = None
    supported_platforms: list[str] | None = None


class AgentCreate(AgentBase):
    pass


class AgentResponse(AgentBase):
    id: str
    commit_id: str | None = None
    logo_url: str | None = None
    homepage_url: str | None = None
    license: str | None = None
    readme_content: str | None = None
    agent_yaml_content: str | None = None
    parsed_config: dict[str, Any] = Field(default_factory=dict)
    verified: bool = False
    star_count: int = 0
    contributor_count: int = 0
    security_score: int | None = None
    download_count: int = 0
    rating: str | None = None
    latest_commit_id: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int
    skip: int
    limit: int


class AgentVersionResponse(BaseModel):
    version: str
    commit_id: str | None = None
    author: str | None = None
    message: str | None = None
    released_at: datetime | None = None
    download_count: int = 0

    class Config:
        from_attributes = True


class AgentVersionsResponse(BaseModel):
    agent_id: str
    versions: list[AgentVersionResponse]
```

### Task T5: 扩展 AgentRoutes

**修改文件**: `src/api/routes/agents.py`

```python
from src.api.schemas.agent import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentVersionsResponse,
    AgentVersionResponse,
)

@router.get("/", response_model=AgentListResponse)
async def list_agents(
    skip: int = Query(ge=0, default=0),
    limit: int = Query(ge=1, le=100, default=20),
    category: str | None = None,
    tags: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    repo = AgentRepository(db)
    agents, total = await repo.list(skip=skip, limit=limit, category=category, tags=tags)
    return AgentListResponse(
        agents=[agent_to_response(a) for a in agents],
        total=total,
        skip=skip,
        limit=limit,
    )

@router.get("/{agent_id:path}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    repo = AgentRepository(db)
    agent = await repo.get_by_agent_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent_to_response(agent)

@router.get("/{agent_id:path}/versions", response_model=AgentVersionsResponse)
async def get_agent_versions(agent_id: str, db: AsyncSession = Depends(get_db)):
    repo = AgentRepository(db)
    agent = await repo.get_by_agent_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    versions = await repo.get_versions(agent.id)
    return AgentVersionsResponse(
        agent_id=agent_id,
        versions=[AgentVersionResponse(
            version=v.version,
            commit_id=v.commit_id,
            author=v.author,
            message=v.message,
            released_at=v.released_at,
            download_count=v.download_count,
        ) for v in versions],
    )

@router.get("/{agent_id:path}/download")
async def download_agent(agent_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    repo = AgentRepository(db)
    agent = await repo.get_by_agent_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    download_url = await download_manager.get_download_url(
        agent.source, agent.source_url, agent.agent_id, agent.version, agent.latest_commit_id
    )

    await repo.increment_download(agent.id)
    return {"download_url": download_url}

@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(agent_data: AgentCreate, db: AsyncSession = Depends(get_db)):
    repo = AgentRepository(db)
    existing = await repo.get_by_agent_id(agent_data.agent_id)
    if existing:
        raise HTTPException(status_code=409, detail="Agent already exists")

    agent = await repo.create(agent_data.model_dump())
    return agent_to_response(agent)

@router.delete("/{agent_id:path}")
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    repo = AgentRepository(db)
    deleted = await repo.delete(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Agent deleted", "agent_id": agent_id}
```

### Task T8-T15: 前端任务

参见 `AgentDetail.vue` 页面结构：

```
AgentDetail.vue
├── Header Section
│   ├── Logo + Name
│   ├── Author + Verified Badge
│   ├── Version Selector
│   └── Stats (Stars, Downloads)
│
├── Tab Navigation
│   ├── Overview (默认)
│   ├── Skills
│   ├── Tools
│   ├── Subagents
│   └── Security
│
├── Tab Content
│   ├── Overview: README + Identity
│   ├── Skills: SkillCard 列表
│   ├── Tools: 权限表格
│   ├── Subagents: SubagentPanel 组件 (折叠)
│   └── Security: 安全报告
│
└── Sidebar
    ├── PlatformBadges
    ├── Category & Tags
    └── Action Buttons
```

---

## 9. 数据库迁移 SQL

```sql
-- 添加新字段到 agents 表
ALTER TABLE agents
ADD COLUMN logo_url TEXT,
ADD COLUMN homepage_url TEXT,
ADD COLUMN license VARCHAR(50),
ADD COLUMN readme_content TEXT,
ADD COLUMN agent_yaml_content TEXT,
ADD COLUMN parsed_config JSONB DEFAULT '{}',
ADD COLUMN supported_platforms TEXT[],
ADD COLUMN verified BOOLEAN DEFAULT FALSE,
ADD COLUMN star_count INTEGER DEFAULT 0,
ADD COLUMN contributor_count INTEGER DEFAULT 0,
ADD COLUMN latest_commit_id VARCHAR(40);

-- 创建 agent_versions 表
CREATE TABLE agent_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    version VARCHAR(50) NOT NULL,
    commit_id VARCHAR(40),
    author VARCHAR(255),
    message TEXT,
    released_at TIMESTAMPTZ,
    download_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(agent_id, version, commit_id)
);

-- 创建索引
CREATE INDEX idx_agents_source ON agents(source);
CREATE INDEX idx_agents_verified ON agents(verified);

-- 扩展 security_audits 表支持 agent 类型
-- (resource_type 字段已存在，只需确保 resource_id 可以关联 agent)
```

---

## 10. 版本历史

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| v1.0 | 2026-06-22 | 初始版本 |
