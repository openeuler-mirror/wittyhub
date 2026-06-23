结合目前公开的 GitHub、SkillHub、MCP 社区以及最近几篇 Agent Skill Security 的论文来看，目前**真正定位为 Skill Security Scanner（Skill 安全扫描）**，并且**开源、可商用**的工具其实并不多。

整个行业基本形成了三条技术路线：

1. **Cisco** —— 偏安全产品（Security Scanner）
2. **NVIDIA** —— 偏研究+平台（Research + Platform）
3. **社区工具（SkillsSafe / Bawbel / MCP Scanner 等）** —— 偏轻量检测及MCP生态

实际上，目前真正能够称得上”完整Skill扫描框架”的只有 Cisco Skill Scanner 和 NVIDIA SkillSpector 两个，其余更多属于辅助工具。 

下面按照能力做一个完整分析。

------

# **一、目前主流开源 Skill Scanner**

| **工具**            | **公司** | **开源** | **License** | **扫描对象**       | **定位**         |
| ------------------- | -------- | -------- | ----------- | ------------------ | ---------------- |
| Cisco Skill Scanner | Cisco    | ✅        | Apache-2.0  | Skill Repo         | 企业安全扫描     |
| NVIDIA SkillSpector | NVIDIA   | ✅        | Apache-2.0  | Skill Repo/MCP     | AI Agent安全平台 |
| SkillsSafe          | 社区     | 部分开源 | MIT(部分)   | Skill/MCP          | 在线扫描         |
| Bawbel Scanner      | 社区     | ✅        | MIT         | MCP Server + Skill | MCP安全          |
| MCPScan             | 社区     | ✅        | MIT         | MCP Server         | MCP配置扫描      |

Cisco 与 NVIDIA 基本代表了目前业界两个方向。 

------

# **二、Cisco Skill Scanner**

官方定位：

Security Scanner for AI Agent Skills

GitHub：

https://github.com/cisco-ai-defense/skill-scanner

## **核心架构**

Cisco采用的是多引擎检测：

```
             Skill

                │

        Parser

      /    |      \

 YAML  AST  Markdown

      \    |     /

      Rule Engine

      /     |      \

YARA  Dataflow  LLM Judge

        │

Risk Score

        │

Report
```

官方称为

Multi Engine Detection

包括：

- Pattern Rule
- YARA
- Behavioral Analysis
- Dataflow Analysis
- LLM Judge

不是单纯regex。

------

## **Cisco检测内容**

包括：

Prompt Injection

例如

```
Ignore previous instructions

Reveal secrets

System Prompt Override
```

------

Data Exfiltration

例如

```
~/.ssh

~/.aws

.env

token

apikey
```

------

危险Shell

```
curl | bash

wget | sh

rm -rf

chmod 777
```

------

Python危险API

例如

```
subprocess

os.system

eval

exec
```

------

Dataflow分析

Cisco最大的特点其实是：

不是扫字符串。

而是分析：

```
Prompt

↓

Instruction

↓

Command

↓

Sensitive File

↓

Network

↓

Remote Endpoint
```

例如

```
Read ~/.ssh

↓

base64

↓

curl

↓

POST
```

这一整条攻击链都能识别。 

------

## **优势**

业内目前Dataflow最完整。

适合：

Agent Marketplace

SkillHub

企业审核

CI/CD

------

## **缺点**

LLM Judge速度较慢。

误报依赖Prompt质量。

更多关注：

恶意Skill

而不是：

Skill质量。

------

# **三、NVIDIA SkillSpector**

GitHub：

https://github.com/NVIDIA/SkillSpector

它和Cisco最大的区别：

不是做”安全产品”

而是在做

Skill Security Framework

官方文档明确把它定位为 Agent Skills 的安装前安全分析工具。 

------

## **官方架构**

```
Skill

↓

Input Loader

↓

Static Analyzer

↓

Semantic Analyzer

↓

Risk Engine

↓

Report
```

比Cisco更加模块化。

------

## **SkillSpector检测内容**

官方目前

64个Pattern

16类漏洞

包括：

Prompt Injection

Data Exfiltration

Privilege Escalation

Supply Chain

Output Handling

Memory Poisoning

Tool Misuse

Trigger Abuse

Dangerous Code

Taint Tracking

YARA

MCP Least Privilege

MCP Tool Poisoning

等等。 

------

最有意思的是：

它新增了：

## **MCP扫描**

例如：

```
permission:

*
```

检测：

Wildcard Permission

------

例如：

Tool声明：

```
read file
```

实际代码：

```
delete
```

检测：

Behavior Mismatch

------

例如：

HTML Comment

Zero Width Space

RTL字符

Unicode混淆

Base64

都可以识别。

Cisco目前没有这么细。

------

## **SkillSpector特点**

真正覆盖了：

Markdown

Python

Node

Zip

Repo

Git URL

MCP

整个Skill Package。

------

还有：

OSV

实时漏洞查询

例如：

requirements.txt

package.json

自动查询：

CVE

供应链漏洞。

Cisco目前没有这么深入。 

------

## **优势**

覆盖面最大。

Rule最丰富。

MCP支持最好。

插件化最好。

容易扩展。

------

## **缺点**

