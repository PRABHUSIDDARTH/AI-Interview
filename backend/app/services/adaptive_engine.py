import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field

logger = logging.getLogger("uvicorn.error")

# Fine-grained topic taxonomy with keywords for evidence-based detection
_TOPIC_KEYWORDS = {
    "React Hooks": ["hook", "useeffect", "usestate", "usememo", "usecallback", "useref", "usecontext", "custom hook", "dependency array", "stale closure"],
    "React Components": ["component", "jsx", "functional component", "composition", "props", "children", "render", "lifecycle"],
    "React State Management": ["redux", "context api", "zustand", "recoil", "action", "reducer", "state flow", "dispatch", "immutability"],
    "React Performance": ["usememo", "usecallback", "react.memo", "virtual dom", "re-render", "profiler", "lazy", "suspense", "code splitting"],
    "Spring Security": ["spring security", "securityfilterchain", "authentication", "userdetailsservice", "bcrypt", "csrf", "cors", "jwt", "authorization"],
    "Spring Dependency Injection": ["autowired", "ioc", "inversion of control", "bean", "applicationcontext", "dependency injection", "qualifier"],
    "Spring Data JPA": ["jpa", "hibernate", "transactional", "repository", "query", "orm", "entity", "cascade"],
    "Database Indexing": ["b-tree", "index", "btree", "indexing", "query optimization", "explain plan", "composite index"],
    "SQL Fundamentals": ["join", "group by", "foreign key", "primary key", "normalization", "acid", "transaction"],
    "REST API Design": ["rest", "http method", "status code", "idempotent", "rate limit", "endpoint", "crud", "payload"],
    "Docker & Containers": ["docker", "container", "dockerfile", "compose", "image", "volume", "port forwarding"],
    "Python Fundamentals": ["decorator", "generator", "gil", "list comprehension", "dunder", "magic method", "oop", "polymorphism", "inheritance"],
    "FastAPI & Async": ["fastapi", "async def", "await", "pydantic", "starlette", "uvicorn", "asyncio", "coroutine"],
    "Node.js & Express": ["express", "middleware", "event loop", "non-blocking", "cluster", "stream", "buffer", "npm"],
    "JavaScript ES6+": ["closure", "promise", "async/await", "prototype", "event loop", "hoisting", "arrow function", "destructuring"],
    "System Design": ["system design", "distributed", "load balancer", "cache", "sharding", "microservices", "concurrency", "rate limiter"],
}

_STOP_WORDS = {
    "what", "is", "the", "a", "an", "and", "or", "in", "on", "at", "to", "for",
    "with", "by", "of", "from", "how", "do", "does", "did", "can", "could", "would",
    "should", "you", "your", "we", "explain", "describe", "discuss", "tell", "me",
    "about", "difference", "between", "when", "why", "which", "use", "using", "work"
}


@dataclass
class AdaptiveDecision:
    next_skill: str
    next_topic: str
    difficulty: str
    question_type: str  # conceptual, practical, scenario, debugging, problem_solving, architecture, resume_project
    strategy: str       # clarify_relevance, simplify_foundation, probe_deeper, escalate, resume_project, explore_untested
    context_directive: str
    target_concept: Optional[str] = None
    is_follow_up: bool = False
    project_ref: Optional[Dict[str, Any]] = None


