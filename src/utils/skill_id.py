"""Skill ID generation: {source}:{owner}/{repo}/{skill_name}."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def build_skill_id(
    source: str,
    owner_repo: str,
    relative_skill_path: str,
) -> str:
    """Build a public skill_id.

    Args:
        source: e.g. ``"github"``, ``"gitcode"``.
        owner_repo: e.g. ``"owner/repo"`` (from ``extract_owner_repo``).
        relative_skill_path: repo-relative SKILL.md path, e.g.
            ``"skills/foo/SKILL.md"`` or ``"SKILL.md"`` (root-level).

    Returns:
        ``"{source}:{owner}/{repo}/{skill_name}"``.
    """
    if relative_skill_path == 'SKILL.md':
        skill_name = owner_repo.rsplit('/', 1)[-1]
    elif relative_skill_path.endswith('/SKILL.md'):
        skill_name = Path(relative_skill_path).parent.name
    else:
        raise ValueError(f'Expected a SKILL.md file, got: {relative_skill_path}')
    return f'{source}:{owner_repo}/{skill_name}'


def resolve_relative_skill_path(repo: Any, record: Any) -> str:
    """从 skill 记录的 source_url 推导仓库内 SKILL.md 相对路径。

    优先匹配 ``/blob/<ref>/`` 形式的 source_url；否则由 skill_id 反推
    （``{source}:{owner}/{repo}/{skill_name}`` → ``{skill_name}/SKILL.md``）。
    扫描路径与安全补齐路径共用同一实现，保证触发审计时 skill_path 口径一致。
    """
    refs = []
    if getattr(record, 'commit_id', None):
        refs.append(record.commit_id)
    version = getattr(record, 'version', None)
    if version:
        refs.append(version)
    branch = getattr(repo, 'branch', None)
    if branch:
        refs.append(branch)
    refs.extend(['HEAD', 'master', 'main'])

    for ref in dict.fromkeys(refs):
        marker = f'/blob/{ref}/'
        if marker in record.source_url:
            relative_path = record.source_url.split(marker, 1)[1]
            if relative_path == 'SKILL.md' or relative_path.endswith('/SKILL.md'):
                return relative_path

    owner_repo = extract_owner_repo(getattr(repo, 'url', None))
    prefix = f'{getattr(repo, "source", "")}:{owner_repo}/'
    skill_path = record.skill_id.removeprefix(prefix)
    repository_name = owner_repo.rsplit('/', 1)[-1]
    if skill_path == repository_name:
        return 'SKILL.md'
    return f'{skill_path.strip("/")}/SKILL.md'


def extract_owner_repo(repo_url: str | None) -> str:
    if not repo_url:
        raise ValueError('Repository url is required to derive skill_id')

    normalized_url = repo_url.strip()
    ssh_match = re.match(r'git@([^:]+):(.+)', normalized_url)
    if ssh_match:
        path = ssh_match.group(2).strip('/')
    else:
        parsed = urlparse(normalized_url)
        path = parsed.path.strip('/')

    if path.endswith('.git'):
        path = path[:-4]

    segments = [segment for segment in path.split('/') if segment]
    if len(segments) < 2:
        raise ValueError(f'Failed to extract owner/repo from url: {repo_url}')

    owner = slugify_identifier(segments[-2])
    repo = slugify_identifier(segments[-1])
    if not owner or not repo:
        raise ValueError(f'Invalid owner/repo derived from url: {repo_url}')
    return f'{owner}/{repo}'


def slugify_identifier(value: str) -> str:
    """将输入值规范化为小写标识符片段。

    转小写并去除首尾空白，将 ``[a-z0-9._-]`` 之外的任意字符替换为单个
    ``-``，压缩连续 ``-``，并去掉首尾的 ``-``。空白输入返回空字符串。

    示例::

        >>> slugify_identifier('  Foo-Bar  ')
        'foo-bar'
        >>> slugify_identifier('Hello World!!')
        'hello-world'
        >>> slugify_identifier('a  --  b')
        'a-b'
        >>> slugify_identifier('--trim--')
        'trim'
        >>> slugify_identifier('Repo_Name.git')
        'repo_name.git'
        >>> slugify_identifier('中文技能')
        ''
        >>> slugify_identifier('   ')
        ''

    这是所有 skill_id 组件（owner、repo、skill_name）派生时使用的唯一
    canonical slugify —— 爬虫、下载器和 telemetry 必须统一使用它，
    以保证生成的 skill_id 一致。
    """
    lowered = value.strip().lower()
    if not lowered:
        return ''
    normalized = re.sub(r'[^a-z0-9._-]+', '-', lowered)
    normalized = re.sub(r'-{2,}', '-', normalized)
    return normalized.strip('-')