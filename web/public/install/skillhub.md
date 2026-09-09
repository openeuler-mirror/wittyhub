# openEuler SkillHub 安装指南（供 AI Agent 阅读并执行）

## 概述

SkillHub 是 openEuler 社区的 AI Agent 技能商店（https://skillhub.openeuler.org/），提供技能的搜索、安装与安全审计。本文档覆盖两种场景：安装 CLI（wittyhub）和安装技能。

## 适用场景（先判断，避免多余操作）

- 用户要求「安装 wittyhub / 安装 CLI / 安装 SkillHub 商店」→ 执行第一、二节
- 用户要求安装某个技能 → CLI 已安装则直接跳第三节；未安装先走第一、二节
- 仅需搜索技能 → 直接执行 `wittyhub find <关键词>`（第三节），不要询问其他配置

## 一、检查并安装 CLI

```bash
command -v wittyhub && wittyhub --version
```

- 已安装 → 直接进行技能操作（第三节）
- 未安装 → 执行安装：

```bash
# 一键脚本（推荐）
curl -fsSL https://skillhub.openeuler.org/install/install.sh | bash

# 或 npm 全局安装
npm install -g wittyhub@latest
```

- 无全局安装权限时，用 `npx wittyhub@latest` 代替 `wittyhub` 命令
- 沙箱限网时，需以允许联网的权限执行以上命令

## 二、验证安装

```bash
wittyhub --help   # 应显示 add / install / find / list / audit 等命令
```

## 三、安装技能（统一使用 skill_id）

技能的统一标识是 **skill_id**，新格式为：

```
{source_type}:{owner}/{repo}/{skill_dir}
```

例如：`gitcode:openeuler/ib_robot/deepwiki-config`（`skill_dir` 为 SKILL.md 所在目录名）。

### 1) 已知 skill_id（推荐）

用户提示词中给出的标识若形如 `{source_type}:{owner}/{repo}/{目录名}`，即为 skill_id，直接安装：

```bash
wittyhub install <skill_id> -y
```

（等价写法：`wittyhub add <skill_id> -y`）

注意：必须使用完整的 skill_id（含 `source_type:` 前缀与冒号），不要自行拼写或改写。

### 2) 只知道技能名：先查 skill_id 再安装

```bash
# 1. 搜索，输出中每条结果都有 skill_id 字段
wittyhub find <技能名或关键词>

# 2. 取与技能名精确匹配的那条 skill_id 安装
wittyhub install <skill_id> -y
```

安装过程中 CLI 会展示安全审计风险等级（safe/low/medium/high/critical）。

## 四、安装位置

- 默认：自动识别当前 Agent（Trae/Claude Code/Cursor 等）并安装到其 skills 目录，同时安装到项目通用目录 `.agents/skills/`（多数 Agent 会扫描此目录）
- 手动指定：`wittyhub install <skill_id> --agent <agent名>` 或 `--agent '*'`（装到全部已检测 Agent）
- 常用 AI Client 的 Skills 路径（手动核对用）：
  - Claude Code: `~/.claude/skills/`
  - Cursor: `~/.cursor/skills/`
  - Codex: `~/.codex/skills/`
  - Gemini CLI: `~/.gemini/skills/`
  - 通用/项目级: `.agents/skills/`

## 五、注意事项

- 安装完成后，当前会话中新技能可能需要重启 Agent 才能生效
- 查看技能安全审计详情：`wittyhub audit <skill_id>`
- 查看技能元信息（作者/分类/版本/标签）：`wittyhub get <skill_id>`
- 更换测试环境时，将上文域名替换为 https://openeuler-skillhub.test.osinfra.cn/
