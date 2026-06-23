# Agent 详情页功能设计说明书

## 文档信息

| 项目 | 内容 |
|------|------|
| 项目名称 | SkillHub - Agent 详情页功能设计 |
| 文档版本 | v1.0 |
| 创建日期 | 2026-06-22 |
| 更新日期 | 2026-06-22 |
| 文档状态 | 进行中 |

---

## 1. 概述

### 1.1 项目背景

Agent 是基于 Universal Agent Specification (UAS) 标准定义的 AI Agent 配置文件。一个 Agent 以 Git 仓库形式存在，包含 `agent.yaml` 核心配置文件以及可选的 prompts、skills、subagents 等模块。

当前 SkillHub 平台已支持 Skills 的完整功能（浏览、搜索、下载、安全检测），需要扩展 Agent 的前后端能力，使其与 Skills 功能对齐。

### 1.2 设计目标

- 支持 Agent 的多版本管理
- 展示 Agent 的 YAML 配置解析内容（prompt、skills、tools、subagents 等）
- 支持多平台兼容性展示（Claude Code、OpenCode、OpenClaw、SDK）
- 提供与其他 Git 平台类似的详情页体验

---

## 2. 业界参考

### 2.1 参考平台

#### 1. AI Templates (aitmpl.com)

URL: https://www.aitmpl.com

**特点**:
- **Agent 分类展示**: Skills、Agents、Commands、Hooks、MCPs、Loops、Plugins 分开展示
- **Featured Integration**: 精选集成，带 Logo 和描述
- **Quick Install**: 一键安装命令 `npx claude-code-templates@latest --skill ...`
- **Verified Badge**: 认证标识
- **集成类型标签**: MCP、Skills、CLI、Platform
- **组件统计**: Components 数量、Tools 数量
- **平台支持**: E-Commerce、Professional Networks、Social Media 等
- **Use Cases**: 用例分类展示
- **Links Section**: Skills Repository、MCP Server、API Documentation 等链接
- **CTA Button**: "Try XXX Free" 带外部链接
- **Type/Category/Stage**: 类型、分类、阶段标识

**详情页结构** (以 Bright Data 为例):
```
┌─────────────────────────────────────────────────────────────┐
│ [Logo] Name                           [✓ Verified] [★ Rating] │
│ Type: Web Data | Category: Infrastructure                   │
├─────────────────────────────────────────────────────────────┤
│ [Try Free]  External Link                                   │
├─────────────────────────────────────────────────────────────┤
│ ## Overview                                                │
│ ## Template Architecture                                    │
│   - Skills Layer (search, scrape, data-feeds, MCP, etc.)  │
│   - Integration Layer (MCP)                               │
│   - Configuration Layer (.env vars)                        │
│ ## Installation                                            │
│   Option 1: Skills Only                                   │
│   Option 2: Complete Template                             │
│   Option 3: MCP Only                                      │
│ ## Supported Platforms                                     │
│   E-Commerce | Professional Networks | Social Media | etc.  │
│ ## Use Cases                                               │
│   Research | Competitive Intelligence | Lead Generation    │
│ ## Additional Resources                                   │
│   Links to Dashboard, Docs, GitHub, etc.                   │
├─────────────────────────────────────────────────────────────┤
│ Quick Install: npx claude-code-templates@latest --skill... │
├─────────────────────────────────────────────────────────────┤
│ Details: Type | Category | Components: 8 | Tools: 60+    │
│ Integration: MCP, Skills, CLI                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2. ClawHub (clawhub.ai)

URL: https://clawhub.ai

**特点**:
- **Publisher 展示**: 头像、名称、发布者页面
- **Trust Signals**: signed manifests、moderated releases、version history
- **OpenClaw Ecosystem**: crabbox、clickclack、crawler packs、gateway plugins
- **Category Navigation**: Skills、Plugins、Publishers、Audits
- **API Endpoints**: /api/v1/skills、/owners、/audit、/ship
- **安全特性**: safe browse paths、official gateways、publisher handles、org trust
- **CLI Tool**: clawhub publish & sync 命令
- **ecosystem 标识**: hooks、runners、slash-commands、skill.md、templates、scanners、review-bots

**关键功能**:
- Skills for apps (GitHub, VS Code, Notion, Slack, Gmail, Google Drive, etc.)
- Gateway plugins
- Signed manifests for package integrity

#### 3. GitHub Actions Marketplace

URL: https://github.com/marketplace

**特点**:
- 版本选择器（Version selector dropdown）
- Verified Badge 认证标识
- Star 数量统计
- 分类标签
- Tab 切换（Overview, Marketplace, Reviews）
- 一键安装按钮
- 贡献者列表

#### MCP Registry

URL: https://modelcontextprotocol.io/registry

**特点**:
- Logo + 名称 + 作者
- 下载数量统计
- Use Cases 用例列表
- Installation 多方式安装（VS Code、Docker、CLI）
- Configuration 配置示例代码
- Tools 工具列表及描述
- Resources 文档/源码/许可证链接

#### Universal Agent Template (agent_template)

URL: https://gitcode.com/duan_pengjie/agent_template

**Agent 仓库结构**:
```
agent-name/
├── agent.yaml              # 核心配置（必须）
├── README.md               # 说明文档
├── prompts/                # 外部 prompt 文件
│   ├── system.md
│   └── workflow.md
├── skills/                 # 绑定的 skills
│   └── tdd/
│       └── SKILL.md
├── subagents/              # 子代理定义
└── external/               # 跨平台模块
    ├── modules/
    └── openclaw/