class AdaptiveDecisionEngine:
    """Core decision engine for the adaptive interview loop.
    Decoupled from database models and responsible for:
    - Topic classification and tracking
    - Evidence-based difficulty escalation/de-escalation
    - Off-topic relevance gating and concept clarification
    - Contextual follow-up generation
    - Resume project deep-dives without hallucination
    - Semantic deduplication
    """

    DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard"]

    def classify_question_topic(
        self,
        question: str,
        answer: str = "",
        candidate_skills: Optional[List[str]] = None,
        weaknesses: Optional[List[str]] = None,
        job_role: str = "Software Developer"
    ) -> Tuple[str, str]:
        """Identifies fine-grained topic and parent skill from question, answer, and evaluation context."""
        text = f"{question} {answer} {' '.join(weaknesses or [])}".lower()
        skills = candidate_skills or []

        # 1. Match topics matching candidate's explicit skills first
        cand_skills_lower = [s.lower() for s in skills if s]
        if cand_skills_lower:
            best_cand_topic = None
            best_cand_score = 0
            for topic, keywords in _TOPIC_KEYWORDS.items():
                parent_skill = topic.split()[0]
                if any(cs in parent_skill.lower() or parent_skill.lower() in cs for cs in cand_skills_lower):
                    matches = sum(1 for kw in keywords if kw in text)
                    if matches > best_cand_score:
                        best_cand_score = matches
                        best_cand_topic = topic
            if best_cand_topic and best_cand_score >= 1:
                ps = best_cand_topic.split()[0]
                for s in skills:
                    if s.lower() == ps.lower():
                        ps = s
                        break
                return best_cand_topic, ps

        # 2. Match general explicit topic keywords
        best_topic = None
        best_score = 0
        for topic, keywords in _TOPIC_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text)
            if matches > best_score:
                best_score = matches
                best_topic = topic

        if best_topic and best_score >= 1:
            parent_skill = best_topic.split()[0]
            if parent_skill in ["Docker", "REST", "Database", "System", "SQL"]:
                matched_cand = [s for s in skills if s.lower() in best_topic.lower()]
                parent_skill = matched_cand[0] if matched_cand else "Technical"
            return best_topic, parent_skill

        # 2. Match against candidate's selected skills
        for s in skills:
            if s.lower() in text:
                return f"{s} Fundamentals", s

        # 3. Fallback to first selected skill or general role
        primary_skill = skills[0] if skills else "Technical"
        return f"{primary_skill} Core Concepts", primary_skill

    def initialize_state(
        self,
        initial_difficulty: str = "Medium",
        selected_skills: Optional[List[str]] = None,
        resume_skills: Optional[List[str]] = None,
        available_topics: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Initializes state structure for a new adaptive interview session."""
        skills = selected_skills or resume_skills or []
        untested = []
        if available_topics:
            for t in available_topics:
                t_name = t.get("topic")
                if t_name and t_name not in untested:
                    untested.append(t_name)

        return {
            "current_difficulty": initial_difficulty,
            "selected_skills": skills,
            "topics_covered": [],
            "topic_scores": {},        # topic -> list of scores [8.5, 9.0]
            "weak_topics": [],          # topics confirmed weak through evidence
            "strong_topics": [],        # topics confirmed strong through evidence
            "untested_topics": untested,
            "questions_asked": [],      # chronological question texts
            "question_records": [],    # structured metadata for each question
            "project_questions_asked": 0,
            "conversation_history": [],
        }

    def update_adaptive_state(
        self,
        state: Dict[str, Any],
        question: str,
        answer: str,
        evaluation: Dict[str, Any],
        detected_topic: str,
        detected_skill: str,
    ) -> Dict[str, Any]:
        """Updates topic score history, evaluates weak/strong topics, adjusts difficulty, and tracks history."""
        score = float(evaluation.get("score", 0.0))
        relevance = float(evaluation.get("relevance", 1.0))
        weaknesses = evaluation.get("weaknesses", [])
        strengths = evaluation.get("strengths", [])

        # Record question in history
        if question not in state.setdefault("questions_asked", []):
            state["questions_asked"].append(question)

        # Track fine-grained topic scores
        topic_scores = state.setdefault("topic_scores", {})
        if detected_topic not in topic_scores:
            topic_scores[detected_topic] = []
        topic_scores[detected_topic].append(score)

        topics_covered = state.setdefault("topics_covered", [])
        if detected_topic not in topics_covered:
            topics_covered.append(detected_topic)

        untested = state.setdefault("untested_topics", [])
        if detected_topic in untested:
            untested.remove(detected_topic)

        # Evidence-based weak/strong topic classification
        all_topic_evals = topic_scores[detected_topic]
        avg_topic_score = sum(all_topic_evals) / len(all_topic_evals)
        weak_topics = state.setdefault("weak_topics", [])
        strong_topics = state.setdefault("strong_topics", [])

        # RULE: Weak Topic Detection
        # Repeated poor performance (>= 2 evals with avg < 6.5) OR single severe failure (score <= 4.0 with explicit weakness)
        is_weak = (len(all_topic_evals) >= 2 and avg_topic_score < 6.5) or (score <= 4.0 and len(weaknesses) >= 1)
        if is_weak:
            if detected_topic not in weak_topics:
                weak_topics.append(detected_topic)
            if detected_topic in strong_topics:
                strong_topics.remove(detected_topic)

        # RULE: Strong Topic Detection
        # Consistent strong answers (avg >= 7.5 and count >= 1)
        is_strong = avg_topic_score >= 7.5 and score >= 7.5
        if is_strong:
            if detected_topic not in strong_topics:
                strong_topics.append(detected_topic)
            if detected_topic in weak_topics:
                weak_topics.remove(detected_topic)

        # RULE: Difficulty Adjustment
        curr_diff = state.get("current_difficulty", "Medium")
        diff_idx = self.DIFFICULTY_LEVELS.index(curr_diff) if curr_diff in self.DIFFICULTY_LEVELS else 1

        if relevance < 0.4:
            # Low relevance rule: Do NOT increase difficulty
            pass
        elif score >= 8.0 and relevance >= 0.6:
            # Strong performance: Escalate difficulty
            if diff_idx < len(self.DIFFICULTY_LEVELS) - 1:
                curr_diff = self.DIFFICULTY_LEVELS[diff_idx + 1]
        elif score <= 4.0:
            # Weak performance: De-escalate difficulty
            if diff_idx > 0:
                curr_diff = self.DIFFICULTY_LEVELS[diff_idx - 1]

        state["current_difficulty"] = curr_diff

        # Record structured question metadata
        state.setdefault("question_records", []).append({
            "question": question,
            "skill": detected_skill,
            "topic": detected_topic,
            "difficulty": curr_diff,
            "score": score,
            "relevance": relevance,
            "strengths": strengths,
            "weaknesses": weaknesses,
        })

        return state

    def determine_next_question(
        self,
        interview_state: Dict[str, Any],
        latest_evaluation: Optional[Dict[str, Any]],
        resume_context: Dict[str, Any],
        selected_skills: List[str],
        available_topics: Optional[List[Dict[str, Any]]] = None,
    ) -> AdaptiveDecision:
        """Determines next topic, difficulty, question type, and instructional directive
        based on performance history and selected skill boundaries.
        """
        curr_diff = interview_state.get("current_difficulty", "Medium")
        questions_asked = interview_state.get("questions_asked", [])
        q_count = len(questions_asked)
        weak_topics = interview_state.get("weak_topics", [])
        strong_topics = interview_state.get("strong_topics", [])
        untested_topics = interview_state.get("untested_topics", [])

        # Target skill selection respecting selected skills boundary
        focus_skills = selected_skills or ["Technical"]
        # Intelligent balancing across multiple selected skills
        skill_counts = {s: 0 for s in focus_skills}
        for rec in interview_state.get("question_records", []):
            sk = rec.get("skill")
            if sk in skill_counts:
                skill_counts[sk] += 1
        target_skill = min(skill_counts, key=skill_counts.get) if skill_counts else focus_skills[0]

        # Case 0: First question (baseline)
        if not latest_evaluation:
            first_topic = available_topics[0].get("topic", f"{target_skill} Fundamentals") if available_topics else f"{target_skill} Fundamentals"
            return AdaptiveDecision(
                next_skill=target_skill,
                next_topic=first_topic,
                difficulty=curr_diff,
                question_type="conceptual",
                strategy="baseline",
                context_directive=f"Start with a clear, foundational interview question assessing core concepts in {target_skill} ({first_topic}).",
                target_concept=None,
                is_follow_up=False,
            )

        last_score = float(latest_evaluation.get("score", 5.0))
        last_relevance = float(latest_evaluation.get("relevance", 1.0))
        last_question = latest_evaluation.get("question", "")
        last_weaknesses = latest_evaluation.get("weaknesses", [])
        last_topic, _ = self.classify_question_topic(last_question, candidate_skills=focus_skills, weaknesses=last_weaknesses)

        # -------------------------------------------------------------------
        # Rule 1: Relevance < 0.4 (Off-topic Answer)
        # -------------------------------------------------------------------
        if last_relevance < 0.4:
            return AdaptiveDecision(
                next_skill=target_skill,
                next_topic=last_topic,
                difficulty=curr_diff,
                question_type="clarification",
                strategy="clarify_relevance",
                context_directive=(
                    f"Candidate's previous response was off-topic (relevance {last_relevance:.2f}). "
                    f"Do NOT increase difficulty. Ask a direct clarification question re-testing the core intended concept of {last_topic}."
                ),
                target_concept=last_topic,
                is_follow_up=True,
            )

        # -------------------------------------------------------------------
        # Rule 2: Score <= 4.0 (Struggling / Weak Answer)
        # -------------------------------------------------------------------
        if last_score <= 4.0:
            # Simplify and reinforce basics of that same topic
            concept_hint = last_weaknesses[0] if last_weaknesses else "core mechanics and syntax"
            return AdaptiveDecision(
                next_skill=target_skill,
                next_topic=last_topic,
                difficulty=curr_diff,
                question_type="foundational",
                strategy="simplify_foundation",
                context_directive=(
                    f"Candidate struggled on {last_topic} (score {last_score}/10). "
                    f"Ask a simpler, foundational reinforcement question breaking down {concept_hint}. "
                    f"Do not jump to unrelated advanced topics."
                ),
                target_concept=concept_hint,
                is_follow_up=True,
            )

        # -------------------------------------------------------------------
        # Rule 3: Resume Project Inquiries (Section 9)
        # -------------------------------------------------------------------
        projects = (resume_context or {}).get("projects", [])
        project_count = interview_state.get("project_questions_asked", 0)
        if projects and project_count == 0 and q_count in [1, 2]:
            matching_projects = [
                p for p in projects
                if any(f.lower() in " ".join(p.get("technologies", [])).lower() or f.lower() in p.get("name", "").lower() for f in focus_skills)
            ]
            if matching_projects:
                proj = matching_projects[0]
                techs = [t for t in proj.get("technologies", []) if any(f.lower() in t.lower() for f in focus_skills)]
                skill_ref = techs[0] if techs else target_skill
                interview_state["project_questions_asked"] = project_count + 1
                return AdaptiveDecision(
                    next_skill=skill_ref,
                    next_topic=f"{skill_ref} Project Integration",
                    difficulty=curr_diff,
                    question_type="resume_project",
                    strategy="resume_project",
                    context_directive=(
                        f"Candidate listed project '{proj.get('name')}' using {skill_ref}. "
                        f"Ask how they managed architecture or challenges in '{proj.get('name')}'. "
                        f"DO NOT invent technologies not listed in: {', '.join(proj.get('technologies', []))}."
                    ),
                    target_concept=f"Project {proj.get('name')}",
                    is_follow_up=False,
                    project_ref=proj,
                )

        # -------------------------------------------------------------------
        # Rule 4: Score between 5.0 and 7.9 (Partial Understanding)
        # -------------------------------------------------------------------
        if 5.0 <= last_score < 8.0:
            return AdaptiveDecision(
                next_skill=target_skill,
                next_topic=last_topic,
                difficulty=curr_diff,
                question_type="practical",
                strategy="probe_deeper",
                context_directive=(
                    f"Candidate has partial understanding of {last_topic} (score {last_score}/10). "
                    f"Ask a deeper follow-up probing practical implementation, error handling, or lifecycle behavior around this concept."
                ),
                target_concept=last_topic,
                is_follow_up=True,
            )

        # -------------------------------------------------------------------
        # Rule 5: Score >= 8.0 (Strong Understanding)
        # -------------------------------------------------------------------
        # Check if candidate has weak topics waiting for re-testing
        if weak_topics:
            target_weak = weak_topics[0]
            return AdaptiveDecision(
                next_skill=target_skill,
                next_topic=target_weak,
                difficulty=curr_diff,
                question_type="debugging",
                strategy="probe_deeper",
                context_directive=(
                    f"Candidate previously struggled with {target_weak}. "
                    f"Present a targeted scenario or debugging problem to test if their understanding has solidified."
                ),
                target_concept=target_weak,
                is_follow_up=False,
            )

        # Advance to deeper practical, scenario, architecture, or untested topic
        next_topic = last_topic
        if untested_topics:
            # Prioritize untested topic for breadth
            next_topic = untested_topics[0]

        return AdaptiveDecision(
            next_skill=target_skill,
            next_topic=next_topic,
            difficulty=curr_diff,
            question_type="scenario",
            strategy="escalate",
            context_directive=(
                f"Candidate demonstrated mastery in fundamentals (score {last_score}/10). "
                f"Escalate difficulty to {curr_diff} with an advanced architecture, performance optimization, or real-world scenario in {next_topic}."
            ),
            target_concept=next_topic,
            is_follow_up=False,
        )

    def is_semantically_duplicate(self, candidate_question: str, questions_asked: List[str], threshold: float = 0.60) -> bool:
        """Determines if a candidate question is a near-duplicate of any previously asked question."""
        if not candidate_question or not questions_asked:
            return False

        def get_tokens(text: str) -> Set[str]:
            words = set(re.findall(r"[a-z0-9_]+", text.lower()))
            return words - _STOP_WORDS

        cand_tokens = get_tokens(candidate_question)
        if not cand_tokens:
            return False

        for prev in questions_asked:
            prev_tokens = get_tokens(prev)
            if not prev_tokens:
                continue
            intersection = len(cand_tokens & prev_tokens)
            union = len(cand_tokens | prev_tokens)
            if union > 0 and (intersection / union) >= threshold:
                return True

        return False
