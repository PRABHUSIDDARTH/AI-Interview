import json
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.interview_session import InterviewSession
from app.schemas.coaching import (
    AICoachResponse,
    CoachSummaryResponse,
    TopicMetricDTO,
    SkillMetricDTO,
    ImprovementTrendDTO,
    RecommendedInterviewDTO,
    PracticeQuestionResponse,
    CoachChatResponse,
)
from app.services.ai import AIProvider
from app.services.knowledge.retriever import LocalKnowledgeRetriever

logger = logging.getLogger("uvicorn.error")

# Fine-grained topic taxonomy with keywords aligned with AdaptiveDecisionEngine
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


class UserInterviewHistoryRetriever:
    """Strictly queries and aggregates data for the CURRENT authenticated user only.
    Never queries or returns data for any other user.
    """

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def get_user_sessions(self) -> List[InterviewSession]:
        """Fetch all sessions belonging exclusively to this user, ordered chronologically."""
        return (
            self.db.query(InterviewSession)
            .filter(InterviewSession.user_id == self.user_id)
            .order_by(InterviewSession.created_at.asc())
            .all()
        )

    def get_candidate_profile(self, sessions: List[InterviewSession]) -> Tuple[List[str], Dict[str, Any]]:
        """Extract candidate resume skills and structured profile from the latest sessions."""
        skills: List[str] = []
        profile: Dict[str, Any] = {}

        for sess in reversed(sessions):
            if not skills and sess.resume_skills:
                try:
                    loaded = json.loads(sess.resume_skills)
                    if isinstance(loaded, list):
                        skills = loaded
                except Exception:
                    pass

            if not profile and sess.resume_profile:
                try:
                    loaded = json.loads(sess.resume_profile)
                    if isinstance(loaded, dict) and loaded:
                        profile = loaded
                except Exception:
                    pass

            if skills and profile:
                break

        return skills, profile


