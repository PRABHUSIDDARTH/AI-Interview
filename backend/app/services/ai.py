import os
import json
import logging
import requests
from functools import lru_cache
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger("uvicorn.error")

class AIConfigError(Exception):
    """Raised when AI provider is not properly configured."""
    pass


class AIProviderError(Exception):
    """Raised when a real LLM call fails (network, HTTP status, or malformed response).

    Messages are redacted: they never contain the API key.
    """
    pass


# Default model per provider, used when AI_MODEL is unset or clearly belongs to another provider.
DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o-mini",
}
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
MAX_CHAT_HISTORY_MESSAGES = 10

class QuestionDTO(BaseModel):
    text: str = Field(..., description="The interview question text")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AnswerDTO(BaseModel):
    question_id: int = Field(..., description="ID of the question being answered")
    answer: str = Field(..., description="User's answer text")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationDTO(BaseModel):
    score: int = Field(..., ge=0, le=10, description="Overall score out of 10")
    correctness: float = Field(..., ge=0, le=1, description="Correctness ratio")
    relevance: float = Field(..., ge=0, le=1, description="Relevance ratio")
    technical_depth: float = Field(..., ge=0, le=1, description="Technical depth ratio")
    communication_quality: float = Field(..., ge=0, le=1, description="Communication quality ratio")
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    feedback: str = Field(..., description="Human‑readable feedback string")

from app.core.config import settings
from app.schemas.coaching import AICoachResponse