```

**agent.yaml 核心字段**:

| 字段 | 必须 | 平台 | 说明 |
|------|:----:|------|------|
| `name` | ✓ | 全部 | 唯一标识，kebab-case |
| `prompt.system` | ✓ | 全部 | System prompt |
| `version` | - | registry | 语义化版本 |
| `description` | - | registry | 一行描述 |
| `author` | - | registry | 作者信息 |
| `tags` | - | registry | 搜索标签 |
| `repository` | - | registry | 仓库地址 |
| `model` | - | OC, SDK | LLM 配置 |
| `tools` | - | 全部 | 工具列表及权限 |
| `skills` | - | CC, OC, OCW | 技能引用 |
| `subagents` | - | 全部 | 子代理定义 |
| `openclaw` | - | OpenClaw | OpenClaw 独占模块 |

### 2.2 详情页信息架构

基于业界研究，Agent 详情页采用以下信息架构：

```
┌─────────────────────────────────────────────────────────────┐
│ [Logo] Agent Name                        [v1.0.0 ▼] [⭐ 128] │
│ By author_name                                          [✓] │
├─────────────────────────────────────────────────────────────┤
│ Description: Agent description here                       │
├─────────────────────────────────────────────────────────────┤
│ TABS: [Overview] [Installation] [Configuration] [Security]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Overview Tab:                                              │
│  ├── README Content (rendered markdown)                   │
│  ├── Prompts Section (system.md, workflow.md)             │
│  └── Bundled Skills list                                  │
│                                                             │
│  Installation Tab:                                         │
│  ├── CLI Install Command                                   │
│  └── Platform-specific Install Instructions                │
│                                                             │
│  Configuration Tab:                                        │
│  ├── agent.yaml full content                              │
│  ├── tools permission table                               │
│  └── subagents definition                                 │
│                                                             │
│  Security Tab:                                             │
│  ├── Security Score                                        │
│  ├── Risk Level                                            │
│  └── Risk Signals                                          │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Platforms: [Claude Code] [OpenCode] [OpenClaw] [SDK]       │
├─────────────────────────────────────────────────────────────┤
│ [⭐ Star] [📦 Download ZIP] [🔗 Source] [🐛 Report Issue] │
├─────────────────────────────────────────────────────────────┤
│ Tags: #code-review #security #productivity                 │
│ License: MIT | Category: development | Source: GitCode     │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 数据库设计

