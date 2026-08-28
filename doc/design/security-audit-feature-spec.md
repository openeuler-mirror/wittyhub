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

---

## 三、完整审计链路

### 3.1 同步模式（API 创建 Skill）

```
POST /skills/

routes/skills.py : create_skill()
  │
  ├── skill_repo_id 解析（查已有或新建 SkillRepoModel）  ← 路由层处理
  ├── SkillRepository.create()                           ← 入库（纯数据写入，不触发审计）
  │
  ├── enable_audit == false ──▶ 返回（risk_score = NULL）
  │
  └── enable_audit == true
        │
        ▼
  SecurityService.audit_skill()
    │
    ├── scanners 默认: 自动检测
    │     ├── has_skillspector → ["skillspector"]
    │     └── 否则 → []（无可用扫描器）
    │
    ├── Skillspector（已配置时）
    │     SkillspectorClient.run_scan()
    │       ├── POST Jenkins /buildWithParameters
    │       ├── 轮询 build 状态（每5秒，最多150秒）
    │       ├── GET /artifact/reports/skillspector/report.json
    │       └── report_to_risk_signals()
    │     → risk_score = report.risk_assessment.score  （直接使用 SkillSpector 风险分）
    │
    └── 持久化（audit_skill 内部完成）
          ├── INSERT security_audits（风险信号 + 完整 report.json）
          ├── UPDATE skills.risk_score
          └── COMMIT

routes/skills.py
  └── 返回 SkillResponse（risk_score 已由 audit_skill 写入）
```

### 3.2 异步模式

```
async_mode=True

SkillspectorClient.trigger_scan()
  └── POST Jenkins /buildWithParameters → fire-and-forget
       details 记录: { skillspector_async: true, skillspector_build_number: N }

后台: SkillspectorCollector（每 30s，仅 enable_audit=true + 凭证已配时启动）
  ├── 查询 pending audits（skillspector_async=true, collected=null）
  ├── wait_for_build(N)
  ├── fetch_report(N)
  └── 回写 skills.risk_score（风险分）+ security_audits
```

启动: `src/security/detector.py` → `start_skillspector_collector()`（内部自行导入 `AsyncSessionLocal`），由 `src/api/main.py` lifespan 调用。

### 3.3 手动触发

```
POST /skills/{skill_id}/audit?scanners=skillspector
```

调用 `SecurityService.audit_skill()` 重新扫描并返回最新 `SecurityAuditResponse`。

---

## 四、模块架构

```
src/security/detector.py          ← 唯一核心（扫描逻辑 + Collector 工厂函数）
  ├── SecurityDetector             ← 总入口
  ├── SkillspectorClient           ← Jenkins HTTP 交互
  ├── SkillspectorCollector        ← 后台异步回写
  └── start_skillspector_collector()  ← 工厂函数（内部导入 AsyncSessionLocal）

src/api/services/security.py      ← 编排层
  └── SecurityService.audit_skill()

src/api/routes/skills.py          ← 业务入口
  ├── create_skill()              ← POST /skills/        skill_repo_id 解析 → 入库 → 审计
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

### 6.1 创建 Skill（自动审计）

```
POST /api/v1/skills/
```

请求体 → `SkillCreate schema`。`enable_audit=true` 时入库后自动触发审计，`risk_score` 由 `audit_skill()` 写入并返回。审计失败不影响入库。

### 6.2 查询审计结果

```
GET /api/v1/skills/{skill_id}/audit
```

返回最近一次审计记录，无记录返回 `{"error": "No audit found"}`。

### 6.3 手动触发审计

```
POST /api/v1/skills/{skill_id}/audit
```

| Query 参数 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `scanners` | `str` | 否 | `skillspector`。默认自动检测可用扫描器 |

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

### 6.4 SecurityService.audit_skill() 内部接口

```python
async def audit_skill(
    skill_id: str,                        # skill 唯一标识
    source: str,                          # "github" / "gitcode" / "clawhub"
    source_url: str,                      # 仓库 URL
    metadata: dict[str, Any],             # { version, content, skill_path }
    scanners: list[str] | None = None,    # None → 自动检测可用扫描器
    async_mode: bool = False,             # True → skillspector fire-and-forget
) -> dict[str, Any]:
```

**返回**:

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
| 2 | **skill_repo_id 路由层解析** | 无 `skill_repo_id` 时在 `create_skill` 路由层从 `source_url` 解析 `repo_name`（去协议头、去 `.git`、`/` 换 `_`），查重或新建 `SkillRepoModel` |
| 3 | **只读展示** | `GET /audit` 仅返回已存储结果，不触发新扫描 |
| 4 | **降级容错** | 无可用扫描器或 Jenkins 不可用时，降级为 `risk_level=unknown`，审计失败不影响入库 |
| 5 | **异步优先** | 批量场景用 `async_mode`，后台 `SkillspectorCollector` 每 30s 轮询回写 |
| 6 | **评分体系统一** | 全部使用 NVIDIA SkillSpector 原生风险分（0–100，高分=危险），包括直接扫描和降级回退 |
