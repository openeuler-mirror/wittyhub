"""Skill frontmatter parsing, ID generation, and URL building."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from src.models.orm import SkillRepoModel


# ── URL building ───────────────────────────────────────────────────


def build_skill_md_url(
    repo: "SkillRepoModel",
    relative_path: str,
    ref: str | None = None,
) -> str | None:
    if not repo.url:
        return None
    browse_base_url = normalize_repository_browse_base_url(repo.url)
    if not browse_base_url:
        return None
    if ref and ref != 'HEAD':
        branch = ref
    elif repo.branch:
        branch = repo.branch
    else:
        # GitHub supports /blob/HEAD/ as a placeholder for the default branch;
        # other platforms (GitCode, Gitee, GitLab) do not and need an actual
        # branch name.  Fall back to 'master' which is the most common default
        # on those platforms.
        branch = 'HEAD' if repo.source == 'github' else 'master'
    cleaned_relative_path = relative_path.lstrip('/')
    return f'{browse_base_url}/blob/{branch}/{cleaned_relative_path}'


def normalize_repository_browse_base_url(repo_url: str) -> str | None:
    normalized_url = repo_url.strip()
    if not normalized_url:
        return None

    ssh_match = re.match(r'git@([^:]+):(.+)', normalized_url)
    if ssh_match:
        host = ssh_match.group(1)
        path = ssh_match.group(2).strip('/')
        if path.endswith('.git'):
            path = path[:-4]
        return f'https://{host}/{path}'

    parsed = urlparse(normalized_url)
    if not parsed.netloc:
        return None
    path = parsed.path.strip('/')
    if path.endswith('.git'):
        path = path[:-4]
    if not path:
        return None
    return f'{parsed.scheme}://{parsed.netloc}/{path}'


# ── Skill source derivation ────────────────────────────────────────


def derive_skill_source(repo_url: str | None) -> tuple[str, str]:
    if not repo_url:
        raise ValueError('Repository url is required to derive skill source')

    normalized_url = repo_url.strip()
    ssh_match = re.match(r'git@([^:]+):(.+)', normalized_url)
    if ssh_match:
        raw_host = ssh_match.group(1).lower()
        path = ssh_match.group(2).strip('/')
    else:
        parsed = urlparse(normalized_url)
        if not parsed.netloc:
            raise ValueError(f'Invalid git repository url: {repo_url}')
        raw_host = parsed.netloc.lower()
        path = parsed.path.strip('/')

    if path.endswith('.git'):
        path = path[:-4]

    if raw_host == 'github.com':
        host = 'github'
    elif raw_host == 'gitcode.com':
        host = 'gitcode'
    elif raw_host == 'gitlab.com':
        host = 'gitlab'
    elif raw_host == 'gitee.com':
        host = 'gitee'
    else:
        raise ValueError(f'Unsupported git repository host: {repo_url}')

    segments = [segment for segment in path.split('/') if segment]
    if len(segments) < 2:
        raise ValueError(f'Failed to extract repository owner from url: {repo_url}')

    owner = segments[-2].strip()
    if not owner:
        raise ValueError(f'Invalid repository owner derived from url: {repo_url}')

    return host, owner


# ── Frontmatter parsing ────────────────────────────────────────────


def load_skill_frontmatter(
    skill_file: Path,
) -> tuple[dict[str, object], str]:
    text = skill_file.read_text(encoding='utf-8')
    return parse_skill_frontmatter_text(text)


def parse_skill_frontmatter_text(text: str) -> tuple[dict[str, object], str]:
    stripped = text.lstrip()
    if not stripped.startswith('---'):
        return {}, text.strip()
    parts = stripped.split('---', maxsplit=2)
    if len(parts) < 3:
        return {}, text.strip()

    raw_frontmatter = parts[1]
    content = parts[2].lstrip('\r\n')

    metadata: dict[str, object] = {}
    current_key: str | None = None
    block_scalar_indicator: str | None = None
    for line in raw_frontmatter.splitlines():
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith('#'):
            continue

        # While in a YAML block scalar (| or >), any indented line is content;
        # a non-indented line ends the block and is processed normally.
        if block_scalar_indicator is not None:
            if line[:1] in (' ', '\t'):
                if current_key is not None:
                    existing = metadata.get(current_key)
                    if isinstance(existing, str) and existing:
                        if block_scalar_indicator == '|':
                            metadata[current_key] = f'{existing}\n{stripped_line}'
                        else:  # folded '>'
                            metadata[current_key] = f'{existing} {stripped_line}'
                    else:
                        metadata[current_key] = stripped_line
                continue
            block_scalar_indicator = None

        if stripped_line.startswith('- ') and current_key == 'triggers':
            triggers = metadata.setdefault('triggers', [])
            if isinstance(triggers, list):
                trigger = stripped_line[2:].strip()
                if trigger:
                    triggers.append(trigger)
            continue

        if ':' not in line:
            if current_key is not None:
                existing = metadata.get(current_key)
                if isinstance(existing, str):
                    metadata[current_key] = f'{existing} {stripped_line}'.strip()
            continue

        key, value = line.split(':', 1)
        current_key = key.strip()
        value = value.strip()

        if value in ('|', '>', '|-', '>-', '|+', '>+'):
            block_scalar_indicator = value[0]
            metadata[current_key] = ''
            continue

        block_scalar_indicator = None
        metadata[current_key] = _parse_frontmatter_value(current_key, value)

    return metadata, content.strip()


def _parse_frontmatter_value(key: str, value: str) -> object:
    if not value:
        return [] if key == 'triggers' else ''

    if key == 'triggers':
        if value.startswith('[') and value.endswith(']'):
            try:
                parsed = json.loads(value.replace("'", '"'))
            except Exception:
                parsed = None
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        return [value.strip('"\'')] if value.strip('"\'') else []

    lowered = value.lower()
    if lowered == 'true':
        return True
    if lowered == 'false':
        return False
    return value.strip('"\'')


# ── Misc helpers ───────────────────────────────────────────────────


def derive_repository_skill_name(
    skill_file: Path, metadata: dict[str, object],
) -> str:
    metadata_name = metadata.get('name')
    if isinstance(metadata_name, str) and metadata_name.strip():
        return metadata_name.strip()
    if skill_file.name == 'SKILL.md':
        return skill_file.parent.name
    return skill_file.stem




def should_skip_relative_path(relative_path: str) -> bool:
    relative_path = relative_path.lower()
    path_parts = relative_path.split('/')
    return any(
        part in {
            'template', 'templates', 'example', 'examples',
            'demo', 'demos', 'test', 'tests',
            'fixture', 'fixtures', 'docs', 'doc',
            'archive', 'archives', 'legacy',
        }
        for part in path_parts[:-1]
    )


def normalize_git_clone_url(url: str | None) -> str:
    if not url:
        return ''
    stripped = url.strip()

    ssh_match = re.match(r'git@([^:]+):(.+)', stripped)
    if ssh_match:
        host = ssh_match.group(1)
        path = ssh_match.group(2).strip('/')
        return f'git@{host}:{path}'

    parsed = urlparse(stripped)
    if not parsed.scheme or not parsed.netloc:
        return ''

    path = parsed.path.strip('/')
    if path.endswith('.git'):
        path = path[:-4]
    return f'{parsed.scheme}://{parsed.netloc}/{path}'


def normalize_clone_url_for_git(repo_url: str | None) -> str:
    if not repo_url:
        raise ValueError('git skill repos require url')
    if repo_url.endswith('.git'):
        return repo_url
    return f'{repo_url}.git'


def as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)


def as_optional_str_list(value: object) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        normalized = [str(item).strip() for item in value if str(item).strip()]
        return normalized or None
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else None
    return [str(value)]