class RAGCoachService:
    def __init__(self, ai_provider: Optional[AIProvider] = None):
        self.ai_provider = ai_provider or AIProvider()
        self.knowledge_retriever = LocalKnowledgeRetriever()

    # ----------------------------------------------------------------------
    # Core Analysis & Data Construction (User-Scoped)
    # ----------------------------------------------------------------------

    def build_user_context(self, db: Session, user_id: int, user_full_name: Optional[str] = None) -> Dict[str, Any]:
        """Constructs an exhaustive analytics document for the authenticated candidate only."""
        retriever = UserInterviewHistoryRetriever(db, user_id)
        sessions = retriever.get_user_sessions()
        completed_sessions = [s for s in sessions if s.status == "completed"]
        resume_skills, resume_profile = retriever.get_candidate_profile(sessions)

        if not completed_sessions:
            return {
                "has_history": False,
                "user_id": user_id,
                "user_name": user_full_name or "Candidate",
                "total_interviews": len(sessions),
                "completed_interviews": 0,
                "resume_skills": resume_skills,
                "resume_profile": resume_profile,
            }

        session_scores: List[float] = []
        all_evaluations: List[Dict[str, Any]] = []
        all_questions_asked: List[str] = []

        # Topic and skill tracking
        topic_stats: Dict[str, Dict[str, Any]] = {}
        skill_stats: Dict[str, Dict[str, Any]] = {}

        metrics_acc = {
            "correctness": [],
            "relevance": [],
            "technical_depth": [],
            "communication_quality": [],
        }

        for sess in completed_sessions:
            evals = json.loads(sess.evaluations or "[]")
            if not evals:
                continue

            session_score = round(sum(e.get("score", 0) for e in evals) / len(evals), 1)
            session_scores.append(session_score)

            sess_skills = []
            try:
                sess_skills = json.loads(sess.selected_skills or sess.resume_skills or "[]")
            except Exception:
                sess_skills = []

            # If session has recorded structured question_records in adaptive_state, use them for topic mapping
            recorded_topics_map = {}
            if sess.adaptive_state:
                try:
                    ad_state = json.loads(sess.adaptive_state)
                    for qr in ad_state.get("question_records", []):
                        if qr.get("question") and qr.get("topic"):
                            recorded_topics_map[qr["question"].strip()] = (qr["topic"], qr.get("skill"))
                except Exception:
                    pass

            for e in evals:
                q_text = e.get("question", "")
                a_text = e.get("answer", "")
                q_score = float(e.get("score", 0.0))
                all_questions_asked.append(q_text)

                for m in ["correctness", "relevance", "technical_depth", "communication_quality"]:
                    if m in e and e[m] is not None:
                        metrics_acc[m].append(float(e[m]))

                # Detect or infer topic and parent skill (preferring adaptive engine records if present)
                if q_text.strip() in recorded_topics_map:
                    detected_topic, parent_skill = recorded_topics_map[q_text.strip()]
                    if not parent_skill:
                        _, parent_skill = self._classify_topic(
                            question=q_text,
                            answer=a_text,
                            candidate_skills=sess_skills or resume_skills,
                            weaknesses=e.get("weaknesses", []),
                            job_role=sess.job_role,
                        )
                else:
                    detected_topic, parent_skill = self._classify_topic(
                        question=q_text,
                        answer=a_text,
                        candidate_skills=sess_skills or resume_skills,
                        weaknesses=e.get("weaknesses", []),
                        job_role=sess.job_role,
                    )

                # Aggregate topic stats
                if detected_topic not in topic_stats:
                    topic_stats[detected_topic] = {
                        "topic": detected_topic,
                        "skill": parent_skill,
                        "scores": [],
                        "weaknesses": [],
                        "strengths": [],
                        "questions": [],
                    }
                topic_stats[detected_topic]["scores"].append(q_score)
                topic_stats[detected_topic]["weaknesses"].extend(e.get("weaknesses", []))
                topic_stats[detected_topic]["strengths"].extend(e.get("strengths", []))
                topic_stats[detected_topic]["questions"].append(q_text)

                # Aggregate skill stats
                if parent_skill not in skill_stats:
                    skill_stats[parent_skill] = {"skill": parent_skill, "scores": [], "count": 0}
                skill_stats[parent_skill]["scores"].append(q_score)
                skill_stats[parent_skill]["count"] += 1

                all_evaluations.append({
                    "session_id": sess.id,
                    "role": sess.job_role,
                    "type": sess.interview_type,
                    "difficulty": sess.difficulty,
                    "question": q_text,
                    "answer": a_text,
                    "score": q_score,
                    "feedback": e.get("feedback", ""),
                    "strengths": e.get("strengths", []),
                    "weaknesses": e.get("weaknesses", []),
                    "topic": detected_topic,
                    "skill": parent_skill,
                })

        overall_avg = round(sum(session_scores) / len(session_scores), 1) if session_scores else 0.0
        best_score = max(session_scores) if session_scores else 0.0
        recent_score = session_scores[-1] if session_scores else 0.0

        # Topic metric calculations & evidence-based categorization
        weak_topics_list: List[TopicMetricDTO] = []
        strong_topics_list: List[TopicMetricDTO] = []
        all_topics_list: List[TopicMetricDTO] = []

        for topic_name, data in topic_stats.items():
            scores = data["scores"]
            t_avg = round(sum(scores) / len(scores), 1)
            t_count = len(scores)

            # Retrieve grounded technical knowledge for pitfalls & recommendations
            grounded_knowledge = self._retrieve_grounding_for_topic(data["skill"], topic_name)

            # EVIDENCE RULE FOR WEAK TOPIC:
            # - Consistent poor performance (count >= 2 with avg < 6.5)
            # - OR single session with score <= 5.0 and explicit weakness evidence
            is_weak = (t_count >= 2 and t_avg < 6.5) or (t_avg <= 5.0 and len(data["weaknesses"]) >= 1)

            # EVIDENCE RULE FOR STRONG TOPIC:
            # - Consistent high performance (avg >= 7.5)
            is_strong = (t_avg >= 7.5)

            status = "weak" if is_weak else ("strong" if is_strong else "neutral")

            dto = TopicMetricDTO(
                topic=topic_name,
                skill=data["skill"],
                score=t_avg,
                evaluations_count=t_count,
                status=status,
                common_pitfalls=grounded_knowledge.get("mistakes", [])[:3],
                recommendations=grounded_knowledge.get("actions", [])[:4],
            )
            all_topics_list.append(dto)
            if is_weak:
                weak_topics_list.append(dto)
            elif is_strong:
                strong_topics_list.append(dto)

        # Sort topics: weak by score ascending, strong by score descending
        weak_topics_list.sort(key=lambda x: (x.score, -x.evaluations_count))
        strong_topics_list.sort(key=lambda x: (-x.score, -x.evaluations_count))
        all_topics_list.sort(key=lambda x: x.score)

        # Skill rankings
        skill_metric_list = []
        for s_name, s_data in skill_stats.items():
            s_avg = round(sum(s_data["scores"]) / len(s_data["scores"]), 1)
            skill_metric_list.append(SkillMetricDTO(skill=s_name, score=s_avg, evaluations_count=s_data["count"]))
        skill_metric_list.sort(key=lambda x: x.score)

        strongest_skill = skill_metric_list[-1] if skill_metric_list else None
        weakest_skill = skill_metric_list[0] if skill_metric_list else None

        # Improvement Trend calculation (honest, non-fake analysis)
        trend = self._calculate_improvement_trend(session_scores)

        # Metrics averages
        calc_metrics = {}
        for k, v in metrics_acc.items():
            calc_metrics[k] = round(sum(v) / len(v), 2) if v else 0.0

        # Build recommended next interview targeting candidate's weakest topic and skill
        primary_weak_topic = weak_topics_list[0].topic if weak_topics_list else "General Core Fundamentals"
        primary_weak_skill = weak_topics_list[0].skill if weak_topics_list else (weakest_skill.skill if weakest_skill else "Technical")
        latest_sess = completed_sessions[-1]

        rec_interview = RecommendedInterviewDTO(
            job_role=latest_sess.job_role,
            interview_type="Technical",
            difficulty=latest_sess.difficulty,
            experience_level=latest_sess.experience_level,
            focus_topic=primary_weak_topic,
            selected_skills=[primary_weak_skill] if primary_weak_skill else [],
            title=f"{latest_sess.experience_level} {primary_weak_skill} Interview: {primary_weak_topic} Focus",
            reason=f"Targeted practice to strengthen {primary_weak_topic} where your recent average score was {weak_topics_list[0].score if weak_topics_list else overall_avg}/10.",
        )

        return {
            "has_history": True,
            "user_id": user_id,
            "user_name": user_full_name or "Candidate",
            "total_interviews": len(sessions),
            "completed_interviews": len(completed_sessions),
            "overall_score": overall_avg,
            "recent_score": recent_score,
            "best_score": best_score,
            "strongest_skill": strongest_skill,
            "weakest_skill": weakest_skill,
            "weak_topics": weak_topics_list,
            "strong_topics": strong_topics_list,
            "all_topics": all_topics_list,
            "improvement_trend": trend,
            "metrics": calc_metrics,
            "recommended_interview": rec_interview,
            "all_questions_asked": all_questions_asked,
            "recent_evaluations": all_evaluations[-10:],
            "resume_skills": resume_skills,
            "resume_profile": resume_profile,
        }

    # ----------------------------------------------------------------------
    # API Methods
    # ----------------------------------------------------------------------

    def get_coach_summary(self, db: Session, user: User) -> CoachSummaryResponse:
        """Returns the complete structured dashboard coach summary for the authenticated user."""
        ctx = self.build_user_context(db, user.id, user.full_name)

        if not ctx.get("has_history"):
            return CoachSummaryResponse(
                has_enough_data=False,
                summary="Welcome! Complete your first interview session to unlock personalized AI interview coaching.",
                overall_score=0.0,
                recent_score=0.0,
                best_score=0.0,
                improvement_trend=ImprovementTrendDTO(
                    direction="baseline",
                    description="No interview history recorded yet.",
                    history_scores=[],
                    delta=0.0,
                ),
                next_action="Start your first interview session to establish baseline metrics.",
                candidate_resume_skills=ctx.get("resume_skills", []),
            )

        weak_topics = ctx["weak_topics"]
        strong_topics = ctx["strong_topics"]
        trend = ctx["improvement_trend"]
        strongest = ctx["strongest_skill"]
        weakest = ctx["weakest_skill"]
        user_name = ctx["user_name"]
        is_preliminary = (ctx.get("completed_interviews", 0) == 1)

        # Synthesize clear, grounded summary paragraph
        if is_preliminary:
            summary_lines = [f"Hi {user_name}! [Preliminary Analysis - 1 interview completed] Based on your initial interview, here are preliminary insights. Complete more sessions to uncover recurring patterns."]
        else:
            summary_lines = [f"Hi {user_name}! Here's what I found from your recent interview performance."]

        if strongest and strongest.score >= 7.0:
            summary_lines.append(f"Your strongest area is {strongest.skill} ({strongest.score}/10).")
        if weak_topics:
            top_weaks = ", ".join(f"{w.topic} ({w.score}/10)" for w in weak_topics[:2])
            summary_lines.append(f"Your primary focus area for improvement is {top_weaks}.")
        summary_lines.append(trend.description)

        # Actionable recommendations list
        actions = []
        if weak_topics:
            actions.extend(weak_topics[0].recommendations[:3])
            actions.append(f"Practice a targeted interview focusing on {weak_topics[0].topic}")
        else:
            actions.append("Practice advanced scenarios to further challenge your technical depth.")

        next_action = f"Practice {weak_topics[0].topic}" if weak_topics else "Start an advanced interview"

        return CoachSummaryResponse(
            has_enough_data=True,
            summary=" ".join(summary_lines),
            overall_score=ctx["overall_score"],
            recent_score=ctx["recent_score"],
            best_score=ctx["best_score"],
            strongest_skill=strongest,
            weakest_skill=weakest,
            weak_topics=weak_topics,
            strong_topics=strong_topics,
            improvement_trend=trend,
            metrics=ctx["metrics"],
            recommended_interview=ctx["recommended_interview"],
            recommended_actions=actions,
            next_action=next_action,
            all_topics=ctx.get("all_topics", []),
            candidate_resume_skills=ctx.get("resume_skills", []),
            is_preliminary=is_preliminary,
        )

    def get_coach_topics(self, db: Session, user: User) -> List[TopicMetricDTO]:
        """Returns the full topic breakdown for the authenticated user."""
        ctx = self.build_user_context(db, user.id, user.full_name)
        return ctx.get("all_topics", [])

    def get_coach_weak_topics(self, db: Session, user: User) -> List[TopicMetricDTO]:
        """Returns identified weak topics for the authenticated candidate."""
        ctx = self.build_user_context(db, user.id, user.full_name)
        return ctx.get("weak_topics", [])

    def get_coach_strong_topics(self, db: Session, user: User) -> List[TopicMetricDTO]:
        """Returns identified strong topics for the authenticated candidate."""
        ctx = self.build_user_context(db, user.id, user.full_name)
        return ctx.get("strong_topics", [])

    def get_coach_recommendations(self, db: Session, user: User) -> List[TopicMetricDTO]:
        """Returns detailed actionable recommendations for weak topics."""
        ctx = self.build_user_context(db, user.id, user.full_name)
        return ctx.get("weak_topics", [])

    def generate_practice_question(
        self, db: Session, user: User, target_topic: Optional[str] = None
    ) -> PracticeQuestionResponse:
        """Generates a targeted practice question that has NEVER been asked to this user."""
        ctx = self.build_user_context(db, user.id, user.full_name)
        asked_questions = set(q.strip().lower() for q in ctx.get("all_questions_asked", []))

        # Determine target topic and skill
        weak_topics = ctx.get("weak_topics", [])
        if target_topic:
            selected_topic = target_topic
            matching = [w for w in weak_topics if w.topic.lower() == target_topic.lower()]
            selected_skill = matching[0].skill if matching else "Technical"
        elif weak_topics:
            selected_topic = weak_topics[0].topic
            selected_skill = weak_topics[0].skill
        else:
            selected_topic = "Core Fundamentals"
            selected_skill = "Technical"

        # Grounding knowledge retrieval
        topic_records = self.knowledge_retriever.retrieve(
            selected_skills=[selected_skill],
            difficulty="Medium",
            experience_level="Intermediate",
            max_topics=6,
        )

        candidate_questions = []
        for r in topic_records:
            for c in r.concepts:
                candidate_questions.append(
                    f"In {r.skill} ({r.topic}), can you explain how {c} works in practice and how you prevent common mistakes like {r.common_mistakes[0] if r.common_mistakes else 'unexpected bugs'}?"
                )
            for m in r.common_mistakes:
                candidate_questions.append(
                    f"You are debugging an issue in {r.skill} involving '{m}'. What is the root cause of this problem and how would you resolve it?"
                )

        # Fallback pool
        candidate_questions.extend([
            f"Can you walk through a real-world scenario where you had to implement and optimize {selected_topic}?",
            f"What are the most critical architectural tradeoffs when designing with {selected_topic} in a production environment?",
            f"Describe how you identify, isolate, and debug performance bottlenecks in {selected_topic}.",
        ])

        # Filter out questions already asked
        fresh_question = None
        for q in candidate_questions:
            if q.strip().lower() not in asked_questions:
                fresh_question = q
                break

        if not fresh_question:
            fresh_question = f"How would you architect a fault-tolerant module for {selected_topic} avoiding stale state and concurrency pitfalls?"

        rationale = (
            f"Selected specifically to address your performance in {selected_topic}, "
            f"targeting concepts like {topic_records[0].concepts[0] if topic_records and topic_records[0].concepts else 'core behavior'}."
        )

        return PracticeQuestionResponse(
            question=fresh_question,
            topic=selected_topic,
            skill=selected_skill,
            difficulty="Medium",
            rationale=rationale,
        )

    def chat_with_coach(
        self, db: Session, user: User, message: str, history: Optional[List[Dict[str, str]]] = None
    ) -> CoachChatResponse:
        """Conversational AI Coach grounded in the authenticated user's actual history and technical knowledge."""
        ctx = self.build_user_context(db, user.id, user.full_name)

        if not ctx.get("has_history"):
            return CoachChatResponse(
                response="You don't have any completed interviews yet! Once you complete your first interview, I will analyze your performance, identify your strong and weak topics, and provide tailored practice advice.",
                practice_question=None,
                referenced_topics=[],
            )

        msg_lower = message.strip().lower()
        weak_topics = ctx.get("weak_topics", [])
        strong_topics = ctx.get("strong_topics", [])
        overall_avg = ctx.get("overall_score", 0.0)
        strongest = ctx.get("strongest_skill")
        user_name = ctx.get("user_name", "there")

        referenced: List[str] = []
        practice_q: Optional[str] = None

        # Check if user asked for a practice question
        wants_practice = any(w in msg_lower for w in ["practice question", "give me a question", "ask me a question", "test me"])
        if wants_practice:
            pq = self.generate_practice_question(db, user)
            practice_q = pq.question
            referenced.append(pq.topic)
            reply = (
                f"Here is a targeted practice question for your weakest topic, **{pq.topic}**:\n\n"
                f"> **{pq.question}**\n\n"
                f"*Rationale:* {pq.rationale}"
            )
            return CoachChatResponse(response=reply, practice_question=practice_q, referenced_topics=referenced)

        # Check if user asked "Why?" or explanation for weaknesses
        if msg_lower in ["why", "why?", "explain why", "why is that"]:
            if weak_topics:
                wt = weak_topics[0]
                referenced.append(wt.topic)
                # Find recent evals for this topic
                recent_evals = [e for e in ctx.get("recent_evaluations", []) if e.get("topic") == wt.topic or wt.topic.lower() in e.get("question", "").lower()]
                evidence = []
                for ev in recent_evals[:2]:
                    evidence.append(f"- Question: \"{ev['question'][:60]}...\" → Score: {ev['score']}/10. Feedback: {ev['feedback'][:90]}...")
                evidence_text = "\n".join(evidence) if evidence else f"Across {wt.evaluations_count} questions targeting {wt.topic}, your average score was {wt.score}/10."
                reply = (
                    f"Based on your actual interview history, {wt.topic} is flagged because:\n\n"
                    f"{evidence_text}\n\n"
                    f"Common mistakes detected: {', '.join(wt.common_pitfalls) if wt.common_pitfalls else 'superficial technical depth'}.\n"
                    f"I recommend reviewing: {', '.join(wt.recommendations[:2])}."
                )
            else:
                reply = f"Your performance across all tested topics has been solid (Average: {overall_avg}/10) with no recurring failure patterns detected!"
            return CoachChatResponse(response=reply, practice_question=None, referenced_topics=referenced)

        # Check if user asked "What should I improve?"
        if any(w in msg_lower for w in ["what should i improve", "how can i improve", "areas to improve", "what to improve"]):
            if weak_topics:
                recs = []
                for wt in weak_topics[:3]:
                    referenced.append(wt.topic)
                    recs.append(f"- **{wt.topic}** (Score: {wt.score}/10): {', '.join(wt.recommendations[:2])}")
                reply = (
                    f"Based on your {ctx['completed_interviews']} completed interviews, your weakest areas are:\n\n"
                    + "\n".join(recs)
                    + f"\n\n**Next Action:** {ctx['recommended_interview'].title}. Type 'Give me a practice question' to practice now!"
                )
            else:
                reply = f"You are doing well across all tested topics! Your average score is {overall_avg}/10. Focus on sharpening high-level system architecture and edge cases."
            return CoachChatResponse(response=reply, practice_question=None, referenced_topics=referenced)

        # Check if user asked about their resume or skills
        if any(w in msg_lower for w in ["resume", "my skills", "my project", "technologies", "experience with", "do i know", "have i used"]):
            r_skills = ctx.get("resume_skills", [])
            r_profile = ctx.get("resume_profile", {})
            projects = r_profile.get("projects", []) if isinstance(r_profile, dict) else []

            # Check if asking about a specific skill not in resume
            unsupported_found = None
            for tech in ["rust", "golang", "c++", "ruby", "aws", "kubernetes", "flutter", "swift", "angular"]:
                if tech in msg_lower and not any(tech == s.lower() for s in r_skills):
                    unsupported_found = tech.capitalize()
                    break

            if unsupported_found:
                reply = f"I verified your uploaded resume and interview records. {unsupported_found} is not listed on your resume, and you haven't taken interviews on it. I only report facts grounded in your verified candidate profile."
                return CoachChatResponse(response=reply, practice_question=None, referenced_topics=r_skills[:3])

            if r_skills:
                skills_str = ", ".join(r_skills)
                reply = f"According to your uploaded resume, your verified skills are: {skills_str}."
                if projects:
                    proj_names = [p.get("name") for p in projects if isinstance(p, dict) and p.get("name")]
                    if proj_names:
                        reply += f" Documented projects: {', '.join(proj_names)}."
                reply += " I only reference skills and experience confirmed in your profile."
            else:
                reply = "You haven't uploaded a resume with extracted skills yet. Your coaching insights are currently derived from your interview evaluations."
            return CoachChatResponse(response=reply, practice_question=None, referenced_topics=r_skills[:3])

        # General conversational response
        if self.ai_provider.provider_name != "mock":
            # Real LLM call with strict candidate grounding context
            prompt_context = {
                "user_name": user_name,
                "overall_score": overall_avg,
                "weak_topics": [{"topic": w.topic, "score": w.score, "pitfalls": w.common_pitfalls} for w in weak_topics[:3]],
                "strong_topics": [{"topic": s.topic, "score": s.score} for s in strong_topics[:3]],
                "trend": ctx["improvement_trend"].description,
                "resume_skills": ctx.get("resume_skills", []),
            }
            llm_reply = self.ai_provider.generate_coach_chat(prompt_context, message, history or [])
            return CoachChatResponse(
                response=llm_reply,
                practice_question=None,
                referenced_topics=[w.topic for w in weak_topics[:2]],
            )

        # Mock fallback response
        weak_str = f"**{weak_topics[0].topic}**" if weak_topics else "core technical concepts"
        strong_str = f"**{strongest.skill}**" if strongest else "general communication"
        if weak_topics:
            referenced.append(weak_topics[0].topic)
        reply = (
            f"Hello {user_name}! In your recent interviews, your strongest skill has been {strong_str}. "
            f"Your primary growth opportunity is {weak_str}. "
            f"{ctx['improvement_trend'].description} "
            f"Would you like a targeted practice question or advice on preparing for your next interview?"
        )
        return CoachChatResponse(response=reply, practice_question=None, referenced_topics=referenced)

    # ----------------------------------------------------------------------
    # Backward-Compatible Legacy Method
    # ----------------------------------------------------------------------

    def generate_coaching_guidance(self, db: Session, user: User) -> AICoachResponse:
        """Preserved for existing code & tests: returns legacy AICoachResponse."""
        ctx = self.build_user_context(db, user.id, user_full_name=user.full_name)

        if not ctx.get("has_history"):
            return AICoachResponse(
                summary="I don't have enough interview history yet to make a reliable recommendation.",
                strengths=[],
                weak_areas=[],
                recommended_topics=[],
                next_action="Complete at least one interview session to unlock personalized AI coaching.",
                has_enough_data=False,
            )

        weak_areas = [w.topic for w in ctx.get("weak_topics", [])]
        strong_areas = [s.topic for s in ctx.get("strong_topics", [])]
        recs = []
        for w in ctx.get("weak_topics", [])[:3]:
            recs.extend(w.recommendations[:2])

        if not recs:
            recs = ["Review core software architecture fundamentals", "Practice debugging complex state transitions"]

        next_action = f"Practice a focused interview on {weak_areas[0]}" if weak_areas else "Complete an advanced interview"

        return AICoachResponse(
            summary=f"Based on your {ctx['completed_interviews']} completed interviews (Average: {ctx['overall_score']}/10), focus on bolstering your depth in {', '.join(weak_areas[:2]) if weak_areas else 'core skills'}.",
            strengths=strong_areas if strong_areas else ["Structured communication", "Problem breakdown"],
            weak_areas=weak_areas if weak_areas else ["Advanced edge cases"],
            recommended_topics=recs[:4],
            next_action=next_action,
            has_enough_data=True,
        )

    # ----------------------------------------------------------------------
    # Internal Helpers
    # ----------------------------------------------------------------------

    def _classify_topic(
        self, question: str, answer: str, candidate_skills: List[str], weaknesses: List[str], job_role: str
    ) -> Tuple[str, str]:
        """Identifies specific topic and parent skill from question, answer, and evaluation context."""
        text = f"{question} {answer} {' '.join(weaknesses)}".lower()
        cand_skills_lower = [s.lower() for s in candidate_skills if s]

        # 1. Match topics matching candidate's explicit skills first
        if cand_skills_lower:
            for topic, keywords in _TOPIC_KEYWORDS.items():
                parent_skill = topic.split()[0]
                if any(cs in parent_skill.lower() or parent_skill.lower() in cs for cs in cand_skills_lower):
                    if any(kw in text for kw in keywords):
                        return topic, parent_skill

        # 2. Check explicit keyword mapping for domain-neutral topics (Docker, REST, Database, SQL, System)
        for topic, keywords in _TOPIC_KEYWORDS.items():
            parent_skill = topic.split()[0]
            if parent_skill in ["Docker", "REST", "Database", "SQL", "System"]:
                if any(kw in text for kw in keywords):
                    ps = "Technical" if parent_skill in ["Docker", "REST", "Database", "System"] else "SQL"
                    return topic, ps

        # 3. Check weaknesses tags
        for w in weaknesses:
            w_lower = w.lower()
            if "hook" in w_lower or "useeffect" in w_lower:
                return "React Hooks", "React"
            if "security" in w_lower:
                return ("Spring Security", "Spring") if ("spring" in text or any("spring" in s for s in cand_skills_lower)) else ("System Security", "Technical")
            if "index" in w_lower or "b-tree" in w_lower:
                return "Database Indexing", "SQL"

        # 4. Fallback check for all remaining topics
        for topic, keywords in _TOPIC_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                parent_skill = topic.split()[0]
                if parent_skill in ["Docker", "REST", "Database", "System"]:
                    parent_skill = "Technical"
                return topic, parent_skill

        # 5. Match against candidate skills
        for s in candidate_skills:
            if s.lower() in text:
                return f"{s} Fundamentals", s

        return f"{job_role} Concepts", "Technical"

    def _retrieve_grounding_for_topic(self, skill: str, topic: str) -> Dict[str, List[str]]:
        """Queries local knowledge base for authoritative concept pitfalls and actionable tips."""
        records = self.knowledge_retriever.retrieve(
            selected_skills=[skill],
            difficulty="Medium",
            experience_level="Intermediate",
            max_topics=8,
        )

        matching_mistakes: List[str] = []
        matching_actions: List[str] = []

        topic_words = set(topic.lower().replace("-", " ").split())
        best_record = None
        best_score = 0

        for r in records:
            score = 0
            if r.topic.lower() in topic.lower() or topic.lower() in r.topic.lower():
                score += 10
            for tag in (r.tags or []):
                if tag.lower() in topic_words or tag.lower() in topic.lower():
                    score += 5
            for c in (r.concepts or []):
                if any(w in c.lower() for w in topic_words if len(w) > 3):
                    score += 2
            if score > best_score:
                best_score = score
                best_record = r

        if best_record:
            matching_mistakes.extend(best_record.common_mistakes)
            matching_actions.extend([f"Review {c}" for c in best_record.concepts])
        elif records:
            matching_mistakes.extend(records[0].common_mistakes)
            matching_actions.extend([f"Review {c}" for c in records[0].concepts])

        # If specific topic has explicit known guidance
        if "hook" in topic.lower() or "useeffect" in topic.lower():
            matching_actions = [
                "Review useState and state immutability",
                "Review useEffect dependencies and cleanup functions",
                "Practice dependency array rules and stale closure prevention",
                "Take a targeted React Hooks practice interview",
            ]
        elif "security" in topic.lower():
            matching_actions = [
                "Review Spring SecurityFilterChain and filter ordering",
                "Configure JWT authentication filter and UserDetailsService",
                "Practice method-level security with @PreAuthorize",
                "Take a targeted Spring Security interview",
            ]

        if not matching_actions:
            matching_actions = [
                f"Review official {skill} documentation",
                f"Practice debugging {topic} scenarios",
                f"Build a miniature prototype applying {topic}",
            ]

        return {
            "mistakes": list(dict.fromkeys(matching_mistakes)),
            "actions": list(dict.fromkeys(matching_actions)),
        }

    def _calculate_improvement_trend(self, scores: List[float]) -> ImprovementTrendDTO:
        """Determines honest improvement trend across chronological sessions."""
        if not scores:
            return ImprovementTrendDTO(
                direction="baseline",
                description="No completed interview history yet.",
                history_scores=[],
                delta=0.0,
            )

        if len(scores) == 1:
            return ImprovementTrendDTO(
                direction="baseline",
                description="Baseline interview completed (Score: " + str(scores[0]) + "/10). Complete more interviews to track your growth.",
                history_scores=scores,
                delta=0.0,
            )

        delta = round(scores[-1] - scores[0], 1)

        # If 3 or more sessions, check progression
        if len(scores) >= 3:
            first_half = scores[: len(scores) // 2]
            second_half = scores[len(scores) // 2 :]
            half_delta = round((sum(second_half) / len(second_half)) - (sum(first_half) / len(first_half)), 1)
            
            if half_delta >= 0.5 or (scores[-1] > scores[-2] > scores[0]):
                return ImprovementTrendDTO(
                    direction="improving",
                    description=f"Your interview score has improved steadily across your last {len(scores)} interviews (+{delta} overall).",
                    history_scores=scores,
                    delta=delta,
                )
            elif half_delta <= -0.5:
                return ImprovementTrendDTO(
                    direction="declining",
                    description=f"Your recent scores have declined compared to earlier sessions ({delta} points). We recommend reviewing core concepts before taking another full interview.",
                    history_scores=scores,
                    delta=delta,
                )
            else:
                return ImprovementTrendDTO(
                    direction="consistent",
                    description=f"Your performance has remained consistent across your last {len(scores)} interviews (Average: {round(sum(scores)/len(scores), 1)}/10).",
                    history_scores=scores,
                    delta=delta,
                )

        # 2 sessions
        if delta >= 0.8:
            return ImprovementTrendDTO(
                direction="improving",
                description=f"Your interview score improved by +{delta} points in your latest session.",
                history_scores=scores,
                delta=delta,
            )
        elif delta <= -0.8:
            return ImprovementTrendDTO(
                direction="declining",
                description=f"Your latest score dipped by {abs(delta)} points. Review your feedback to target areas needing reinforcement.",
                history_scores=scores,
                delta=delta,
            )
        else:
            return ImprovementTrendDTO(
                direction="consistent",
                description=f"Your scores have been stable across your 2 interviews (Average: {round(sum(scores)/len(scores), 1)}/10).",
                history_scores=scores,
                delta=delta,
            )