目前仍偏静态分析。

Dataflow没有Cisco深。

LLM部分更多用于语义补充。

------

# **四、SkillsSafe**

其实属于：

Browser Scanner。

特点：

浏览器直接扫。

不用上传。

检测：

Credential

Unicode

Prompt

Shell

.env

Reverse Shell

速度非常快。

<100ms。

但是：

规则只有20多个。

没有AST。

没有Dataflow。

更适合：

普通用户安装Skill之前快速检查。 

------

# **五、Bawbel Scanner**

定位已经偏MCP。

主要：

```
MCP Server

↓

Manifest

↓

Server Card

↓

Prompt

↓

Tool Description
```

扫描：

Prompt Injection

Server Card

Manifest

Spec Compliance

Attack Chain

更像：

MCP安全。

不是Skill安全。 

------

# **六、MCPScan**

也是：

Semgrep

Dependency

Code Pattern

偏：

Server实现。

不是：

Skill内容。

更多检测：

Python

Node

Dependency

Semgrep Rule。 

------

# **七、能力对比**

| **能力**          | **Cisco** | **NVIDIA** | **SkillsSafe** | **Bawbel** |
| ----------------- | --------- | ---------- | -------------- | ---------- |
| Prompt Injection  | ⭐⭐⭐⭐⭐     | ⭐⭐⭐⭐⭐      | ⭐⭐⭐            | ⭐⭐⭐⭐       |
| Data Exfiltration | ⭐⭐⭐⭐⭐     | ⭐⭐⭐⭐⭐      | ⭐⭐⭐            | ⭐⭐⭐        |
| Dangerous Code    | ⭐⭐⭐⭐      | ⭐⭐⭐⭐⭐      | ⭐⭐             | ⭐⭐⭐        |
| AST分析           | ✅         | ✅          | ❌              | ❌          |
| Dataflow          | ⭐⭐⭐⭐⭐     | ⭐⭐⭐        | ❌              | ⭐          |
| YARA              | ✅         | ✅          | ❌              | ❌          |
| Taint Analysis    | ⭐⭐⭐⭐      | ⭐⭐⭐⭐       | ❌              | ❌          |
| MCP扫描           | ⭐⭐        | ⭐⭐⭐⭐⭐      | ⭐⭐⭐⭐           | ⭐⭐⭐⭐⭐      |
| CVE检查           | ❌         | ⭐⭐⭐⭐⭐      | ❌              | ❌          |
| Supply Chain      | ⭐⭐⭐       | ⭐⭐⭐⭐⭐      | ⭐              | ⭐          |
| LLM Judge         | ⭐⭐⭐⭐⭐     | ⭐⭐⭐⭐       | ❌              | ❌          |
| Plugin扩展        | ⭐⭐⭐       | ⭐⭐⭐⭐⭐      | ⭐              | ⭐⭐         |
| SARIF输出         | ✅         | ✅          | ❌              | ❌          |

------

# **八、业界技术路线演进**

从这些项目可以看出，Skill Scanner 正在从传统静态扫描逐渐演进为多层检测体系：

```
Skill
│
├── ① Metadata
│
├── ② Prompt
│
├── ③ Code
│
├── ④ Dependency
│
├── ⑤ MCP Manifest
│
├── ⑥ Behavior
│
├── ⑦ Dataflow
│
├── ⑧ Semantic
│
└── ⑨ Supply Chain
```

其中：

- **Cisco** 的核心竞争力在于**行为分析（Behavior）+ 数据流分析（Dataflow）**，更适合企业安全审计和 CI/CD 场景。 
- **NVIDIA** 的优势在于**覆盖广度和平台化**，尤其增加了 **MCP Least Privilege、Tool Poisoning、OSV 漏洞联动** 等能力，更适合作为 SkillHub 或 Agent 平台的统一扫描框架。 
- **SkillsSafe** 和 **Bawbel** 更适合作为安装前的轻量级守门员（Pre-install Guard），而不是企业级安全平台。 

------

# **九、如果你的目标是建设企业级 SkillHub / AgentHub**

结合你此前一直在研究的 **SkillHub、AgentHub、Agent Runtime 和安全调度体系**，我建议不要简单复刻 Cisco 或 NVIDIA，而是设计一个**四层扫描架构**：

1. **静态层（Static）**：复用 NVIDIA 的规则覆盖思路，对 SKILL.md、脚本、依赖和 MCP Manifest 做快速扫描。
2. **行为层（Behavior）**：借鉴 Cisco 的 Dataflow 和 Taint Analysis，对敏感文件访问、命令执行、网络外联等攻击链进行分析。
3. **运行时层（Runtime）**：这是目前开源工具普遍缺失的部分，可结合 **eBPF + seccomp notify**，在 Skill 实际执行时监控 `execve`、文件访问、网络连接、权限使用等行为，实现动态风险检测。
4. **治理层（Governance）**：将扫描结果与 SkillHub 的发布审核、风险评级、签名校验、CI/CD、运行时准入控制结合，形成完整的 Skill 生命周期安全治理。

这也是目前公开的 Cisco、NVIDIA 方案尚未覆盖的方向，对于面向生产环境的大规模 Agent 平台会具有明显的差异化优势。