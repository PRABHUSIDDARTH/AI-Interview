"""
LocalKnowledgeRetriever — concrete implementation of KnowledgeRetriever.

Loads curated topic records from JSON files in:
    backend/app/data/knowledge/<skill_normalized>.json

Design properties:
- Fully offline: no network calls, no external dependencies
- RAG-ready: implement EmbeddingRetriever(KnowledgeRetriever) to upgrade to
  vector search without changing any upstream code
- Skill normalization: "node.js" → "nodejs", "postgres" → "postgresql", etc.
- Difficulty banding:
    Easy  → beginner records (may include some intermediate)
    Medium → intermediate records (may include some beginner + advanced)
    Hard   → advanced records (may include some intermediate)
- Falls back to _fallback.json for unknown/unsupported skills
"""

import json
import logging
import os
from typing import List, Dict, Optional

from app.services.knowledge.base import KnowledgeRetriever, TopicRecord
from app.services.knowledge.registry import get_sources_for_skill

logger = logging.getLogger("uvicorn.error")

# Path to the curated knowledge JSON files
_DATA_DIR = os.path.join(
    os.path.dirname(__file__),   # .../app/services/knowledge/
    "..", "..",                   # → app/
    "data", "knowledge"           # → app/data/knowledge/
)
_DATA_DIR = os.path.normpath(_DATA_DIR)

# Skill name normalization map — maps common aliases to JSON file names
_SKILL_NORMALIZER: Dict[str, str] = {
    # JavaScript variants
    "javascript": "javascript",
    "js": "javascript",
    "es6": "javascript",
    "ecmascript": "javascript",
    # Node.js variants
    "node": "nodejs",
    "node.js": "nodejs",
    "nodejs": "nodejs",
    # Python variants
    "python": "python",
    "python3": "python",
    # React variants
    "react": "react",
    "reactjs": "react",
    "react.js": "react",
    # TypeScript variants
    "typescript": "typescript",
    "ts": "typescript",
    # PostgreSQL variants
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "psql": "postgresql",
    "sql": "postgresql",
    # Docker variants
    "docker": "docker",
    # Git variants
    "git": "git",
    "github": "git",
    "gitlab": "git",
    # FastAPI variants
    "fastapi": "fastapi",
    "fast api": "fastapi",
    # MongoDB variants
    "mongodb": "mongodb",
    "mongo": "mongodb",
    # Redis variants
    "redis": "redis",
    # AWS variants
    "aws": "aws",
    "amazon web services": "aws",
    # Kubernetes variants
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    # CSS/HTML
    "css": "css",
    "css3": "css",
    "html": "html",
    "html5": "html",
    # Django
    "django": "django",
    # Flask (maps to fastapi/python knowledge as fallback)
    "flask": "fastapi",
    # Java variants
    "java": "java",
    "core java": "java",
    # Spring variants
    "spring": "spring",
    "spring boot": "spring",
    "springboot": "spring",
    "spring security": "spring",
}

# Difficulty → allowed difficulty bands (ordered by preference)
_DIFFICULTY_BANDS: Dict[str, List[str]] = {
    "easy":         ["beginner", "intermediate"],
    "medium":       ["intermediate", "beginner", "advanced"],
    "hard":         ["advanced", "intermediate"],
    # Case-insensitive variants
    "Easy":         ["beginner", "intermediate"],
    "Medium":       ["intermediate", "beginner", "advanced"],
    "Hard":         ["advanced", "intermediate"],
}


