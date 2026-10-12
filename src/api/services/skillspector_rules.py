"""SkillSpector 规则目录：17 个风险维度、检测项（规则 ID）映射与中文本地化。

分类体系与中文文案全部取自 ``RISK_MODEL_SUMMARY.md``：

- 第二章「风险维度」：17 个维度 -> 4 大类的归属（5 / 2 / 9 / 1）；
- 「各维度详细介绍」：维度级中文风险描述（本模块 ``RiskDimension.description``）；
- 「各维度修复建议」：检测项级中文名称与中文修复建议（本模块 ``RULE_CATALOG``）。

扩展规则（AS / SSRF / DS / BH）在总览表中未单列维度，按该文档「扩展规则」小节
的归类说明并入相近的标准维度（AS -> 权限提升，SSRF -> 工具滥用，DS -> 行为 AST，
BH -> 数据外泄），从而保持 17 维度 / 四大类的固定层级。
"""

from __future__ import annotations

from typing import NamedTuple


class RiskDimension(NamedTuple):
    """17 个风险维度之一（含所属高层大类与中文风险描述）。"""

    key: str
    name: str
    category_key: str
    description: str


class RiskCategory(NamedTuple):
    """高层四大类。"""

    key: str
    name: str
    description: str
    dimensions: tuple[str, ...]


class SkillspectorRule(NamedTuple):
    """一个检测项（规则 ID）的归属与中文本地化文案。"""

    rule_id: str
    dimension: str
    name: str
    remediation: str


# --------------------------------------------------------------------------
# 高层四大类（``RISK_MODEL_SUMMARY.md`` 第二章「四大类总览」）
# --------------------------------------------------------------------------

CATEGORIES: tuple[RiskCategory, ...] = (
    RiskCategory(
        key="prompt",
        name="提示操控类",
        description="操控大模型意图：指令覆盖、越狱、记忆投毒、泄露系统提示词",
        dimensions=(
            "prompt_injection",
            "system_prompt_leakage",
            "memory_poisoning",
            "anti_refusal",
            "trigger_abuse",
        ),
    ),
    RiskCategory(
        key="data",
        name="数据泄露类",
        description="窃取、外传敏感数据：密钥、上下文、文件、跨信任边界输出",
        dimensions=(
            "data_exfiltration",
            "output_handling",
        ),
    ),
    RiskCategory(
        key="privilege_code",
        name="权限与代码执行类",
        description="越权、危险代码执行、污点流、恶意样本、MCP 工具投毒等",
        dimensions=(
            "privilege_escalation",
            "excessive_agency",
            "tool_misuse",
            "rogue_agent",
            "dangerous_code",
            "data_flow",
            "yara_match",
            "mcp_least_privilege",
            "mcp_tool_poisoning",
        ),
    ),
    RiskCategory(
        key="supply_chain",
        name="供应链风险类",
        description="依赖漏洞：typosquat、废弃包、远程执行、未锁版本依赖",
        dimensions=("supply_chain",),
    ),
)


# --------------------------------------------------------------------------
# 17 个风险维度（中文名 + 维度级风险描述）
# --------------------------------------------------------------------------

