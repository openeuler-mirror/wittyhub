#!/usr/bin/env python3
import os
import re
import yaml
import httpx
from pathlib import Path
from datetime import datetime
from typing import Any

SKILLS_DIR = Path("/Users/duan/skills/official-skills")

API_BASE = "http://localhost:8080/api/v1"


def parse_skill_md(content: str) -> dict[str, Any]:
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}

    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def extract_description(content: str) -> str:
    lines = content.split("\n")
    description = []
    in_description = False

    for line in lines:
        if line.startswith("# "):
            in_description = True
            continue
        if in_description and line.startswith("##"):
            break
        if in_description and line.strip():
            description.append(line.strip())

    return " ".join(description)[:500]


def find_git_remote(skill_dir: Path) -> tuple[str, str, Path] | None:
    """Find GitHub org, repo, and repo root path from .git directory"""
    current = skill_dir
    for _ in range(10):
        git_dir = current / ".git"
        if git_dir.exists() and git_dir.is_dir():
            config_file = git_dir / "config"
            if config_file.exists():
                content = config_file.read_text()
                match = re.search(r"github\.com[/:]([\w-]+)/([\w.-]+?)(?:\.git)?$", content, re.MULTILINE)
                if match:
                    return match.group(1), match.group(2), current
        current = current.parent
    return None


def find_skills(base_dir: Path) -> list[tuple[Path, str, str, str, Path]]:
    """Returns (skill_md_path, skill_id, github_org, github_repo, repo_root)"""
    skills = []

    for root, dirs, files in os.walk(base_dir):
        root_path = Path(root)

        if "SKILL.md" in files:
            skill_md = root_path / "SKILL.md"
            skill_id = root_path.name

            git_info = find_git_remote(root_path)
            if git_info:
                github_org, github_repo, repo_root = git_info
            else:
                github_org = "unknown"
                github_repo = "unknown"
                repo_root = root_path

            skills.append((skill_md, skill_id, github_org, github_repo, repo_root))

    return skills


def create_skill_data(skill_md: Path, skill_id: str, github_org: str, github_repo: str, repo_root: Path) -> dict[str, Any]:
    content = skill_md.read_text()
    frontmatter = parse_skill_md(content)

    name = frontmatter.get("name", skill_id)
    description = frontmatter.get("description", extract_description(content))

    category = skill_md.parent.parent.name if skill_md.parent.parent.name != "skills" else "general"

    tags = []
    if "tags" in frontmatter:
        tags = frontmatter["tags"] if isinstance(frontmatter["tags"], list) else [frontmatter["tags"]]
    elif "TRIGGER" in content:
        tags.append("trigger-based")

    skill_dir = skill_md.parent
    has_python = any((skill_dir / f).name == "python" for f in os.listdir(skill_dir)) if skill_dir.exists() else False
    has_typescript = any((skill_dir / f).name == "typescript" for f in os.listdir(skill_dir)) if skill_dir.exists() else False
    has_go = any((skill_dir / f).name == "go" for f in os.listdir(skill_dir)) if skill_dir.exists() else False

    platforms = []
    if has_python:
        platforms.append("python")
    if has_typescript:
        platforms.append("typescript")
    if has_go:
        platforms.append("go")

    skill_path = "/".join(skill_md.parent.relative_to(repo_root).parts)
    source_url = f"https://github.com/{github_org}/{github_repo}/tree/master/{skill_path}"

    return {
        "skill_id": f"github:{github_org}/{skill_id}",
        "name": name,
        "description": description,
        "source": "github",
        "source_url": source_url,
        "category": category,
        "tags": tags,
        "platform": ",".join(platforms) if platforms else None,
        "metadata": {
            "license": frontmatter.get("license"),
            "has_python": has_python,
            "has_typescript": has_typescript,
            "has_go": has_go,
            "github_org": github_org,
            "github_repo": github_repo,
        },
    }


async def import_skill(client: httpx.AsyncClient, skill_data: dict[str, Any]) -> bool:
    try:
        response = await client.post(f"{API_BASE}/skills/", json=skill_data)
        if response.status_code == 201:
            return True
        elif response.status_code == 409:
            return True
        else:
            print(f"Error creating skill {skill_data['skill_id']}: {response.status_code} - {response.text[:200]}")
            return False
    except Exception as e:
        print(f"Exception creating skill {skill_data['skill_id']}: {e}")
        return False


async def main():
    print("Scanning for skills...")
    skills = find_skills(SKILLS_DIR)
    print(f"Found {len(skills)} skills")

    success = 0
    failed = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, (skill_md, skill_id, github_org, github_repo, repo_root) in enumerate(skills):
            try:
                skill_data = create_skill_data(skill_md, skill_id, github_org, github_repo, repo_root)
                if await import_skill(client, skill_data):
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Error processing {skill_id}: {e}")
                failed += 1

            if (i + 1) % 100 == 0:
                print(f"Progress: {i + 1}/{len(skills)} (success: {success}, failed: {failed})")

    print(f"\nImport complete: {success} success, {failed} failed")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{API_BASE}/skills/?limit=1")
        if response.status_code == 200:
            data = response.json()
            print(f"Total skills in database: {data['total']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())