### 3.1 Agent 表

在现有 `agents` 表基础上扩展字段：

```sql
CREATE TABLE agents (
    -- 现有字段（保留）
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(255) UNIQUE NOT NULL,          -- 唯一标识 owner/repo
    name VARCHAR(255) NOT NULL,                      -- 显示名称
    description TEXT,                               -- 描述
    version VARCHAR(50),                            -- 当前版本
    author VARCHAR(255),                            -- 作者
    source VARCHAR(50) NOT NULL,                    -- Git托管平台 github/gitcode/gitee
    source_url TEXT NOT NULL,                        -- Git 仓库地址
    category VARCHAR(100),                           -- 分类
    tags TEXT[],                                    -- 标签数组
    extra_metadata JSONB DEFAULT '{}',              -- 额外元数据
    security_score INTEGER,                          -- 安全评分
    download_count INTEGER DEFAULT 0,               -- 下载次数
    rating VARCHAR(10),                             -- 评分
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_indexed_at TIMESTAMPTZ,

    -- 新增字段
    logo_url TEXT,                                  -- Logo URL
    homepage_url TEXT,                              -- 项目主页
    license VARCHAR(50),                            -- 许可证
    readme_content TEXT,                            -- README 全文（渲染用）
    agent_yaml_content TEXT,                        -- agent.yaml 原始内容
    parsed_config JSONB,                            -- 解析后的配置（prompt/tools/skills等）
    supported_platforms TEXT[],                     -- 支持的Agent平台列表 (claude-code/opencode/openclaw/sdk)
    verified BOOLEAN DEFAULT FALSE,                 -- 是否认证
    star_count INTEGER DEFAULT 0,                   -- Star 数量
    contributor_count INTEGER DEFAULT 0,            -- 贡献者数量
    latest_commit_id VARCHAR(40),                    -- 最新 commit ID
    min_agent_version VARCHAR(50),                  -- 最低兼容版本

    -- 索引
    INDEX idx_agents_category (category),
    INDEX idx_agents_tags USING GIN(tags),
    INDEX idx_agents_source (source),
    INDEX idx_agents_created_at DESC (created_at),
    UNIQUE INDEX idx_agents_source_url_version (source, source_url, version, latest_commit_id)
);
```

### 3.2 字段说明：source vs supported_platforms

| 字段 | 含义 | 示例值 |
|------|------|--------|
| `source` | Git 托管平台（代码仓库所在） | github, gitcode, gitee, gitlab |
| `supported_platforms` | Agent 运行的目标平台 | claude-code, opencode, openclaw, sdk |

**与 Skill 对比**：

| 资源 | source 字段 | platform 字段 |
|------|-------------|--------------|
| Skill | Git 托管平台 (github/gitcode/gitee) | Skill 运行平台 (claude-code/opencode) |
| Agent | Git 托管平台 (github/gitcode/gitee) | Agent 支持的平台 (claude-code/opencode/openclaw/sdk) |

**说明**：Skill 的 `platform` 字段表示 Skill 运行的目标平台。Agent 由于支持更多平台（claude-code, opencode, openclaw, sdk），使用数组 `supported_platforms` 而非单一值。

### 3.3 Agent 与 Model 解耦设计

**设计原则**：Agent 定义与 Model 配置解耦

| 组件 | 归属 | 说明 |
|------|------|------|
| prompt.system | Agent | System prompt 是 Agent 核心 |
| skills | Agent | 依赖的 Skills 列表 |
| tools | Agent | 工具权限配置 |
| subagents | Agent | 子代理定义 |
| model | 运行时 | 由平台/CLI 在运行时决定 |

**原因**：
1. 同一 Agent 可以在不同模型上运行（Claude、GPT-4、Gemini 等）
2. Model 是基础设施选择，Agent 是能力定义
3. 保持 Agent 的可移植性