class AIProvider:
    """Modular AI provider abstraction.

    Reads configuration from app settings (or environment variables).
    Supports Gemini and OpenAI. All real LLM traffic goes through `_call_llm`;
    public methods catch failures and fall back to the deterministic mock logic,
    logging a redacted warning each time they do.
    """

    def __init__(self) -> None:
        raw_provider = settings.AI_PROVIDER or os.getenv("AI_PROVIDER", "mock")
        self.provider_name = raw_provider.lower()
        self.api_key = settings.AI_API_KEY or os.getenv("AI_API_KEY")

        from app.services.adaptive_engine import AdaptiveDecisionEngine
        self.decision_engine = AdaptiveDecisionEngine()

        if self.provider_name in DEFAULT_MODELS:
            if not self.api_key:
                logger.warning(
                    "AI provider is set to '%s' but AI_API_KEY is not configured. "
                    "Every AI call will fall back to mock output.",
                    self.provider_name,
                )
        elif self.provider_name != "mock":
            logger.warning(
                "AI provider '%s' is not recognized. Falling back to mock provider.",
                self.provider_name,
            )
            self.provider_name = "mock"

        self.model = self._resolve_model(settings.AI_MODEL or os.getenv("AI_MODEL"))

    # --------------------- Shared LLM request helper ---------------------
    def _resolve_model(self, configured: Optional[str]) -> Optional[str]:
        """Pick the model for the active provider, honouring AI_MODEL unless it obviously
        belongs to the other provider (e.g. AI_MODEL=gemini-* with AI_PROVIDER=openai)."""
        default = DEFAULT_MODELS.get(self.provider_name)
        if default is None:
            return None
        configured = (configured or "").strip()
        if not configured:
            return default
        is_gemini_model = configured.lower().startswith(("gemini", "gemma"))
        if (self.provider_name == "gemini") != is_gemini_model:
            logger.warning(
                "AI_MODEL '%s' does not look like a %s model; using default '%s'.",
                configured, self.provider_name, default,
            )
            return default
        return configured

    @property
    def is_real_llm(self) -> bool:
        return self.provider_name in DEFAULT_MODELS

    def _redact(self, text: str) -> str:
        if self.api_key:
            text = text.replace(self.api_key, "***")
        return text

    def _call_llm(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        json_mode: bool = True,
        history: Optional[List[Dict[str, str]]] = None,
        timeout: float = 15,
    ) -> str:
        """Send one prompt (plus optional system prompt and chat history) to the configured
        provider and return the raw text reply.

        Raises AIConfigError if no real provider/key is configured, and AIProviderError for
        network, HTTP or response-shape failures. Neither error message contains the API key.
        """
        if not self.is_real_llm:
            raise AIConfigError(f"No real LLM provider configured (AI_PROVIDER='{self.provider_name}').")
        if not self.api_key:
            raise AIConfigError(f"AI provider is '{self.provider_name}' but AI_API_KEY is not configured.")

        turns = [
            (m.get("role", "user"), m.get("content", ""))
            for m in (history or [])[-MAX_CHAT_HISTORY_MESSAGES:]
            if isinstance(m, dict) and m.get("content")
        ]

        if self.provider_name == "gemini":
            # Key goes in a header, never in the URL, so it can't leak via error messages or logs.
            url = f"{GEMINI_BASE_URL}/{self.model}:generateContent"
            headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
            contents = [
                {"role": "model" if role == "assistant" else "user", "parts": [{"text": text}]}
                for role, text in turns
            ]
            contents.append({"role": "user", "parts": [{"text": prompt}]})
            body: Dict[str, Any] = {"contents": contents}
            if system:
                body["systemInstruction"] = {"parts": [{"text": system}]}
            if json_mode:
                body["generationConfig"] = {"responseMimeType": "application/json"}

            def extract(data: Dict[str, Any]) -> str:
                return data["candidates"][0]["content"]["parts"][0]["text"]
        else:  # openai
            url = OPENAI_CHAT_URL
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
            messages = [{"role": "system", "content": system}] if system else []
            messages += [
                {"role": "assistant" if role == "assistant" else "user", "content": text}
                for role, text in turns
            ]
            messages.append({"role": "user", "content": prompt})
            body = {"model": self.model, "messages": messages}
            if json_mode:
                body["response_format"] = {"type": "json_object"}

            def extract(data: Dict[str, Any]) -> str:
                return data["choices"][0]["message"]["content"]

        try:
            res = requests.post(url, json=body, headers=headers, timeout=timeout)
        except requests.RequestException as e:
            raise AIProviderError(
                self._redact(f"{self.provider_name} request failed: {type(e).__name__}: {e}")
            ) from None

        if res.status_code >= 400:
            raise AIProviderError(
                self._redact(f"{self.provider_name} returned HTTP {res.status_code}: {res.text[:300]}")
            )

        try:
            text = extract(res.json())
        except (ValueError, KeyError, IndexError, TypeError):
            raise AIProviderError(
                self._redact(f"{self.provider_name} returned an unexpected response: {res.text[:300]}")
            ) from None
        if not isinstance(text, str) or not text.strip():
            raise AIProviderError(f"{self.provider_name} returned an empty response.")
        return text

    def _call_llm_json(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Like `_call_llm` but in JSON mode, returning the parsed JSON object."""
        text = self._call_llm(prompt, json_mode=True, **kwargs)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            raise AIProviderError(f"{self.provider_name} returned invalid JSON: {text[:200]}") from None
        if not isinstance(parsed, dict):
            raise AIProviderError(f"{self.provider_name} returned JSON that is not an object.")
        return parsed

    def _log_fallback(self, operation: str, error: Exception) -> None:
        """One consistent, redacted log line whenever a real LLM call falls back to mock output."""
        logger.warning(
            "LLM %s failed (provider=%s, model=%s): %s. Falling back to mock output.",
            operation, self.provider_name, self.model, self._redact(str(error)),
        )

    # --------------------- Question Generation ---------------------
    def generate_question(self, setup: Dict[str, Any], history: List[Dict[str, Any]]) -> QuestionDTO:
        """Generate a new interview question. Used dynamically for legacy flows or single questions."""
        if self.provider_name == "mock":
            q_number = len(history) + 1
            role = setup.get("job_role", "Software Developer")
            return QuestionDTO(
                text=f"Mock question {q_number} for role {role}. Explain a key concept related to this role.",
                metadata={"mock": True, "question_number": q_number},
            )
        
        # Call batch generator to get a single question if history is used
        questions = self.generate_questions_batch(setup, len(history) + 1)
        return QuestionDTO(
            text=questions[-1],
            metadata={"ai": True, "provider": self.provider_name}
        )

    def generate_questions_batch(
        self,
        setup: Dict[str, Any],
        count: int,
        resume_text: Optional[str] = None,
        job_description: Optional[str] = None,
        retrieved_knowledge: Optional[List[Dict]] = None,
    ) -> List[str]:
        """Generate a list of N questions in one batch, using selected_skills as the primary focus.
        Falls back to resume_skills if no skill selection made. Validates every returned question
        is relevant to at least one selected skill before returning."""
        if self.provider_name == "mock":
            return self._generate_mock_questions(setup, count, retrieved_knowledge=retrieved_knowledge)

        resume_skills = setup.get("resume_skills", [])
        selected_skills = setup.get("selected_skills", [])
        language = setup.get("interview_language", "English")

        # Determine the effective focus skills: selected > resume > empty
        focus_skills: List[str] = selected_skills if selected_skills else resume_skills

        context_parts = []
        if resume_skills:
            skills_str = ", ".join(resume_skills) if isinstance(resume_skills, list) else str(resume_skills)
            context_parts.append(f"RESUME SKILLS: {skills_str}")
        if selected_skills:
            sel_str = ", ".join(selected_skills) if isinstance(selected_skills, list) else str(selected_skills)
            context_parts.append(
                f"SELECTED INTERVIEW SKILLS: {sel_str}\n"
                f"STRICT RULE: Generate questions PRIMARILY and DIRECTLY about the SELECTED INTERVIEW SKILLS above.\n"
                f"Do NOT generate questions about technologies, frameworks, or languages that are NOT in the selected list.\n"
                f"If multiple skills are selected, you may ask integration questions that combine them."
            )

        # --- Knowledge grounding context (core of the hybrid system) ---
        if retrieved_knowledge:
            knowledge_blocks = []
            for rec in retrieved_knowledge:
                block_lines = [
                    f"SKILL: {rec.get('skill', '')} | TOPIC: {rec.get('topic', '')} | DIFFICULTY: {rec.get('difficulty', '')}",
                    f"CONCEPTS: {', '.join(rec.get('concepts', []))}",
                    f"QUESTION TYPES APPROPRIATE: {', '.join(rec.get('question_types', []))}",
                ]
                mistakes = rec.get("common_mistakes", [])
                if mistakes:
                    block_lines.append(f"COMMON MISTAKES/GOTCHAS: {', '.join(mistakes)}")
                knowledge_blocks.append("\n".join(block_lines))

            knowledge_context = "\n\n".join(knowledge_blocks)

            # Build source references from knowledge records
            seen_sources = set()
            source_lines = []
            for rec in retrieved_knowledge:
                src_name = rec.get("source_name", "")
                src_url = rec.get("source_url", "")
                if src_name and src_name not in seen_sources:
                    seen_sources.add(src_name)
                    source_lines.append(
                        f"  - {src_name}" + (f": {src_url}" if src_url else "")
                    )

            context_parts.append(
                f"RELEVANT KNOWLEDGE CONTEXT (use as grounding — do NOT copy verbatim):\n"
                f"{knowledge_context}\n\n"
                f"SOURCE REFERENCES (attribution only):\n"
                + "\n".join(source_lines)
            )

        if resume_text:
            truncated_resume = resume_text[:2000]
            context_parts.append(f"Resume Context (for personalisation only):\n{truncated_resume}")
        if job_description:
            context_parts.append(f"Job Description:\n{job_description}")

        context_section = "\n\n".join(context_parts) + ("\n\n" if context_parts else "")

        lang_instruction = ""
        if language and language.lower() != "english":
            lang_instruction = (
                f"IMPORTANT LANGUAGE REQUIREMENT:\n"
                f"Generate the questions in {language}.\n"
                f"PRESERVE TECHNICAL TERMS: Keep technical technology names (e.g. Python, FastAPI, REST API, SQL, Docker, React, JavaScript, Git) in English script within the {language} text.\n"
                f"Example for Tamil: \"Python-ல் polymorphism என்றால் என்ன?\"\n"
            )

        difficulty = setup.get('difficulty', 'Medium')
        experience_level = setup.get('experience_level', 'Intermediate')

        prompt = (
            f"Generate a list of exactly {count} personalized, high-quality interview questions for a candidate.\n"
            f"Role: {setup.get('job_role')}\n"
            f"Type: {setup.get('interview_type')}\n"
            f"Experience Level: {experience_level}\n"
            f"Difficulty: {difficulty}\n"
            f"{lang_instruction}\n"
            f"GENERATION REQUIREMENTS:\n"
            f"1. Questions MUST be directly about the SELECTED INTERVIEW SKILLS only. Do not mention unselected technologies.\n"
            f"2. Use the RELEVANT KNOWLEDGE CONTEXT topics and concepts above as grounding. Do NOT copy source text verbatim.\n"
            f"3. Generate a BALANCED MIX of question types drawn from the context: conceptual, practical, scenario, debugging, advanced.\n"
            f"4. Use COMMON MISTAKES/GOTCHAS from the context to inspire debugging and scenario-based questions.\n"
            f"5. Make questions DISTINCT — avoid duplicate or near-identical questions on the same subtopic.\n"
            f"6. Match difficulty '{difficulty}' strictly:\n"
            f"   - Easy: foundational definitions, basic usage, simple comparisons.\n"
            f"   - Medium: practical application, trade-offs, debugging common issues.\n"
            f"   - Hard: architecture, optimisation, edge cases, design decisions.\n"
            f"7. Do NOT invent unsupported technical claims or technologies not in selected skills.\n"
            f"8. Generate ORIGINAL questions — not copies of source documentation.\n"
            f"9. Return response as a JSON object with a single key 'questions' containing a list of strings.\n"
            f"Example:\n{{\"questions\": [\"Question 1?\", \"Question 2?\"]}}\n"
        )
        if context_section:
            prompt = context_section + prompt

        if self.is_real_llm and not self.api_key:
            raise AIConfigError(f"AI provider is set to '{self.provider_name}' but AI_API_KEY is not configured in backend/.env.")

        def _call_ai(prompt_text: str) -> List[str]:
            try:
                parsed = self._call_llm_json(
                    prompt_text,
                    system="You are a professional technical interviewer who strictly follows skill focus constraints. Return JSON only.",
                )
                questions = parsed.get("questions", [])
                if isinstance(questions, list):
                    return [q for q in questions if isinstance(q, str) and q.strip()]
            except Exception as e:
                self._log_fallback("question generation", e)
            return []

        questions = _call_ai(prompt)

        # Pad/trim to requested count
        if len(questions) > count:
            questions = questions[:count]
        elif 0 < len(questions) < count:
            while len(questions) < count:
                questions.append(f"Follow-up question about {', '.join(focus_skills) if focus_skills else setup.get('job_role')}.")

        # ── Validation pipeline ──────────────────────────────────────────

        # Gate 1: Skill focus — hard gate, retry on failure
        if focus_skills and questions:
            valid, invalid_indices = self._validate_skill_focus(questions, focus_skills)
            if not valid:
                logger.warning(
                    "Skill focus validation failed for %d question(s). Attempting one retry.",
                    len(invalid_indices)
                )
                knowledge_hint = ""
                if retrieved_knowledge:
                    topics = list({rec.get("topic", "") for rec in retrieved_knowledge if rec.get("topic")})
                    knowledge_hint = f" Focus on these topics: {', '.join(topics[:5])}."
                retry_prompt = (
                    f"The following questions are NOT relevant to the selected skills ({', '.join(focus_skills)}).{knowledge_hint} "
                    f"Replace ONLY these questions with ones strictly about {', '.join(focus_skills)}:\n"
                    + "\n".join(f"{i+1}. {questions[i]}" for i in invalid_indices)
                    + f"\n\nRole: {setup.get('job_role')} | Experience: {setup.get('experience_level')} | Difficulty: {setup.get('difficulty')}\n"
                    + f"Return JSON: {{\"questions\": [<{len(invalid_indices)} replacement question(s)>]}}"
                )
                retry_result = _call_ai(retry_prompt)
                for new_idx, orig_idx in enumerate(invalid_indices):
                    if new_idx < len(retry_result):
                        questions[orig_idx] = retry_result[new_idx]
                    else:
                        skill = focus_skills[orig_idx % len(focus_skills)]
                        questions[orig_idx] = self._skill_fallback_question(skill, setup)

        # Gate 2: Deduplication — remove near-identical questions
        if questions:
            questions = self._deduplicate_questions(questions, focus_skills, setup)

        # Gate 3: Difficulty validation — soft gate (replace obvious mismatches for Hard)
        if questions:
            questions = self._validate_difficulty(questions, setup.get("difficulty", "Medium"), focus_skills, setup)

        # Gate 4: Source grounding check (soft gate, logs coverage)
        if questions and retrieved_knowledge:
            self._validate_source_grounding(questions, retrieved_knowledge, focus_skills)

        if questions:
            return questions

        return self._generate_mock_questions(setup, count, retrieved_knowledge=retrieved_knowledge)

    def _validate_skill_focus(self, questions: List[str], focus_skills: List[str]) -> tuple:
        """Validate each question mentions at least one focus skill keyword.
        Returns (all_valid: bool, invalid_indices: List[int]).
        """
        skill_keywords = [s.lower() for s in focus_skills]
        invalid_indices = []
        for i, q in enumerate(questions):
            q_lower = q.lower()
            if not any(kw in q_lower for kw in skill_keywords):
                invalid_indices.append(i)
        return (len(invalid_indices) == 0, invalid_indices)

    def _skill_fallback_question(self, skill: str, setup: Dict[str, Any]) -> str:
        """Return a guaranteed skill-specific fallback question."""
        level = setup.get("experience_level", "Intermediate")
        diff = setup.get("difficulty", "Medium")
        fallbacks = [
            f"Explain a key concept in {skill} and how you have applied it in a real project.",
            f"What are the most important features of {skill} for a {level} {setup.get('job_role', 'developer')}?",
            f"Describe a challenging problem you solved using {skill}.",
            f"What are the performance or architecture considerations when working with {skill} at {diff} level?",
        ]
        import hashlib
        idx = int(hashlib.md5(skill.encode()).hexdigest(), 16) % len(fallbacks)
        return fallbacks[idx]

    def _deduplicate_questions(
        self,
        questions: List[str],
        focus_skills: List[str],
        setup: Dict[str, Any]
    ) -> List[str]:
        """Detect and replace near-identical questions (>60% non-stopword token overlap)."""
        import re
        stop_words = {
            "what", "is", "the", "a", "an", "and", "or", "in", "on", "at", "to", "for",
            "with", "by", "of", "from", "how", "do", "does", "did", "can", "could", "would",
            "should", "you", "your", "we", "explain", "describe", "discuss", "tell", "me",
            "about", "difference", "between", "when", "why", "which", "use", "using", "work"
        }

        def get_tokens(q_text: str) -> set:
            words = set(re.findall(r"[a-z0-9_]+", q_text.lower()))
            return words - stop_words

        unique_questions = []
        token_sets = []

        for i, q in enumerate(questions):
            tokens = get_tokens(q)
            is_dup = False
            for prev_tokens in token_sets:
                if not tokens or not prev_tokens:
                    continue
                intersection = len(tokens & prev_tokens)
                union = len(tokens | prev_tokens)
                if union > 0 and (intersection / union) > 0.60:
                    is_dup = True
                    break

            if is_dup:
                logger.info("Deduplication: Replacing near-duplicate question: '%s'", q)
                skill = focus_skills[i % len(focus_skills)] if focus_skills else setup.get("job_role", "Software Development")
                replacement = self._skill_fallback_question(skill, setup)
                if replacement in unique_questions:
                    replacement = f"How do you handle error boundaries, debugging, and edge cases in {skill} applications?"
                unique_questions.append(replacement)
                token_sets.append(get_tokens(replacement))
            else:
                unique_questions.append(q)
                token_sets.append(tokens)

        return unique_questions

    def _validate_difficulty(
        self,
        questions: List[str],
        difficulty: str,
        focus_skills: List[str],
        setup: Dict[str, Any]
    ) -> List[str]:
        """Adjust or replace questions that significantly mismatch requested difficulty."""
        import re
        diff_lower = (difficulty or "medium").lower()
        adjusted = []

        for i, q in enumerate(questions):
            q_lower = q.lower().strip()
            # If Hard difficulty, overly basic definition questions are too shallow
            if diff_lower == "hard":
                is_basic = bool(re.match(r"^(what is|define|what are the basics of)\s+[a-z0-9\.\s]+\??$", q_lower))
                if is_basic:
                    skill = focus_skills[i % len(focus_skills)] if focus_skills else setup.get("job_role", "Software")
                    replacement = (
                        f"In a high-scale production system, what are the architectural trade-offs, "
                        f"memory profiling techniques, or performance bottlenecks when working with {skill}?"
                    )
                    logger.info("Difficulty validation: Replacing overly basic question for Hard difficulty: '%s'", q)
                    adjusted.append(replacement)
                    continue

            adjusted.append(q)

        return adjusted

    def _validate_source_grounding(
        self,
        questions: List[str],
        retrieved_knowledge: Optional[List[Dict]],
        focus_skills: List[str]
    ) -> bool:
        """Soft check: log whether questions mention concepts/topics from retrieved knowledge."""
        if not retrieved_knowledge or not questions:
            return True
        known_concepts = set()
        for rec in retrieved_knowledge:
            for c in rec.get("concepts", []):
                known_concepts.add(c.lower())
            topic = rec.get("topic", "").lower()
            if topic:
                known_concepts.add(topic)
        grounded_count = 0
        for q in questions:
            q_lower = q.lower()
            if any(concept in q_lower for concept in known_concepts):
                grounded_count += 1
        logger.info("Source grounding validation: %d/%d questions grounded in curated topics.", grounded_count, len(questions))
        return grounded_count > 0

    def _validate_generated_question(
        self,
        question: str,
        focus_skills: List[str],
        questions_asked: List[str],
        difficulty: str = "Medium",
        resume_profile: Optional[Dict[str, Any]] = None,
        job_description: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Validates a generated question against skill focus, deduplication, technology grounding, and difficulty."""
        if not question or len(question.strip()) < 15:
            return False, "Question text is too short or empty."

        q_lower = question.lower().strip()

        # 1. Deduplication check against history
        if question in questions_asked or self.decision_engine.is_semantically_duplicate(question, questions_asked):
            return False, "Question is a duplicate of a previously asked question."

        # 2. Skill focus & grounding check
        skill_keywords = [s.lower() for s in focus_skills if s]

        # Collect allowed project technologies
        project_techs = []
        if resume_profile and isinstance(resume_profile, dict) and "projects" in resume_profile:
            for p in resume_profile.get("projects", []):
                for t in p.get("technologies", []):
                    project_techs.append(t.lower())

        allowed_techs = set(skill_keywords + project_techs)

        # Ensure question relates to at least one focus skill or valid project tech
        if focus_skills and not any(kw in q_lower for kw in allowed_techs):
            return False, f"Question does not mention or relate to selected skills: {focus_skills}"

        # 3. No Hallucinated Unmentioned Technologies
        unmentioned_tech_buzzwords = [
            "kubernetes", "docker", "kafka", "graphql", "aws", "terraform", "redox", "solidity", "swift"
        ]
        for buzz in unmentioned_tech_buzzwords:
            if buzz in q_lower and buzz not in allowed_techs and not (job_description and buzz in job_description.lower()):
                return False, f"Question hallucinates unmentioned technology '{buzz}'"

        # 4. Difficulty Alignment Check
        if difficulty.lower() == "hard":
            if re.match(r"^(what is|define|what are the basics of)\s+[a-z0-9\.\s]+\??$", q_lower):
                return False, "Question is too basic for Hard difficulty."

        return True, None

    def generate_question_metadata(
        self,
        question: str,
        skill: str,
        setup: Dict[str, Any],
        retrieved_knowledge: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Builds structured metadata for a generated question to establish evaluation contract."""
        evidence = self._build_question_evidence(question, retrieved_knowledge, setup.get("job_role"))
        return {
            "question": question,
            "skill": skill,
            "topic": evidence.get("question_type", "General"),
            "difficulty": setup.get("difficulty", "Medium"),
            "question_type": evidence.get("question_type", "conceptual"),
            "expected_concepts": evidence.get("expected_concepts", []),
            "contradiction_triggers": evidence.get("contradiction_triggers", []),
            "source_refs": evidence.get("source_refs", [])
        }

    def _generate_mock_questions(
        self,
        setup: Dict[str, Any],
        count: int,
        retrieved_knowledge: Optional[List[Dict]] = None
    ) -> List[str]:
        role = setup.get("job_role", "Software Developer")
        diff = setup.get("difficulty", "Medium")
        level = setup.get("experience_level", "Intermediate")
        itype = setup.get("interview_type", "Technical")
        resume_skills = setup.get("resume_skills", [])
        selected_skills = setup.get("selected_skills", [])
        language = setup.get("interview_language", "English")
        job_description = setup.get("job_description")
        resume_profile = setup.get("resume_profile", {})

        if isinstance(selected_skills, str):
            try: selected_skills = json.loads(selected_skills)
            except Exception: selected_skills = [selected_skills]
        if isinstance(resume_skills, str):
            try: resume_skills = json.loads(resume_skills)
            except Exception: resume_skills = [resume_skills]
        if isinstance(resume_profile, str):
            try: resume_profile = json.loads(resume_profile)
            except Exception: resume_profile = {}

        skills = selected_skills if selected_skills else (resume_skills if resume_skills else [role])

        # 1. Project-grounded templates
        project_templates = []
        projects = resume_profile.get("projects", []) if isinstance(resume_profile, dict) else []
        if projects:
            for p in projects:
                p_name = p.get("name", "your recent project")
                p_techs = [t for t in p.get("technologies", []) if any(s.lower() in t.lower() for s in skills)]
                skill_ref = p_techs[0] if p_techs else skills[0]
                project_templates.extend([
                    f"In your project '{p_name}', how did you utilize {skill_ref} to handle core data flow and component interactions?",
                    f"What architectural or performance challenges did you solve when integrating {skill_ref} in '{p_name}'?"
                ])

        # 2. Knowledge-grounded templates
        grounded_templates = []
        if retrieved_knowledge:
            for rec in retrieved_knowledge:
                s = rec.get("skill", skills[0])
                t = rec.get("topic", "core architecture")
                concepts = rec.get("concepts", [])
                concept_sample = concepts[0] if concepts else "core mechanics"
                gotchas = rec.get("common_mistakes", [])
                gotcha_sample = gotchas[0] if gotchas else "performance bottlenecks"

                if diff.lower() == "easy":
                    grounded_templates.append(f"What is the core purpose of {t} in {s} and how is {concept_sample} used?")
                elif diff.lower() == "hard":
                    grounded_templates.append(f"In a high-scale production system, what are the architectural trade-offs when optimizing {t} ({concept_sample}) in {s}?")
                else:
                    grounded_templates.append(f"How do you effectively implement {t} (specifically {concept_sample}) in {s} and avoid {gotcha_sample}?")

        # 3. JD-aware templates
        jd_templates = []
        if job_description:
            jd_lower = job_description.lower()
            if "rest" in jd_lower or "api" in jd_lower:
                jd_templates.append(f"Given the job requirements around REST APIs, how do you integrate {skills[0]} with backend services?")
            if "state" in jd_lower or "react" in jd_lower:
                jd_templates.append(f"The job description emphasizes state management. How do you structure state flow in {skills[0]}?")

        # 4. Rich Skill Question Templates (Varying Question Types)
        skill_templates = []
        for idx, skill in enumerate(skills):
            if diff.lower() == "easy":
                skill_templates.append(f"What is {skill} and what core problem does it solve in a {level} {role} application?")
                skill_templates.append(f"Explain the basic syntax and lifecycle flow when working with {skill}.")
            elif diff.lower() == "hard":
                skill_templates.append(f"What are the advanced concurrency, memory profiling, or architectural trade-offs when scaling {skill}?")
                skill_templates.append(f"How would you debug a subtle memory leak or race condition in a production {skill} application?")
            else: # Medium
                skill_templates.append(f"How do you approach structuring and modularizing code when developing with {skill}?")
                skill_templates.append(f"What is the difference between standard usage patterns and performance-optimized patterns in {skill}?")
                skill_templates.append(f"Describe a real-world scenario where you had to debug a difficult issue in {skill}.")

        # Combine template pools with precedence
        candidate_pool = project_templates + grounded_templates + jd_templates + skill_templates
        if not candidate_pool:
            candidate_pool = [f"Can you describe how you use {skills[0]} in your daily work as a {role}?"]

        questions = []
        for i in range(count):
            template = candidate_pool[i % len(candidate_pool)]
            q_text = self._format_question_language(template, language)
            questions.append(q_text)
        return questions

    # --------------------- Adaptive Question Generation ---------------------
    def generate_adaptive_next_question(
        self,
        setup: Dict[str, Any],
        questions_asked: List[str],
        evaluations: List[Dict[str, Any]],
        adaptive_state: Dict[str, Any],
        resume_profile: Optional[Dict[str, Any]] = None,
        retrieved_knowledge: Optional[List[Dict[str, Any]]] = None,
        decision: Optional[Any] = None,
    ) -> str:
        """Generate the next interview question adaptively based on candidate's previous answers,
        evaluation scores, detected weak/strong topics, project context, selected skill focus, and AdaptiveDecision.
        """
        if self.provider_name == "mock":
            return self._generate_mock_adaptive_question(
                setup=setup,
                questions_asked=questions_asked,
                evaluations=evaluations,
                adaptive_state=adaptive_state,
                resume_profile=resume_profile,
                retrieved_knowledge=retrieved_knowledge,
                decision=decision,
            )

        focus_skills = setup.get("selected_skills") or setup.get("resume_skills") or [setup.get("job_role", "Software")]
        current_diff = (decision.difficulty if decision else None) or adaptive_state.get("current_difficulty") or setup.get("difficulty", "Medium")
        language = setup.get("interview_language", "English")

        # Build prompt sections
        last_eval = evaluations[-1] if evaluations else {}
        last_score = last_eval.get("score", 5)
        last_relevance = last_eval.get("relevance", 1.0)
        last_weaknesses = last_eval.get("weaknesses", [])
        last_answer = last_eval.get("answer", "")

        strategy_directive = "Maintain steady interview progression across selected skills."
        if decision and getattr(decision, "context_directive", None):
            strategy_directive = decision.context_directive
        elif last_relevance < 0.4:
            strategy_directive = f"Candidate's previous answer was off-topic. Ask a clear, direct question focusing on the core concept of {focus_skills[0]} to evaluate their actual understanding."
        elif last_score <= 4:
            weak_hint = f" ({last_weaknesses[0]})" if last_weaknesses else ""
            strategy_directive = f"Candidate gave a weak/incomplete answer{weak_hint}. Generate a targeted follow-up probing the underlying concept or practical gotcha in {focus_skills[0]}."
        elif last_score >= 8:
            strategy_directive = f"Candidate demonstrated strong understanding. Escalate difficulty to {current_diff} with an advanced question on architectural trade-offs, scalability, or edge-case handling in {focus_skills[0]}."

        # Check project context
        project_context_str = ""
        if decision and getattr(decision, "project_ref", None):
            p = decision.project_ref
            techs_str = ", ".join(p.get("technologies", []))
            project_context_str = (
                f"CANDIDATE PROJECT:\n"
                f"Name: {p.get('name')}\n"
                f"Description: {p.get('description', '')}\n"
                f"Technologies: {techs_str}\n"
                f"DIRECTIVE: Ask a question directly connecting {decision.next_skill} to their project '{p.get('name')}'. "
                f"DO NOT invent technologies not listed above.\n"
            )
        else:
            projects = (resume_profile or {}).get("projects", [])
            if projects and adaptive_state.get("project_questions_asked", 0) == 0 and len(questions_asked) >= 1:
                matching = [p for p in projects if any(f.lower() in " ".join(p.get("technologies", [])).lower() or f.lower() in p.get("name", "").lower() for f in focus_skills)]
                if matching:
                    p = matching[0]
                    techs_str = ", ".join(p.get("technologies", []))
                    project_context_str = (
                        f"CANDIDATE PROJECT:\n"
                        f"Name: {p.get('name')}\n"
                        f"Description: {p.get('description', '')}\n"
                        f"Technologies: {techs_str}\n"
                        f"DIRECTIVE: Ask a question directly connecting {focus_skills[0]} to their project '{p.get('name')}'. "
                        f"DO NOT invent technologies not listed above.\n"
                    )

        knowledge_context_str = ""
        if retrieved_knowledge:
            topics_sample = [f"Skill: {r.get('skill')} | Topic: {r.get('topic')} | Concepts: {', '.join(r.get('concepts', []))}" for r in retrieved_knowledge[:5]]
            knowledge_context_str = "GROUNDING KNOWLEDGE:\n" + "\n".join(topics_sample) + "\n"

        target_skill_str = getattr(decision, "next_skill", None) or (', '.join(focus_skills))

        prompt = (
            f"You are an expert technical interviewer conducting an adaptive technical interview.\n"
            f"Generate the SINGLE NEXT INTERVIEW QUESTION for the candidate.\n\n"
            f"CONTEXT:\n"
            f"Job Role: {setup.get('job_role')}\n"
            f"Experience Level: {setup.get('experience_level')}\n"
            f"Difficulty: {current_diff}\n"
            f"Language: {language}\n"
            f"Selected Skills: {', '.join(focus_skills)}\n"
            f"Target Skill for this question: {target_skill_str}\n\n"
            f"PREVIOUS QUESTIONS ASKED:\n"
            + "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions_asked))
            + f"\n\nLAST CANDIDATE ANSWER:\n\"{last_answer}\"\n"
            f"Last Score: {last_score}/10 | Relevance: {last_relevance}\n\n"
            f"{project_context_str}"
            f"ADAPTIVE STRATEGY:\n{strategy_directive}\n\n"
            f"{knowledge_context_str}\n"
            f"STRICT RULES:\n"
            f"1. Generate EXACTLY ONE question as a JSON object: {{\"question\": \"...\"}}.\n"
            f"2. Stay strictly within SELECTED SKILLS ({', '.join(focus_skills)}).\n"
            f"3. Do NOT duplicate or repeat previous questions.\n"
            f"4. Do NOT invent unmentioned technologies for projects.\n"
            f"5. Match difficulty '{current_diff}'.\n"
        )

        try:
            parsed = self._call_llm_json(
                prompt,
                system="You are a professional adaptive technical interviewer. Return JSON only.",
            )
            q = parsed.get("question")
            if not isinstance(q, str) or not q.strip():
                raise AIProviderError("response JSON has no 'question' string")
            val, _ = self._validate_skill_focus([q], focus_skills)
            if not val:
                raise AIProviderError(f"generated question is not about the selected skills: {q[:120]}")
            return q
        except Exception as e:
            self._log_fallback("adaptive question generation", e)

        return self._generate_mock_adaptive_question(
            setup=setup,
            questions_asked=questions_asked,
            evaluations=evaluations,
            adaptive_state=adaptive_state,
            resume_profile=resume_profile,
            retrieved_knowledge=retrieved_knowledge,
        )

    def _generate_mock_adaptive_question(
        self,
        setup: Dict[str, Any],
        questions_asked: List[str],
        evaluations: List[Dict[str, Any]],
        adaptive_state: Dict[str, Any],
        resume_profile: Optional[Dict[str, Any]] = None,
        retrieved_knowledge: Optional[List[Dict[str, Any]]] = None,
        decision: Optional[Any] = None,
    ) -> str:
        """Deterministic mock generator for adaptive interview questions.
        Applies project deep-dive, weak-topic follow-up, difficulty escalation, and multi-skill rotation.
        """
        focus_skills = setup.get("selected_skills") or setup.get("resume_skills") or [setup.get("job_role", "Software")]
        diff = (decision.difficulty if decision else None) or adaptive_state.get("current_difficulty") or setup.get("difficulty", "Medium")
        level = setup.get("experience_level", "Intermediate")
        role = setup.get("job_role", "Software Developer")
        language = setup.get("interview_language", "English")

        target_skill = getattr(decision, "next_skill", None)
        if not target_skill or target_skill not in focus_skills:
            skill_counts = {s: sum(1 for q in questions_asked if s.lower() in q.lower()) for s in focus_skills}
            target_skill = min(skill_counts, key=skill_counts.get) if skill_counts else focus_skills[0]

        target_topic = getattr(decision, "next_topic", None) or f"{target_skill} Core Concepts"
        strategy = getattr(decision, "strategy", None)

        last_eval = evaluations[-1] if evaluations else {}
        last_score = last_eval.get("score", 5)
        last_relevance = last_eval.get("relevance", 1.0)
        last_weaknesses = last_eval.get("weaknesses", [])

        # 1. Relevance Clarification Strategy
        if strategy == "clarify_relevance" or last_relevance < 0.4:
            q_idx = len(questions_asked) + 1
            if q_idx % 2 == 0:
                q = f"To clarify and focus directly on {target_skill} ({target_topic}): could you explain how its foundational mechanics work and why it is essential?"
            else:
                q = f"To clarify and focus directly on {target_skill} ({target_topic}): can you explain its core definition and practical purpose in an application?"
            return self._format_question_language(q, language)

        # 2. Project Deep-Dive Strategy (via decision or fallback check)
        if strategy == "resume_project" and getattr(decision, "project_ref", None):
            p = decision.project_ref
            techs = [t for t in p.get("technologies", []) if any(f.lower() in t.lower() for f in focus_skills)]
            skill_ref = techs[0] if techs else target_skill
            adaptive_state["project_questions_asked"] = adaptive_state.get("project_questions_asked", 0) + 1
            q = f"In your project '{p.get('name')}', how did you utilize {skill_ref} and what architecture or performance challenges did you solve?"
            return self._format_question_language(q, language)

        projects = (resume_profile or {}).get("projects", [])
        if projects and adaptive_state.get("project_questions_asked", 0) == 0 and len(questions_asked) >= 1:
            matching = [p for p in projects if any(f.lower() in " ".join(p.get("technologies", [])).lower() or f.lower() in p.get("name", "").lower() for f in focus_skills)]
            if matching:
                p = matching[0]
                techs = [t for t in p.get("technologies", []) if any(f.lower() in t.lower() for f in focus_skills)]
                skill_ref = techs[0] if techs else target_skill
                adaptive_state["project_questions_asked"] = adaptive_state.get("project_questions_asked", 0) + 1
                q = f"In your project '{p.get('name')}', how did you utilize {skill_ref} and what architecture or performance challenges did you solve?"
                return self._format_question_language(q, language)

        # 3. Simplify Foundation Strategy (De-escalation / Weakness)
        if strategy == "simplify_foundation" or (last_score <= 4 and last_relevance >= 0.4):
            concept = getattr(decision, "target_concept", None) or "basic lifecycle and state flow"
            q = f"Let's step back to the foundations of {target_skill} ({target_topic}): could you explain how {concept} works in its simplest form?"
            return self._format_question_language(q, language)

        # 4. Probe Deeper Strategy (Partial understanding / Probing)
        if strategy == "probe_deeper" or (5.0 <= last_score < 8.0 and last_relevance >= 0.4):
            concept = getattr(decision, "target_concept", None) or "lifecycle hooks and dependency management"
            if retrieved_knowledge:
                for r in retrieved_knowledge:
                    if r.get("skill", "").lower() == target_skill.lower():
                        c_list = r.get("concepts", [])
                        if c_list:
                            concept = c_list[len(questions_asked) % len(c_list)]
                            break
            if target_skill.lower() == "react":
                q = f"Let's dive deeper into {target_skill} ({target_topic}): how does {concept} behave under complex component re-renders or updates?"
            else:
                q = f"Let's dive deeper into {target_skill} ({target_topic}): how does {concept} behave under complex runtime scenarios or edge cases?"
            return self._format_question_language(q, language)

        # 5. Escalate / Advanced Scenario Strategy
        if strategy == "escalate" or last_score >= 8:
            if diff == "Hard":
                q = f"Under high-concurrency production scenarios with {target_skill} ({target_topic}), what architectural patterns and optimization strategies would you use as a {level} {role}?"
            else:
                q = f"In {target_skill} ({target_topic}), how would you design a scalable pattern and handle edge cases or performance bottlenecks?"
            return self._format_question_language(q, language)

        # 6. Grounded Knowledge Record Strategy
        if retrieved_knowledge:
            for r in retrieved_knowledge:
                if r.get("skill", "").lower() == target_skill.lower():
                    topic = r.get("topic", "")
                    if not any(topic.lower() in prev.lower() for prev in questions_asked):
                        concepts = ", ".join(r.get("concepts", [])[:2])
                        q = f"In {target_skill}, explain how {topic} ({concepts}) is implemented and managed in production."
                        return self._format_question_language(q, language)

        # Fallback question
        q = f"Explain a challenging scenario you encountered while building systems with {target_skill}."
        return self._format_question_language(q, language)

    def _format_question_language(self, question: str, language: str) -> str:
        """Adapt question string for selected language while preserving technical terms."""
        if not language or language.lower() == "english":
            return question
        if language.lower() == "tamil":
            return f"{question} (Tamil translation preserving technical terms)"
        if language.lower() == "hindi":
            return f"{question} (Hindi translation preserving technical terms)"
        return question

    # --------------------- Answer Evaluation ---------------------
    def _build_question_evidence(
        self,
        question: str,
        retrieved_knowledge: Optional[List[Dict[str, Any]]] = None,
        job_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build question-specific expected concept evidence and trusted source references."""
        q_lower = question.lower()

        # Classify Question Type
        q_type = "conceptual"
        if any(kw in q_lower for kw in ["what is", "define", "what are the basics", "what does"]):
            q_type = "definition"
        elif any(kw in q_lower for kw in ["difference between", "vs", "compare", "distinguish"]):
            q_type = "comparison"
        elif any(kw in q_lower for kw in ["how to implement", "write code", "algorithm", "how would you code"]):
            q_type = "implementation"
        elif any(kw in q_lower for kw in ["how would you optimize", "high scale", "troubleshoot", "bottleneck"]):
            q_type = "scenario"
        elif any(kw in q_lower for kw in ["tell me about a time", "describe a situation", "project"]):
            q_type = "behavioral"

        expected_concepts = []
        source_refs = []

        if retrieved_knowledge:
            for rec in retrieved_knowledge:
                concepts = rec.get("concepts", [])
                if concepts:
                    expected_concepts.extend(concepts)
                src_name = rec.get("source_name")
                src_url = rec.get("source_url")
                if src_name:
                    source_refs.append({"name": src_name, "url": src_url or ""})

        # Pre-built Domain Knowledge Map for fine-grained evidence building
        domain_evidence_map = {
            "polymorphism": {
                "concepts": ["common interface", "different object types/classes", "method overriding", "duck typing", "dynamic dispatch"],
                "contradiction_triggers": ["guido van rossum", "created by python", "functions cannot be overridden", "static typing only"],
            },
            "primary key": {
                "concepts": ["unique identifier", "uniquely identifies rows", "cannot contain null", "one per table"],
                "contradiction_triggers": ["allow duplicate", "allows duplicate", "duplicate values", "can be null", "can contain null", "multiple primary keys"],
            },
            "thread": {
                "concepts": ["lightweight unit of execution", "shares process memory space", "concurrency", "thread context switching"],
                "contradiction_triggers": ["separate memory space", "isolated memory", "cannot run concurrently"],
            },
            "rest": {
                "concepts": ["representational state transfer", "stateless communication", "http methods (GET/POST/PUT/DELETE)", "resource endpoints"],
                "contradiction_triggers": ["stateful connection", "requires permanent socket"],
            },
            "index": {
                "concepts": ["b-tree data structure", "speeds up query data retrieval", "write overhead", "lookup optimization"],
                "contradiction_triggers": ["speeds up write operations", "deletes table rows"],
            }
        }

        matched_contradiction_triggers = []
        for topic_key, data in domain_evidence_map.items():
            if topic_key in q_lower:
                expected_concepts.extend(data["concepts"])
                matched_contradiction_triggers.extend(data["contradiction_triggers"])

        unique_concepts = list(dict.fromkeys(expected_concepts))

        return {
            "question_type": q_type,
            "expected_concepts": unique_concepts[:6],
            "contradiction_triggers": matched_contradiction_triggers,
            "source_refs": source_refs[:3]
        }

    def evaluate_answer(
        self,
        question: str,
        answer: str,
        history: Optional[List[Dict[str, Any]]] = None,
        experience_level: Optional[str] = None,
        job_role: Optional[str] = None,
        difficulty: Optional[str] = None,
        retrieved_knowledge: Optional[List[Dict[str, Any]]] = None,
    ) -> EvaluationDTO:
        """Evaluate a candidate's answer using evidence-based scoring, question-specific rubric, and relevance gating."""
        if self.provider_name == "mock":
            return self._mock_evaluation(
                question,
                answer,
                experience_level=experience_level,
                retrieved_knowledge=retrieved_knowledge
            )

        exp_ctx = f"\nCandidate Experience Level: {experience_level}" if experience_level else ""
        role_ctx = f"\nTarget Job Role: {job_role}" if job_role else ""
        diff_ctx = f"\nTarget Difficulty: {difficulty}" if difficulty else ""

        evidence = self._build_question_evidence(question, retrieved_knowledge, job_role)
        expected_concepts_str = ", ".join(evidence["expected_concepts"]) if evidence["expected_concepts"] else "Core domain concepts"
        contradictions_str = ", ".join(evidence["contradiction_triggers"]) if evidence["contradiction_triggers"] else "None specified"
        sources_str = ", ".join(s["name"] for s in evidence["source_refs"]) if evidence["source_refs"] else "Official Technical Documentation"

        prompt = (
            f"You are a rigorous technical interviewer evaluating a candidate's answer.{exp_ctx}{role_ctx}{diff_ctx}\n\n"
            f"QUESTION:\n\"{question}\"\n"
            f"Question Type: {evidence['question_type']}\n"
            f"Expected Answer Concepts: {expected_concepts_str}\n"
            f"Trusted Technical Sources: {sources_str}\n"
            f"Known Contradiction Triggers: {contradictions_str}\n\n"
            f"CANDIDATE ANSWER:\n\"{answer}\"\n\n"
            f"EVALUATION RULES:\n"
            f"1. HARD RELEVANCE GATE:\n"
            f"   - Evaluate if the answer directly addresses '{question}'.\n"
            f"   - If candidate answer discusses an unrelated topic (e.g. historical trivia like 'Guido van Rossum created Python' for a polymorphism question, or database facts for a network question), RELEVANCE MUST BE < 0.4!\n"
            f"   - IF RELEVANCE < 0.4, OVERALL SCORE MUST NOT EXCEED 2 OUT OF 10, REGARDLESS OF ANSWER LENGTH, GRAMMAR, OR TECHNICAL TERMS!\n"
            f"2. FACTUAL CORRECTNESS & CONTRADICTIONS:\n"
            f"   - Check candidate claims against trusted technical concepts ({expected_concepts_str}).\n"
            f"   - If the answer contains explicit factual contradictions (e.g. claiming primary keys allow duplicates), CORRECTNESS MUST BE <= 0.3 AND SCORE MUST BE <= 3!\n"
            f"3. LENGTH INDEPENDENCE:\n"
            f"   - A short answer that correctly states the core concept MUST receive a HIGH score (8-10).\n"
            f"   - A long answer that is off-topic or contains contradictions MUST receive a LOW score.\n"
            f"4. SPAM / NON-ANSWER:\n"
            f"   - Empty answer or keyboard spam ('asdfghjkl', 'python python python') MUST receive score 0 or 1.\n\n"
            f"Return response as a JSON object matching this schema:\n"
            f"{{\n"
            f"  \"score\": 8,\n"
            f"  \"correctness\": 0.9,\n"
            f"  \"relevance\": 0.95,\n"
            f"  \"technical_depth\": 0.8,\n"
            f"  \"communication_quality\": 0.9,\n"
            f"  \"strengths\": [\"Accurately states common interface and method overriding\"],\n"
            f"  \"weaknesses\": [],\n"
            f"  \"feedback\": \"Clear, concise, and technically accurate answer.\"\n"
            f"}}\n"
        )

        try:
            parsed = self._call_llm_json(
                prompt,
                system="You are a professional technical interviewer enforcing a strict relevance gate. Return JSON only.",
            )
            dto = EvaluationDTO(**parsed)
            # Code-enforced Hard Relevance Gate
            if dto.relevance < 0.4:
                dto.score = min(dto.score, 2)
            if dto.correctness <= 0.3:
                dto.score = min(dto.score, 3)
            return dto
        except Exception as e:
            self._log_fallback("answer evaluation", e)

        return self._mock_evaluation(
            question,
            answer,
            experience_level=experience_level,
            retrieved_knowledge=retrieved_knowledge
        )

    def _mock_evaluation(
        self,
        question: str,
        answer: str,
        experience_level: Optional[str] = None,
        retrieved_knowledge: Optional[List[Dict[str, Any]]] = None
    ) -> EvaluationDTO:
        clean_ans = answer.strip() if answer else ""
        if not clean_ans:
            return EvaluationDTO(
                score=0,
                correctness=0.0,
                relevance=0.0,
                technical_depth=0.0,
                communication_quality=0.0,
                strengths=[],
                weaknesses=["No answer provided"],
                feedback="No answer was provided for this question.",
            )

        q_lower = question.lower()
        a_lower = clean_ans.lower()
        words = a_lower.split()

        # Non-answers ("i don't know", "idk", "no idea", "yes", "no", "maybe")
        non_answers = ["i don't know", "idk", "no idea", "not sure", "don't know", "dont know", "no answer", "dunno"]
        if clean_ans.lower() in ["yes", "no", "maybe", "ok"] or any(na in a_lower for na in non_answers):
            return EvaluationDTO(
                score=1,
                correctness=0.1,
                relevance=0.1,
                technical_depth=0.0,
                communication_quality=0.3,
                strengths=[],
                weaknesses=["Candidate indicated no knowledge of the topic"],
                feedback="Candidate indicated they do not know the answer.",
            )

        # Keyword Spam / Incoherent / Repetitive Text / Keyboard Smash
        if any(smash in a_lower for smash in ["asdfghjkl", "qwertyuiop", "zxcvbnm"]) or (len(words) == 1 and len(clean_ans) > 6 and not clean_ans.isalpha()):
            return EvaluationDTO(
                score=0,
                correctness=0.0,
                relevance=0.0,
                technical_depth=0.0,
                communication_quality=0.1,
                strengths=[],
                weaknesses=["Incoherent keyboard input"],
                feedback="The response appears to be random keyboard text without a coherent explanation.",
            )

        stopwords = {"and", "the", "a", "an", "of", "to", "in", "is", "are", "but", "or", "with", "on", "for", "as", "by", "that", "this", "it", "your"}
        non_stop_words = [w.strip("?,.!") for w in words if w.strip("?,.!") not in stopwords]
        word_counts = {w: non_stop_words.count(w) for w in set(non_stop_words) if len(w) > 2}
        max_freq = max(word_counts.values()) if word_counts else 0
        if len(words) >= 5 and max_freq >= 4 and (len(set(non_stop_words)) <= 4 or (max_freq / len(words)) >= 0.20):
            return EvaluationDTO(
                score=2,
                correctness=0.2,
                relevance=0.3,
                technical_depth=0.2,
                communication_quality=0.2,
                strengths=[],
                weaknesses=["Repetitive keyword spam without sentence structure"],
                feedback="The answer repeats technical terms without providing a coherent explanation or proper sentence structure.",
            )

        # Topic domain dictionary for accurate mock evaluation
        topic_keywords = {
            "polymorphism": ["polymorphism", "polymorphic", "interface", "overriding", "method", "subclass", "duck typing", "same name", "different implementation", "common interface", "different object"],
            "primary key": ["primary key", "unique", "uniquely", "row", "identifier", "table", "key"],
            "index": ["index", "indexing", "b-tree", "lookup", "speed", "search", "table", "performance", "query", "database"],
            "thread": ["thread", "threads", "process", "processes", "memory", "lightweight", "concurrency", "overhead", "execution", "shared"],
            "rate limit": ["rate limit", "limiter", "token bucket", "leaky bucket", "redis", "throttle", "requests", "api"],
            "rest": ["rest", "api", "http", "endpoint", "get", "post", "put", "delete", "stateless", "resource"],
            "lifecycle": ["lifecycle", "request", "response", "middleware", "routing", "controller", "handler"],
            "cache": ["cache", "caching", "redis", "memcached", "ttl", "invalidation", "hit", "miss"],
            "microservice": ["microservice", "microservices", "monolith", "decoupled", "service", "architecture"],
            "security": ["security", "auth", "jwt", "oauth", "encryption", "hash", "token", "vulnerability"],
            "sql": ["sql", "nosql", "relational", "schema", "table", "document", "query", "join"],
            "clean code": ["clean", "test", "testable", "refactor", "solid", "modular", "readable"],
            "memory": ["memory", "leak", "garbage collection", "heap", "profiler", "allocation"],
        }

        # Identify question topic domain
        matched_domain_terms = set()
        for topic, terms in topic_keywords.items():
            if topic in q_lower or any(t in q_lower for t in terms[:2]):
                matched_domain_terms.update(terms)

        # Fallback: extract non-stopwords from question if no preset topic matches
        if not matched_domain_terms:
            q_stopwords = {"what", "is", "are", "the", "a", "an", "in", "for", "to", "of", "and", "or", "how", "do", "you", "explain", "describe", "your", "with"}
            q_words = [w.strip("?,.!") for w in q_lower.split() if w.strip("?,.!") not in q_stopwords and len(w.strip("?,.!")) > 3]
            matched_domain_terms = set(q_words)

        # Count matching concept terms in answer
        found_terms = [t for t in matched_domain_terms if t in a_lower]
        has_domain_relevance = len(found_terms) > 0

        # Check explicit factual contradictions
        contradictions = []
        if "primary key" in q_lower:
            if "duplicate" in a_lower:
                if any(kw in a_lower for kw in ["allow", "allowed", "allows", "possible", "duplicate values", "duplicate primary"]):
                    if not any(neg in a_lower for neg in ["cannot", "can't", "no duplicate", "never duplicate", "without duplicate"]):
                        contradictions.append("Claiming primary key allows duplicate values")
            if "null" in a_lower:
                if any(kw in a_lower for kw in ["allow", "allowed", "allows", "can have", "have null", "multiple times"]):
                    if not any(neg in a_lower for neg in ["cannot", "can't", "not null", "no null", "never null"]):
                        contradictions.append("Claiming primary key can contain null values")
        elif "polymorphism" in q_lower:
            if "function cannot be overridden" in a_lower or "cannot be overridden" in a_lower:
                contradictions.append("Claiming functions cannot be overridden in polymorphism")

        if contradictions:
            return EvaluationDTO(
                score=2,
                correctness=0.2,
                relevance=0.85,
                technical_depth=0.2,
                communication_quality=0.6,
                strengths=["Addressed the target topic"],
                weaknesses=[f"Factually incorrect statement: {contradictions[0]}"],
                feedback=f"The answer contains a factually incorrect statement: {contradictions[0]}.",
            )

        # Candidate uncertainty / partial memory
        uncertainty_phrases = ["don't remember", "dont remember", "not sure", "forget", "cannot remember", "can't remember", "don't recall"]
        if any(up in a_lower for up in uncertainty_phrases):
            return EvaluationDTO(
                score=5,
                correctness=0.6,
                relevance=0.8,
                technical_depth=0.5,
                communication_quality=0.7,
                strengths=["Identified main purpose of topic"],
                weaknesses=["Candidate expressed uncertainty on key concept details"],
                feedback="The candidate answered part of the question accurately but acknowledged uncertainty on secondary concepts.",
            )

        # Factually True but Completely Irrelevant Answer (e.g. Guido van Rossum facts for polymorphism or DB index)
        guido_facts = ["guido", "van rossum", "dynamically typed", "created by", "creator of python", "programming language created"]
        is_guido_fact = any(g in a_lower for g in guido_facts)

        if not has_domain_relevance:
            if is_guido_fact or "python" in a_lower:
                return EvaluationDTO(
                    score=1,
                    correctness=0.8,
                    relevance=0.1,
                    technical_depth=0.1,
                    communication_quality=0.6,
                    strengths=["Factually true statement about Python"],
                    weaknesses=["Fails to address the specific question topic"],
                    feedback="The answer is factually correct about Python, but it does not address the question asked.",
                )
            else:
                return EvaluationDTO(
                    score=0,
                    correctness=0.1,
                    relevance=0.0,
                    technical_depth=0.0,
                    communication_quality=0.3,
                    strengths=[],
                    weaknesses=["Completely off-topic"],
                    feedback="The answer is completely unrelated to the question.",
                )

        # Short but technically accurate answer reward (e.g. "Polymorphism allows the same interface to work with different object types.")
        if "polymorphism" in q_lower and ("interface" in a_lower or "different object" in a_lower or "different class" in a_lower):
            return EvaluationDTO(
                score=9,
                correctness=0.95,
                relevance=0.95,
                technical_depth=0.8,
                communication_quality=0.9,
                strengths=["Accurately states common interface and object type dynamic behavior"],
                weaknesses=[],
                feedback="Clear, concise, and technically accurate definition of polymorphism.",
            )

        if "primary key" in q_lower and ("unique" in a_lower or "uniquely" in a_lower or "identifies" in a_lower):
            return EvaluationDTO(
                score=9,
                correctness=0.95,
                relevance=0.95,
                technical_depth=0.8,
                communication_quality=0.9,
                strengths=["Accurately identifies row uniqueness property"],
                weaknesses=[],
                feedback="Clear and accurate explanation of primary key functionality.",
            )

        # Partially Relevant / Incomplete Answer (e.g. Threads are lightweight and share memory)
        if len(found_terms) <= 2 or len(words) < 15:
            if experience_level == "Beginner":
                score = 7
                depth = 0.6
                fb = "Good basic answer addressing the core concept for a beginner."
            else:
                score = 5
                depth = 0.4
                fb = "Relevant response, but incomplete. Provide more technical detail and trade-offs."

            return EvaluationDTO(
                score=score,
                correctness=0.8,
                relevance=0.85,
                technical_depth=depth,
                communication_quality=0.7,
                strengths=[f"Mentions core concepts ({', '.join(found_terms[:2])})"],
                weaknesses=["Incomplete technical coverage", "Needs deeper explanation"],
                feedback=fb,
            )

        # Fully Relevant & Detailed Answer
        if experience_level == "Advanced":
            has_advanced_terms = any(t in a_lower for t in ["trade-off", "overhead", "bottleneck", "edge case", "scale", "performance", "optimization", "lock", "synchronization", "race condition"])
            if has_advanced_terms or len(words) >= 30:
                score = 9
                depth = 0.9
                fb = "Excellent, thorough response with strong technical depth and design reasoning."
            else:
                score = 7
                depth = 0.6
                fb = "Good explanation, but advanced roles expect explicit discussion of trade-offs and edge cases."
        else:
            score = 9
            depth = 0.85
            fb = "Clear, comprehensive, and well-structured answer addressing all aspects of the question."

        return EvaluationDTO(
            score=score,
            correctness=0.9,
            relevance=0.95,
            technical_depth=depth,
            communication_quality=0.9,
            strengths=["Comprehensive explanation", "Accurate technical terminology"],
            weaknesses=[],
            feedback=fb,
        )

    # --------------------- AI Coaching RAG ---------------------
    def generate_coaching(self, context: Dict[str, Any]) -> AICoachResponse:
        """Generate personalized AI interview coaching based on retrievable candidate history context."""
        if self.provider_name == "mock":
            return self._mock_coaching(context)

        prompt = (
            f"You are a personalized AI Interview Coach analyzing a candidate's actual interview history.\n"
            f"Ground all advice strictly in the provided candidate context data below.\n\n"
            f"Candidate Context:\n"
            f"{json.dumps(context, indent=2)}\n\n"
            f"Instructions:\n"
            f"1. Provide a concise summary of the candidate's progress and history.\n"
            f"2. Identify key strengths based on high-scoring sessions and feedback.\n"
            f"3. Identify primary weak areas needing improvement.\n"
            f"4. Recommend 2 to 4 specific topics or action items to practice next.\n"
            f"5. Specify a single clear 'next_action' recommendation.\n"
            f"6. Return JSON only matching this exact schema:\n"
            f"{{\n"
            f"  \"summary\": \"Based on your recent interviews...\",\n"
            f"  \"strengths\": [\"Strength 1\", \"Strength 2\"],\n"
            f"  \"weak_areas\": [\"Weak area 1\", \"Weak area 2\"],\n"
            f"  \"recommended_topics\": [\"Practice REST API design\", \"Review database indexing\"],\n"
            f"  \"next_action\": \"Complete one medium System Design interview\",\n"
            f"  \"has_enough_data\": true\n"
            f"}}\n"
        )

        try:
            parsed = self._call_llm_json(
                prompt,
                system="You are an expert AI interview coach. Ground recommendations strictly in user data. Return JSON only.",
                timeout=20,
            )
            return AICoachResponse(**parsed)
        except Exception as e:
            self._log_fallback("coaching generation", e)

        return self._mock_coaching(context)

    def _mock_coaching(self, context: Dict[str, Any]) -> AICoachResponse:
        weaknesses = context.get("aggregated_weaknesses", [])
        strengths = context.get("aggregated_strengths", [])
        weakest_role = context.get("weakest_role", "Technical")
        weakest_type = context.get("weakest_type", "System Design")
        avg_score = context.get("average_score", 0.0)

        weak_area_str = ", ".join(weaknesses[:2]) if weaknesses else f"{weakest_type} and {weakest_role}"
        recs = [
            f"Practice core concepts in {weakest_role}",
            "Review system architecture fundamentals",
            "Focus on detailed code examples and edge case handling"
        ]
        if weaknesses:
            recs = [f"Improve on: {w}" for w in weaknesses[:3]]

        return AICoachResponse(
            summary=f"Based on your {context.get('completed_interviews', 0)} completed interviews (Average Score: {avg_score}/10), focus on bolstering your depth in {weak_area_str}.",
            strengths=strengths if strengths else ["Good baseline communication", "Structured approach"],
            weak_areas=weaknesses if weaknesses else [f"{weakest_type} depth", f"{weakest_role} advanced scenarios"],
            recommended_topics=recs,
            next_action=f"Practice a {weakest_type} interview for {weakest_role}.",
            has_enough_data=True,
        )

    def generate_coach_chat(
        self, context: Dict[str, Any], user_message: str, chat_history: List[Dict[str, str]]
    ) -> str:
        """Generate conversational coaching response strictly grounded in candidate data."""
        if self.provider_name == "mock":
            weak_topics = context.get("weak_topics", [])
            user_name = context.get("user_name", "Candidate")
            weak_str = weak_topics[0]["topic"] if weak_topics else "core software engineering fundamentals"
            return (
                f"Hello {user_name}! In your past interviews, your primary focus area has been {weak_str}. "
                f"Grounding advice in your actual interview scores: {context.get('trend', '')} "
                f"Feel free to ask for a practice question or targeted feedback on any specific topic."
            )

        prompt = (
            f"You are a personalized AI Interview Coach conversing with candidate {context.get('user_name')}.\n"
            f"Ground your advice strictly in the candidate's real interview metrics and history below.\n"
            f"Do not invent or hallucinate facts not in this context.\n\n"
            f"Candidate Context:\n{json.dumps(context, indent=2)}\n\n"
            f"User message: {user_message}\n"
            f"Instructions: Answer concisely, encouragingly, and actionably. Ground claims in their scores."
        )

        # The frontend sends the current message as the last history entry; the prompt already
        # contains it, so drop that entry to avoid sending it twice.
        prior_turns = list(chat_history or [])
        if (
            prior_turns
            and isinstance(prior_turns[-1], dict)
            and prior_turns[-1].get("role") == "user"
            and (prior_turns[-1].get("content") or "").strip() == user_message.strip()
        ):
            prior_turns = prior_turns[:-1]

        try:
            return self._call_llm(
                prompt,
                system="You are an expert AI interview coach grounded strictly in candidate metrics.",
                json_mode=False,
                history=prior_turns,
                timeout=20,
            )
        except Exception as e:
            self._log_fallback("coach chat", e)

        weak_topics = context.get("weak_topics", [])
        weak_str = weak_topics[0]["topic"] if weak_topics else "technical concepts"
        return f"Based on your recent scores, focusing on {weak_str} will deliver the highest improvement in your interviews."




@lru_cache(maxsize=1)
def ai_status() -> Dict[str, Any]:
    """Non-secret summary of the active LLM configuration (for /health). Cached: settings are
    read once at startup, so this also avoids re-logging config warnings on every health check."""
    provider = AIProvider()
    return {
        "provider": provider.provider_name,
        "model": provider.model,
        "api_key_configured": bool(provider.api_key) if provider.is_real_llm else None,
    }
