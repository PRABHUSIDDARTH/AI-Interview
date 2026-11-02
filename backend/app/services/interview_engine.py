import os
from typing import List, Dict, Any, Optional

try:
    from fastapi import HTTPException, status
except ImportError:
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            self.status_code = status_code
            self.detail = detail
    class status:
        HTTP_404_NOT_FOUND = 404
from datetime import datetime

from app.models.interview_session import InterviewSession
from app.schemas.interview import InterviewSessionResponse, InterviewSessionCreate
from app.services.ai import AIProvider
from sqlalchemy.orm import Session


import json

from app.services.knowledge.retriever import LocalKnowledgeRetriever
from app.services.adaptive_engine import AdaptiveDecisionEngine, AdaptiveDecision

class InterviewEngine:
    def __init__(self):
        # Initialize AI provider (mock or real based on env)
        self.provider = AIProvider()
        self.decision_engine = AdaptiveDecisionEngine()

    def _get_session(self, db: Session, session_id: int) -> InterviewSession:
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")
        return session

    def create_session(
        self,
        db: Session,
        session_in: InterviewSessionCreate,
        user_id: int,
        resume_text: Optional[str] = None,
        job_description: Optional[str] = None,
        resume_profile: Optional[Dict[str, Any]] = None,
    ) -> InterviewSession:
        # Determine candidate skills for knowledge retrieval
        effective_skills = list(session_in.selected_skills or session_in.resume_skills or [])

        # Parse resume profile if resume_text provided, or use provided profile
        resume_profile_dict = dict(resume_profile) if resume_profile else {}
        if not resume_profile_dict and resume_text and resume_text.strip():
            try:
                from app.services.resume_parser import ResumeParserService
                parser = ResumeParserService(self.provider)
                parsed = parser.parse_resume_text(resume_text)
                resume_profile_dict = parsed.get("profile") or {}
                if not session_in.resume_skills and parsed.get("extracted_skills"):
                    session_in.resume_skills = parsed["extracted_skills"]
                    if not effective_skills:
                        effective_skills = list(session_in.resume_skills)
            except Exception as parse_err:
                pass

        # Retrieve curated topic records for grounding
        retriever = LocalKnowledgeRetriever()
        retrieved_topics = retriever.retrieve(
            selected_skills=effective_skills,
            difficulty=session_in.difficulty,
            experience_level=session_in.experience_level,
            max_topics=min(session_in.question_count * 3, 24)
        )
        retrieved_dicts = [r.to_dict() for r in retrieved_topics]
        source_refs = retriever.get_source_references(effective_skills)

        # Initialize adaptive state
        adaptive_state_dict = self.decision_engine.initialize_state(
            initial_difficulty=session_in.difficulty,
            selected_skills=session_in.selected_skills,
            resume_skills=session_in.resume_skills,
            available_topics=retrieved_dicts,
        )

        # Determine decision for Q1 (baseline)
        initial_decision = self.decision_engine.determine_next_question(
            interview_state=adaptive_state_dict,
            latest_evaluation=None,
            resume_context=resume_profile_dict,
            selected_skills=effective_skills,
            available_topics=retrieved_dicts,
        )

        # Generate initial adaptive Question 1
        q1 = self.provider.generate_adaptive_next_question(
            setup={
                "job_role": session_in.job_role,
                "interview_type": session_in.interview_type,
                "experience_level": session_in.experience_level,
                "difficulty": session_in.difficulty,
                "interview_language": session_in.interview_language or "English",
                "selected_skills": session_in.selected_skills or [],
                "resume_skills": session_in.resume_skills or [],
            },
            questions_asked=[],
            evaluations=[],
            adaptive_state=adaptive_state_dict,
            resume_profile=resume_profile_dict,
            retrieved_knowledge=retrieved_dicts,
            decision=initial_decision,
        )

        if not q1:
            setup = {
                "job_role": session_in.job_role,
                "interview_type": session_in.interview_type,
                "experience_level": session_in.experience_level,
                "difficulty": session_in.difficulty,
                "question_count": 1,
                "interview_language": session_in.interview_language or "English",
                "resume_skills": session_in.resume_skills or [],
                "selected_skills": session_in.selected_skills or [],
            }
            q_batch = self.provider.generate_questions_batch(
                setup, 1, resume_text=resume_text, job_description=job_description, retrieved_knowledge=retrieved_dicts
            )
            q1 = q_batch[0] if q_batch else "Can you describe a challenging project you worked on recently?"

        questions_list = [q1]
        adaptive_state_dict.setdefault("questions_asked", []).append(q1)
        adaptive_state_dict.setdefault("conversation_history", []).append({"question": q1})

        # Create interview session record and set status to in_progress
        new_session = InterviewSession(
            user_id=user_id,
            job_role=session_in.job_role,
            interview_type=session_in.interview_type,
            experience_level=session_in.experience_level,
            difficulty=session_in.difficulty,
            question_count=session_in.question_count,
            job_description=job_description,
            interview_language=session_in.interview_language or "English",
            resume_skills=json.dumps(session_in.resume_skills or []),
            selected_skills=json.dumps(session_in.selected_skills or []),
            resume_profile=json.dumps(resume_profile_dict),
            adaptive_state=json.dumps(adaptive_state_dict),
            source_context=json.dumps(source_refs),
            status="in_progress",
            questions=json.dumps(questions_list),
            evaluations='[]',
            answered_count=0,
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return new_session

    def get_next_question(self, db: Session, session_id: int) -> Dict[str, Any]:
        session = self._get_session(db, session_id)
        questions_list = json.loads(session.questions or '[]')
        idx = session.answered_count or 0

        if idx >= session.question_count:
            return {
                "question_id": None,
                "text": "No more questions. The interview is complete.",
                "metadata": {"complete": True, "total_questions": session.question_count}
            }

        # If question for this index has not been generated yet, generate dynamically
        if idx >= len(questions_list):
            adaptive_state_dict = json.loads(session.adaptive_state or '{}')
            resume_profile_dict = json.loads(session.resume_profile or '{}')
            evals = json.loads(session.evaluations or '[]')
            
            selected_skills = json.loads(session.selected_skills or '[]')
            resume_skills = json.loads(session.resume_skills or '[]')
            effective_skills = selected_skills or resume_skills or []
            
            retriever = LocalKnowledgeRetriever()
            retrieved_topics = retriever.retrieve(
                selected_skills=effective_skills,
                difficulty=adaptive_state_dict.get("current_difficulty", session.difficulty),
                experience_level=session.experience_level
            )
            retrieved_dicts = [r.to_dict() for r in retrieved_topics]

            latest_eval = evals[-1] if evals else None
            decision = self.decision_engine.determine_next_question(
                interview_state=adaptive_state_dict,
                latest_evaluation=latest_eval,
                resume_context=resume_profile_dict,
                selected_skills=effective_skills,
                available_topics=retrieved_dicts,
            )

            next_q = self.provider.generate_adaptive_next_question(
                setup={
                    "job_role": session.job_role,
                    "interview_type": session.interview_type,
                    "experience_level": session.experience_level,
                    "difficulty": decision.difficulty or adaptive_state_dict.get("current_difficulty", session.difficulty),
                    "interview_language": session.interview_language or "English",
                    "selected_skills": selected_skills,
                    "resume_skills": resume_skills,
                },
                questions_asked=questions_list,
                evaluations=evals,
                adaptive_state=adaptive_state_dict,
                resume_profile=resume_profile_dict,
                retrieved_knowledge=retrieved_dicts,
                decision=decision,
            )

            # Deduplication check
            candidate_q = next_q
            if candidate_q in questions_list or self.decision_engine.is_semantically_duplicate(candidate_q, questions_list):
                fallbacks = [
                    f"In {decision.next_skill} ({decision.next_topic}), how do you optimize for production performance and handle edge cases?",
                    f"Let's explore another aspect of {decision.next_skill} ({decision.next_topic}): how do you test and debug issues in production?",
                    f"When working with {decision.next_skill} ({decision.next_topic}), what architecture patterns prevent memory leaks and performance bottlenecks?",
                ]
                for fb in fallbacks:
                    if fb not in questions_list and not self.decision_engine.is_semantically_duplicate(fb, questions_list):
                        candidate_q = fb
                        break
            next_q = candidate_q

            questions_list.append(next_q)
            session.questions = json.dumps(questions_list)
            conv_history = adaptive_state_dict.setdefault("conversation_history", [])
            conv_history.append({"question": next_q})
            adaptive_state_dict.setdefault("questions_asked", []).append(next_q)
            session.adaptive_state = json.dumps(adaptive_state_dict)
            db.add(session)
            db.commit()

        question_text = questions_list[idx]
        adaptive_state_dict = json.loads(session.adaptive_state or '{}')
        selected_skills = json.loads(session.selected_skills or '[]')
        resume_skills = json.loads(session.resume_skills or '[]')
        focus_skills = selected_skills or resume_skills or []
        detected_topic, _ = self.decision_engine.classify_question_topic(question_text, candidate_skills=focus_skills)

        return {
            "question_id": idx + 1,
            "text": question_text,
            "metadata": {
                "question_number": idx + 1,
                "total_questions": session.question_count,
                "current_difficulty": adaptive_state_dict.get("current_difficulty", session.difficulty),
                "topic": detected_topic,
                "adaptive": True,
            },
        }

    def submit_answer(self, db: Session, session_id: int, answer: str) -> Dict[str, Any]:
        session = self._get_session(db, session_id)
        questions_list = json.loads(session.questions or '[]')
        idx = session.answered_count or 0

        if idx >= session.question_count:
            raise HTTPException(status_code=400, detail="All questions have already been answered.")

        if idx >= len(questions_list):
            raise HTTPException(status_code=400, detail="Current question was not found in session.")

        question_text = questions_list[idx]

        # Fetch trusted technical knowledge context for evaluation grounding
        selected_skills = json.loads(session.selected_skills or '[]')
        resume_skills = json.loads(session.resume_skills or '[]')
        effective_skills = selected_skills or resume_skills or [session.job_role]

        retriever = LocalKnowledgeRetriever()
        retrieved_topics = retriever.retrieve(
            selected_skills=effective_skills,
            difficulty=session.difficulty,
            experience_level=session.experience_level
        )
        retrieved_dicts = [r.to_dict() for r in retrieved_topics]

        # Evaluate answer using the AI provider with trusted knowledge context
        evaluation_dto = self.provider.evaluate_answer(
            question_text,
            answer,
            [],
            experience_level=session.experience_level,
            job_role=session.job_role,
            difficulty=session.difficulty,
            retrieved_knowledge=retrieved_dicts,
        )

        # Relevance gate: if relevance < 0.4, score cannot exceed 2.0
        final_score = min(float(evaluation_dto.score), 2.0) if evaluation_dto.relevance < 0.4 else float(evaluation_dto.score)

        eval_dict = {
            "question": question_text,
            "answer": answer,
            "score": final_score,
            "feedback": evaluation_dto.feedback,
            "correctness": evaluation_dto.correctness,
            "relevance": evaluation_dto.relevance,
            "technical_depth": evaluation_dto.technical_depth,
            "communication_quality": evaluation_dto.communication_quality,
            "strengths": evaluation_dto.strengths,
            "weaknesses": evaluation_dto.weaknesses,
        }

        # Update adaptive state
        adaptive_state_dict = json.loads(session.adaptive_state or '{}')
        conv_history = adaptive_state_dict.setdefault("conversation_history", [])
        if conv_history and conv_history[-1].get("question") == question_text:
            conv_history[-1]["answer"] = answer
            conv_history[-1]["score"] = final_score
        else:
            conv_history.append({"question": question_text, "answer": answer, "score": final_score})

        # Classify topic and skill using AdaptiveDecisionEngine
        selected_skills = json.loads(session.selected_skills or '[]')
        resume_skills = json.loads(session.resume_skills or '[]')
        all_skills = selected_skills or resume_skills or []

        detected_topic, detected_skill = self.decision_engine.classify_question_topic(
            question=question_text,
            answer=answer,
            candidate_skills=all_skills,
            weaknesses=evaluation_dto.weaknesses,
            job_role=session.job_role,
        )

        # Update fine-grained state and difficulty via decision engine
        adaptive_state_dict = self.decision_engine.update_adaptive_state(
            state=adaptive_state_dict,
            question=question_text,
            answer=answer,
            evaluation=eval_dict,
            detected_topic=detected_topic,
            detected_skill=detected_skill,
        )
        curr_diff = adaptive_state_dict.get("current_difficulty", session.difficulty or "Medium")

        # Persist evaluation
        existing_evals = json.loads(session.evaluations or '[]')
        existing_evals.append(eval_dict)
        session.evaluations = json.dumps(existing_evals)

        # Increment answered count
        session.answered_count = idx + 1

        # If more questions remain, generate next adaptive question using decision engine
        if session.answered_count < session.question_count:
            resume_profile_dict = json.loads(session.resume_profile or '{}')
            retriever = LocalKnowledgeRetriever()
            retrieved_topics = retriever.retrieve(
                selected_skills=all_skills,
                difficulty=curr_diff,
                experience_level=session.experience_level
            )
            retrieved_dicts = [r.to_dict() for r in retrieved_topics]

            next_decision = self.decision_engine.determine_next_question(
                interview_state=adaptive_state_dict,
                latest_evaluation=eval_dict,
                resume_context=resume_profile_dict,
                selected_skills=all_skills,
                available_topics=retrieved_dicts,
            )

            next_q = self.provider.generate_adaptive_next_question(
                setup={
                    "job_role": session.job_role,
                    "interview_type": session.interview_type,
                    "experience_level": session.experience_level,
                    "difficulty": next_decision.difficulty or curr_diff,
                    "interview_language": session.interview_language or "English",
                    "selected_skills": selected_skills,
                    "resume_skills": resume_skills,
                },
                questions_asked=questions_list,
                evaluations=existing_evals,
                adaptive_state=adaptive_state_dict,
                resume_profile=resume_profile_dict,
                retrieved_knowledge=retrieved_dicts,
                decision=next_decision,
            )

            # Deduplication validation
            candidate_q = next_q
            if candidate_q in questions_list or self.decision_engine.is_semantically_duplicate(candidate_q, questions_list):
                fallbacks = [
                    f"In {next_decision.next_skill} ({next_decision.next_topic}), how do you optimize for production performance and handle edge cases?",
                    f"Let's explore another aspect of {next_decision.next_skill} ({next_decision.next_topic}): how do you test and debug issues in production?",
                    f"When working with {next_decision.next_skill} ({next_decision.next_topic}), what architecture patterns prevent memory leaks and performance bottlenecks?",
                ]
                for fb in fallbacks:
                    if fb not in questions_list and not self.decision_engine.is_semantically_duplicate(fb, questions_list):
                        candidate_q = fb
                        break
            next_q = candidate_q

            questions_list.append(next_q)
            conv_history.append({"question": next_q})
            adaptive_state_dict.setdefault("questions_asked", []).append(next_q)
            session.questions = json.dumps(questions_list)

        # If all questions answered, mark session completed
        if session.answered_count >= session.question_count:
            session.status = "completed"
            session.completed_at = datetime.utcnow()

        session.adaptive_state = json.dumps(adaptive_state_dict)

        db.add(session)
        db.commit()

        return eval_dict

    def get_aggregated_evaluation(self, db: Session, session_id: int) -> Dict[str, Any]:
        """Aggregate all per-question evaluations into a final summary."""
        session = self._get_session(db, session_id)
        evals = json.loads(session.evaluations or '[]')

        if not evals:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No evaluations found for this interview session."
            )

        count = len(evals)

        avg_score = round(sum(e.get("score", 0) for e in evals) / count, 1)
        avg_correctness = round(sum(e.get("correctness", 0) for e in evals) / count, 3)
        avg_relevance = round(sum(e.get("relevance", 0) for e in evals) / count, 3)
        avg_technical_depth = round(sum(e.get("technical_depth", 0) for e in evals) / count, 3)
        avg_communication = round(sum(e.get("communication_quality", 0) for e in evals) / count, 3)

        # Collect all unique strengths and weaknesses
        all_strengths = []
        all_weaknesses = []
        all_feedback = []
        for e in evals:
            all_strengths.extend(e.get("strengths", []))
            all_weaknesses.extend(e.get("weaknesses", []))
            if e.get("feedback"):
                all_feedback.append(e["feedback"])

        # Deduplicate strengths/weaknesses
        unique_strengths = list(dict.fromkeys(all_strengths))
        unique_weaknesses = list(dict.fromkeys(all_weaknesses))

        adaptive_state = json.loads(session.adaptive_state or '{}')
        strong_topics = adaptive_state.get("strong_topics", [])
        weak_topics = adaptive_state.get("weak_topics", [])

        return {
            "session_id": session.id,
            "job_role": session.job_role,
            "interview_type": session.interview_type,
            "difficulty": session.difficulty,
            "question_count": session.question_count,
            "answered_count": session.answered_count or count,
            "status": session.status,
            "overall_score": avg_score,
            "overall_correctness": avg_correctness,
            "overall_relevance": avg_relevance,
            "overall_technical_depth": avg_technical_depth,
            "overall_communication_quality": avg_communication,
            "strengths": unique_strengths,
            "weaknesses": unique_weaknesses,
            "strong_topics": strong_topics,
            "weak_topics": weak_topics,
            "feedback": " | ".join(all_feedback) if all_feedback else "No feedback available.",
            "per_question_evaluations": evals,
        }

    def get_user_analytics(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Compute analytics across all interview sessions for a specific user.
        Returns a dict with overall statistics, performance breakdown, trends,
        strengths, weaknesses, and recent interview summaries.
        """
        # Fetch all sessions for the user
        sessions = db.query(InterviewSession).filter(InterviewSession.user_id == user_id).order_by(InterviewSession.created_at.desc()).all()
        total = len(sessions)
        completed_sessions = [s for s in sessions if s.status == "completed"]
        in_progress = len([s for s in sessions if s.status == "in_progress"])

        # Prepare aggregates for completed sessions
        scores = []
        correctness = []
        relevance = []
        technical = []
        communication = []
        strengths = []
        weaknesses = []
        trend = []
        recent = []

        for sess in completed_sessions:
            agg = self.get_aggregated_evaluation(db, sess.id)
            overall = agg.get("overall_score", 0)
            scores.append(overall)
            correctness.append(agg.get("overall_correctness", 0))
            relevance.append(agg.get("overall_relevance", 0))
            technical.append(agg.get("overall_technical_depth", 0))
            communication.append(agg.get("overall_communication_quality", 0))
            strengths.extend(agg.get("strengths", []))
            weaknesses.extend(agg.get("weaknesses", []))
            trend.append({"date": sess.created_at.isoformat(), "score": overall})
            recent.append({
                "id": sess.id,
                "job_role": sess.job_role,
                "interview_type": sess.interview_type,
                "difficulty": sess.difficulty,
                "score": overall,
                "status": sess.status,
                "date": sess.created_at.isoformat(),
            })

        trend.sort(key=lambda x: x["date"])
        recent = recent[:5]

        avg_score = round(sum(scores) / len(scores), 1) if scores else None
        best_score = max(scores) if scores else None
        latest_score = scores[0] if scores else None
        avg_correctness = round(sum(correctness) / len(correctness), 3) if correctness else None
        avg_relevance = round(sum(relevance) / len(relevance), 3) if relevance else None
        avg_technical = round(sum(technical) / len(technical), 3) if technical else None
        avg_communication = round(sum(communication) / len(communication), 3) if communication else None

        unique_strengths = list(dict.fromkeys(strengths))
        unique_weaknesses = list(dict.fromkeys(weaknesses))

        return {
            "total_interviews": total,
            "completed_interviews": len(completed_sessions),
            "in_progress_interviews": in_progress,
            "average_score": avg_score,
            "best_score": best_score,
            "latest_score": latest_score,
            "average_correctness": avg_correctness,
            "average_relevance": avg_relevance,
            "average_technical_depth": avg_technical,
            "average_communication_quality": avg_communication,
            "strengths": unique_strengths,
            "weaknesses": unique_weaknesses,
            "trend": trend,
            "recent_interviews": recent,
        }