**parsed_config 结构**（不含 model）：

```python
parsed_config = {
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
        "permission": {...}
    },
    "skills": [
        {"name": "tdd", "source": "./skills/tdd/SKILL.md", "when": ["TDD"]},
        {"name": "security", "inline": "...", "when": ["security"]}
    ],
    "subagents": [...]
}
```

### 3.4 Agent 版本表

```sql
CREATE TABLE agent_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    version VARCHAR(50) NOT NULL,                   -- 版本号
    commit_id VARCHAR(40),                         -- Commit ID
    author VARCHAR(255),                          -- 版本作者
    message TEXT,                                 -- Commit message
    released_at TIMESTAMPTZ,                      -- 发布时间
    download_count INTEGER DEFAULT 0,              -- 该版本下载次数
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE INDEX idx_agent_version_unique (agent_id, version, commit_id)
);
```

### 3.5 Agent 模型类（Python/SQLAlchemy）

```python
class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    commit_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

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
    min_agent_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 关系
    versions: Mapped[list["AgentVersion"]] = relationship(back_populates="agent", cascade="all, delete-orphan")
    audits: Mapped[list["SecurityAudit"]] = relationship(back_populates="agent", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_agents_category", "category"),
        Index("idx_agents_tags", "tags", postgresql_using="gin"),
        Index("idx_agents_source", "source"),
        Index("idx_agents_created_at", desc("created_at")),
    )


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

### 3.6 SecurityAudit 表扩展

扩展 `resource_type` 支持 agent：

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
```

---

## 4. API 设计

### 4.1 Agent 相关端点

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/agents/` | 列表查询（分页、筛选） |
| GET | `/api/v1/agents/{agent_id}` | 获取详情 |
| GET | `/api/v1/agents/{agent_id}/versions` | 获取版本列表 |
| GET | `/api/v1/agents/{agent_id}/download` | 获取下载链接 |
| GET | `/api/v1/agents/{agent_id}/audit` | 获取安全报告 |
| POST | `/api/v1/agents/` | 创建 Agent（爬虫/导入） |
| DELETE | `/api/v1/agents/{agent_id}` | 删除 Agent |

### 4.2 请求/响应示例

#### GET /api/v1/agents/{agent_id}

```json
{
  "id": "uuid",
  "agent_id": "duan-pengjie/code-reviewer",
  "name": "Code Reviewer",
  "description": "A senior code reviewer focused on security and quality",
  "version": "1.0.0",
  "commit_id": "abc123...",
  "author": "duan_pengjie",
  "source": "gitcode",
  "source_url": "https://gitcode.com/duan_pengjie/code-reviewer",
  "category": "development",
  "tags": ["code-review", "security", "quality"],
  "logo_url": "https://gitcode.com/.../logo.png",
  "homepage_url": "https://...",
  "license": "MIT",
  "readme_content": "# README content...",
  "agent_yaml_content": "完整 YAML 内容...",
  "parsed_config": {
    "prompt": {
      "system": "You are a senior code reviewer...",
      "identity": {
        "role": "Senior Software Engineer",
        "emoji": "🧐",
        "vibe": "professional"
      }
    },
    "tools": {
      "allowed": ["read", "grep", "glob", "bash"]
    },
    "skills": [
      {"name": "tdd", "source": "./skills/tdd/SKILL.md", "when": ["TDD"]}
    ]
  },
  "supported_platforms": ["claude-code", "opencode", "openclaw", "sdk"],
  "verified": false,
  "star_count": 128,
  "contributor_count": 3,
  "security_score": 85,
  "download_count": 1024,
  "rating": "4.8",
  "min_agent_version": "1.0.0",
  "created_at": "2026-01-15T10:00:00Z",
  "updated_at": "2026-06-01T15:30:00Z"
}
```

#### GET /api/v1/agents/{agent_id}/versions

```json
{
  "agent_id": "duan-pengjie/code-reviewer",
  "versions": [
    {
      "version": "1.0.0",
      "commit_id": "abc123...",
      "author": "duan_pengjie",
      "message": "feat: initial release",
      "released_at": "2026-01-15T10:00:00Z",
      "download_count": 500
    },
    {
      "version": "1.1.0",
      "commit_id": "def456...",
      "author": "duan_pengjie",
      "message": "feat: add TDD skill",
      "released_at": "2026-03-20T14:00:00Z",
      "download_count": 524
    }
  ]
}
```

---

## 5. 前端页面设计

### 5.1 AgentDetail.vue 页面结构

```
AgentDetail.vue
├── Header Section
│   ├── Logo + Name
│   ├── Author + Verified Badge
│   ├── Version Selector (dropdown)
│   └── Stats (Stars, Downloads)
│
├── Tab Navigation
│   ├── Overview (默认)
│   ├── Installation
│   ├── Configuration
│   └── Security
│
├── Overview Tab Content
│   ├── README (rendered markdown)
│   ├── Prompts Section (system prompt preview)
│   └── Skills List (bundled skills)
│
├── Installation Tab Content
│   ├── CLI Install Command
│   └── Platform-specific Instructions
│
├── Configuration Tab Content
│   ├── Full agent.yaml (syntax highlighted)
│   ├── Tools Permission Table
│   └── Subagents Definition
│
├── Security Tab Content
│   ├── Security Score Badge
│   ├── Risk Level Indicator
│   └── Risk Signals List
│
└── Sidebar
    ├── Platform Badges
    ├── Category & Tags
    ├── License & Source
    └── Action Buttons (Star, Download, Source)