DIMENSIONS: tuple[RiskDimension, ...] = (
    RiskDimension(
        "prompt_injection",
        "提示注入",
        "prompt",
        "技能内容试图篡改或绕过模型的安全指令，隐藏恶意指令或影响决策",
    ),
    RiskDimension(
        "system_prompt_leakage",
        "系统提示泄露",
        "prompt",
        "技能引导模型输出内部系统提示、隐藏规则或通过改写/旁路手段间接提取系统指令",
    ),
    RiskDimension(
        "memory_poisoning",
        "记忆投毒",
        "prompt",
        "注入内容持久化到代理记忆或上下文，填充上下文窗口挤占正常指令，或篡改代理记忆与状态",
    ),
    RiskDimension(
        "anti_refusal",
        "反拒答/越狱",
        "prompt",
        "技能引导代理永不拒绝、省略警告或免责声明，或直接清零安全策略，属典型越狱前置",
    ),
    RiskDimension(
        "trigger_abuse",
        "触发滥用",
        "prompt",
        "使用过宽泛、遮蔽内置命令或其他技能、或过分倾向高频激活的触发词",
    ),
    RiskDimension(
        "data_exfiltration",
        "数据外泄",
        "data",
        "技能将用户数据、对话上下文、凭证或敏感文件传输到外部，或批量收集环境变量、扫描敏感目录",
    ),
    RiskDimension(
        "output_handling",
        "输出处理",
        "data",
        "模型输出未经验证或净化即进入下游（SQL、shell、HTML），跨安全上下文传递输出，或输出规模与速率无上限",
    ),
    RiskDimension(
        "privilege_escalation",
        "权限提升",
        "privilege_code",
        "技能申请超出所需权限，或直接以 sudo/root 运行、访问凭证文件",
    ),
    RiskDimension(
        "excessive_agency",
        "过度代理",
        "privilege_code",
        "技能授予代理不受限的工具访问、允许无人工确认的高影响自主决策、功能超出声明范围，"
        "或允许无上限的资源消耗、私自切换外部模型与账户",
    ),
    RiskDimension(
        "tool_misuse",
        "工具滥用",
        "privilege_code",
        "构造工具参数实现意外或不安全行为（如 shell=True）、链式调用绕过单点校验、"
        "采用不安全默认配置、部署特权 Kubernetes 负载",
    ),
    RiskDimension(
        "rogue_agent",
        "流氓代理",
        "privilege_code",
        "技能在运行时修改自身代码或配置，或建立跨会话持久后门（cron、启动脚本、状态文件）",
    ),
    RiskDimension(
        "dangerous_code",
        "危险代码语法",
        "privilege_code",
        "代码中出现危险执行调用（exec/eval/subprocess/os.system、动态 import/getattr、"
        "反序列化链），可直接执行任意代码或绕过静态检测",
    ),
    RiskDimension(
        "data_flow",
        "污点流",
        "privilege_code",
        "数据从不可信来源（环境变量、文件、网络）流向危险 sink（网络输出、exec、文件写入）"
        "且未净化，构成数据外泄或代码执行",
    ),
    RiskDimension(
        "yara_match",
        "恶意签名",
        "privilege_code",
        "直接命中已知恶意软件、webshell、挖矿程序或黑客工具与漏洞利用特征",
    ),
    RiskDimension(
        "mcp_least_privilege",
        "MCP 最小权限",
        "privilege_code",
        "技能实际能力超出已声明权限（可能有欺骗意图）、权限列表使用通配符、"
        "未声明工具权限或声明了无对应能力的权限",
    ),
    RiskDimension(
        "mcp_tool_poisoning",
        "MCP 工具投毒",
        "privilege_code",
        "在技能元数据（描述、触发词、参数）中隐藏指令，使用 Unicode 欺骗，"
        "参数描述夹带注入指令，或描述与实际行为不符",
    ),
    RiskDimension(
        "supply_chain",
        "供应链",
        "supply_chain",
        "依赖未锁定、下载并执行远程代码、混淆代码、存在已知 CVE、包含可疑或伪造依赖、"
        "关闭镜像签名校验、打包可执行字节码或隐藏可执行载荷",
    ),
)

DIMENSION_BY_KEY: dict[str, RiskDimension] = {item.key: item for item in DIMENSIONS}


# --------------------------------------------------------------------------
# 检测项目录：规则 ID -> 维度 + 中文名称 + 中文修复建议
# （文案逐条对应 ``RISK_MODEL_SUMMARY.md``「各维度修复建议」）
# --------------------------------------------------------------------------