class LocalKnowledgeRetriever(KnowledgeRetriever):
    """
    Retrieves topic records from local curated JSON knowledge files.
    No network calls. Works fully offline.
    """

    def __init__(self, data_dir: Optional[str] = None):
        self._data_dir = data_dir or _DATA_DIR
        self._cache: Dict[str, List[TopicRecord]] = {}

    # ------------------------------------------------------------------
    # Public API (implements KnowledgeRetriever ABC)
    # ------------------------------------------------------------------

    def retrieve(
        self,
        selected_skills: List[str],
        difficulty: str = "Medium",
        experience_level: str = "Intermediate",
        max_topics: int = 12,
    ) -> List[TopicRecord]:
        """
        Retrieve topic records for the given skills, filtered by difficulty.

        Topics are distributed evenly across selected_skills so every selected
        skill gets at least some grounding context.
        """
        if not selected_skills:
            return []

        # Normalize difficulty key
        diff_key = difficulty.lower() if difficulty else "medium"
        allowed_bands = _DIFFICULTY_BANDS.get(diff_key, ["intermediate", "beginner", "advanced"])

        results: List[TopicRecord] = []
        per_skill = max(1, max_topics // len(selected_skills))

        for skill in selected_skills:
            records = self._load_skill(skill)
            if not records:
                # Fallback to generic records
                records = self._load_fallback()

            # Filter by difficulty band (primary band first, then others)
            filtered: List[TopicRecord] = []
            for band in allowed_bands:
                band_records = [r for r in records if r.difficulty == band]
                filtered.extend(band_records)
                if len(filtered) >= per_skill:
                    break

            # If still not enough, add any remaining records
            if len(filtered) < per_skill:
                remaining = [r for r in records if r not in filtered]
                filtered.extend(remaining)

            results.extend(filtered[:per_skill])

        return results[:max_topics]

    def get_source_references(self, selected_skills: List[str]) -> List[Dict]:
        """Return de-duplicated source references for all selected skills."""
        seen_names = set()
        refs = []
        for skill in (selected_skills or []):
            sources = get_sources_for_skill(skill)
            for src in sources:
                if src["name"] not in seen_names and src.get("type") != "curated_internal":
                    seen_names.add(src["name"])
                    refs.append({
                        "name": src["name"],
                        "url": src.get("url", ""),
                        "type": src.get("type", ""),
                        "priority": src.get("priority", 3),
                    })
        # Sort by priority
        refs.sort(key=lambda x: x.get("priority", 3))
        return refs

    # ------------------------------------------------------------------
    # Context formatting helpers (used by ai.py)
    # ------------------------------------------------------------------

    def format_knowledge_context(self, records: List[TopicRecord]) -> str:
        """Format a list of topic records into a compact LLM prompt block."""
        if not records:
            return ""
        blocks = [r.to_prompt_context() for r in records]
        return "\n\n".join(blocks)

    def format_source_references(self, selected_skills: List[str]) -> str:
        """Format source references as a compact list for the LLM prompt."""
        refs = self.get_source_references(selected_skills)
        if not refs:
            return ""
        lines = [f"- {r['name']}" + (f": {r['url']}" if r.get("url") else "") for r in refs]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal loading / caching
    # ------------------------------------------------------------------

    def _normalize_skill(self, skill: str) -> str:
        """Normalize a skill name to a JSON file stem."""
        key = skill.strip().lower()
        return _SKILL_NORMALIZER.get(key, key)

    def _load_skill(self, skill: str) -> List[TopicRecord]:
        """Load and cache topic records for one skill."""
        normalized = self._normalize_skill(skill)
        if normalized in self._cache:
            return self._cache[normalized]

        path = os.path.join(self._data_dir, f"{normalized}.json")
        if not os.path.isfile(path):
            logger.debug("No knowledge file found for skill '%s' (normalized: '%s'). Using fallback.", skill, normalized)
            return self._load_fallback()

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            records = [self._parse_record(item) for item in raw]
            self._cache[normalized] = records
            logger.debug("Loaded %d topic records for skill '%s'.", len(records), skill)
            return records
        except Exception as e:
            logger.error("Failed to load knowledge file '%s': %s", path, str(e))
            return self._load_fallback()

    def _load_fallback(self) -> List[TopicRecord]:
        """Load generic software engineering fallback records."""
        if "_fallback" in self._cache:
            return self._cache["_fallback"]

        path = os.path.join(self._data_dir, "_fallback.json")
        if not os.path.isfile(path):
            logger.warning("Fallback knowledge file not found at '%s'. Returning empty.", path)
            return []

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            records = [self._parse_record(item) for item in raw]
            self._cache["_fallback"] = records
            return records
        except Exception as e:
            logger.error("Failed to load fallback knowledge file: %s", str(e))
            return []

    @staticmethod
    def _parse_record(item: dict) -> TopicRecord:
        """Parse a raw dict into a TopicRecord, with safe defaults."""
        return TopicRecord(
            skill=item.get("skill", ""),
            topic=item.get("topic", ""),
            difficulty=item.get("difficulty", "intermediate"),
            concepts=item.get("concepts", []),
            question_types=item.get("question_types", ["conceptual", "practical"]),
            common_mistakes=item.get("common_mistakes", []),
            source_name=item.get("source_name", ""),
            source_url=item.get("source_url", ""),
            tags=item.get("tags", []),
        )