```

### 5.2 关键组件

| 组件 | 位置 | 说明 |
|------|------|------|
| `AgentCard.vue` | `web/src/components/` | Agent 卡片（列表页用） |
| `AgentDetail.vue` | `web/src/pages/` | Agent 详情页 |
| `VersionSelector.vue` | `web/src/components/` | 版本选择器 |
| `PlatformBadge.vue` | `web/src/components/` | 平台徽章 |
| `ParsedConfigViewer.vue` | `web/src/components/` | YAML 配置查看器 |
| `ReadmeRenderer.vue` | `web/src/components/` | README 渲染器 |

### 5.3 类型定义

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
  min_agent_version: string | null
  created_at: string | null
  updated_at: string | null
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
  skills?: Array<{
    name: string
    source?: string
    inline?: string
    installed?: string
    when?: string[]
  }>
  subagents?: any[]
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

## 6. 实现计划

### 6.1 后端实现

| 任务 | 优先级 | 说明 |
|------|--------|------|
| 扩展 Agent 模型字段 | P0 | 添加新字段到 models.py |
| 创建 AgentVersion 模型 | P0 | 版本管理 |
| 扩展 AgentRepository | P0 | 版本查询方法 |
| 扩展 AgentRoutes | P0 | versions、download 端点 |
| 创建 AgentSchema | P0 | Pydantic 响应模型 |
| 解析 agent.yaml | P1 | 提取 prompt/tools/skills |
| 安全审计支持 agent | P2 | 扩展 SecurityAudit |

### 6.2 前端实现

| 任务 | 优先级 | 说明 |
|------|--------|------|
| 添加 Agent 类型定义 | P0 | types.ts |
| 扩展 API Client | P0 | agent 相关方法 |
| 创建 AgentCard 组件 | P0 | 列表页卡片 |
| 创建 AgentDetail 页面 | P0 | 详情页 |
| 实现 VersionSelector | P1 | 版本切换 |
| 实现 PlatformBadge | P1 | 平台徽章 |
| 实现 ParsedConfigViewer | P2 | YAML 查看器 |
| 添加 Agent 路由 | P0 | router.ts |

---

## 7. 版本历史

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| v1.0 | 2026-06-22 | 初始版本 |
