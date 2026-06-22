#!/usr/bin/env python3
import uuid
import random
from datetime import datetime, timezone

CATEGORIES = [
    "AI & Machine Learning",
    "Web Development",
    "DevOps & Cloud",
    "Data Processing",
    "Security",
    "Git & GitHub",
    "API Development",
    "Database",
    "Testing",
    "Documentation"
]

PLATFORMS = ["openclaw", "clawhub", "github", "gitlab", "local"]

SKILL_TEMPLATES = [
    {
        "name": "agent-team-orchestration",
        "description": "A skill for orchestrating multiple AI agents to work together on complex tasks. Provides patterns for agent communication, task delegation, and result aggregation.",
        "category": "AI & Machine Learning",
        "tags": ["ai", "agents", "orchestration", "multi-agent"],
        "content": """# Agent Team Orchestration

This skill enables coordination of multiple AI agents to solve complex problems together.

## Features
- Task decomposition and delegation
- Inter-agent communication protocols
- Result aggregation and synthesis
- Error handling and retry logic

## Usage
```python
from agents import TeamOrchestrator

orchestrator = TeamOrchestrator(agents=[agent1, agent2, agent3])
result = await orchestrator.execute(task)
```
"""
    },
    {
        "name": "code-review-assistant",
        "description": "Automated code review skill that analyzes pull requests for bugs, security issues, and code quality problems.",
        "category": "Git & GitHub",
        "tags": ["code-review", "security", "quality", "automation"],
        "content": """# Code Review Assistant

Automated code review for pull requests.

## Checks Performed
- Security vulnerability detection
- Code smell identification
- Performance issue analysis
- Best practices verification

## Configuration
Configure thresholds and ignore patterns in `.claire.yml`
"""
    },
    {
        "name": "data-pipeline-builder",
        "description": "Build scalable data pipelines for ETL operations with support for multiple data sources and destinations.",
        "category": "Data Processing",
        "tags": ["etl", "data", "pipeline", "automation"],
        "content": """# Data Pipeline Builder

Create and manage ETL data pipelines.

## Supported Sources
- PostgreSQL, MySQL, MongoDB
- S3, GCS, Azure Blob
- REST APIs, GraphQL

## Quick Start
```yaml
pipeline:
  source: postgres://db/main
  transforms:
    - type: filter
      condition: "amount > 0"
  destination: s3://bucket/data.parquet
```
"""
    },
    {
        "name": "api-gateway-setup",
        "description": "Configure and deploy API gateways with rate limiting, authentication, and monitoring.",
        "category": "API Development",
        "tags": ["api", "gateway", "devops", "monitoring"],
        "content": """# API Gateway Setup

Deploy production API gateways.

## Features
- JWT authentication
- Rate limiting per client
- Request/response logging
- Circuit breaker pattern

## Example Configuration
```yaml
gateway:
  port: 8080
  rate_limit: 100/minute
  auth:
    type: jwt
    secret: ${JWT_SECRET}
```
"""
    },
    {
        "name": "kubernetes-deployer",
        "description": "Deploy and manage Kubernetes clusters with automated scaling, rolling updates, and health checks.",
        "category": "DevOps & Cloud",
        "tags": ["kubernetes", "devops", "deployment", "cloud"],
        "content": """# Kubernetes Deployer

Automate Kubernetes deployments.

## Capabilities
- Helm chart deployment
- Rolling updates with zero downtime
- Horizontal pod autoscaling
- ConfigMap and Secret management

## Commands
```bash
k8s deploy --chart ./myapp-1.0.0.tgz
k8s scale --replicas 5 --deployment myapp
```
"""
    },
    {
        "name": "security-scanner",
        "description": "Scan code and dependencies for security vulnerabilities with detailed reporting and remediation suggestions.",
        "category": "Security",
        "tags": ["security", "scanner", "vulnerability", "automation"],
        "content": """# Security Scanner

Find security vulnerabilities in your codebase.

## Scan Types
- Static Application Security Testing (SAST)
- Dependency vulnerability scanning
- Secret detection
- Configuration hardening checks

## Report
Generate HTML/JSON reports with severity classification and remediation steps.
"""
    },
    {
        "name": "database-migration",
        "description": "Manage database schema migrations with version control and rollback support for PostgreSQL and MySQL.",
        "category": "Database",
        "tags": ["database", "migration", "postgresql", "mysql"],
        "content": """# Database Migration

Version-controlled database migrations.

## Commands
```bash
db-migrate create add_users_table
db-migrate up
db-migrate down --steps 1
db-migrate status
```

## Example Migration
```sql
-- migration: 20240115_add_users.sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```
"""
    },
    {
        "name": "test-generator",
        "description": "Automatically generate unit tests and integration tests from code changes using AI analysis.",
        "category": "Testing",
        "tags": ["testing", "automation", "unit-test", "integration-test"],
        "content": """# Test Generator

AI-powered test generation.

## Supported Frameworks
- pytest (Python)
- Jest (JavaScript/TypeScript)
- JUnit (Java)
- Go testing (Go)

## Usage
```bash
testgen generate --file src/calculator.py
testgen generate --coverage 80
```

## Output
Generates comprehensive test suites with edge case coverage.
"""
    },
]

AUTHORS = [
    "arminnaimi",
    "claude",
    "openai",
    "volta",
    "techcorp",
    "devteam",
    "aiskills",
    "cloudnative",
    "datateam",
    "securitypro"
]

def generate_skills(count=20):
    skills = []
    for i in range(count):
        template = random.choice(SKILL_TEMPLATES)
        author = random.choice(AUTHORS)
        version = f"v{random.randint(1,3)}.{random.randint(0,9)}.{random.randint(0,20)}"
        skill_id = f"{author}/{template['name']}"
        skills.append({
            "id": str(uuid.uuid4()),
            "skill_id": skill_id,
            "name": template["name"],
            "description": template["description"],
            "version": version,
            "commit_id": ''.join(random.choices('0123456789abcdef', k=40)),
            "author": author,
            "source": random.choice(["clawhub", "github", "local"]),
            "source_url": f"https://clawskills.sh/skills/{author}-{template['name']}",
            "category": template["category"],
            "tags": template["tags"],
            "platform": random.choice(PLATFORMS),
            "extra_metadata": {},
            "content": template["content"],
            "security_score": random.randint(60, 100),
            "download_count": random.randint(0, 500),
            "rating": round(random.uniform(3.5, 5.0), 1),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    return skills

if __name__ == "__main__":
    skills = generate_skills(20)
    for s in skills:
        print(f"{s['skill_id']} | {s['version']} | {s['category']}")
    print(f"\nTotal: {len(skills)} skills")