RULE_CATALOG: tuple[SkillspectorRule, ...] = (
    # 1. 提示注入
    SkillspectorRule("P1", "prompt_injection", "覆盖指令", "删除或重写任何让代理忽略提示、覆盖安全规则或不信任未验证内容的文本"),
    SkillspectorRule("P2", "prompt_injection", "隐藏指令", "审计所有注释与隐形字符，移除引导未授权操作的指令，使用简明可审内容"),
    SkillspectorRule("P3", "prompt_injection", "外部传输指令", "移除把用户数据、提示词或上下文发往外部 URL 的指令；若确需遥测，采用文档化且重隐私的方式"),
    SkillspectorRule("P4", "prompt_injection", "隐性操控", "审查显性、隐性操控与偏见，确保指令明确且与声明目的一致"),
    SkillspectorRule("P5", "prompt_injection", "危险内容", "移除可能导致危险后果的内容，为高风险操作增加护栏与人工监督"),
    SkillspectorRule("P9", "prompt_injection", "空白填充", "移除大段空白填充，审查被隐藏内容；保持技能文件紧凑可审"),
    # 2. 系统提示泄露
    SkillspectorRule("P6", "system_prompt_leakage", "直接泄露", "移除任何揭示、打印或输出系统提示与内部规则的指令"),
    SkillspectorRule("P7", "system_prompt_leakage", "间接提取", "禁止摘要、翻译或复述系统指令，加入显式防提取条款"),
    SkillspectorRule("P8", "system_prompt_leakage", "工具外泄", "防止系统提示被写入文件、经网络发送或被记录；将系统指令视为机密并过滤出所有工具输出"),
    # 3. 记忆投毒
    SkillspectorRule("MP1", "memory_poisoning", "持久化注入", "不允许不可信输入持久化到代理记忆或上下文；存储前校验全部内容，并实现会话间记忆隔离"),
    SkillspectorRule("MP2", "memory_poisoning", "上下文填充", "实现可检测并拒绝填充、塞入的上下文管理，系统指令优先于用户注入内容"),
    SkillspectorRule("MP3", "memory_poisoning", "记忆操纵", "保护代理记忆与状态免受不可信内容修改；关键指令用只读记忆并校验所有状态变更"),
    # 4. 反拒答/越狱
    SkillspectorRule("AR1", "anti_refusal", "抑制拒答", "移除任何让代理永不拒绝或总是服从的指令；代理必须保留拒绝不安全、越界、有害请求的能力"),
    SkillspectorRule("AR2", "anti_refusal", "抑制警告", "移除压制警告、免责声明或伦理评论的指令，让代理向用户呈现安全相关提示"),
    SkillspectorRule("AR3", "anti_refusal", "清零安全策略", "移除清零安全策略与限制的越狱框架；技能内容不得让代理忽略指南或无护栏运行"),
    # 5. 触发滥用
    SkillspectorRule("TR1", "trigger_abuse", "过宽触发", "使用精确、狭窄的触发模式，仅匹配技能预期用例；避免单词或常见短语触发"),
    SkillspectorRule("TR2", "trigger_abuse", "遮蔽命令触发", "选择不冲突于内置命令或其他技能的触发词，必要时加唯一命名空间前缀"),
    SkillspectorRule("TR3", "trigger_abuse", "关键词诱导触发", "使用描述性触发词，清晰表明技能用途，而非为最大化激活频率的通用关键词"),
    # 6. 数据外泄
    SkillspectorRule("E1", "data_exfiltration", "外部传输", "核验目标 URL 是否可信且必要，移除或替换为文档化 API；确保不传输密钥、令牌与个人信息"),
    SkillspectorRule("E2", "data_exfiltration", "枚举环境变量", "仅按名称读取明确需要的环境变量，避免枚举或复制整个环境，切勿向不可信目标记录或传输凭证"),
    SkillspectorRule("E3", "data_exfiltration", "文件系统枚举", "移除不必要的文件扫描；按需使用显式限定路径，避免读取 ~/.ssh、~/.aws 或凭证目录"),
    SkillspectorRule("E4", "data_exfiltration", "上下文泄露", "移除任何发送提示、响应或会话数据的代码，保护隐私，绝不外泄对话内容"),
    SkillspectorRule("E5", "data_exfiltration", "云存储上传", "核验目标 bucket 属于且仅属于你；绝不向外部或未验证云存储上传凭证、密钥与工作区内容"),
    # 7. 输出处理
    SkillspectorRule("OH1", "output_handling", "未净化输出注入", "在下游使用前校验并净化模型输出；SQL 用参数化查询、shell 用命令引用、网页用 HTML 编码"),
    SkillspectorRule("OH2", "output_handling", "跨上下文输出", "强制严格上下文边界；未经显式校验与敏感内容脱敏，不把某安全域输出传入另一域"),
    SkillspectorRule("OH3", "output_handling", "无界输出", "对输出长度、生成数量与速率设置显式上限，用 max_tokens 与截断防止无界输出"),
    # 8. 权限提升
    SkillspectorRule("PE1", "privilege_escalation", "过度权限", "仅申请最小必要权限，并说明每个权限的用途；移除 * 与 all 等宽泛权限"),
    SkillspectorRule("PE2", "privilege_escalation", "sudo/root 调用", "非必要避免 sudo/root，优先最小权限模式；确需提权时说明理由与范围"),
    SkillspectorRule("PE3", "privilege_escalation", "访问凭证文件", "移除凭证路径引用，改用环境变量或密钥管理器；生产代码路径绝不加载 .env 或令牌文件"),
    # 9. 过度代理
    SkillspectorRule("EA1", "excessive_agency", "不受限工具访问", "仅开放技能所必需的工具，使用显式白名单而非整体授权"),
    SkillspectorRule("EA2", "excessive_agency", "自主高影响决策", "对破坏性、不可逆、高影响操作加入人工确认，绝不自动执行改文件、发数据或改系统状态的命令"),
    SkillspectorRule("EA3", "excessive_agency", "范围蔓延", "将技能功能限制在其文档化目的内，移除使其执行声明范围之外动作的指令"),
    SkillspectorRule("EA4", "excessive_agency", "无界资源消耗", "为 API 调用、文件操作与计算设置显式限流、超时与配额，为失控循环实现熔断"),
    SkillspectorRule("EA5", "excessive_agency", "外部模型/账户切换", "移除模型与提供商覆盖，或显著披露并要求操作员显式批准后再调用外部计费模型"),
    # 10. 工具滥用
    SkillspectorRule("TM1", "tool_misuse", "参数滥用", "用白名单校验工具参数，拒绝危险值（shell=True、--force、-rf /），使用安全默认值"),
    SkillspectorRule("TM2", "tool_misuse", "链式滥用", "限制工具链深度，每个工具输出传给下一工具前校验；多步链需显式用户批准"),
    SkillspectorRule("TM3", "tool_misuse", "不安全默认值", "用安全设置覆盖不安全默认（verify=True、需认证、受限权限），审查并加固所有工具配置"),
    SkillspectorRule("TM4", "tool_misuse", "特权 K8s 负载", "移除 privileged、hostPath 与 host-namespace 设置；用最小权限 securityContext、去除 capabilities、避免挂载宿主文件系统"),
    # 11. 流氓代理
    SkillspectorRule("RA1", "rogue_agent", "自我修改", "阻止技能修改自身代码、SKILL.md 或配置文件；运行时将技能文件视为只读"),
    SkillspectorRule("RA2", "rogue_agent", "会话持久化", "移除所有持久化机制（cron、启动脚本、状态文件）；无用户显式同意不得跨会话保留状态"),
    # 12. 行为 AST
    SkillspectorRule("AST1", "dangerous_code", "exec() 动态执行", "用安全替代方案替换 exec()；确需动态执行时使用沙箱或禁用 __builtins__ 的受限 eval"),
    SkillspectorRule("AST2", "dangerous_code", "eval() 动态求值", "用 ast.literal_eval() 解析数据，或使用显式解析逻辑；绝不求值不可信字符串"),
    SkillspectorRule("AST3", "dangerous_code", "动态 __import__", "用标准 import 替代；确需动态加载时用 importlib 配合允许模块白名单"),
    SkillspectorRule("AST4", "dangerous_code", "subprocess 执行", "用 subprocess.run(shell=False) 与显式参数列表；校验所有输入，避免把用户可控数据传给命令"),
    SkillspectorRule("AST5", "dangerous_code", "os.system 执行", "用 subprocess.run(shell=False) 替代；显式参数列表并校验命令输入"),
    SkillspectorRule("AST6", "dangerous_code", "compile() 动态编译", "避免用动态字符串 compile()；用模板或带严格校验的 AST 处理"),
    SkillspectorRule("AST7", "dangerous_code", "动态 getattr()", "用显式属性访问或白名单字典查找替代动态 getattr()"),
    SkillspectorRule("AST8", "dangerous_code", "危险执行链", "彻底移除该链；绝不将网络数据、解码字节或动态 import 的代码传给 exec/eval"),
    SkillspectorRule("AST9", "dangerous_code", "反射访问执行 sink", "直接调用函数而非反射；确需反射时限定到排除执行 sink 的安全属性白名单"),
    SkillspectorRule("AST10", "dangerous_code", "不安全反序列化", "绝不反序列化不可信 pickle/marshal/dill/jsonpickle/joblib；用 JSON；YAML 用 safe_load、torch 用 weights_only"),
    # 13. 污点追踪
    SkillspectorRule("TT1", "data_flow", "直接污染流", "在数据源与 sink 之间增加校验与净化，禁止把未处理源数据直接传给 sink"),
    SkillspectorRule("TT2", "data_flow", "变量中介污染流", "将污染变量传给 sink 前校验；对外部来源数据使用白名单、类型检查或净化"),
    SkillspectorRule("TT3", "data_flow", "凭证外泄流", "绝不通过网络发送凭证与环境变量，使用安全凭证库，避免将密钥放入请求体或 URL"),
    SkillspectorRule("TT4", "data_flow", "文件外泄流", "在联网前校验并过滤文件内容，确保凭证与配置等敏感文件永不发往外部端点"),
    SkillspectorRule("TT5", "data_flow", "外部输入执行流", "外部输入绝不经 exec/eval/os.system/subprocess 直接执行，须严格校验并使用白名单与参数化命令"),
    SkillspectorRule("TT6", "data_flow", "反序列化污染流", "不反序列化外部输入或下载文件（pickle/marshal/dill/yaml.unsafe_load）；用 JSON，加载二进制前校验完整性"),
    # 14. 恶意签名
    SkillspectorRule("YR1", "yara_match", "恶意软件", "立即移除恶意载荷与受损文件，调查其进入路径并审计其余工件"),
    SkillspectorRule("YR2", "yara_match", "webshell", "立即移除 webshell 代码；webshell 提供未授权远程命令执行，审计技能中的后门或持久化机制"),
    SkillspectorRule("YR3", "yara_match", "挖矿程序", "移除所有挖矿代码、矿池引用与矿机二进制；将技能标记为恶意"),
    SkillspectorRule("YR4", "yara_match", "黑客工具/漏洞利用", "移除攻击性工具引用与利用代码；正规技能不应包含渗透测试工具、利用框架或侦察工具"),
    # 15. MCP 最小权限
    SkillspectorRule("LP1", "mcp_least_privilege", "能力超声明", "在扫描的 manifest 中声明缺失能力（Agent Skills 的 allowed-tools、MCP server 的 permissions），否则移除该代码"),
    SkillspectorRule("LP2", "mcp_least_privilege", "通配符权限", "用明确的权限清单替换通配符（*、all、full、any）"),
    SkillspectorRule("LP3", "mcp_least_privilege", "缺少权限声明", "在 manifest 中声明工具范围（Agent Skills 列 allowed-tools，MCP server 加 permissions 清单）"),
    SkillspectorRule("LP4", "mcp_least_privilege", "过声明权限", "若能力已不再使用，移除对应声明权限"),
    # 16. MCP 工具投毒
    SkillspectorRule("TP1", "mcp_tool_poisoning", "隐藏指令", "从元数据字段移除隐藏内容（HTML/Markdown 注释、零宽字符、base64 块），元数据只含普通可见文本"),
    SkillspectorRule("TP2", "mcp_tool_poisoning", "Unicode 欺骗", "用 ASCII 替换标识符中的非 ASCII 字符，移除 RTL 覆盖与隐形格式化字符"),
    SkillspectorRule("TP3", "mcp_tool_poisoning", "参数描述注入", "从参数描述与默认值移除注入模式、系统令牌与可疑内容"),
    SkillspectorRule("TP4", "mcp_tool_poisoning", "描述与行为不符", "更新技能描述以准确反映全部能力，或移除未声明功能"),
    # 17. 供应链
    SkillspectorRule("SC1", "supply_chain", "依赖未锁定", "在 requirements.txt/pyproject.toml 中锁定所有依赖版本，使用精确版本或兼容区间，定期执行 pip-audit"),
    SkillspectorRule("SC2", "supply_chain", "远程执行代码", "避免下载并执行远程脚本，使用可信的 PyPI/npm 包；确需远程拉取时校验校验和并使用 HTTPS"),
    SkillspectorRule("SC3", "supply_chain", "混淆代码", "移除混淆代码，使用简洁可读实现；混淆妨碍安全审查并引发信任问题"),
    SkillspectorRule("SC4", "supply_chain", "已知漏洞依赖", "升级依赖到修复该 CVE 的补丁版本，通过 OSV/NVD 查询漏洞详情"),
    SkillspectorRule("SC5", "supply_chain", "弃维依赖", "更换为积极维护的替代包，核查仓库最近提交与 open issues"),
    SkillspectorRule("SC6", "supply_chain", "typosquatting", "核验包名正确、非近似伪造变体，对照 PyPI/npm 官方包名"),
    SkillspectorRule("SC7", "supply_chain", "未验证镜像", "保持镜像签名校验（Docker Content Trust/cosign）与 registry TLS 开启，仅拉取签名且来自可信 registry 的镜像"),
    SkillspectorRule("SC8", "supply_chain", "打包字节码", "不要在技能中打包 __pycache__ 或 .pyc/.pyo，打包前删除；确需保留的 fixture 隔离到技能安装路径之外"),
    SkillspectorRule("SC9", "supply_chain", "隐藏可执行工件", "让可执行文件显式、可直接审查；审查文档、隐藏文件与伪装容器内打包可执行内容的来源"),
    # 扩展规则：Agent Snooping（归类见文档「扩展规则」-> 权限与代码执行类）
    SkillspectorRule("AS1", "privilege_escalation", "代理配置访问", "移除访问代理配置目录（.claude/、.codex/、.gemini/）的代码与指令；配置值改为显式参数或环境变量传入"),
    SkillspectorRule("AS2", "privilege_escalation", "MCP 配置访问", "移除读取 MCP 配置文件（mcp.json）的代码与指令；MCP 服务器详情应由代理运行时管理"),
    SkillspectorRule("AS3", "privilege_escalation", "技能枚举", "移除列出或读取其他技能文件的代码与指令；技能应独立运行，跨技能访问属提权"),
    # 扩展规则：SSRF（归类见文档「扩展规则」-> 权限与代码执行类）
    SkillspectorRule("SSRF1", "tool_misuse", "云元数据访问", "移除对云元数据端点的访问（除非严格必需）；若确需，加以限制（如 IMDSv2 跳数限制），绝不暴露返回的凭证"),
    SkillspectorRule("SSRF2", "tool_misuse", "内网/回环请求", "技能代码避免请求回环、链路本地与私网主机；若确有内网访问意图，文档化并按白名单校验目标"),
    SkillspectorRule("SSRF3", "tool_misuse", "动态请求目标", "不用不可信输入构造请求 URL；按白名单校验主机，发请求前拒绝内部与元数据地址"),
    # 扩展规则：不安全反序列化（与 AST10/TT6 同族 -> 行为 AST）
    SkillspectorRule("DS1", "dangerous_code", "PHP 对象注入", "避免对不可信 PHP 输入使用 unserialize()；用 json_decode()，或经 allowed_classes => false 限制类"),
    SkillspectorRule("DS2", "dangerous_code", "Ruby Marshal", "绝不对不可信数据调用 Marshal.load/restore；数据交换用 JSON.parse"),
    SkillspectorRule("DS3", "dangerous_code", "不安全 YAML", "用 YAML.safe_load（或 Psych.safe_load）并传入显式类白名单；Oj 避免对不可信输入使用 :object 模式"),
    SkillspectorRule("DS4", "dangerous_code", "JS 反序列化", "不用 node-serialize/funcster/serialize-to-js 反序列化不可信输入；用 JSON.parse（不执行嵌入代码）"),
    # 扩展规则：BH2/BH3 为条件激活的远程外泄发现（见文档「计分规则」风险下限）
    SkillspectorRule("BH2", "data_exfiltration", "闭环远程外泄", "断开该外泄链路，移除把本地数据闭环回传远程的代码；确认数据流向并做最小权限收敛"),
    SkillspectorRule("BH3", "data_exfiltration", "远程外泄载荷", "移除远程外泄载荷与相关网络调用；确认数据流向并做最小权限收敛"),
)

