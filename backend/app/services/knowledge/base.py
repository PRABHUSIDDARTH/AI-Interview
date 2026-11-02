"""
Abstract base types for the knowledge/retrieval layer.

Design Goals:
- Fully offline by default (LocalKnowledgeRetriever reads curated JSON files)
- RAG-ready: KnowledgeRetriever ABC can be swapped for an embedding/vector retriever
  without changing the engine or AI service layers
- Source attribution without scraping: TopicRecord carries source_name/source_url
  as metadata references only — no copied article text is stored
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class TopicRecord:
    """
    A curated knowledge record for a specific technical topic.

    Fields are designed to ground LLM question generation without reproducing
    copyrighted content. Only topic metadata (concept lists, question type
    categories, common mistake patterns) is stored.
    """
    skill: str                          # e.g. "React"
    topic: str                          # e.g. "Hooks — useEffect"
    difficulty: str                     # "beginner" | "intermediate" | "advanced"
    concepts: List[str]                 # e.g. ["side effects", "dependency array"]
    question_types: List[str]           # ["conceptual", "practical", "debugging", "scenario"]
    common_mistakes: List[str]          # Common pitfalls useful for debugging questions
    source_name: str                    # Attribution reference: "React Official Documentation"
    source_url: str                     # Attribution URL: "https://react.dev/..."
    tags: List[str] = field(default_factory=list)  # ["hooks", "lifecycle"]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_prompt_context(self) -> str:
        """Format this record as a compact LLM prompt context block."""
        lines = [
            f"SKILL: {self.skill} | TOPIC: {self.topic} | DIFFICULTY: {self.difficulty}",
            f"CONCEPTS: {', '.join(self.concepts)}",
            f"QUESTION TYPES: {', '.join(self.question_types)}",
        ]
        if self.common_mistakes:
            lines.append(f"COMMON MISTAKES/GOTCHAS: {', '.join(self.common_mistakes)}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Abstract retriever
# ---------------------------------------------------------------------------

class KnowledgeRetriever(ABC):
    """
    Abstract base for knowledge retrieval.

    Current implementation: LocalKnowledgeRetriever (JSON files, fully offline).
    Future implementation: EmbeddingRetriever (vector store, semantic search).

    The engine and AI service layers depend only on this ABC so the concrete
    implementation can be swapped without any upstream changes.
    """

    @abstractmethod
    def retrieve(
        self,
        selected_skills: List[str],
        difficulty: str,
        experience_level: str,
        max_topics: int = 12,
    ) -> List[TopicRecord]:
        """
        Retrieve the most relevant topic records for the given skills and level.

        Args:
            selected_skills: Skills the user chose to focus on (from resume).
            difficulty: "Easy" | "Medium" | "Hard"
            experience_level: "Beginner" | "Intermediate" | "Advanced"
            max_topics: Maximum number of records to return.

        Returns:
            List of TopicRecord, distributed across selected_skills.
        """
        ...

    @abstractmethod
    def get_source_references(self, selected_skills: List[str]) -> List[Dict[str, str]]:
        """
        Return source attribution metadata for the given skills.
        Used to populate the source_context DB column.

        Returns:
            List of {"name": ..., "url": ..., "type": ..., "priority": ...}
        """
        ...
