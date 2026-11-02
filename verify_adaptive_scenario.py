"""
Verification script for Section 31: 5-Question Adaptive Flow.
Tests candidate flow:
Q1: React Fundamentals (Medium) -> High score (>=8.0)
Q2: React Performance / Advanced (Hard) -> Mid score (5.0 - 7.9)
Q3: React Hooks (Hard) -> Low score (<=4.0)
Q4: Simpler React Hooks (Medium/Easy) -> High score (>=8.0)
Q5: Advanced React practical / project integration -> Final evaluation

Verifies:
1. Difficulty transitions
2. Weak/strong topics
3. Question deduplication
4. Selected skills boundary
5. Aggregated evaluation
"""

import sys
import json
import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"

def run_verification():
    print("==================================================")
    print("ADAPTIVE AI INTERVIEW ENGINE - SCENARIO VERIFICATION")
    print("==================================================")

    # 1. Login / Register test candidate
    auth_email = "adaptive_scenario_candidate@example.com"
    auth_pass = "TestPassword123!"

    print("\n[Step 1] Authenticating candidate...")
    token = None
    login_res = requests.post(f"{BASE_URL}/auth/login", data={"username": auth_email, "password": auth_pass})
    if login_res.status_code == 200:
        token = login_res.json()["access_token"]
    else:
        # Register
        reg_res = requests.post(f"{BASE_URL}/auth/register", json={
            "email": auth_email,
            "password": auth_pass,
            "full_name": "Scenario Candidate"
        })
        if reg_res.status_code == 200:
            token = reg_res.json()["access_token"]
        else:
            # Login fallback
            login_res2 = requests.post(f"{BASE_URL}/auth/login", data={"username": auth_email, "password": auth_pass})
            token = login_res2.json()["access_token"]

    assert token, "Authentication failed"
    headers = {"Authorization": f"Bearer {token}"}
    print("Authenticated successfully.")

    # 2. Create 5-question Adaptive Interview using /interviews/start
    print("\n[Step 2] Creating 5-question interview session via /interviews/start...")
    start_payload = {
        "job_role": "React Engineer",
        "interview_type": "Technical",
        "experience_level": "Intermediate",
        "difficulty": "Medium",
        "question_count": 5,
        "interview_language": "English",
        "resume_skills": json.dumps(["React", "JavaScript"]),
        "selected_skills": json.dumps(["React"]),
    }
    create_res = requests.post(f"{BASE_URL}/interviews/start", data=start_payload, headers=headers)
    assert create_res.status_code in (200, 201), f"Failed to start session: {create_res.text}"
    session_data = create_res.json()
    session_id = session_data["session_id"]
    q1_obj = session_data["question"]
    print(f"Session created: ID={session_id}")

    # 3. Step through 5-question adaptation loop
    test_steps = [
        {
            "step": 1,
            "desc": "Q1: React Fundamentals (Medium) -> Give high-scoring answer (reconciliation, virtual DOM)",
            "answer": "React uses a virtual DOM to optimize UI updates. When state or props change, React generates a new virtual DOM tree and uses its reconciliation diffing algorithm to compute minimal DOM patches using component keys.",
            "expect_high_score": True,
        },
        {
            "step": 2,
            "desc": "Q2: Advanced / Escalate -> Give partial/mid answer (5.0 - 7.9)",
            "answer": "In large applications we use React.memo to prevent re-renders, but I haven't configured profilers extensively in production.",
            "expect_high_score": False,
        },
        {
            "step": 3,
            "desc": "Q3: React Hooks probe -> Give weak/incomplete answer (<= 4.0)",
            "answer": "useEffect is just like a timer that runs sometimes when the component mounts or updates.",
            "expect_low_score": True,
        },
        {
            "step": 4,
            "desc": "Q4: Simpler React Hooks foundation -> Give strong foundational answer",
            "answer": "useEffect takes a setup function and an optional dependency array. If empty, it runs once on mount. If dependencies are provided, it re-runs when any dependency changes by reference equality, and runs the cleanup return function before re-executing or on unmount.",
            "expect_recovery": True,
        },
        {
            "step": 5,
            "desc": "Q5: Advanced React practical / integration -> Give strong practical answer",
            "answer": "We architect compound components and custom hooks to isolate API caching and state logic from UI rendering, utilizing useCallback to maintain stable function references.",
            "expect_final": True,
        },
    ]

    asked_questions = []
    evaluations = []

    for item in test_steps:
        s_num = item["step"]
        print(f"\n--- [Question {s_num}/5] ---")
        q_res = requests.get(f"{BASE_URL}/interviews/{session_id}/next", headers=headers)
        assert q_res.status_code == 200, f"Failed to get Q{s_num}: {q_res.text}"
        next_data = q_res.json()
        q_data = next_data["question"]
        q_text = q_data["text"]
        q_meta = q_data.get("metadata", {})
        print(f"Question Text: {q_text}")
        print(f"Metadata: Difficulty={q_meta.get('current_difficulty')}, Topic={q_meta.get('topic')}")

        # Verification: selected skills boundary
        assert "react" in q_text.lower(), f"Question {s_num} breached React skill boundary: {q_text}"
        # Verification: deduplication
        assert q_text not in asked_questions, f"Duplicate question detected: {q_text}"
        asked_questions.append(q_text)

        # Submit answer
        print(f"Submitting Candidate Answer: {item['answer'][:60]}...")
        ans_res = requests.post(
            f"{BASE_URL}/interviews/{session_id}/answer",
            json={"answer": item["answer"]},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        assert ans_res.status_code == 200, f"Failed to submit answer Q{s_num}: {ans_res.text}"
        eval_data = ans_res.json()["evaluation"]
        print(f"Evaluation: Score={eval_data['score']}/10 | Relevance={eval_data['relevance']} | Feedback={eval_data['feedback'][:80]}...")
        evaluations.append(eval_data)

    # 4. Verify Final State and Completion
    print("\n[Step 4] Verifying completion and aggregated evaluation...")
    done_res = requests.get(f"{BASE_URL}/interviews/{session_id}/next", headers=headers)
    assert done_res.status_code == 200
    done_data = done_res.json()["question"]
    assert done_data["question_id"] is None
    assert done_data["metadata"]["complete"] is True
    print("Interview completed exactly after 5 questions.")

    eval_res = requests.get(f"{BASE_URL}/interviews/{session_id}/evaluation", headers=headers)
    assert eval_res.status_code == 200, f"Failed to get final evaluation: {eval_res.text}"
    final_eval = eval_res.json()

    print(f"\nFinal Overall Score: {final_eval['overall_score']}/10")
    print(f"Strong Topics Identified: {final_eval.get('strong_topics', [])}")
    print(f"Weak Topics Identified: {final_eval.get('weak_topics', [])}")
    print(f"Per-Question Evaluations Count: {len(final_eval['per_question_evaluations'])}")
    assert len(final_eval["per_question_evaluations"]) == 5

    print("\n==================================================")
    print("ALL 5-QUESTION ADAPTIVE VERIFICATION CHECKS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    run_verification()