RULE_BY_ID: dict[str, SkillspectorRule] = {rule.rule_id: rule for rule in RULE_CATALOG}

# 规则 ID（大写） -> 维度 key（检测项与维度的映射关系）
RULE_DIMENSIONS: dict[str, str] = {rule.rule_id: rule.dimension for rule in RULE_CATALOG}

# SkillSpector category（小写） -> 维度 key（报告里 category 优先于规则目录）
CATEGORY_TO_DIMENSION: dict[str, str] = {
    "prompt injection": "prompt_injection",
    "system prompt leakage": "system_prompt_leakage",
    "memory poisoning": "memory_poisoning",
    "anti refusal": "anti_refusal",
    "anti-refusal": "anti_refusal",
    "trigger abuse": "trigger_abuse",
    "data exfiltration": "data_exfiltration",
    "output handling": "output_handling",
    "privilege escalation": "privilege_escalation",
    "excessive agency": "excessive_agency",
    "tool misuse": "tool_misuse",
    "rogue agent": "rogue_agent",
    "behavioral ast": "dangerous_code",
    "taint tracking": "data_flow",
    "yara match": "yara_match",
    "yara signatures": "yara_match",
    "mcp least privilege": "mcp_least_privilege",
    "mcp tool poisoning": "mcp_tool_poisoning",
    "supply chain": "supply_chain",
    "agent snooping": "privilege_escalation",
}

