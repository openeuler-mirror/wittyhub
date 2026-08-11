import asyncio
from unittest.mock import AsyncMock

from src.api.services.telemetry import TelemetryService, build_skill_id_from_telemetry


class TestSkillsTelemetry:
    def test_build_skill_id_from_telemetry_uses_source_type_source_and_skill(self):
        skill_id = build_skill_id_from_telemetry(
            "github",
            "vercel-labs/agent-skills",
            "deploy-to-vercel",
        )

        assert skill_id == "github/vercel-labs/agent-skills/deploy-to-vercel"

    def test_build_skill_id_from_telemetry_prefers_skill_files_path(self):
        skill_id = build_skill_id_from_telemetry(
            "github",
            "vercel-labs/agent-skills",
            "Deploy to Vercel",
            {"Deploy to Vercel": "skills/deploy-to-vercel/SKILL.md"},
        )

        assert skill_id == "github/vercel-labs/agent-skills/skills/deploy-to-vercel"

    def test_build_skill_id_from_telemetry_root_skill_matches_crawler(self):
        # Root-level SKILL.md resolves to the repo slug — same as the crawler
        # (build_public_skill_id), so the lookup hits the same DB record.
        skill_id = build_skill_id_from_telemetry(
            "github",
            "acme/agent-skills",
            "agent-skills",
            {"agent-skills": "SKILL.md"},
        )

        assert skill_id == "github/acme/agent-skills/agent-skills"

    def test_build_skill_id_from_telemetry_gitcode_matches_crawler(self):
        skill_id = build_skill_id_from_telemetry(
            "gitcode",
            "openeuler/yuanrong",
            "gitcode-api",
            {"gitcode-api": ".skills/gitcode-api/SKILL.md"},
        )

        assert skill_id == "gitcode/openeuler/yuanrong/.skills/gitcode-api"

    def test_process_install_telemetry_increments_each_matched_skill(self):
        service = TelemetryService(AsyncMock())
        service.skill_repo = AsyncMock()
        service.session.commit = AsyncMock()
        service.skill_repo.increment_download.side_effect = [True, True]
        params = {
            "event": "install",
            "source": "vercel-labs/agent-skills",
            "sourceType": "github",
            "skills": "deploy-to-vercel,create-sdk-plugin",
            "skillFiles": (
                '{"deploy-to-vercel":"skills/deploy-to-vercel/SKILL.md",'
                '"create-sdk-plugin":"skills/create-sdk-plugin/SKILL.md"}'
            ),
        }

        matched_skill_ids = asyncio.run(service.process(params))

        assert matched_skill_ids == [
            "github/vercel-labs/agent-skills/skills/deploy-to-vercel",
            "github/vercel-labs/agent-skills/skills/create-sdk-plugin",
        ]
        assert service.skill_repo.increment_download.await_count == 2
        service.skill_repo.increment_download.assert_any_await(
            "github/vercel-labs/agent-skills/skills/deploy-to-vercel"
        )
        service.skill_repo.increment_download.assert_any_await(
            "github/vercel-labs/agent-skills/skills/create-sdk-plugin"
        )
        service.session.commit.assert_awaited_once()

    def test_process_install_telemetry_skips_unmatched_skill_ids(self):
        service = TelemetryService(AsyncMock())
        service.skill_repo = AsyncMock()
        service.session.commit = AsyncMock()
        service.skill_repo.increment_download.side_effect = [True, False]
        params = {
            "event": "install",
            "source": "vercel-labs/agent-skills",
            "sourceType": "github",
            "skills": "deploy-to-vercel,missing-skill",
            "skillFiles": (
                '{"deploy-to-vercel":"skills/deploy-to-vercel/SKILL.md",'
                '"missing-skill":"skills/missing-skill/SKILL.md"}'
            ),
        }

        matched_skill_ids = asyncio.run(service.process(params))

        assert matched_skill_ids == [
            "github/vercel-labs/agent-skills/skills/deploy-to-vercel",
        ]
        service.session.commit.assert_awaited_once()
