import json
import sys
import requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://127.0.0.1:8000/api/v1"

print("\n" + "="*70)
print("SECTION 23: MANUAL VERIFICATION OF USERS A & B")
print("="*70)

import time
ts = int(time.time())

# 1. Register and Login User A
email_a = f"manual_user_a_{ts}@example.com"
pw_a = "PassA@1234"
requests.post(f"{BASE}/auth/register", json={"email": email_a, "password": pw_a, "full_name": "User A (React/Python)"})
res_login_a = requests.post(f"{BASE}/auth/login", data={"username": email_a, "password": pw_a})
token_a = res_login_a.json()["access_token"]
headers_a = {"Authorization": f"Bearer {token_a}"}

# Create User A's session: Weak React Hooks (e.g. score 4.2)
res_start_a = requests.post(f"{BASE}/interviews/start", data={
    "interview_type": "Technical",
    "job_role": "React Engineer",
    "experience_level": "Intermediate",
    "difficulty": "Medium",
    "question_count": 3,
    "resume_skills": json.dumps(["React", "Python"]),
    "selected_skills": json.dumps(["React"]),
}, headers=headers_a)
session_a_id = res_start_a.json()["session_id"]

# Answer Q1, Q2, Q3 with weak React Hooks answer
requests.post(f"{BASE}/interviews/{session_a_id}/answer", json={"answer": "I am not clear about useEffect dependency array and lifecycle."}, headers=headers_a)
requests.post(f"{BASE}/interviews/{session_a_id}/answer", json={"answer": "I do not use custom hooks and I get infinite loops."}, headers=headers_a)
requests.post(f"{BASE}/interviews/{session_a_id}/answer", json={"answer": "I don't know how useMemo or useCallback work."}, headers=headers_a)

# 2. Register and Login User B
email_b = f"manual_user_b_{ts}@example.com"
pw_b = "PassB@1234"
requests.post(f"{BASE}/auth/register", json={"email": email_b, "password": pw_b, "full_name": "User B (Java/Spring)"})
res_login_b = requests.post(f"{BASE}/auth/login", data={"username": email_b, "password": pw_b})
token_b = res_login_b.json()["access_token"]
headers_b = {"Authorization": f"Bearer {token_b}"}

# Create User B's session: Weak Spring Security (e.g. score 3.5)
res_start_b = requests.post(f"{BASE}/interviews/start", data={
    "interview_type": "Technical",
    "job_role": "Java Spring Developer",
    "experience_level": "Intermediate",
    "difficulty": "Medium",
    "question_count": 3,
    "resume_skills": json.dumps(["Java", "Spring"]),
    "selected_skills": json.dumps(["Spring"]),
}, headers=headers_b)
session_b_id = res_start_b.json()["session_id"]

# Answer Q1, Q2, Q3 with weak Spring Security answer
requests.post(f"{BASE}/interviews/{session_b_id}/answer", json={"answer": "Spring Security is too confusing, I don't know SecurityFilterChain."}, headers=headers_b)
requests.post(f"{BASE}/interviews/{session_b_id}/answer", json={"answer": "I don't know JWT filters or authentication managers."}, headers=headers_b)
requests.post(f"{BASE}/interviews/{session_b_id}/answer", json={"answer": "I struggle with Spring CORS and CSRF configurations."}, headers=headers_b)

# 3. Retrieve Coach Summary for User A
coach_a = requests.get(f"{BASE}/coach/summary", headers=headers_a).json()
print("\n--- USER A COACH SUMMARY ---")
print(f"Candidate: {email_a}")
print(f"Overall Score: {coach_a.get('overall_score')}/10")
print(f"Weak Topics: {[w['topic'] for w in coach_a.get('weak_topics', [])]}")
print(f"Recommended Interview: {coach_a.get('recommended_interview', {}).get('title')}")
print(f"Summary: {coach_a.get('summary')}")

# 4. Retrieve Coach Summary for User B
coach_b = requests.get(f"{BASE}/coach/summary", headers=headers_b).json()
print("\n--- USER B COACH SUMMARY ---")
print(f"Candidate: {email_b}")
print(f"Overall Score: {coach_b.get('overall_score')}/10")
print(f"Weak Topics: {[w['topic'] for w in coach_b.get('weak_topics', [])]}")
print(f"Recommended Interview: {coach_b.get('recommended_interview', {}).get('title')}")
print(f"Summary: {coach_b.get('summary')}")

# 5. Security & Isolation Assertions
user_a_sees_react_hooks = any("React Hooks" in w["topic"] or "React" in w["skill"] for w in coach_a.get("weak_topics", []))
user_b_sees_spring_sec = any("Spring Security" in w["topic"] or "Spring" in w["skill"] for w in coach_b.get("weak_topics", []))
user_a_sees_spring = "Spring" in str(coach_a)
user_b_sees_react = "React" in str(coach_b)

# User A tries to directly access User B's session
cross_session_req = requests.get(f"{BASE}/interviews/{session_b_id}", headers=headers_a)

print("\n--- PRACTICING & CHATTING (USER A) ---")
res_practice = requests.post(f"{BASE}/coach/practice-question", json={"topic": "React Hooks", "difficulty": "Medium"}, headers=headers_a)
practice_data = res_practice.json()
print(f"Practice Question: {practice_data.get('question')}")
print(f"Is Practice Question Valid: {'✅ YES' if practice_data.get('question') else '❌ NO'}")

res_chat = requests.post(f"{BASE}/coach/chat", json={"message": "What is my biggest weakness right now and how do I fix it?"}, headers=headers_a)
chat_data = res_chat.json()
print(f"Chat status: {res_chat.status_code}, Chat Data: {chat_data}")
print(f"Chat Response: {chat_data.get('response', chat_data.get('reply'))}")
print(f"Grounding Topic: {chat_data.get('grounding_topic')}")
print(f"Is Chat Response Valid: {'✅ YES' if chat_data.get('response') or chat_data.get('reply') else '❌ NO'}")

print("\n--- VERIFICATION RESULTS ---")
print(f"1. User A sees React Hooks recommendation: {'✅ YES' if user_a_sees_react_hooks else '❌ NO'}")
print(f"2. User B sees Spring Security recommendation: {'✅ YES' if user_b_sees_spring_sec else '❌ NO'}")
print(f"3. User A NEVER sees User B information: {'✅ SECURE (Spring not in A)' if not user_a_sees_spring else '❌ LEAK'}")
print(f"4. User B NEVER sees User A information: {'✅ SECURE (React not in B)' if not user_b_sees_react else '❌ LEAK'}")
print(f"5. Cross-User Direct Session Access: {'✅ 404 FORBIDDEN' if cross_session_req.status_code == 404 else '❌ LEAK'}")
print(f"6. Practice Question Generation: {'✅ SUCCESS' if practice_data.get('question') else '❌ FAIL'}")
print(f"7. Grounded Chat Response: {'✅ SUCCESS' if chat_data.get('response') else '❌ FAIL'}")
print("="*70 + "\n")
