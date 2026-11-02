"""
Source Registry — centralized metadata about trusted technical knowledge sources.

IMPORTANT:
- This registry stores METADATA ONLY (name, url, type, priority).
- No article text, no scraped content, no copyrighted material is stored here.
- Source URLs are attribution references so generated questions can be traced
  back to the knowledge domain they came from.
- Not every source is scrapeable; all sources here are referenced as metadata.
- Allowed usage column clarifies how each source can be used.
"""

from typing import Dict, List


# Priority levels:
#   1 = Official documentation (highest authority)
#   2 = Trusted educational source (curated, peer-reviewed-style)
#   3 = Internal curated knowledge bank (fallback)

SOURCE_REGISTRY: Dict[str, List[Dict]] = {

    "React": [
        {
            "name": "React Official Documentation",
            "url": "https://react.dev",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
            "notes": "Primary source for hooks, components, state, routing patterns",
        },
        {
            "name": "MDN Web Docs — JavaScript",
            "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
            "type": "trusted_educational",
            "priority": 2,
            "allowed_usage": "reference_metadata_only",
            "notes": "Useful for JavaScript concepts relevant to React (Promises, closures, etc.)",
        },
        {
            "name": "Internal Curated React Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
            "notes": "Curated topic records in data/knowledge/react.json",
        },
    ],

    "Python": [
        {
            "name": "Python Official Documentation",
            "url": "https://docs.python.org/3/",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated Python Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
            "notes": "Curated topic records in data/knowledge/python.json",
        },
    ],

    "JavaScript": [
        {
            "name": "MDN Web Docs — JavaScript",
            "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
            "type": "trusted_educational",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "ECMAScript Language Specification",
            "url": "https://tc39.es/ecma262/",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated JavaScript Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
        },
    ],

    "Node.js": [
        {
            "name": "Node.js Official Documentation",
            "url": "https://nodejs.org/en/docs/",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated Node.js Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
        },
    ],

    "PostgreSQL": [
        {
            "name": "PostgreSQL Official Documentation",
            "url": "https://www.postgresql.org/docs/current/",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated PostgreSQL Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
        },
    ],

    "Docker": [
        {
            "name": "Docker Official Documentation",
            "url": "https://docs.docker.com/",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated Docker Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
        },
    ],

    "Git": [
        {
            "name": "Git Official Documentation",
            "url": "https://git-scm.com/doc",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated Git Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
        },
    ],

    "TypeScript": [
        {
            "name": "TypeScript Official Documentation",
            "url": "https://www.typescriptlang.org/docs/",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated TypeScript Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
        },
    ],

    "FastAPI": [
        {
            "name": "FastAPI Official Documentation",
            "url": "https://fastapi.tiangolo.com/",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated FastAPI Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
        },
    ],

    "MongoDB": [
        {
            "name": "MongoDB Official Documentation",
            "url": "https://www.mongodb.com/docs/",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated MongoDB Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
        },
    ],

    "Redis": [
        {
            "name": "Redis Official Documentation",
            "url": "https://redis.io/docs/",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated Redis Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
        },
    ],

    "AWS": [
        {
            "name": "AWS Official Documentation",
            "url": "https://docs.aws.amazon.com/",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated AWS Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
        },
    ],

    "Kubernetes": [
        {
            "name": "Kubernetes Official Documentation",
            "url": "https://kubernetes.io/docs/",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated Kubernetes Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
        },
    ],

    "CSS": [
        {
            "name": "MDN Web Docs — CSS",
            "url": "https://developer.mozilla.org/en-US/docs/Web/CSS",
            "type": "trusted_educational",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated CSS Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
        },
    ],

    "HTML": [
        {
            "name": "MDN Web Docs — HTML",
            "url": "https://developer.mozilla.org/en-US/docs/Web/HTML",
            "type": "trusted_educational",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated HTML Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
        },
    ],

    "Django": [
        {
            "name": "Django Official Documentation",
            "url": "https://docs.djangoproject.com/",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated Django Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
        },
    ],

    "SQL": [
        {
            "name": "PostgreSQL Official Documentation",
            "url": "https://www.postgresql.org/docs/current/sql.html",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated SQL Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
            "notes": "Maps to postgresql.json for retrieval",
        },
    ],

    "Java": [
        {
            "name": "Oracle Java Documentation",
            "url": "https://docs.oracle.com/javase/tutorial/",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated Java Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
            "notes": "Curated topic records in data/knowledge/java.json",
        },
    ],

    "Spring": [
        {
            "name": "Spring Official Documentation",
            "url": "https://docs.spring.io",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Spring Security Reference",
            "url": "https://docs.spring.io/spring-security/reference/",
            "type": "official_documentation",
            "priority": 1,
            "allowed_usage": "reference_metadata_only",
        },
        {
            "name": "Internal Curated Spring Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
            "notes": "Curated topic records in data/knowledge/spring.json",
        },
    ],

    "_fallback": [
        {
            "name": "General Technical Documentation & Standards",
            "url": "https://developer.mozilla.org",
            "type": "trusted_educational",
            "priority": 2,
            "allowed_usage": "reference_metadata_only",
            "notes": "Used when no skill-specific source exists",
        },
        {
            "name": "Internal Curated General Software Engineering Knowledge Bank",
            "url": "",
            "type": "curated_internal",
            "priority": 3,
            "allowed_usage": "full_use",
            "notes": "Used when no skill-specific knowledge file exists",
        },
    ],
}


def get_sources_for_skill(skill: str) -> list:
    """Return source entries for a skill. Falls back to _fallback."""
    normalized = skill.strip()
    # Try exact match first
    if normalized in SOURCE_REGISTRY:
        return SOURCE_REGISTRY[normalized]
    # Try case-insensitive
    for key in SOURCE_REGISTRY:
        if key.lower() == normalized.lower():
            return SOURCE_REGISTRY[key]
    return SOURCE_REGISTRY.get("_fallback", [])
