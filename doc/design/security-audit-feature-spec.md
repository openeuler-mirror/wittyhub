# 安全审计功能设计说明书

## 一、功能概述

安全审计在 Skill 入库后自动触发，基于 [NVIDIA SkillSpector](https://github.com/NVIDIA/SkillSpector) 对 Skill 源码执行深度扫描：

| 扫描层 | 引擎 | 检测内容 |
|------|------|------|
| 深度审计 | Skillspector（Jenkins Job） | 68 项漏洞模式 × 17 大类 + LLM 语义分析 |

扫描结果写入 `skills.risk_score` 和 `security_audits` 表，前端通过 API 查询渲染安全报告。

---

## 二、总开关

```yaml
# config.yaml
security:
  enable_audit: true   # 关闭则跳过全部审计
```

```mermaid
flowchart TD
    A[拉取仓库更新] --> B[数据库记录已存在]
    B --> C{当前 HEAD 与数据库 commit 相同?}
    C -->|相同| D[存在 risk_score 为 NULL 的记录?]
    D -->|是| E[重试触发这些记录的审计]
    D -->|否| F[标记 unchanged 并返回]
    C -->|不同| G[重新扫描 SKILL.md]
    G --> H[安全检测结果复用判断]
    H -->|内容未变| I[复用已有结果，不重复提交]
    H -->|内容有变| J[物化 blob 后异步触发 Skillspector]
    J --> K[保存安全检测任务信息]
```

---

## 三、完整审计链路

### 3.1 爬虫 discover 链路（主要触发源）

```
skillcrawler（后台定时 discover）

skill_manager.py : discover_skill_repository()
  │
  ├── 拉取仓库更新（partial clone: --depth 1 --no-checkout --filter=blob:none）
  │
  ├── 当前 HEAD 与数据库 repository_commit_id 相同（_is_commit_unchanged）
  │     └── _retry_unscored_security_audits()
  │           ├── 查询该仓库 risk_score 为 NULL 的 skills/skill_versions
  │           ├── 有 → 逐条重新触发 Skillspector（自愈上次失败的审计）
  │           │      日志: retry unscored audits for unchanged repo %s:
  │           │             triggered=%d skipped=%d total_unscored=%d
  │           └── 无 → 标记 unchanged 直接返回（不触发审计）
  │
  └── HEAD 已变更 → 完整扫描
        │
        ├── _scan_latest_skills()   ← HEAD 上的技能
        ├── _scan_tagged_skills()  ← 最近 N 个 tag（config: max_tags_per_repo，默认 5）
        │     ├── commit 预去重: (skill_id, commit_id) 已见 → 跳过组装
        │     └── version 去重: (skill_id, version) 已见 → 丢弃重复记录
        │
        └── 两者组装每个 skill 时均调用 _build_skill_record()
              → _resolve_security_result() 决定是否触发审计（见下方三层复用）
                ├── 可复用 → 不提交 Jenkins，直接使用历史/缓存评分
                └── 需新提交 → _audit_skill_security()
                      ├── 物化 blob（partial clone 无 blob，需预先拉取）
                      ├── async_mode=True  → trigger_skillspector()
                      │     details: { skillspector_async: true, build_number: N }
                      │     risk_score 暂为 NULL，等 Collector 回写

  安全审计复用判定与提交（skill_scanner.py : _resolve_security_result，三层策略）
    │  返回 SecurityResolution(risk_score, audit_details, audit_triggered)
    │
    ├── ① DB 历史复用: existing_record.tree_hash == 新 tree_hash 且 risk_score 非 NULL
    │      → 直接复用历史评分，不提交 Jenkins
    ├── ② 扫描级缓存复用: security_cache[tree_hash]（同一次扫描内，latest 与 tag 内容相同）
    │      → 复用首次提交结果（含等待 Jenkins 回写的 pending 状态）
    └── ③ 新提交: _audit_skill_security()
          ├── 物化 blob（见 3.1.1）
          ├── trigger_skillspector() → 触发 Jenkins 异步审计
          └── 返回details记录: { skillspector_async: true, skillspector_build_number: N }

扫描完成日志（skill_manager.py）:（见 3.1.2）
  Discover: scan completed for %s: latest_skills=%d, tagged_skills=%d,
  security_cache_hits=%d, security_audits_submitted=%d, security_audits_pending=%d

异步结果回写: SkillspectorCollector（见 3.2 异步模式）
```

#### 3.1.1 blob 物化（触发 Jenkins 前置步骤）

缓存仓库是 `--filter=blob:none` 的 partial clone，本地只有 commit 和 tree 元数据。
skillspector 容器以只读方式挂载缓存目录且无网络访问，无法在容器内懒拉取 blob。
因此爬虫在宿主机上（缓存可写、网络可用）触发 Jenkins 前调用
`git_operations.materialize_skill_objects()`：

```
ls-tree 列出技能路径下全部 blob
  → cat-file --batch-check 触发 Git on-demand 懒拉取（写入 .git/objects/pack/）
  → 校验输出无 missing
```

物化失败时跳过本次审计（`details.error = materialize_failed`，不缓存结果），
下轮 discover 检测到 risk_score 仍为 NULL 会自动重试。

#### 3.1.2 统计指标说明

| 指标 | 含义 |
|------|------|
| `security_cache_hits` | 命中 ①DB 复用 或 ②扫描级缓存的次数 |
| `security_audits_submitted` | 新提交到 Jenkins 的审计次数 |
| `security_audits_pending` | 已提交且等待 Jenkins 回写结果的次数（submitted 的子集） |

三者关系: 
- `cache_hits + submitted = latest_skills + tagged_skills`（去重后的记录总数）
- `pending ≤ submitted`

### 3.2 异步模式下后台收集安全审计结果

```
async_mode=True（爬虫 discover 或 API 手动触发均可启用）

  SkillspectorClient.trigger_scan()
    └── POST Jenkins /buildWithParameters
        details 记录: { skillspector_async: true, skillspector_build_number: N }

后台收集: SkillspectorCollector（每 30s，仅 enable_audit=true + 凭证已配时启动）
  ├── 查询 pending audits（skillspector_async=true, collected=null）
  ├── wait_for_build(N)
  ├── fetch_report(N)
  └── 回写 skills.risk_score（风险分）+ security_audits
```

启动: `src/security/detector.py` → `start_skillspector_collector()`（内部自行导入 `AsyncSessionLocal`），由 `src/api/main.py` lifespan 调用。

---

## 四、模块架构

```
skillcrawler/                      ← 爬虫侧（discover 主要触发源）
  core/skill_manager.py
  │   ├── discover_skill_repository()      ← 入口: commit 未变 → 重试未评分审计
  │   ├── _retry_unscored_security_audits() ← 重试 risk_score=NULL 的记录
  │   └── _store_to_security_audits()     ← 扫描后写入 security_audits
  core/skill_scanner.py
  │   ├── _scan_latest_skills()           ← HEAD 技能扫描
  │   ├── _scan_tagged_skills()           ← tag 技能扫描（commit/version 去重）
  │   ├── _resolve_security_result()      ← 三层复用（DB / 扫描缓存 / 新提交）
  │   └── _audit_skill_security()         ← 物化 blob + 触发 Jenkins
  └── core/git_operations.py
      ├── get_skill_tree_hashes()         ← 目录级 tree hash（复用 key）
      └── materialize_skill_objects()     ← 触发前物化技能路径 blob

src/security/detector.py          ← 唯一核心（扫描逻辑 + Collector 工厂函数）
  ├── SecurityDetector             ← 总入口
  ├── SkillspectorClient           ← Jenkins HTTP 交互
  ├── SkillspectorCollector        ← 后台异步回写
  └── start_skillspector_collector()  ← 工厂函数（内部导入 AsyncSessionLocal）

src/api/services/security.py      ← 编排层
  └── SecurityService.audit_skill()

src/api/routes/skills.py          ← 业务入口
  ├── trigger_skill_audit()       ← POST /skills/{id}/audit  手动触发
  └── audit_skill()               ← GET  /skills/{id}/audit  查询结果

src/models/repository.py
  ├── SkillRepository.create()    ← 纯数据写入，不触发审计
  ├── SkillRepository.update()    ← 审计结果回写 risk_score
  ├── SkillRepoRepository         ← skill_repos 表 CRUD
  └── SecurityAuditRepository     ← security_audits 表 CRUD

src/api/main.py                   ← lifespan 调用 start_skillspector_collector()
```

---

## 五、数据库表

### 5.1 skills.risk_score

| 字段 | 类型 | 说明 |
|------|------|------|
| `risk_score` | `INTEGER` | SkillSpector 风险分：0=safe → 100=critical。未审计时为 `NULL` |

### 5.2 security_audits

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `UUID` | 主键 |
| `resource_type` | `VARCHAR(20)` | 固定 `"skill"` |
| `resource_id` | `UUID` | `skills.id` 外键 |
| `version` | `VARCHAR(50)` | Skill 版本号 |
| `commit_id` | `VARCHAR(40)` | Git commit |
| `audit_type` | `VARCHAR(50)` | 扫描器组合：`skillspector`；无扫描时 `none` |
| `risk_level` | `VARCHAR(20)` | `critical` / `high` / `medium` / `low` / `unknown` |
| `risk_signals` | `JSONB` | 风险信号数组 |
| `details` | `JSONB` | 扫描元数据 + 完整 report.json |
| `audited_at` | `TIMESTAMPTZ` | 审计时间 |

**details 结构**:

```json
{
    "scanners": ["skillspector"],
    "skillspector_score": 85,
    "skillspector_version": "2.3.1",
    "recommendation": "SAFE",
    "skillspector_report": { /* Jenkins 返回的完整 report.json，供前端渲染 */ }
}
```

**索引**: `(resource_type, resource_id)`, `risk_level`, `audited_at DESC`, `(resource_id, version, commit_id)`

---

## 六、对外 API 接口

### 6.1 已入库 Skill 重审

```
POST /api/v1/skills/{skill_id}/audit
```

鉴权: `require_admin_token`。对已入库 Skill 重新触发安全审计。

| Query 参数 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `scanners` | `str` | 否 | 逗号分隔: `skillspector`。默认自动检测可用扫描器 |
| `async_mode` | `bool` | 否 | `true` = 仅触发不等待结果（默认 `false`） |

**调用链路**:

```
routes/skills.py : trigger_skill_audit()
  ├── skill 不存在 → 404
  ├── enable_audit == false → 503
  │
  └── SecurityService.audit_skill()
        ├── source_url 优先取 skill.repo_url（Jenkins 需要合法 git 仓库 URL）
        ├── version 取 skill.commit_id（Jenkins 需要真实 git ref）
        ├── skill_path 由 _derive_scan_skill_path() 推导
        │
        ├── async_mode == false（同步）
        │     ├── detect_skillspector() → 轮询 Jenkins（每5秒，最多150秒）
        │     ├── GET /artifact/reports/skillspector/report.json
        │     ├── report_to_risk_signals()
        │     └── risk_score = report.risk_assessment.score（SkillSpector 风险分）
        │
        └── async_mode == true（异步）
              ├── trigger_skillspector() → 触发 Jenkins 异步审计
              └── risk_level = unknown, risk_score = NULL（等 Collector 回写）

  持久化（audit_skill 内部 upsert_by_resource 保证幂等）
    ├── upsert security_audits（风险信号 + 完整 report.json）
    ├── update skills.risk_score
    └── commit
```

**返回** `SecurityAuditResponse`（含 `risk_level` / `risk_signals` / `details`）。

### 6.2 外部 Git URL 一次性审计（PR 门禁）

```
POST /api/v1/skills/audit-by-url
```

鉴权: `require_admin_token`。对未入库的 Git 仓库或 SKILL.md 链接执行一次性审计，不写库。
用于 openEuler-skills PR 门禁：在内容合入索引前执行安全审计，**仅返回结果**。

**请求体** `AuditByUrlRequest`:

| 字段 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `repo_url` | `str` | 二选一 | 仓库 URL（审计整个仓库） |
| `skill_url` | `str` | 二选一 | `.../blob/<ref>/<path>/SKILL.md`（审计单个 skill） |
| `branch` | `str` | 否 | 指定分支，默认 `ls-remote` 解析 |
| `scanners` | `str` | 否 | 逗号分隔扫描器列表 |
| `async_mode` | `bool` | 否 | `true`，直接返回 `build_number` |

**调用链路**:

```
routes/skills.py : audit_by_url()
  ├── repo_url 和 skill_url 均为空 → 422
  ├── _derive_audit_target() 解析 git_url / ref / skill_path（纯解析，无网络）
  ├── validate_git_url() → SSRF 校验
  ├── ref 为空 → _resolve_default_branch()（git ls-remote，线程池执行）
  │
  └── SecurityService.audit_external(git_url, ref, skill_path, ...)
        ├── async_mode == false → 同步等待 Jenkins 返回完整报告
        └── async_mode == true  → 触发 Jenkins 异步审计，返回 build_number

  不持久化，details 中携带 skillspector_build_number 供轮询
```

**返回** `AuditByUrlResponse`（含 `risk_level` / `risk_score` / `risk_signals` / `details`，不持久化）。

### 6.3 异步审计结果轮询

```
GET /api/v1/skills/audit-by-url/result?build_number=N
```

鉴权: `require_admin_token`。轮询 `audit-by-url` 异步扫描的结果。

| Query 参数 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `build_number` | `int` | 是 | Jenkins build 编号（≥1） |

**调用链路**:

```
routes/skills.py : audit_by_url_result()
  └── SecurityService.get_external_result(build_number)
        ├── Jenkins build 仍在运行 → status = "pending"
        ├── 报告已收集 → status = "done" + 完整审计结果
        └── Jenkins 失败 → status = "error"
```

**返回** `AuditByUrlResultResponse`:

```json
{
    "status": "pending" | "done" | "error",
    "risk_level": "low",
    "risk_score": 85,
    "risk_signals": [ /* ... */ ],
    "details": { /* skillspector_report 等 */ }
}
```

### 6.4 审计报告下载

```
GET /api/v1/skills/audit-by-url/report?build_number=N&filename=...
```

**无鉴权**（PR 门禁评论中的详情链接，可直接浏览器打开）。按需从 Jenkins artifact 拉取 `report.md`，返回 `text/markdown` 附件下载。

| Query 参数 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `build_number` | `int` | 是 | Jenkins build 编号 |
| `filename` | `str` | 否 | 自定义下载文件名，非 ASCII 使用 RFC 5987 编码 |

**调用链路**:

```
routes/skills.py : audit_by_url_report()
  └── SecurityService.get_external_report_md(build_number)
        ├── 从 Jenkins artifact 按需拉取 report.md
        └── 返回 text/markdown + Content-Disposition 附件下载
              非 ASCII 文件名使用 RFC 5987 filename* 编码
```

### 6.5 查询审计结果

```
GET /api/v1/skills/{skill_id}/audit
```

返回最近一次审计记录，无记录返回 `{"error": "No audit found"}`。

**返回** `SecurityAuditResponse`:

```json
{
    "id": "uuid",
    "resource_type": "skill",
    "resource_id": "uuid",
    "version": "v1.0.0",
    "commit_id": "abc1234",
    "audit_type": "skillspector",
    "risk_level": "low",
    "risk_signals": [
        {
            "id": "SQP-1",
            "name": "Skillspector SQP-1 (SKILL.md:12)",
            "description": "Skill references external API...",
            "severity": "MEDIUM",
            "data": {
                "confidence": 0.6,
                "location": { "file": "SKILL.md", "start_line": 12, "end_line": 19 },
                "remediation": "...",
                "source": "skillspector"
            }
        }
    ],
    "details": {
        "scanners": ["skillspector"],
        "skillspector_score": 85,
        "skillspector_version": "2.3.1",
        "recommendation": "SAFE",
        "skillspector_report": { /* Jenkins 原始 report.json，前端直接渲染 */ }
    },
    "audited_at": "2026-07-14T12:00:00Z"
}
```

### 6.6 SecurityService 内部接口

```python
# 已入库 Skill 审计（写库）
async def audit_skill(
    skill_id: str,                        # skill 唯一标识
    source: str,                          # "github" / "gitcode" / "clawhub"
    source_url: str,                      # 仓库 URL（优先 repo_url）
    metadata: dict[str, Any],             # { version, commit_id, content, skill_path }
    scanners: list[str] | None = None,    # None → 自动检测可用扫描器
    async_mode: bool = False,             # True → 仅触发不等待结果，返回 build_number
) -> dict[str, Any]:

# 外部 Git URL 一次性审计（不写库，PR 门禁用）
async def audit_external(
    git_url: str,                         # 合法 git 仓库 URL
    ref: str = "main",                    # git ref（branch / tag / commit）
    skill_path: str = "",                 # 仓库内 skill 子路径（空=整仓库）
    scanners: list[str] | None = None,
    async_mode: bool = False,
) -> dict[str, Any]:

# 轮询 audit_external 异步结果
async def get_external_result(build_number: int) -> dict[str, Any]:
    # → { status: "pending"|"done"|"error", risk_level, risk_score, ... }

# 拉取 audit_external 的 report.md
async def get_external_report_md(build_number: int) -> str | None:
```

**audit_skill 返回**:

```json
{
    "risk_level": "low",
    "risk_signals": [
        { "id": "...", "name": "...", "description": "...", "severity": "..." }
    ],
    "risk_score": 75,
    "scanners": ["skillspector"]
}
```

**audit_external 返回**（不持久化）:

```json
{
    "git_url": "https://github.com/owner/repo",
    "ref": "main",
    "skill_path": "skills/my-skill",
    "risk_level": "low",
    "risk_score": 10,
    "risk_signals": [ /* ... */ ],
    "details": {
        "scanners": ["skillspector"],
        "skillspector_build_number": 42,
        "skillspector_async": true
    }
}
```

---

## 七、评分计算

### 7.1 两阶段分析流程

```
Stage 1: 静态分析（始终执行）              Stage 2: LLM 语义分析（可选）
  ├─ 正则模式匹配（11 个静态分析器）          ├─ 评估上下文和意图
  ├─ AST 行为分析（exec/eval/subprocess）     ├─ 过滤误报
  ├─ YARA 签名匹配                            └─ 精确率提升至 ~87%
  └─ SC4 实时 CVE 查询（OSV.dev）
```

### 7.2 SkillSpector 风险累积分

NVIDIA SkillSpector 采用**累积分制**（高=危险），单个漏洞分值如下：

| 漏洞等级 | 分值 | 可执行脚本加成 |
|----------|:----:|:--------------:|
| CRITICAL | +50 | ×1.3 |
| HIGH | +25 | ×1.3 |
| MEDIUM | +10 | ×1.3 |
| LOW | +5 | ×1.3 |

> 存在 `.py` / `.sh` / `.js` 等可执行脚本时，总风险分 **×1.3** 倍。研究数据：含可执行脚本的 skill 漏洞概率是纯声明式的 **2.12 倍**。

```
SkillSpector 风险分 = min(Σ(漏洞数 × 分级分值) × 可执行脚本加成, 100)
```

### 7.3 五个风险等级（SkillSpector 标准）

| 风险分 | 等级 | 建议 | 含义 |
|:------:|------|------|------|
| **81–100** | `critical` | 🚫 DO NOT INSTALL | 疑似恶意代码或已知恶意特征 |
| **51–80** | `high` | 🚫 DO NOT INSTALL | 发现高危漏洞（数据外泄、权限提升） |
| **21–50** | `medium` | ⚠️ CAUTION | 存在中等风险，建议人工审查 |
| **0–20** | `low` | ✅ SAFE | 无显著漏洞，可放心安装 |
| — | `unknown` | ❓ 未扫描 | 无可用扫描器或扫描未产生结果，风险不明确 |

#### 降级回退

当 SkillSpector 不可用时，根据风险信号数量估算风险分：

| risk_level | 估算风险分 | 说明 |
|------|:--:|------|
| `critical` | 90 | 存在 Critical 信号 |
| `high` | 65 | 存在 High 信号，无 Critical |
| `medium` | 35 | 存在 Medium 信号 |
| `low` | 10 | 仅有 Low 信号 |
| `unknown` | NULL | 无可用扫描器或扫描失败，不评分 |

| 场景 | 处理 |
|------|------|
| 无可用扫描器 | `risk_level = unknown` → `risk_score = NULL` |
| Jenkins 不可达 | `risk_level = unknown` → `risk_score = NULL` |
| 审计异常 | 捕获异常不阻塞入库，`risk_score` 保持 NULL |

### 7.5 影响评分的 17 大类因素（SkillSpector 68 项检测模式）

| 类别 | ID | 等级 | 检测项 | 说明 |
|:-----|:--:|:----:|--------|------|
| **1. Prompt Injection**<br>提示注入 | P1 | HIGH | 指令覆盖 | 要求 Agent 忽略安全约束：`disregard previous instructions` |
| | P2 | HIGH | 隐藏指令 | HTML注释/零宽字符/不可见文本中嵌入指令，绕过人工审查 |
| | P3 | HIGH | 外泄指令 | 指示 Agent 将上下文/系统提示发送到外部 URL 或写入文件 |
| | P4 | MEDIUM | 行为操控 | 以微妙措辞诱导 Agent 偏离预期决策 |
| | P5 | CRITICAL | 有害内容 | 包含可能导致物理伤害的指令 |
| **2. Anti-Refusal**<br>反拒绝 | AR1 | HIGH | 拒绝抑制 | `never refuse` / `always comply` / `you must obey` |
| | AR2 | HIGH | 免责声明抑制 | `no disclaimers` / `do not moralize`，省略安全警告 |
| | AR3 | HIGH | 安全策略作废 | Jailbreak：`no restrictions` / `ignore guidelines` / `DAN` |
| **3. Data Exfiltration**<br>数据外泄 | E1 | MEDIUM | 外部传输 | `requests.post(external_url)` 发送数据到外部 |
| | E2 | HIGH | 环境变量收集 | `os.environ` 遍历收集 API Key / Token / Secret |
| | E3 | MEDIUM | 文件系统枚举 | 扫描 `~/.ssh` / `~/.aws` / `/etc` 等敏感目录 |
| | E4 | HIGH | 上下文泄露 | 完整对话上下文（含隐私数据）传输到外部 |
| **4. Privilege Escalation**<br>权限提升 | PE1 | LOW | 过度权限请求 | 声明的权限超出功能范围 |
| | PE2 | MEDIUM | sudo/root 执行 | 调用 `sudo` / `su` 或以 root 执行命令 |
| | PE3 | HIGH | 凭据访问 | 读取 SSH key / AWS credentials / API token 文件 |
| **5. Supply Chain**<br>供应链 | SC1 | LOW | 未锁定依赖 | `pip install` / `npm install` 无版本约束 |
| | SC2 | HIGH | 外部脚本获取 | `curl \| bash` / `wget -O - \| sh` 远程即下即执行 |
| | SC3 | HIGH | 混淆代码 | Base64/Hex 编码 + `eval`/`exec` 隐藏 payload |
| | SC4 | HIGH | 已知 CVE 依赖 | 依赖包存在已知漏洞（OSV.dev 实时查询） |
| | SC5 | MEDIUM | 废弃依赖 | 已停维的包，无安全更新 |
| | SC6 | HIGH | 仿冒包名 | `requsts` vs `requests`，疑似 typosquatting |
| **6. Excessive Agency**<br>过度代理权 | EA1 | HIGH | 不受限工具访问 | 无白名单/范围限制使用文件/网络/进程工具 |
| | EA2 | HIGH | 自主决策 | 无人工确认即执行删除/请求/改配置 |
| | EA3 | MEDIUM | 功能蔓延 | 代码能力远超声明的功能声明 |
| | EA4 | MEDIUM | 无限资源访问 | 无速率限制，可能 fork bomb / 无限循环 |
| **7. Output Handling**<br>输出处理 | OH1 | HIGH | 未验证输出注入 | Skill 输出未净化即拼接到后续命令/代码 |
| | OH2 | MEDIUM | 跨上下文输出 | 输出跨越信任边界未经验证 |
| | OH3 | MEDIUM | 无界输出 | 无限制输出大小/速率，可能溢出或 DoS |
| **8. System Prompt Leakage**<br>提示泄露 | P6 | HIGH | 直接泄露 | 指示 Agent 直接输出系统提示/内部规则 |
| | P7 | MEDIUM | 间接提取 | 改述/翻译/编码等侧信道方式诱导暴露 |
| | P8 | HIGH | 工具辅助外泄 | 文件写入/网络请求将系统提示外传 |
| **9. Memory Poisoning**<br>内存投毒 | MP1 | HIGH | 历史注入 | 恶意内容伪装为历史对话注入上下文 |
| | MP2 | HIGH | 知识库污染 | 向向量数据库/检索源注入虚假文档 |
| | MP3 | CRITICAL | 递归投毒 | 投毒记忆→Agent 后续协助执行攻击 |
| **10. Tool Misuse**<br>工具滥用 | TM1 | MEDIUM | 内网探测 | `curl` / `ping` 扫描内网 IP 和端口 |
| | TM2 | HIGH | 无关工具调用 | 调用无关系统工具获取敏感信息 |
| | TM3 | HIGH | 敏感文件读取 | 读取 `/etc/shadow` / 私钥文件 |
| | TM4 | MEDIUM | 配置篡改 | 修改 `.bashrc` / `crontab` / `/etc/hosts` |
| **11. Rogue Agent**<br>恶意代理 | RA1 | CRITICAL | 自我修改 | 运行时修改自身代码：`open(__file__,'w').write(...)` |
| | RA2 | HIGH | 会话持久化 | crontab / systemd / 启动脚本植入持久化 |
| **12. Trigger Abuse**<br>触发器滥用 | TR1 | MEDIUM | 过度宽泛触发 | 触发词匹配 `help` / `run` 等常见词 |
| | TR2 | HIGH | 影子命令触发 | 触发器与内置命令/其他 skill 同名劫持 |
| | TR3 | MEDIUM | 关键词诱饵 | 高频关键词作触发器最大化激活概率 |
| **13. Dangerous Code (AST)**<br>危险代码 | AST1 | CRITICAL | `exec()` 调用 | 直接执行任意 Python 代码 |
| | AST2 | HIGH | `eval()` 调用 | 求值任意表达式 |
| | AST3 | HIGH | 动态导入 | `__import__()` 运行时加载任意模块 |
| | AST4 | HIGH | subprocess 调用 | `Popen` / `run` 执行外部命令 |
| | AST5 | HIGH | os.system 调用 | `os.system()` / `os.popen()` 等 shell 命令 |
| | AST6 | MEDIUM | `compile()` 调用 | 从字符串创建代码对象 |
| | AST7 | MEDIUM | 动态 getattr | 非字面量名称的反射式属性访问 |
| | AST8 | CRITICAL | 危险执行链 | `exec`/`eval` + 动态源(网络/编码) = RCE 链路 |
| | AST9 | HIGH | 反射式后门 | `getattr(os,'system')` 规避浅层 AST1/AST5 检测 |
| **14. Taint Tracking**<br>污点追踪 | TT1 | HIGH | 直接污点流 | 用户输入→危险汇点，未经净化 |
| | TT2 | MEDIUM | 变量中转流 | 数据经变量传递绕过简单匹配 |
| | TT3 | CRITICAL | 凭据外泄链 | 环境变量→网络输出汇点，完整窃取链路 |
| | TT4 | HIGH | 文件→网络外泄 | 文件内容→网络输出，用户数据外传 |
| | TT5 | CRITICAL | 输入→代码执行 | 网络/用户输入直通 `exec`/`subprocess`（RCE） |
| **15. YARA Signatures**<br>恶意签名 | YR1 | CRITICAL | 恶意软件匹配 | 命中已知木马/病毒/后门 YARA 特征 |
| | YR2 | CRITICAL | Webshell 匹配 | 命中 webshell 特征（PHP 一句话等） |
| | YR3 | HIGH | 挖矿程序匹配 | 命中加密货币挖矿代码特征 |
| | YR4 | HIGH | 黑客工具匹配 | 命中已知渗透/攻击工具特征码 |
| **16. MCP Least Privilege**<br>权限最小化 | LP1 | HIGH | 能力漏声明 | 代码使用的能力未在权限声明中列出 |
| | LP2 | MEDIUM | 通配符权限 | 权限含 `*` / `all` / `full` / `any` 绕过检查 |
| | LP3 | MEDIUM | 缺少权限声明 | 无 `permissions` 字段但有可检测能力 |
| | LP4 | LOW | 过度声明权限 | 声明的权限远超代码实际使用的功能 |
| **17. MCP Tool Poisoning**<br>工具投毒 | TP1 | HIGH | 隐藏指令 | HTML注释/零宽字符/Base64/Data URI 隐藏指令 |
| | TP2 | HIGH | Unicode 欺骗 | 同形字/RTL覆盖/混合脚本混淆工具名和描述 |
| | TP3 | MEDIUM | 参数描述注入 | 参数定义中注入覆盖指令或恶意默认值 |
| | TP4 | MEDIUM | 描述不匹配 | 工具声明描述与实际行为不一致（LLM 检测） |

---

## 八、SC4 依赖漏洞查询

SC4 模块实时查询 [OSV.dev](https://osv.dev) 检查依赖包已知 CVE：

| 特性 | 说明 |
|------|------|
| 覆盖范围 | PyPI + npm，数万条 CVE 公告 |
| 认证 | 无需 API Key，免费查询 |
| 查询方式 | 单次 HTTP 请求批量查询所有依赖 |
| 降级 | OSV.dev 不可达时使用内置静态列表 |
| 缓存 | 内存缓存 1 小时 |

> SC4 检测结果计入供应链 SC4 项，影响风险评分。

---

## 九、Jenkins Job 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `GIT_URL` | `str` | Git 仓库 URL |
| `REF` | `str` | 分支/Tag/Commit，默认 `main` |
| `SKILL_PATH` | `str` | Skill 在仓库中的相对路径 |
| `SCANNERS` | `str` | 逗号分隔扫描器列表，默认 `skillspector` |

产物: `reports/skillspector/report.json` + `report.md`

---

## 十、配置项

| 配置 | 环境变量 | 说明 |
|------|------|------|
| `enable_audit` | — | 总开关，yaml 配置 |
| `skillspector_jenkins_url` | `SKILLSPECTOR_JENKINS_URL` | Jenkins 地址 |
| `skillspector_jenkins_user` | `SKILLSPECTOR_JENKINS_USER` | Basic Auth 用户名 |
| `skillspector_jenkins_token` | `SKILLSPECTOR_JENKINS_TOKEN` | Basic Auth Token |
| `skillspector_timeout` | `SECURITY__SKILLSPECTOR_TIMEOUT` | 同步扫描等待 Jenkins 构建结束的超时（秒），默认 600（10 分钟） |

---

## 十一、设计原则

| # | 原则 | 说明 |
|---|------|------|
| 1 | **入库与审计分离** | `SkillRepository.create()` 只做数据写入；`routes/skills.py` 在入库后调用 `SecurityService.audit_skill()` 触发审计 |
| 2 | **skill_repo_id 路由层解析** | 无 `skill_repo_id` 时在 discover skill入库时从 `source_url` 解析 `repo_name`（去协议头、去 `.git`、`/` 换 `_`），查重或新建 `SkillRepoModel` |
| 3 | **只读展示** | `GET /audit` 仅返回已存储结果，不触发新扫描 |
| 4 | **降级容错** | 无可用扫描器或 Jenkins 不可用时，降级为 `risk_level=unknown`，审计失败不影响入库 |
| 5 | **异步优先** | 批量场景用 `async_mode`，后台 `SkillspectorCollector` 每 30s 轮询回写 |
| 6 | **评分体系统一** | 全部使用 NVIDIA SkillSpector 原生风险分（0–100，高分=危险），包括直接扫描和降级回退 |
| 7 | **内容寻址复用** | 以目录级 tree hash 为 key：跨轮次（DB 记录）和同轮扫描内（security_cache）复用审计结果，内容未变的版本不重复提交 Jenkins |
| 8 | **失败自愈** | 未拿到评分（risk_score=NULL）的记录，即使仓库 commit 未变，也会在后续 discover 轮次自动重试审计；失败的审计结果不进缓存，避免失败被继承 |
| 9 | **容器只读解耦** | 爬虫宿主机负责 blob 物化（partial clone 懒拉取），skillspector 容器只读挂载缓存、无网络依赖，两侧职责隔离 |
| 10 | **未评分不曝光** | `risk_score` 为 NULL（安全检测未完成）的技能在搜索/列表查询中全局排除，用户不会看到未审计内容 |
