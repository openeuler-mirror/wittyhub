# SkillHub

AI Agent Skills 检索与分发平台。发现、评估和获取可复用的 AI Agent Skills，支持关键词搜索、分类浏览、安全检测。

## 特性

### 核心功能
- **Skill 发现与搜索** - 支持全文搜索、分类筛选、标签过滤
- **多版本管理** - 支持 Skill 的多个版本，查看版本历史
- **安全检测** - 自动进行安全扫描，生成风险评估报告
- **CLI 工具** - 一键安装 Skills 到本地 `~/.agents/skills/` 目录

### 技术优势
- **高性能** - 基于 FastAPI + Uvicorn，提供异步 API
- **快速搜索** - Meilisearch 全文搜索引擎，毫秒级响应
- **安全可靠** - 代码安全扫描、依赖检查、风险信号识别
- **易于部署** - Docker Compose 一键部署
- **现代化前端** - Vue 3 + TypeScript，支持暗色模式

## 架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   前端 Vue   │────▶│  Nginx 代理 │────▶│   FastAPI   │
│   (Port 80) │     │             │     │  (Port 8080)│
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                    ┌─────────────┬────────────┤
                    │             │            │
               ┌────▼────┐  ┌────▼────┐ ┌────▼────┐
               │PostgreSQL│  │Meilisearch│ │ LocalFS │
               │ (5432)   │  │  (7700)  │ │ /data   │
               └──────────┘  └──────────┘ └─────────┘
```

## 快速开始

### 环境要求
- Docker & Docker Compose
- Python 3.10+ (本地开发)

### Docker 部署

1. 克隆项目
```bash
git clone https://gitcode.com/your-username/skillhub.git
cd skillhub
```

2. 启动服务
```bash
cd deploy/docker
docker-compose up -d
```

3. 初始化数据库
```bash
docker exec skillhub-api python -m src.migrations.env  # 运行迁移
# 或使用脚本
./scripts/init_db.sh
```

4. 生成测试数据
```bash
docker exec skillhub-api python scripts/generate_test_data.py \
  --host skillhub-db --password skillhub_secret
```

5. 访问服务
- 前端: http://localhost:8090
- API: http://localhost:8081
- API 文档: http://localhost:8081/docs

### 本地开发

1. 安装依赖
```bash
pip install -e ".[dev]"
```

2. 配置数据库
```bash
cp config.yaml.example config.yaml
# 编辑 config.yaml 配置数据库连接
```

3. 运行迁移
```bash
alembic upgrade head
```

4. 启动服务
```bash
# 前端
cd web && npm install && npm run dev

# 后端
uvicorn src.api.main:app --reload --port 8080
```

## 使用指南

### Web 界面

1. **浏览 Skills**
   - 首页展示热门 Skills 和分类导航
   - 点击分类查看该分类下的所有 Skills

2. **搜索 Skills**
   - 使用搜索框输入关键词
   - 支持按分类、平台、标签筛选

3. **查看详情**
   - 点击 Skill 卡片进入详情页
   - 查看版本历史、安全报告、安装命令

### CLI 工具

```bash
# 搜索 Skills
skillhub search "api framework"

# 查看 Skill 详情
skillhub show python-api-framework

# 安装 Skill
skillhub install python-api-framework

# 查看已安装的 Skills
skillhub list
```

### API 调用

```bash
# 获取所有 Skills
curl http://localhost:8081/api/v1/skills/?limit=10

# 搜索 Skills
curl "http://localhost:8081/api/v1/index/search?q=api"

# 获取分类
curl http://localhost:8081/api/v1/index/categories

# 获取 Skill 详情
curl http://localhost:8081/api/v1/skills/python-api-framework

# 获取版本历史
curl http://localhost:8081/api/v1/skills/python/api-framework/versions
```

## 项目结构

```
skillhub/
├── src/
│   ├── api/              # FastAPI 应用
│   │   ├── routes/      # API 路由
│   │   ├── models/       # 数据模型
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # 业务逻辑
│   ├── cli/              # CLI 工具
│   ├── core/             # 核心配置
│   ├── indexer/          # 搜索引擎索引
│   ├── security/         # 安全扫描
│   ├── storage/          # 文件存储
│   ├── migrations/       # 数据库迁移
│   └── utils/            # 工具函数
├── web/                  # Vue 3 前端
│   └── src/
│       ├── components/    # 组件
│       ├── pages/        # 页面
│       ├── api/          # API 客户端
│       └── router/       # 路由配置
├── scripts/              # 脚本
│   ├── init_db.sh        # 数据库初始化
│   └── generate_test_data.py  # 测试数据生成
├── deploy/               # 部署配置
│   └── docker/           # Docker 部署
└── tests/                # 测试
```

## 配置说明

主要配置项 (`config.yaml`):

```yaml
database:
  host: skillhub-db
  port: 5432
  user: skillhub
  password: your_password
  dbname: skillhub

meilisearch:
  host: http://skillhub-search:7700
  api_key: your_api_key

storage:
  type: local
  local_path: /data/skills
  github_token: your_github_token

security:
  enable_audit: true

app:
  host: 0.0.0.0
  port: 8080
  cors_origins:
    - "*"
```

## 开发指南

### 运行测试
```bash
pytest tests/ -v
```

### 代码检查
```bash
ruff check .
mypy src/
```

### 构建前端
```bash
cd web
npm install
npm run build
```

## License

MIT License
