# skillcrawler

`skillcrawler` 是 WittyHub 的 Skill 仓库发现工具。它从一组明确的 Git 仓库完成 clone/fetch、扫描 `SKILL.md`、分类和入库。

> 实现细节（总体流程、Git 同步策略、Tag 两阶段拉取、commit 去重、安全检测集成、数据库写入、错误处理与性能排查）见 [`doc/design/skillcrawler-discover-design.md`](../doc/design/skillcrawler-discover-design.md)，建议从「§2 总体流程」开始阅读。

---

## 1. CLI 命令

入口文件：

```bash
python skillcrawler/main.py <command>
```

| 命令 | 用途 |
|------|------|
| `query` | 查询 `skill_repos` 记录 |
| `discover` | 注册、clone/fetch、扫描并同步 Skill |
| `delete` | 删除 `skill_repos` 记录及本地 clone |

### query

查询所有 skill repo：

```bash
python skillcrawler/main.py query
```

按 id 查询：

```bash
python skillcrawler/main.py query --id <repo_id>
```

支持参数：

- `-i` / `--id`：查询单个 skill repo

### discover

`discover` 是唯一扫描入口。

支持参数：

| 参数 | 说明 |
|------|------|
| `-p` / `--platform` | 选择 `community` / `enterprise` / `personal` 仓库列表；不传时读取全部列表 |
| `-r` / `--repository-path` | 指定已有的 openEuler-skills 本地目录；默认下载到 `<storage.local_path>/skill-repositories/openEuler-skills` |
| `-u` / `--url` | 扫描单个仓库 URL，不依赖配置列表 |
| `-b` / `--branch` | 与 `--url` 搭配使用，指定分支 |

参数约束：

- `--branch` 只能和 `--url` 一起使用。

默认扫描全部配置列表：

```bash
python skillcrawler/main.py discover
```

扫描指定平台配置列表：

```bash
python skillcrawler/main.py discover --platform community
python skillcrawler/main.py discover --platform enterprise
python skillcrawler/main.py discover --platform personal
```

使用已有的本地 openEuler-skills 仓库：

```bash
python skillcrawler/main.py discover --repository-path /path/to/openEuler-skills
```

扫描单个仓库：

```bash
python skillcrawler/main.py discover --url https://gitcode.com/openeuler/wittyhub-cli
```

单个 URL 平台识别规则：

- `https://gitcode.com/openeuler/<repo>` 会自动识别为 `platform=community`
- 如果显式传入 `--platform`，以显式参数为准

扫描单个仓库指定分支：

```bash
python skillcrawler/main.py discover --url https://gitcode.com/openeuler/wittyhub-cli --branch master
```

### delete

删除仓库记录和本地 clone：

```bash
python skillcrawler/main.py delete --id <repo_id>
```

支持参数：

- `-i` / `--id`：必填，指定要删除的 skill repo

---

## 2. 仓库来源配置

默认仓库列表来源：

```text
openEuler-skills/{community,enterprise,personal}/*/skill.yaml
```

示例：

```yaml
# community/Infrastructure/skill.yaml
name: Infrastructure
skill_repos:
  - url: https://gitcode.com/openeuler/IB_Robot
```

平台映射：

| 目录分组 | 写入 platform |
|----------|---------------|
| `community` | `community` |
| `personal` | `personal` |
| `enterprise` | `enterprise` |

---

## 3. 输出与日志路径

默认本地存储来自 `config.yaml`：

```yaml
storage:
  local_path: /opt/wittyhub/
```

仓库 clone 路径：

```text
<storage.local_path>/skill-repositories/<repo_name>
```

示例：

```text
/opt/wittyhub/skill-repositories/gitcode.com_openeuler_wittyhub-cli
```

`repo_name` 的生成方式：

```text
删除 http:// 或 https://
删除末尾 .git
将 / 替换为 _
```

日志路径：

```text
<storage.local_path>/logs/skillcrawler.log
```

---

## 4. 推荐使用方式

推荐从项目根目录执行：

```bash
cd wittyhub
python skillcrawler/main.py query
python skillcrawler/main.py discover
```

也支持从 `skillcrawler/` 目录执行：

```bash
cd wittyhub/skillcrawler
python main.py query
python main.py discover
```

查看帮助：

```bash
python skillcrawler/main.py --help
python skillcrawler/main.py query --help
python skillcrawler/main.py discover --help
python skillcrawler/main.py delete --help
```