# 规则 ID 前缀 -> 维度 key（规则目录之外的未知规则兜底；按长度降序匹配）
RULE_PREFIX_TO_DIMENSION: dict[str, str] = {
    "SSRF": "tool_misuse",
    "AST": "dangerous_code",
    "ASI": "mcp_least_privilege",
    "TT": "data_flow",
    "YR": "yara_match",
    "MP": "memory_poisoning",
    "PE": "privilege_escalation",
    "EA": "excessive_agency",
    "TM": "tool_misuse",
    "RA": "rogue_agent",
    "TP": "mcp_tool_poisoning",
    "LP": "mcp_least_privilege",
    "SC": "supply_chain",
    "TR": "trigger_abuse",
    "OH": "output_handling",
    "AR": "anti_refusal",
    "AS": "privilege_escalation",
    "DS": "dangerous_code",
    "BH": "data_exfiltration",
    "P": "prompt_injection",
    "E": "data_exfiltration",
}

# 未知规则兜底维度
FALLBACK_DIMENSION = "dangerous_code"


def resolve_dimension(issue: dict) -> str:
    """把一条 SkillSpector issue 归一化到 17 个风险维度之一。

    优先级：报告自带 ``category`` -> 检测项（规则 ID）映射 -> 规则 ID 前缀 -> 兜底维度。
    """
    category = str(issue.get("category") or "").strip().lower()
    if category in CATEGORY_TO_DIMENSION:
        return CATEGORY_TO_DIMENSION[category]

    rule_id = str(issue.get("id") or "").strip().upper()
    if rule_id in RULE_DIMENSIONS:
        return RULE_DIMENSIONS[rule_id]

    for prefix in sorted(RULE_PREFIX_TO_DIMENSION, key=len, reverse=True):
        if rule_id.startswith(prefix):
            return RULE_PREFIX_TO_DIMENSION[prefix]
    return FALLBACK_DIMENSION


def rule_meta(rule_id: str) -> SkillspectorRule | None:
    """按规则 ID 取检测项元数据（未知返回 None）。"""
    return RULE_BY_ID.get(str(rule_id or "").strip().upper())