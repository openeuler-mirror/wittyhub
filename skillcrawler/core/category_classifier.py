from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx

from skillcrawler.core.config import load_crawler_config


_logger = logging.getLogger(__name__)


class CategoryClassificationError(RuntimeError):
    pass


class DeepSeekCategoryClassifier:
    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path
        self._config = load_crawler_config(config_path)
        self.categories = self._load_categories()
        self.model_name = self._load_model_name()
        self.api_key = self._load_api_key()
        self.base_url = self._load_base_url()
        self.timeout = float(self._load_timeout())

    def classify(
        self,
        *,
        skill_file: Path,
        metadata: dict[str, object],
        content: str,
        source_url: str,
    ) -> str | None:
        metadata_category = self._normalize_category(metadata.get("category"))
        if metadata_category is not None:
            return metadata_category

        if not self.api_key or not self.categories:
            return None

        prompt = self._build_prompt(
            skill_file=skill_file,
            metadata=metadata,
            content=content,
            source_url=source_url,
        )

        try:
            response_text = self._call_deepseek(prompt)
        except Exception as exc:
            message = f"DeepSeek category classification failed for {skill_file}: {exc}"
            _logger.warning(message)
            raise CategoryClassificationError(message) from exc

        return self._normalize_category(response_text)

    def _load_categories(self) -> list[str]:
        categories = self._config.get("categories") or []
        if not isinstance(categories, list):
            return []
        normalized = [str(item).strip() for item in categories if str(item).strip()]
        return normalized

    def _load_model_name(self) -> str:
        model_cfg = self._config.get("model") or {}
        value = model_cfg.get("name") or "deepseek-chat"
        return str(value).strip()

    def _load_api_key(self) -> str:
        model_cfg = self._config.get("model") or {}
        value = model_cfg.get("api_key") or ""
        return str(value).strip()

    def _load_base_url(self) -> str:
        model_cfg = self._config.get("model") or {}
        value = model_cfg.get("base_url") or "https://api.deepseek.com"
        return str(value).rstrip("/")

    def _load_timeout(self) -> float:
        model_cfg = self._config.get("model") or {}
        value = model_cfg.get("timeout") or 30
        return float(value)

    def _build_prompt(
        self,
        *,
        skill_file: Path,
        metadata: dict[str, object],
        content: str,
        source_url: str,
    ) -> str:
        description = str(metadata.get("description") or "").strip()
        tags = metadata.get("tags") or []
        if isinstance(tags, list):
            tag_text = ", ".join(str(tag) for tag in tags[:10])
        else:
            tag_text = str(tags)
        excerpt = content.strip()[:2000]
        categories_text = ", ".join(self.categories)

        return (
            "You are classifying an AI skill into exactly one category.\n"
            f"Available categories: {categories_text}\n"
            "Return only one category from the list above. Do not explain.\n"
            "If you are uncertain, return others.\n\n"
            f"Skill file: {skill_file.name}\n"
            f"Source URL: {source_url}\n"
            f"Name: {metadata.get('name') or skill_file.parent.name}\n"
            f"Description: {description}\n"
            f"Tags: {tag_text}\n"
            "Content excerpt:\n"
            f"{excerpt}"
        )

    def _call_deepseek(self, prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You classify skills into one predefined category.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

    def _normalize_category(self, value: object) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        if not text:
            return None

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                text = str(parsed.get("category") or "").strip()
        except Exception:
            pass

        lowered = text.lower()
        for category in self.categories:
            if lowered == category.lower():
                return category
        return None
