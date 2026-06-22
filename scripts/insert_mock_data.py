#!/usr/bin/env python3
import uuid
import random

SKILL_TEMPLATES = [
    {
        "name": "agent-team-orchestration",
        "description": "A skill for orchestrating multiple AI agents to work together on complex tasks.",
        "category": "AI & Machine Learning",
        "tags": ["ai", "agents", "orchestration", "multi-agent"],
        "content": "# Agent Team Orchestration\n\nThis skill enables coordination of multiple AI agents.\n\n## Features\n- Task decomposition\n- Inter-agent communication\n- Result aggregation"
    },
    {
        "name": "code-review-assistant",
        "description": "Automated code review skill that analyzes pull requests.",
        "category": "Git & GitHub",
        "tags": ["code-review", "security", "quality"],
        "content": "# Code Review Assistant\n\nAutomated code review for pull requests."
    },
    {
        "name": "data-pipeline-builder",
        "description": "Build scalable data pipelines for ETL operations.",
        "category": "Data Processing",
        "tags": ["etl", "data", "pipeline"],
        "content": "# Data Pipeline Builder\n\nCreate and manage ETL data pipelines."
    },
    {
        "name": "api-gateway-setup",
        "description": "Configure and deploy API gateways with rate limiting.",
        "category": "API Development",
        "tags": ["api", "gateway", "devops"],
        "content": "# API Gateway Setup\n\nDeploy production API gateways."
    },
    {
        "name": "kubernetes-deployer",
        "description": "Deploy and manage Kubernetes clusters.",
        "category": "DevOps & Cloud",
        "tags": ["kubernetes", "devops", "deployment"],
        "content": "# Kubernetes Deployer\n\nAutomate Kubernetes deployments."
    },
    {
        "name": "security-scanner",
        "description": "Scan code for security vulnerabilities.",
        "category": "Security",
        "tags": ["security", "scanner", "vulnerability"],
        "content": "# Security Scanner\n\nFind security vulnerabilities."
    },
]

AUTHORS = ["arminnaimi", "claude", "openai", "volta", "techcorp"]

sql_parts = []
for i in range(20):
    template = random.choice(SKILL_TEMPLATES)
    author = random.choice(AUTHORS)
    version = f"v{random.randint(1,3)}.{random.randint(0,9)}.{random.randint(0,20)}"
    skill_id = f"{author}/{template['name']}:{version}"
    commit_id = ''.join(random.choices('0123456789abcdef', k=40))
    security_score = random.randint(60, 100)
    download_count = random.randint(0, 500)
    rating = round(random.uniform(3.5, 5.0), 1)

    tags_list = template["tags"]
    tags_sql = "ARRAY[" + ", ".join(f"'{t}'" for t in tags_list) + "]::text[]"

    sql = f"""INSERT INTO skills (id, skill_id, name, description, version, commit_id, author, source, source_url, category, tags, platform, extra_metadata, content, security_score, download_count, rating, created_at, updated_at)
VALUES (
    '{uuid.uuid4()}',
    '{skill_id}',
    '{template["name"]}',
    E'{template["description"].replace("'", "''")}',
    '{version}',
    '{commit_id}',
    '{author}',
    'clawhub',
    'https://clawskills.sh/skills/{author}-{template["name"]}',
    '{template["category"]}',
    {tags_sql},
    'openclaw',
    '{{}}'::jsonb,
    E'{template["content"].replace("'", "''")}',
    {security_score},
    {download_count},
    '{rating}',
    NOW(),
    NOW()
);"""
    sql_parts.append(sql)

print("\n".join(sql_parts))